# YouTube Video Uploader

A Python utility for uploading videos to YouTube and managing playlists. This module provides a simple interface to upload videos, create playlists, and add videos to playlists using the YouTube Data API v3.

## Features

- Upload videos to YouTube with custom titles, descriptions, and tags
- Support for video thumbnails
- Create and manage playlists
- Add videos to existing playlists
- Automatic playlist creation if it doesn't exist
- Comprehensive error handling and logging
- OAuth 2.0 authentication with automatic token refresh
- Resumable uploads for large files
- FastAPI endpoints for easy integration

## API Endpoints

### Upload Video
```http
POST /youtube/upload
```

Upload a video to YouTube with optional playlist and thumbnail support.

**Form Parameters:**
- `video` (required): The video file to upload
- `title` (required): Title of the video
- `description` (required): Description of the video
- `privacy_status` (optional): Privacy status (private, unlisted, or public). Defaults to "private"
- `tags` (optional): Comma-separated list of tags
- `playlist_name` (optional): Name of the playlist to add the video to
- `create_playlist` (optional): Whether to create the playlist if it doesn't exist. Defaults to false
- `thumbnail` (optional): Thumbnail image for the video

**Response:**
```json
{
    "message": "Video uploaded successfully",
    "video_id": "youtube_video_id",
    "video_url": "https://www.youtube.com/watch?v=youtube_video_id",
    "playlist_id": "youtube_playlist_id"  // Only if playlist was specified
}
```

### List Playlists
```http
GET /youtube/playlists
```

List all playlists for the authenticated user.

**Response:**
```json
{
    "playlists": [
        {
            "id": "playlist_id",
            "title": "Playlist Title",
            "description": "Playlist Description",
            "thumbnail": "thumbnail_url"
        }
    ]
}
```

## Server-Side Setup

For server environments where manual browser authentication isn't possible, follow these steps:

1. **Initial Setup (One-time, on your local machine)**:
   - Follow the Google Cloud Console setup steps below
   - Run the token generation script:
     ```bash
     python scripts/get_youtube_token.py
     ```
   - This will:
     - Open a browser window for one-time authentication
     - Generate a refresh token
     - Save server configuration to `server_youtube_config.json`

2. **Server Configuration**:
   - Copy `server_youtube_config.json` to your server
   - Keep this file secure and never commit it to version control
   - The file contains:
     ```json
     {
       "refresh_token": "your_refresh_token",
       "client_id": "your_client_id",
       "client_secret": "your_client_secret",
       "token_uri": "https://oauth2.googleapis.com/token"
     }
     ```

3. **Environment Variables** (Optional):
   - Instead of using the config file, you can set these environment variables:
     ```bash
     YOUTUBE_REFRESH_TOKEN=your_refresh_token
     YOUTUBE_CLIENT_ID=your_client_id
     YOUTUBE_CLIENT_SECRET=your_client_secret
     ```

## Google Cloud Console Setup

1. **Create a Google Cloud Project**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the YouTube Data API v3:
     - Navigate to "APIs & Services" > "Library"
     - Search for "YouTube Data API v3"
     - Click "Enable"

2. **Configure OAuth Consent Screen**:
   - In Google Cloud Console, go to "APIs & Services" > "OAuth consent screen"
   - Choose "External" user type
   - Fill in the required information:
     - App name
     - User support email
     - Developer contact information
   - Add the following scopes:
     - `https://www.googleapis.com/auth/youtube.upload`
     - `https://www.googleapis.com/auth/youtube`
   - Add your email as a test user
   - Save and continue

3. **Create OAuth Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Web application" as the application type
   - Add these authorized redirect URIs:
     - `http://localhost:8080`
     - `http://localhost:8080/oauth2callback`
   - Name your credentials (e.g., "YouTube Uploader")
   - Click "Create"
   - Download the credentials JSON file
   - Rename it to `client_secrets.json`
   - Place it in your project's root directory

## Usage

### Using cURL

#### Upload a Video
```bash
# Basic upload
curl -X POST http://your-server/youtube/upload \
  -F "video=@/path/to/video.mp4" \
  -F "title=My Video Title" \
  -F "description=Video description" \
  -F "privacy_status=private"

# Upload with all options
curl -X POST http://your-server/youtube/upload \
  -F "video=@/path/to/video.mp4" \
  -F "title=My Video Title" \
  -F "description=Video description" \
  -F "privacy_status=private" \
  -F "tags=tag1,tag2,tag3" \
  -F "playlist_name=My Playlist" \
  -F "create_playlist=true" \
  -F "thumbnail=@/path/to/thumbnail.jpg"
```

#### List Playlists
```bash
curl -X GET http://your-server/youtube/playlists
```

### Using the FastAPI Endpoints

```python
import requests

# Upload a video
files = {
    'video': ('video.mp4', open('video.mp4', 'rb')),
    'thumbnail': ('thumbnail.jpg', open('thumbnail.jpg', 'rb'))  # Optional
}

data = {
    'title': 'My Video Title',
    'description': 'Video description',
    'privacy_status': 'private',
    'tags': 'tag1,tag2,tag3',
    'playlist_name': 'My Playlist',
    'create_playlist': 'true'
}

response = requests.post('http://your-server/youtube/upload', files=files, data=data)
print(response.json())

# List playlists
response = requests.get('http://your-server/youtube/playlists')
print(response.json())
```

### Server-Side Usage

```python
from app.utils.youtube import upload_video_to_youtube

# Using config file
result = upload_video_to_youtube(
    video_path="path/to/your/video.mp4",
    title="My Video Title",
    description="Video description",
    config_path="server_youtube_config.json",  # Path to your server config
    privacy_status="private"
)

# Or using environment variables
import os
os.environ['YOUTUBE_REFRESH_TOKEN'] = 'your_refresh_token'
os.environ['YOUTUBE_CLIENT_ID'] = 'your_client_id'
os.environ['YOUTUBE_CLIENT_SECRET'] = 'your_client_secret'

result = upload_video_to_youtube(
    video_path="path/to/your/video.mp4",
    title="My Video Title",
    description="Video description"
)
```

### Basic Video Upload

```python
from app.utils.youtube import upload_video_to_youtube

result = upload_video_to_youtube(
    video_path="path/to/your/video.mp4",
    title="My Video Title",
    description="Video description",
    privacy_status="private"  # or "public" or "unlisted"
)

if result["success"]:
    print(f"Video uploaded successfully! Video ID: {result['video_id']}")
else:
    print(f"Upload failed: {result['error']}")
```

### Upload with Playlist

```python
result = upload_video_to_youtube(
    video_path="path/to/your/video.mp4",
    title="My Video Title",
    description="Video description",
    playlist_name="My Playlist",
    create_playlist_if_not_exists=True,
    privacy_status="private"
)

if result["success"]:
    print(f"Video uploaded successfully!")
    print(f"Video ID: {result['video_id']}")
    if result.get("playlist_id"):
        print(f"Added to playlist with ID: {result['playlist_id']}")
```

### Testing

A test script is provided in `test_youtube_upload.py`. To use it:

1. Edit the script to set your video path and other parameters
2. Run the test:
```bash
python test_youtube_upload.py
```

## Parameters

The `upload_video_to_youtube` function accepts the following parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| video_path | str | Yes | Path to the video file |
| title | str | Yes | Video title |
| description | str | Yes | Video description |
| client_secrets_file | str | No | Path to OAuth credentials (default: 'client_secrets.json') |
| privacy_status | str | No | Video privacy status: 'private', 'public', or 'unlisted' (default: 'private') |
| tags | list | No | List of tags for the video |
| thumbnail_path | str | No | Path to the thumbnail image |
| playlist_name | str | No | Name of the playlist to add the video to |
| create_playlist_if_not_exists | bool | No | Whether to create the playlist if it doesn't exist (default: False) |

## Logging

All upload activities are logged to `youtube_upload.log` with the following format:
```
%(asctime)s - %(levelname)s - %(message)s
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify that `client_secrets.json` is in the correct location
   - Ensure you've enabled the YouTube Data API v3
   - Check that your email is added as a test user
   - Delete `token.pickle` and try again

2. **Upload Failed**
   - Check `youtube_upload.log` for detailed error messages
   - Verify the video file exists and is in a supported format
   - Ensure you have sufficient quota for the YouTube API
   - Check your internet connection

3. **Playlist Issues**
   - Verify you have the correct playlist name
   - Check that you have permission to modify the playlist
   - Ensure the playlist exists if `create_playlist_if_not_exists` is False

### Getting Help

If you encounter any issues:
1. Check the `youtube_upload.log` file for detailed error messages
2. Verify your Google Cloud Console settings
3. Ensure all required dependencies are installed
4. Check your OAuth consent screen configuration

## Security Notes

- Never commit `client_secrets.json`, `server_youtube_config.json`, or `token.pickle` to version control
- Keep your OAuth credentials and refresh tokens secure
- Use private videos for testing
- Regularly review and revoke unused OAuth tokens
- Consider using environment variables instead of config files on production servers
- Rotate refresh tokens periodically for better security

## API Quotas

Be aware of YouTube Data API quotas:
- Each project has a daily quota limit
- Video uploads consume quota
- Monitor your usage in the Google Cloud Console

## License

This project is licensed under the MIT License - see the LICENSE file for details. 