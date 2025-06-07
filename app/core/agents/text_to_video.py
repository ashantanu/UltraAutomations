import os
import uuid
import time
import shutil
from typing import TypedDict, Dict, Any, List, Tuple
from elevenlabs.client import ElevenLabs
from langgraph.graph import StateGraph, END
from openai import OpenAI
import base64
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from pathlib import Path
import tempfile
from pydub import AudioSegment
from app.utils.logging_utils import get_logger
from app.utils.config import config
from app.video import VideoProcessor, VideoInput, VideoConfig, AudioConfig
from app.core.agents.ai_news_summarizer import AUDIO_SCRIPT_ITEM_DELIMITER, AUDIO_SCRIPT_DELIMITER

# Global configuration for video processing
DEFAULT_VIDEO_CONFIG = VideoConfig(
    fps=24,
    video_bitrate='1000k',
    audio_bitrate='128k',
    min_free_space_gb=1.0,
    preset='ultrafast',
    threads=2
)

DEFAULT_AUDIO_CONFIG = AudioConfig(
    main_audio_volume=1.0,
    background_music_volume=0.025
)

# Get background music path from config
BACKGROUND_MUSIC_PATH = config.background_music_path

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

logger = get_logger(__name__)

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


def generate_segmented_audio(
    text: str,
    section_pause_duration_ms: int = 1000,
    item_pause_duration_ms: int = 500
) -> str:
    """
    Generate audio from a segmented script with pauses between sections and items.

    Args:
        text: The script text to convert to audio
        section_pause_duration_ms: Duration of pause between major sections (opening/items/closing) in milliseconds
        item_pause_duration_ms: Duration of pause between individual items in milliseconds

    Returns:
        str: Path to the generated audio file
    """
    logger.info("Starting segmented audio generation...")
    start_time = time.time()

    # Split the script into segments
    segments = text.split(AUDIO_SCRIPT_DELIMITER)
    if len(segments) != 3:
        raise ValueError("Script must contain exactly two '===' separators")

    opening, items, closing = segments

    # Process items into a list
    items = [item.strip() for item in items.split(
        AUDIO_SCRIPT_ITEM_DELIMITER) if item.strip()]

    # Create a temporary directory for intermediate files
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_segments: List[AudioSegment] = []

        # Generate audio for opening
        opening_audio = _generate_single_segment(
            opening.strip(), temp_dir, "opening")
        audio_segments.append(opening_audio)

        # Add section pause after opening
        audio_segments.append(AudioSegment.silent(
            duration=section_pause_duration_ms))

        # Generate audio for each item
        for i, item in enumerate(items):
            item_audio = _generate_single_segment(item, temp_dir, f"item_{i}")
            audio_segments.append(item_audio)
            # Add item pause after each item except the last one
            if i < len(items) - 1:
                audio_segments.append(AudioSegment.silent(
                    duration=item_pause_duration_ms))

        # Add section pause before closing
        audio_segments.append(AudioSegment.silent(
            duration=section_pause_duration_ms))

        # Generate audio for closing
        closing_audio = _generate_single_segment(
            closing.strip(), temp_dir, "closing")
        audio_segments.append(closing_audio)

        # Combine all segments
        final_audio = sum(audio_segments)

        # Save the final audio
        output_filename = f"{str(config.output_dir)}/{uuid.uuid4()}.mp3"
        final_audio.export(output_filename, format="mp3")

        duration = time.time() - start_time
        logger.info(
            f"Segmented audio generation completed in {duration:.2f} seconds")
        return output_filename


def _generate_single_segment(text: str, temp_dir: str, segment_name: str) -> AudioSegment:
    """Helper function to generate audio for a single text segment."""
    temp_audio_path = os.path.join(temp_dir, f"{segment_name}.mp3")

    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="sage",
        input=text,
        instructions=langfuse_client.get_prompt(PROMPT_NAME).prompt,
    ) as response:
        response.stream_to_file(temp_audio_path)

    return AudioSegment.from_mp3(temp_audio_path)


def text_to_audio(state: AudioState) -> AudioState:
    start_time = time.time()
    logger.info("Starting text-to-audio conversion...")
    text = state["text"]

    try:
        # Use the new segmented audio generation function
        audio_filename = generate_segmented_audio(text)
        state["audio_filepath"] = audio_filename

        duration = time.time() - start_time
        logger.info(
            f"Text-to-audio conversion completed in {duration:.2f} seconds")
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


def create_video(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a video from audio and image using the modular video processor.

    Args:
        state: Dictionary containing audio_filepath and image_filepath

    Returns:
        Updated state dictionary with video_filepath

    Raises:
        Various exceptions with detailed error context
    """
    start_time = time.time()
    logger.info("Starting video creation...")

    try:
        # Extract paths from state
        audio_path = state["audio_filepath"]
        image_path = state["image_filepath"]
        video_filename = f"data/{uuid.uuid4()}.mp4"
        logger.info(f"Generating video filename: {video_filename}")

        # Create video processor with default configurations
        processor = VideoProcessor(
            video_config=DEFAULT_VIDEO_CONFIG,
            audio_config=DEFAULT_AUDIO_CONFIG
        )

        # Prepare input data
        logger.info(f"Background music file path: {BACKGROUND_MUSIC_PATH}")
        logger.info(
            f"Background music file exists: {os.path.exists(BACKGROUND_MUSIC_PATH)}")

        input_data = VideoInput(
            main_audio_path=Path(audio_path),
            image_path=Path(image_path),
            output_path=Path(video_filename),
            background_music_path=Path(BACKGROUND_MUSIC_PATH) if os.path.exists(
                BACKGROUND_MUSIC_PATH) else None
        )

        # Process the video
        result = processor.create_video(input_data)

        if not result.success:
            raise RuntimeError(result.error)

        # Verify the output file was created and has content
        if not os.path.exists(video_filename):
            raise OSError("Video file was not created")
        if os.path.getsize(video_filename) == 0:
            raise OSError("Video file was created but is empty")

        # Update state with video path
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
            "data_dir": os.path.dirname(video_filename) if 'video_filename' in locals() else None,
            "free_space_gb": shutil.disk_usage(os.path.dirname(video_filename)).free / (1024*1024*1024)
            if 'video_filename' in locals() and os.path.exists(os.path.dirname(video_filename)) else None,
            "background_music_path": BACKGROUND_MUSIC_PATH,
            "background_music_exists": os.path.exists(BACKGROUND_MUSIC_PATH) if BACKGROUND_MUSIC_PATH else False,
            "video_config": DEFAULT_VIDEO_CONFIG.dict(),
            "audio_config": DEFAULT_AUDIO_CONFIG.dict()
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
        result = app.invoke({"text": input_text}, config={
                            "callbacks": [langfuse_handler]})
        logger.info(
            f"Pipeline completed successfully. Video ID: {result.get('youtube_video_id', 'N/A')}")
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        raise
