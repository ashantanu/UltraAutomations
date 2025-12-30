from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import logging
import sys
from pathlib import Path

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from app.utils.date_utils import get_pst_date
from app.core.agents.ai_news_summarizer import generate_ai_news_summary, probe_email_availability

router = APIRouter(tags=["agent"])
logger = logging.getLogger(__name__)


class YouTubeUploadRequest(BaseModel):
    text: str
    title: str
    description: str
    thumbnail_path: Optional[str] = None


class EmailToYouTubeRequest(BaseModel):
    date: Optional[datetime] = Field(
        default_factory=get_pst_date,
        description="The date to process emails for. Defaults to today's PST date."
    )


class EmailAvailabilityRequest(BaseModel):
    date: Optional[datetime] = Field(
        default=None,
        description="If provided, checks for emails on that PST date. If omitted, checks last 24 hours."
    )
    max_results: int = Field(default=3, ge=1, le=20)


@router.post("/text-to-youtube")
async def youtube_upload(request: YouTubeUploadRequest):
    """
    Convert text to video and upload to YouTube.
    """
    try:
        from generate_video import generate_video_pipeline
        
        result = generate_video_pipeline(
            text=request.text,
            title=request.title,
            description=request.description,
            thumbnail_path=request.thumbnail_path,
            upload=True
        )
        
        if not result.success:
            raise Exception(result.error)
        
        return {
            "status": "success",
            "message": "Video uploaded successfully",
            "data": {
                "video_path": result.video_path,
                "youtube_video_id": result.youtube_video_id,
                "youtube_video_url": result.youtube_url,
            }
        }
    except Exception as e:
        logger.error(f"text-to-youtube failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/news-summary")
async def news_summary():
    """
    Generate daily AI news summary from emails.
    """
    try:
        result = await generate_ai_news_summary()
        return {
            "status": "success",
            "message": "News summary generated successfully",
            "data": {
                "date": result.date.isoformat(),
                "emails_processed": result.emails_processed,
                "summary": {
                    "title": result.summary.title,
                    "audio_script": result.summary.audio_script,
                    "description": result.summary.description,
                }
            }
        }
    except Exception as e:
        logger.error(f"news-summary failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/email-to-youtube")
async def email_to_youtube_endpoint(request: EmailToYouTubeRequest = None):
    """
    Generate a YouTube video from email summaries.
    """
    try:
        from generate_video import email_to_video_pipeline
        
        result = await email_to_video_pipeline(
            upload=True,
            target_date=request.date if request else None
        )
        
        if not result.success:
            raise Exception(result.error)
        
        return {
            "status": "success",
            "message": "Email-to-YouTube flow completed successfully",
            "data": {
                "video_path": result.video_path,
                "youtube_video_id": result.youtube_video_id,
                "youtube_url": result.youtube_url,
                "duration_seconds": result.duration_seconds
            }
        }
    except Exception as e:
        logger.error(f"email-to-youtube failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/email-availability")
async def email_availability_endpoint(request: EmailAvailabilityRequest):
    """
    Dry-run: probe Gmail for email counts without generating video.
    """
    try:
        report = probe_email_availability(
            target_date=request.date,
            max_results=request.max_results,
        )
        total_found = sum(item.get("count", 0) for item in report)
        logger.info(
            "Email availability check: date=%s total=%s",
            request.date.isoformat() if request.date else None,
            total_found,
        )
        return {
            "status": "success",
            "data": {
                "total_found": total_found,
                "by_source": report,
            },
        }
    except Exception as e:
        logger.error(f"email-availability failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
        }
