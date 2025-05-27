import os
import uuid
import logging
import time
import shutil
from typing import TypedDict
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from langgraph.graph import StateGraph, END
from moviepy.editor import ImageClip, AudioFileClip
from openai import OpenAI
import base64
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Setup your API keys
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID")
VOICE_ID = "kPzsL2i3teMYv0FxEYQ6"
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST")
PROMPT_NAME = "news-summary-tts-instructions"

# Initialize Langfuse callback handler
langfuse_handler = CallbackHandler(
    secret_key=LANGFUSE_SECRET_KEY,
    public_key=LANGFUSE_PUBLIC_KEY,
    host=LANGFUSE_HOST
)

langfuse_client = Langfuse(
    public_key=LANGFUSE_PUBLIC_KEY,
    secret_key=LANGFUSE_SECRET_KEY,
    host=LANGFUSE_HOST
)


logger.info("Initializing API clients...")
# Initialize clients
eleven_client = ElevenLabs(api_key=ELEVEN_LABS_API_KEY)
client = OpenAI(organization=OPENAI_ORG_ID)


# --- Define the state ---
class AudioState(TypedDict):
    text: str
    audio_filepath: str
    image_filepath: str
    video_filepath: str
    youtube_video_id: str

# --- Step 1: Turn text into audio ---
def text_to_audio(state: AudioState) -> AudioState:
    start_time = time.time()
    logger.info("Starting text-to-audio conversion...")
    text = state["text"]
    audio_filename = f"data/{uuid.uuid4()}.mp3"
    logger.info(f"Generated audio filename: {audio_filename}")

    try:
        logger.info("Calling ElevenLabs API...")
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="sage",
            input=text,
            instructions=langfuse_client.get_prompt(PROMPT_NAME),
        ) as response:
            response.stream_to_file(audio_filename)
        # response = eleven_client.text_to_speech.convert(
        #     text=text,
        #     voice_id=VOICE_ID,
        #     model_id="eleven_flash_v2_5",
        #     output_format="mp3_44100_128",
        #     voice_settings=VoiceSettings(
        #         stability=0.5,
        #         similarity_boost=0.5
        #     ),
        # )

        # logger.info("Writing audio file...")
        # with open(audio_filename, "wb") as f:
        #     for chunk in response:
        #         if chunk:
        #             f.write(chunk)

        state["audio_filepath"] = audio_filename
        duration = time.time() - start_time
        logger.info(f"Text-to-audio conversion completed in {duration:.2f} seconds")
        return state
    except Exception as e:
        logger.error(f"Error in text_to_audio: {str(e)}", exc_info=True)
        raise

# --- Step 2: Generate image using DALL-E ---
def generate_image(state: AudioState) -> AudioState:
    start_time = time.time()
    if not state.get('image_filepath') is None:
        logger.info("Image filepath already present. no need to generate")
        return state
    logger.info("Starting image generation...")
    text = state["text"]
    image_filename = f"{uuid.uuid4()}.png"
    logger.info(f"Generating image filename: {image_filename}")

    try:
        logger.info("Calling OpenAI API...")
        img = client.images.generate(
            model="gpt-image-1",
            prompt=text,
            n=1,
            size="1024x1024"
        )

        logger.info("Downloading generated image...")
        image_data = base64.b64decode(img.data[0].b64_json)


        logger.info("Writing image file...")
        with open(image_filename, "wb") as f:
            f.write(image_data)

        state["image_filepath"] = image_filename
        duration = time.time() - start_time
        logger.info(f"Image generation completed in {duration:.2f} seconds")
        return state
    except Exception as e:
        logger.error(f"Error in generate_image: {str(e)}", exc_info=True)
        raise

# --- Step 3: Create video from image and audio ---
def create_video(state: AudioState) -> AudioState:
    start_time = time.time()
    logger.info("Starting video creation...")
    audio_path = state["audio_filepath"]
    image_path = state["image_filepath"]
    video_filename = f"data/{uuid.uuid4()}.mp4"
    logger.info(f"Generating video filename: {video_filename}")

    try:
        # Check if data directory exists and is writable
        data_dir = os.path.dirname(video_filename)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
        if not os.access(data_dir, os.W_OK):
            raise PermissionError(f"No write permission for directory: {data_dir}")

        # Check input files
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Check available disk space (require at least 1GB free)
        free_space = shutil.disk_usage(data_dir).free
        if free_space < 1024 * 1024 * 1024:  # 1GB in bytes
            raise OSError(f"Insufficient disk space. Only {free_space / (1024*1024*1024):.2f}GB available")

        logger.info("Loading audio and image clips...")
        audio_clip = AudioFileClip(audio_path)
        image_clip = ImageClip(image_path).set_duration(audio_clip.duration)
        image_clip = image_clip.set_audio(audio_clip)

        logger.info("Writing video file...")
        # Use more memory-efficient settings
        image_clip.write_videofile(
            video_filename,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            preset='ultrafast',  # Faster encoding, less memory usage
            threads=2,  # Limit thread usage
            bitrate='1000k',  # Lower bitrate for smaller file size
            audio_bitrate='128k',  # Lower audio bitrate
            verbose=True,
            logger=None,  # Disable MoviePy's logger to avoid duplicate messages
            ffmpeg_params=[
                '-max_muxing_queue_size', '1024',  # Increase queue size
                '-thread_queue_size', '512',  # Increase thread queue
                '-max_error_rate', '0.1',  # Allow some errors
                '-err_detect', 'ignore_err',  # Ignore non-critical errors
                '-max_interleave_delta', '0',  # Reduce interleaving
                '-vsync', '0',  # Disable video sync
                '-async', '1'  # Enable audio sync
            ]
        )

        # Verify the output file was created and has content
        if not os.path.exists(video_filename):
            raise OSError("Video file was not created")
        if os.path.getsize(video_filename) == 0:
            raise OSError("Video file was created but is empty")

        state["video_filepath"] = video_filename
        duration = time.time() - start_time
        logger.info(f"Video creation completed in {duration:.2f} seconds")
        return state
    except Exception as e:
        logger.error(f"Error in create_video: {str(e)}", exc_info=True)
        # Add additional context to the error
        error_context = {
            "error": str(e),
            "audio_path": audio_path,
            "image_path": image_path,
            "video_filename": video_filename,
            "data_dir": data_dir,
            "free_space_gb": shutil.disk_usage(data_dir).free / (1024*1024*1024) if 'data_dir' in locals() else None,
            "audio_duration": audio_clip.duration if 'audio_clip' in locals() else None,
            "image_size": os.path.getsize(image_path) if os.path.exists(image_path) else None
        }
        logger.error(f"Error context: {error_context}")
        raise

# --- Build LangGraph ---
logger.info("Building LangGraph...")
graph = StateGraph(AudioState)

# Add nodes to the graph
graph.add_node("generate_audio", text_to_audio)
graph.add_node("generate_image", generate_image)
graph.add_node("create_video", create_video)

# Define edges
graph.set_entry_point("generate_audio")
graph.add_edge("generate_audio", "generate_image")
graph.add_edge("generate_image", "create_video")
graph.add_edge("create_video", END)

# Compile the graph
logger.info("Compiling LangGraph...")
app = graph.compile()

# --- Run the agent ---
if __name__ == "__main__":
    logger.info("Starting pipeline execution...")
    input_text = "Hello! This is a sample text converted into a video and uploaded to YouTube."

    try:
        # Create a new trace for this run
        result = app.invoke({"text": input_text}, config={"callbacks": [langfuse_handler]})
        logger.info(f"Pipeline completed successfully. Video ID: {result.get('youtube_video_id', 'N/A')}")
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        raise