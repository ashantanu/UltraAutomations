from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, List
import os
import tempfile
import shutil
from app.utils.youtube import upload_video_to_youtube

router = APIRouter(prefix="/youtube", tags=["youtube"])

async def cleanup_temp_file(file_path: str):
    """Clean up temporary file after upload."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning up temp file {file_path}: {str(e)}")

@router.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(...),
    privacy_status: str = Form("private"),
    tags: Optional[str] = Form(None),
    playlist_name: Optional[str] = Form(None),
    create_playlist: bool = Form(False),
    thumbnail: Optional[UploadFile] = File(None)
):
    """
    Upload a video to YouTube.
    
    - **video**: The video file to upload
    - **title**: Title of the video
    - **description**: Description of the video
    - **privacy_status**: Privacy status (private, unlisted, or public)
    - **tags**: Comma-separated list of tags
    - **playlist_name**: Name of the playlist to add the video to
    - **create_playlist**: Whether to create the playlist if it doesn't exist
    - **thumbnail**: Optional thumbnail image for the video
    
    Returns:
        JSONResponse with:
        - message: Success message
        - video_id: The YouTube video ID
        - video_url: The complete YouTube URL for the video
        - playlist_id: The playlist ID (if a playlist was created/used)
    """
    # Create temporary files for video and thumbnail
    temp_video = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video.filename)[1])
    temp_thumbnail = None
    
    try:
        # Save video file
        shutil.copyfileobj(video.file, temp_video)
        temp_video.close()
        
        # Save thumbnail if provided
        if thumbnail:
            temp_thumbnail = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(thumbnail.filename)[1])
            shutil.copyfileobj(thumbnail.file, temp_thumbnail)
            temp_thumbnail.close()
        
        # Process tags
        tag_list = tags.split(',') if tags else None
        
        # Upload to YouTube
        result = upload_video_to_youtube(
            video_path=temp_video.name,
            title=title,
            description=description,
            privacy_status=privacy_status,
            tags=tag_list,
            thumbnail_path=temp_thumbnail.name if temp_thumbnail else None,
            playlist_name=playlist_name,
            create_playlist_if_not_exists=create_playlist
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Construct video URL
        video_url = f"https://www.youtube.com/watch?v={result['video_id']}"
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Video uploaded successfully",
                "video_id": result["video_id"],
                "video_url": video_url,
                "playlist_id": result.get("playlist_id")
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Clean up temporary files
        background_tasks.add_task(cleanup_temp_file, temp_video.name)
        if temp_thumbnail:
            background_tasks.add_task(cleanup_temp_file, temp_thumbnail.name)

@router.get("/playlists")
async def list_playlists():
    """List all playlists for the authenticated user."""
    try:
        from app.utils.youtube import YouTubeUploader
        uploader = YouTubeUploader()
        if not uploader.authenticate():
            raise HTTPException(status_code=401, detail="Failed to authenticate with YouTube")
            
        request = uploader.youtube.playlists().list(
            part="snippet",
            mine=True,
            maxResults=50
        )
        response = request.execute()
        
        playlists = [
            {
                "id": item["id"],
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],
                "thumbnail": item["snippet"]["thumbnails"]["default"]["url"]
            }
            for item in response.get("items", [])
        ]
        
        return JSONResponse(
            status_code=200,
            content={"playlists": playlists}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
