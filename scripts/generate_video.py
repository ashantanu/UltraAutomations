#!/usr/bin/env python3
"""
Simplified Video Generation Pipeline

This script generates a video from text input (or email) and optionally uploads to YouTube.
It replaces the complex LangGraph-based approach with a simple, linear pipeline.

Usage:
    # From text input:
    python scripts/generate_video.py --text "Your script here" --title "Video Title"
    
    # From email (daily AI news summary):
    python scripts/generate_video.py --from-email --upload
    
    # With custom thumbnail:
    python scripts/generate_video.py --text "Script" --title "Title" --thumbnail path/to/image.png
"""

import os
import sys
import uuid
import time
import argparse
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from dotenv import load_dotenv
from pydub import AudioSegment
from openai import OpenAI

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logging_utils import get_logger
from app.utils.config import config
from app.utils.youtube import upload_video_to_youtube
from app.utils.image_utils import add_text_overlay
from app.video import VideoProcessor, VideoInput, VideoConfig, AudioConfig

load_dotenv()
logger = get_logger(__name__)

# --- Configuration ---

AUDIO_SCRIPT_DELIMITER = "==="
AUDIO_SCRIPT_ITEM_DELIMITER = "<item>"

VIDEO_CONFIG = VideoConfig(
    fps=24,
    video_bitrate='1000k',
    audio_bitrate='128k',
    min_free_space_gb=1.0,
    preset='ultrafast',
    threads=2
)

AUDIO_CONFIG = AudioConfig(
    main_audio_volume=1.0,
    background_music_volume=0.025
)


@dataclass
class VideoResult:
    """Result of video generation pipeline."""
    success: bool
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    youtube_video_id: Optional[str] = None
    youtube_url: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


# =============================================================================
# STEP 1: Text-to-Speech Audio Generation
# =============================================================================

def generate_audio_segment(text: str, output_dir: str, segment_name: str) -> AudioSegment:
    """Generate audio for a single text segment using OpenAI TTS."""
    client = OpenAI()
    temp_path = os.path.join(output_dir, f"{segment_name}.mp3")
    
    # Get TTS instructions from Langfuse if available
    instructions = "Speak clearly and naturally with a professional tone."
    try:
        from langfuse import Langfuse
        langfuse = Langfuse()
        prompt = langfuse.get_prompt("news-summary-tts-instructions")
        if prompt:
            instructions = prompt.prompt
    except Exception:
        pass  # Use default instructions
    
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="sage",
        input=text,
        instructions=instructions,
    ) as response:
        response.stream_to_file(temp_path)
    
    return AudioSegment.from_mp3(temp_path)


def generate_audio(
    text: str,
    output_path: Optional[str] = None,
    section_pause_ms: int = 1000,
    item_pause_ms: int = 500
) -> str:
    """
    Generate audio from text with pauses between sections.
    
    Supports structured scripts with delimiters:
        Opening text
        ===
        <item> Item 1
        <item> Item 2
        ===
        Closing text
    
    Or plain text (no delimiters).
    
    Returns: Path to generated audio file.
    """
    logger.info("🎙️ Generating audio from text...")
    start = time.time()
    
    output_path = output_path or f"{config.output_dir}/{uuid.uuid4()}.mp3"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        segments = []
        
        # Check if text has structured format
        if AUDIO_SCRIPT_DELIMITER in text:
            parts = text.split(AUDIO_SCRIPT_DELIMITER)
            if len(parts) == 3:
                opening, items_text, closing = parts
                
                # Generate opening
                segments.append(generate_audio_segment(opening.strip(), temp_dir, "opening"))
                segments.append(AudioSegment.silent(duration=section_pause_ms))
                
                # Generate items
                items = [i.strip() for i in items_text.split(AUDIO_SCRIPT_ITEM_DELIMITER) if i.strip()]
                for i, item in enumerate(items):
                    segments.append(generate_audio_segment(item, temp_dir, f"item_{i}"))
                    if i < len(items) - 1:
                        segments.append(AudioSegment.silent(duration=item_pause_ms))
                
                # Generate closing
                segments.append(AudioSegment.silent(duration=section_pause_ms))
                segments.append(generate_audio_segment(closing.strip(), temp_dir, "closing"))
            else:
                # Fallback to single segment
                segments.append(generate_audio_segment(text, temp_dir, "full"))
        else:
            # Plain text - single segment
            segments.append(generate_audio_segment(text, temp_dir, "full"))
        
        # Combine and export
        final_audio = sum(segments)
        final_audio.export(output_path, format="mp3")
    
    logger.info(f"✅ Audio generated in {time.time() - start:.1f}s: {output_path}")
    return output_path


# =============================================================================
# STEP 2: Thumbnail Generation
# =============================================================================

def generate_thumbnail(
    template_path: Optional[str] = None,
    output_path: Optional[str] = None
) -> str:
    """
    Generate a YouTube thumbnail from template.
    
    Returns: Path to generated thumbnail.
    """
    logger.info("🖼️ Generating thumbnail...")
    
    template_path = template_path or config.template_thumbnail_path
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Thumbnail template not found: {template_path}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_path or f"{config.output_dir}/thumbnail_{timestamp}.png"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    add_text_overlay(template_path, output_path)
    
    logger.info(f"✅ Thumbnail generated: {output_path}")
    return output_path


# =============================================================================
# STEP 3: Video Creation
# =============================================================================

def create_video(
    audio_path: str,
    image_path: str,
    output_path: Optional[str] = None,
    background_music_path: Optional[str] = None
) -> str:
    """
    Create video from audio and static image.
    
    Returns: Path to generated video.
    """
    logger.info("🎬 Creating video...")
    start = time.time()
    
    output_path = output_path or f"{config.output_dir}/{uuid.uuid4()}.mp4"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Use configured background music if available
    if background_music_path is None:
        bg_path = config.background_music_path
        if bg_path and os.path.exists(bg_path):
            background_music_path = str(bg_path)
    
    processor = VideoProcessor(
        video_config=VIDEO_CONFIG,
        audio_config=AUDIO_CONFIG
    )
    
    input_data = VideoInput(
        main_audio_path=Path(audio_path),
        image_path=Path(image_path),
        output_path=Path(output_path),
        background_music_path=Path(background_music_path) if background_music_path else None
    )
    
    result = processor.create_video(input_data)
    
    if not result.success:
        raise RuntimeError(f"Video creation failed: {result.error}")
    
    logger.info(f"✅ Video created in {time.time() - start:.1f}s: {output_path}")
    return output_path


# =============================================================================
# STEP 4: YouTube Upload
# =============================================================================

def upload_to_youtube(
    video_path: str,
    title: str,
    description: str,
    thumbnail_path: Optional[str] = None,
    playlist_name: Optional[str] = None,
    privacy_status: str = "public"
) -> dict:
    """
    Upload video to YouTube.
    
    Returns: Upload result with video_id and url.
    """
    logger.info("📤 Uploading to YouTube...")
    start = time.time()
    
    result = upload_video_to_youtube(
        video_path=video_path,
        title=title,
        description=description,
        privacy_status=privacy_status,
        thumbnail_path=thumbnail_path,
        playlist_name=playlist_name or config.youtube_playlist_name,
        create_playlist_if_not_exists=config.create_playlist_if_not_exists
    )
    
    if not result.get("success"):
        raise RuntimeError(f"YouTube upload failed: {result.get('error')}")
    
    video_id = result["video_id"]
    logger.info(f"✅ Uploaded in {time.time() - start:.1f}s: https://youtube.com/watch?v={video_id}")
    
    return {
        "video_id": video_id,
        "url": f"https://youtube.com/watch?v={video_id}",
        "playlist_id": result.get("playlist_id")
    }


# =============================================================================
# STEP 5 (Optional): Fetch & Summarize Email
# =============================================================================

