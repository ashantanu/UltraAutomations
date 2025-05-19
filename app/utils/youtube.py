import os
import logging
from typing import Optional, Dict, Any, List
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configure logging
logging.basicConfig(
    filename='youtube_upload.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class YouTubeUploader:
    def __init__(self):
        """Initialize the YouTube uploader using environment variables."""
        self.youtube = None
        self.credentials = None
        self._load_config()

    def _load_config(self) -> bool:
        """Load configuration from environment variables."""
        try:
            # Get credentials from environment variables
            refresh_token = os.getenv('YOUTUBE_REFRESH_TOKEN')
            client_id = os.getenv('YOUTUBE_CLIENT_ID')
            client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')

            if not all([refresh_token, client_id, client_secret]):
                missing = []
                if not refresh_token: missing.append('YOUTUBE_REFRESH_TOKEN')
                if not client_id: missing.append('YOUTUBE_CLIENT_ID')
                if not client_secret: missing.append('YOUTUBE_CLIENT_SECRET')
                logger.error(f"Missing required environment variables: {', '.join(missing)}")
                return False

            self.credentials = Credentials(
                None,  # No access token initially
                refresh_token=refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=client_id,
                client_secret=client_secret,
                scopes=['https://www.googleapis.com/auth/youtube.upload',
                       'https://www.googleapis.com/auth/youtube']
            )
            return True
        except Exception as e:
            logger.error(f"Failed to load config from environment: {str(e)}")
            return False

    def authenticate(self) -> bool:
        """Authenticate with YouTube API using refresh token."""
        try:
            if not self.credentials:
                if not self._load_config():
                    return False

            # Refresh the token if needed
            if not self.credentials.valid:
                self.credentials.refresh(Request())

            self.youtube = build('youtube', 'v3', credentials=self.credentials)
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False

    def get_playlist_id(self, playlist_name: str) -> Optional[str]:
        """
        Get the playlist ID for a given playlist name.
        
        Args:
            playlist_name: Name of the playlist to find
            
        Returns:
            Playlist ID if found, None otherwise
        """
        if not self.youtube:
            if not self.authenticate():
                return None

        try:
            # Get all playlists for the authenticated user
            request = self.youtube.playlists().list(
                part="snippet",
                mine=True,
                maxResults=50
            )
            response = request.execute()

            # Search for the playlist by name
            for item in response.get("items", []):
                if item["snippet"]["title"].lower() == playlist_name.lower():
                    return item["id"]

            logger.warning(f"Playlist '{playlist_name}' not found")
            return None

        except Exception as e:
            logger.error(f"Failed to get playlist ID: {str(e)}")
            return None

    def create_playlist(self, title: str, description: str = "", privacy_status: str = "private") -> Optional[str]:
        """
        Create a new playlist.
        
        Args:
            title: Title of the playlist
            description: Description of the playlist
            privacy_status: Privacy status of the playlist (private, unlisted, or public)
            
        Returns:
            Playlist ID if created successfully, None otherwise
        """
        if not self.youtube:
            if not self.authenticate():
                return None

        try:
            body = {
                "snippet": {
                    "title": title,
                    "description": description
                },
                "status": {
                    "privacyStatus": privacy_status
                }
            }

            request = self.youtube.playlists().insert(
                part="snippet,status",
                body=body
            )
            response = request.execute()
            playlist_id = response["id"]
            logger.info(f"Created playlist '{title}' with ID: {playlist_id}")
            return playlist_id

        except Exception as e:
            logger.error(f"Failed to create playlist: {str(e)}")
            return None

    def add_video_to_playlist(self, video_id: str, playlist_id: str) -> bool:
        """
        Add a video to a playlist.
        
        Args:
            video_id: ID of the video to add
            playlist_id: ID of the playlist to add the video to
            
        Returns:
            True if successful, False otherwise
        """
        if not self.youtube:
            if not self.authenticate():
                return False

        try:
            body = {
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }

            request = self.youtube.playlistItems().insert(
                part="snippet",
                body=body
            )
            request.execute()
            logger.info(f"Added video {video_id} to playlist {playlist_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add video to playlist: {str(e)}")
            return False

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        category_id: str = "22",  # People & Blogs
        privacy_status: str = "private",
        tags: Optional[list] = None,
        thumbnail_path: Optional[str] = None,
        playlist_name: Optional[str] = None,
        create_playlist_if_not_exists: bool = False
    ) -> Dict[str, Any]:
        """
        Upload a video to YouTube and optionally add it to a playlist.
        
        Args:
            video_path: Path to the video file
            title: Video title
            description: Video description
            category_id: Video category ID (default: 22 for People & Blogs)
            privacy_status: Video privacy status (private, unlisted, or public)
            tags: List of tags for the video
            thumbnail_path: Path to the thumbnail image (optional)
            playlist_name: Name of the playlist to add the video to (optional)
            create_playlist_if_not_exists: Whether to create the playlist if it doesn't exist
            
        Returns:
            Dict containing the upload response or error information
        """
        if not self.youtube:
            if not self.authenticate():
                return {"error": "Failed to authenticate with YouTube"}

        try:
            # Upload the video first
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags or [],
                    'categoryId': category_id
                },
                'status': {
                    'privacyStatus': privacy_status,
                    'selfDeclaredMadeForKids': False
                }
            }

            media = MediaFileUpload(
                video_path,
                mimetype='video/*',
                resumable=True
            )

            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            logger.info(f"Starting upload of video: {title}")
            response = request.execute()
            video_id = response.get('id')

            # Upload thumbnail if provided
            if thumbnail_path and video_id:
                try:
                    self.youtube.thumbnails().set(
                        videoId=video_id,
                        media_body=MediaFileUpload(thumbnail_path)
                    ).execute()
                    logger.info(f"Thumbnail uploaded for video: {video_id}")
                except Exception as e:
                    logger.warning(f"Failed to upload thumbnail: {str(e)}")

            # Add to playlist if specified
            playlist_id = None
            if playlist_name and video_id:
                playlist_id = self.get_playlist_id(playlist_name)
                
                if not playlist_id and create_playlist_if_not_exists:
                    playlist_id = self.create_playlist(
                        title=playlist_name,
                        description=f"Playlist for {playlist_name}",
                        privacy_status=privacy_status
                    )
                
                if playlist_id:
                    if self.add_video_to_playlist(video_id, playlist_id):
                        logger.info(f"Added video to playlist: {playlist_name}")
                    else:
                        logger.warning(f"Failed to add video to playlist: {playlist_name}")

            logger.info(f"Successfully uploaded video: {video_id}")
            return {
                "success": True,
                "video_id": video_id,
                "playlist_id": playlist_id,
                "response": response
            }

        except Exception as e:
            error_msg = f"Failed to upload video: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

def upload_video_to_youtube(
    video_path: str,
    title: str,
    description: str,
    privacy_status: str = "private",
    tags: Optional[list] = None,
    thumbnail_path: Optional[str] = None,
    playlist_name: Optional[str] = None,
    create_playlist_if_not_exists: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to upload a video to YouTube using environment variables.
    
    Args:
        video_path: Path to the video file
        title: Video title
        description: Video description
        privacy_status: Video privacy status (private, unlisted, or public)
        tags: List of tags for the video
        thumbnail_path: Path to the thumbnail image (optional)
        playlist_name: Name of the playlist to add the video to (optional)
        create_playlist_if_not_exists: Whether to create the playlist if it doesn't exist
        
    Returns:
        Dict containing the upload response or error information
    """
    uploader = YouTubeUploader()
    return uploader.upload_video(
        video_path=video_path,
        title=title,
        description=description,
        privacy_status=privacy_status,
        tags=tags,
        thumbnail_path=thumbnail_path,
        playlist_name=playlist_name,
        create_playlist_if_not_exists=create_playlist_if_not_exists
    ) 