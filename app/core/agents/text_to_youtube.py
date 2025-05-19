import os
import logging
from datetime import datetime
from app.utils.youtube import upload_video_to_youtube
from langfuse.decorators import observe
from app.core.agents.text_to_video import app as text_to_video_app
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('text-to-youtube.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@observe(name="text_to_youtube_flow")
def text_to_youtube(text: str,
                    title: str,
                    description: str,
                    thumbnail_path: Optional[str] = None,
                    playlist_name: Optional[str] = None,
                    create_playlist_if_not_exists: bool = False
                    ):
    """
    Combines text-to-video generation with YouTube upload in a single flow.
    
    Args:
        text (str): The text to convert into a video
        title (str): The title for the YouTube video
        description (str): The description for the YouTube video
        thumbnail_path (str, optional): Path to the thumbnail image
    
    Returns:
        dict: A dictionary containing the result of the operation
    """
    start_time = datetime.now()
    logger.info("🎬 STARTING TEXT-TO-YOUTUBE FLOW 🎬")
    logger.info(f"Input text: {text}")
    logger.info(f"Video title: {title}")
    
    try:
        # Step 1: Generate video from text
        logger.info("Step 1: Generating video from text...")
        video_result = text_to_video_app.invoke({
            "text": text,
            "image_filepath": thumbnail_path
            })
        video_path = video_result["video_filepath"]
        
        # Step 2: Upload to YouTube
        logger.info("Step 2: Uploading to YouTube...")
        upload_result = upload_video_to_youtube(
            video_path=video_path,
            title=title,
            description=description,
            privacy_status="private",  # Default to private for safety
            thumbnail_path=thumbnail_path,  # Pass through the thumbnail
            playlist_name=playlist_name,
            create_playlist_if_not_exists=create_playlist_if_not_exists
        )
        
        if not upload_result["success"]:
            raise Exception(f"YouTube upload failed: {upload_result['error']}")
        
        logger.info("🎉 Text-to-YouTube flow completed successfully!")
        return {
            "status": "success",
            "video_path": video_path,
            "title": title,
            "description": description,
            "youtube_video_id": upload_result["video_id"],
            "youtube_video_url": f"https://www.youtube.com/watch?v={upload_result['video_id']}",
            "upload_details": upload_result
        }
    except Exception as e:
        logger.error(f"❌ Text-to-YouTube flow failed: {e}")
        raise
    finally:
        duration = datetime.now() - start_time
        logger.info(f"⏱️ Total time: {duration.total_seconds():.2f} seconds")