async def fetch_and_summarize_email(target_date: Optional[datetime] = None) -> dict:
    """
    Fetch emails and generate AI summary.
    
    Returns: Dict with title, audio_script, and description.
    """
    logger.info("📧 Fetching and summarizing emails...")
    
    # Import here to avoid loading heavy dependencies when not needed
    from app.core.agents.ai_news_summarizer import generate_ai_news_summary
    
    result = await generate_ai_news_summary(date=target_date)
    
    if not result or not result.summary:
        raise RuntimeError("Failed to generate email summary")
    
    return {
        "title": result.summary.title,
        "audio_script": result.summary.audio_script,
        "description": result.summary.description
    }


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def generate_video_pipeline(
    text: str,
    title: str,
    description: str = "",
    thumbnail_path: Optional[str] = None,
    upload: bool = False,
    generate_new_thumbnail: bool = True
) -> VideoResult:
    """
    Main video generation pipeline.
    
    Steps:
        1. Generate TTS audio from text
        2. Generate or use provided thumbnail
        3. Create video from audio + thumbnail
        4. (Optional) Upload to YouTube
    
    Returns: VideoResult with paths and status.
    """
    start = time.time()
    logger.info("🚀 Starting video generation pipeline...")
    logger.info(f"   Title: {title}")
    
    try:
        # Step 1: Generate audio
        audio_path = generate_audio(text)
        
        # Step 2: Get thumbnail
        if thumbnail_path and os.path.exists(thumbnail_path):
            final_thumbnail = thumbnail_path
        elif generate_new_thumbnail:
            final_thumbnail = generate_thumbnail()
        else:
            raise ValueError("No thumbnail provided and generate_new_thumbnail=False")
        
        # Step 3: Create video
        video_path = create_video(
            audio_path=audio_path,
            image_path=final_thumbnail
        )
        
        # Step 4: Upload if requested
        youtube_result = None
        if upload:
            youtube_result = upload_to_youtube(
                video_path=video_path,
                title=title,
                description=description or f"Generated video: {title}",
                thumbnail_path=final_thumbnail
            )
        
        duration = time.time() - start
        logger.info(f"🎉 Pipeline complete in {duration:.1f}s")
        
        return VideoResult(
            success=True,
            video_path=video_path,
            audio_path=audio_path,
            thumbnail_path=final_thumbnail,
            youtube_video_id=youtube_result["video_id"] if youtube_result else None,
            youtube_url=youtube_result["url"] if youtube_result else None,
            duration_seconds=duration
        )
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
        return VideoResult(
            success=False,
            error=str(e),
            duration_seconds=time.time() - start
        )


async def email_to_video_pipeline(
    upload: bool = True,
    target_date: Optional[datetime] = None
) -> VideoResult:
    """
    Full pipeline from email to YouTube video.
    
    Steps:
        1. Fetch emails and generate AI summary
        2. Generate TTS audio
        3. Generate thumbnail
        4. Create video
        5. Upload to YouTube
    """
    logger.info("🚀 Starting email-to-video pipeline...")
    
    try:
        # Step 1: Fetch and summarize
        summary = await fetch_and_summarize_email(target_date)
        
        # Run main pipeline
        return generate_video_pipeline(
            text=summary["audio_script"],
            title=summary["title"],
            description=summary["description"],
            upload=upload
        )
        
    except Exception as e:
        logger.error(f"❌ Email pipeline failed: {e}", exc_info=True)
        return VideoResult(success=False, error=str(e))


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate video from text or email",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from text (no upload):
  python generate_video.py --text "Hello world" --title "Test Video"
  
  # Generate from text and upload:
  python generate_video.py --text "Hello world" --title "Test" --upload
  
  # Generate from email summary:
  python generate_video.py --from-email --upload
  
  # Use custom thumbnail:
  python generate_video.py --text "Script" --title "Title" --thumbnail image.png
        """
    )
    
    # Input source (mutually exclusive)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", type=str, help="Text/script to convert to video")
    source.add_argument("--from-email", action="store_true", help="Fetch from email and summarize")
    
    # Video metadata
    parser.add_argument("--title", type=str, help="Video title (required for --text)")
    parser.add_argument("--description", type=str, default="", help="Video description")
    parser.add_argument("--thumbnail", type=str, help="Path to thumbnail image")
    
    # Options
    parser.add_argument("--upload", action="store_true", help="Upload to YouTube")
    parser.add_argument("--date", type=str, help="Target date for email (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    # Validate
    if args.text and not args.title:
        parser.error("--title is required when using --text")
    
    # Run pipeline
    if args.from_email:
        import asyncio
        target_date = datetime.fromisoformat(args.date) if args.date else None
        result = asyncio.run(email_to_video_pipeline(
            upload=args.upload,
            target_date=target_date
        ))
    else:
        result = generate_video_pipeline(
            text=args.text,
            title=args.title,
            description=args.description,
            thumbnail_path=args.thumbnail,
            upload=args.upload
        )
    
    # Print result
    if result.success:
        print(f"\n✅ Success!")
        print(f"   Video: {result.video_path}")
        if result.youtube_url:
            print(f"   YouTube: {result.youtube_url}")
        print(f"   Duration: {result.duration_seconds:.1f}s")
    else:
        print(f"\n❌ Failed: {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()

