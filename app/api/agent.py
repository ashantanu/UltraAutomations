from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.core.agents.text_to_youtube import text_to_youtube
from app.core.agents.ai_news_summarizer import generate_ai_news_summary
from app.core.agents.email_to_youtube import email_to_youtube
from typing import Optional
import os
from datetime import datetime
from app.utils.date_utils import get_pst_date

router = APIRouter(tags=["agent"])

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
    Endpoint to convert text to video and upload to YouTube.
    
    Args:
        request (YouTubeUploadRequest): The request containing text, title, and description
        
    Returns:
        dict: A dictionary containing the result of the operation
    """
    try:
        result = text_to_youtube(
            text=request.text,
            title=request.title,
            description=request.description,
            thumbnail_path=request.thumbnail_path
        )
        return {
            "status": "success",
            "message": "Video uploaded successfully",
            "data": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@router.post("/news-summary")
async def news_summary():
    """
    Endpoint to generate daily AI news summary.
    
    Returns:
        dict: A dictionary containing the summary and metadata
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
        return {
            "status": "error",
            "message": str(e)
        }

@router.post("/email-to-youtube")
async def email_to_youtube_endpoint(request: EmailToYouTubeRequest = None):
    """
    Endpoint to generate a YouTube video from email summaries.
    
    Args:
        request (EmailToYouTubeRequest, optional): The request containing the date to process.
            If not provided, defaults to the last 24 hours.
    
    Returns:
        dict: A dictionary containing the summary and video details
    """
    try:
        result = await email_to_youtube(date=request.date if request else None)
        return {
            "status": "success",
            "message": "Email-to-YouTube flow completed successfully",
            "data": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        } 


@router.post("/email-availability")
async def email_availability_endpoint(request: EmailAvailabilityRequest):
    """
    Dry-run endpoint: probes Gmail and returns counts/samples for the configured sources.
    Does not call OpenAI, does not generate video.
    """
    try:
        from app.core.agents.ai_news_summarizer import probe_email_availability

        report = probe_email_availability(
            target_date=request.date,
            max_results=request.max_results,
        )
        return {
            "status": "success",
            "data": {
                "total_found": sum(item.get("count", 0) for item in report),
                "by_source": report,
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }