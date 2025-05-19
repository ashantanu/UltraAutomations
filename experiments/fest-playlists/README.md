# Festival Playlist Generator

A Python script that automatically creates Spotify playlists from festival lineups and optionally creates matching YouTube playlists. This tool helps you discover and organize music from festival artists by creating playlists with their top tracks.

## Features

- Creates Spotify playlists from artist lists
- Optionally creates matching YouTube playlists with the same songs
- Supports creating YouTube playlists on specific channels by name
- Handles rate limiting and API errors gracefully
- Configurable number of tracks per artist
- Supports multiple markets/regions
- Batch processing for efficient playlist creation
- Clear separation between Spotify and YouTube operations
- Resume functionality to continue from where you left off
- YouTube API quota management to prevent hitting limits
- Progress tracking with JSON-based state management
- Uses Brave Search API for efficient video discovery
- Optimized YouTube API usage by only using it for playlist operations

## Prerequisites

- Python 3.7+
- Spotify Developer Account
- YouTube Data API credentials (optional, for YouTube playlist creation)
- Brave Search API key (for efficient video discovery)
- Required Python packages (see `requirements.txt`)

## Getting API Credentials

### Spotify API Setup

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and log in with your Spotify account

2. Click "Create App" and fill in the following:
   - App name: Choose any name (e.g., "Festival Playlist Generator")
   - App description: Brief description of your app
   - Website: Can be left blank for personal use
   - Redirect URI: Add `http://127.0.0.1:8888/callback`
   - Terms of Service: Accept the terms

3. After creating the app, you'll be taken to the app dashboard. Here you can find:
   - Client ID: Listed as "Client ID" on the dashboard
   - Client Secret: Click "Show Client Secret" to reveal it

4. Your Spotify Username:
   - Log into your Spotify account in a web browser
   - Go to your profile page
   - Your username is in the URL: `https://open.spotify.com/user/YOUR_USERNAME`

### YouTube API Setup (Optional)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3:
   - Go to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click "Enable"
4. Create credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" as the application type
   - Give it a name (e.g., "Festival Playlist Generator")
   - Click "Create"
5. Download the credentials:
   - Click the download icon (⬇️) next to your new OAuth client
   - Save the file as `youtube_credentials.json` in the project directory

### Brave Search API Setup

1. Go to [Brave Search API](https://brave.com/search/api/)
2. Sign up for an API key
3. Add the API key to your `.env` file:
```env
BRAVE_SEARCH_API_KEY=your_api_key
```

### YouTube Channel Name (Optional)

To create playlists on a specific YouTube channel:

1. Find the channel name you want to use
2. Add it to the script global var

If no channel name is specified or if the channel cannot be found, playlists will be created on the authenticated user's channel.

## Setup

1. Create a `.env` file in the project directory with your credentials:
```env
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
SPOTIPY_USERNAME=your_spotify_username
YOUTUBE_CHANNEL_NAME=channel_name  # Optional
BRAVE_SEARCH_API_KEY=your_api_key  # Required for video search
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Create an `artists.json` file with your festival lineup:
```json
[
    "Artist Name 1",
    "Artist Name 2",
    "Artist Name 3"
]
```

2. Configure the script parameters in `fest-playlists.py`:
```python
PLAYLIST_NAME = 'Your Festival Name - Day'
MAX_SONGS_PER_ARTIST = 5
MARKET = 'US'  # Change to your market code if needed
CREATE_YOUTUBE_PLAYLIST = True  # Set to False to skip YouTube playlist creation
```

3. Run the script:
```bash
python fest-playlists.py
```

The script will process in two distinct phases:

### Phase 1: Spotify Processing
- Search for each artist on Spotify
- Get their top tracks
- Create a new Spotify playlist (if not exists)
- Add only new tracks to the Spotify playlist
- Provide progress updates in the console
- Save progress to `playlist_progress.json`

### Phase 2: YouTube Processing (if enabled)
- Look up the specified channel name (if provided)
- Create a new YouTube playlist (if not exists)
  - If channel name is specified and found, creates the playlist on that channel
  - Otherwise, creates the playlist on the authenticated user's channel
- For each new track found on Spotify:
  - Use Brave Search API to find the corresponding video on YouTube
  - Add the video to the YouTube playlist using YouTube API
  - Track quota usage and progress
- Provide progress updates in the console
- Save progress to `playlist_progress.json`

## Progress and Quota Management

The script includes built-in progress tracking and quota management:

### Progress Tracking
- Saves progress in `playlist_progress.json`
- Tracks:
  - Created playlist IDs for both Spotify and YouTube
  - Processed tracks to avoid duplicates
  - Daily quota usage
  - Last reset date
- Automatically resumes from last position when run again
- Only processes new tracks that haven't been added before

### YouTube API Quota Management
- Tracks daily quota usage (default: 10,000 units)
- Operation costs:
  - Add to playlist: 50 units
  - Create playlist: 50 units
- Uses Brave Search API for video discovery (no YouTube quota cost)
- Automatically stops when quota limit is reached
- Resumes from last position when run again
- Resets quota counter daily
- Provides clear console output about quota usage

### Brave Search API Usage
- Used for efficient video discovery
- No quota impact on YouTube API
- Faster search results
- More reliable video matching
- Free tier available with generous limits

### Resuming Progress
If the script is interrupted or hits quota limits:
1. Progress is automatically saved in `playlist_progress.json`
2. Run the script again to continue from where it left off
3. Only new tracks will be processed
4. Existing playlists will be reused
5. Quota usage is tracked and respected
6. Clear console output shows progress and remaining quota

## Configuration

- `MAX_SONGS_PER_ARTIST`: Number of top tracks to include per artist (default: 5)
- `PLAYLIST_NAME`: Name of the generated playlists
- `MARKET`: Spotify market code for track availability (default: 'US')
- `SPOTIPY_REDIRECT_URI`: OAuth redirect URI (default: 'http://127.0.0.1:8888/callback')
- `CREATE_YOUTUBE_PLAYLIST`: Whether to create a matching YouTube playlist (default: True)
- `YOUTUBE_CHANNEL_NAME`: Optional channel name for YouTube playlist creation
- `DAILY_QUOTA_LIMIT`: Maximum daily YouTube API quota (default: 10,000 units)
- `BRAVE_SEARCH_API_KEY`: Your Brave Search API key

## Error Handling

The script includes robust error handling for:
- Rate limiting for both Spotify and YouTube APIs
- API errors and network issues
- Artist not found scenarios
- Video search failures (both Brave and YouTube)
- Authentication issues
- Channel not found errors
- Quota limit management
- Progress tracking and resume functionality
- Duplicate track prevention

## First Run Notes

- For Spotify: The first run will open a browser window for OAuth authentication
- For YouTube: The first run will:
  1. Open a browser window for OAuth authentication
  2. Save the authentication token for future use
  3. Create a `youtube_token.pickle` file in the project directory
  4. Create a `playlist_progress.json` file to track progress
  5. Initialize quota tracking
- For Brave Search: The first run will validate your API key

## License

MIT License