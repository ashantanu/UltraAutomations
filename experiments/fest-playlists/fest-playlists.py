import os
import json
import time
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
import datetime
import requests
from urllib.parse import quote_plus

load_dotenv()

# === Step 1: Setup ===
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
USERNAME = os.getenv("SPOTIPY_USERNAME")
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")

SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:8888/callback'
MAX_SONGS_PER_ARTIST = 5
PLAYLIST_NAME = 'OutsideLands 2025 - Friday'
MARKET = 'US'
CREATE_YOUTUBE_PLAYLIST = True  # Set to False to skip YouTube playlist creation
YOUTUBE_CHANNEL_NAME = "OneForAllPlaylists"  # Optional: channel name for playlist creation

# YouTube API setup
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
YOUTUBE_CREDENTIALS_FILE = 'youtube_credentials.json'
YOUTUBE_TOKEN_FILE = 'youtube_token.pickle'
PROGRESS_FILE = 'playlist_progress.json'
ARTIST_LIST_FILE = "artists.json"

# Quota management
YOUTUBE_DAILY_QUOTA = 10000  # YouTube's default daily quota
YOUTUBE_QUOTA_PER_PLAYLIST_ITEM = 50  # Cost of adding item to playlist
YOUTUBE_QUOTA_PER_PLAYLIST_CREATE = 50  # Cost of creating playlist

# Brave Search API setup
BRAVE_SEARCH_API_URL = "https://api.search.brave.com/res/v1/web/search"
BRAVE_SEARCH_HEADERS = {
    "Accept": "application/json",
    "X-Subscription-Token": BRAVE_SEARCH_API_KEY
}

# === Progress Tracking ===
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {
        'spotify_playlist_id': None,
        'youtube_playlist_id': None,
        'processed_tracks': [],
        'quota_used': 0,
        'last_reset': datetime.datetime.now().strftime('%Y-%m-%d')
    }

def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def check_quota_limit(progress, operation_cost):
    # Check if we need to reset daily quota
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    if progress['last_reset'] != today:
        progress['quota_used'] = 0
        progress['last_reset'] = today
        save_progress(progress)
    
    # Check if we have enough quota
    if progress['quota_used'] + operation_cost > YOUTUBE_DAILY_QUOTA:
        print(f"⚠️ Daily quota limit reached. Used: {progress['quota_used']}/{YOUTUBE_DAILY_QUOTA}")
        return False
    return True

def update_quota_usage(progress, operation_cost):
    progress['quota_used'] += operation_cost
    save_progress(progress)

# === Spotify Functions ===
def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        scope='playlist-modify-public',
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        username=USERNAME
    ))

def handle_spotify_rate_limits(func, *args, **kwargs):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get("Retry-After", 5))
                print(f"⏳ Spotify rate limit hit. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                print(f"❌ Spotify API error: {e}")
                break
        except Exception as e:
            print(f"⚠️ Unexpected error: {e}")
            time.sleep(2)
    return None

def get_artist_id(sp, artist_name):
    results = handle_spotify_rate_limits(sp.search, q=artist_name, type='artist', limit=1)
    items = results.get('artists', {}).get('items', []) if results else []
    if items:
        return items[0]['id']
    print(f"❌ Artist not found: {artist_name}")
    return None

def get_top_tracks(sp, artist_id, market='US'):
    result = handle_spotify_rate_limits(sp.artist_top_tracks, artist_id, country=market)
    if not result:
        return []
    
    tracks = []
    for track in result['tracks'][:MAX_SONGS_PER_ARTIST]:
        tracks.append({
            'uri': track['uri'],
            'name': track['name'],
            'artist': track['artists'][0]['name']
        })
    return tracks

def create_spotify_playlist(sp, user_id, name):
    playlist = handle_spotify_rate_limits(sp.user_playlist_create, user=user_id, name=name, public=True)
    if playlist:
        print(f"✅ Spotify playlist created: {playlist['external_urls']['spotify']}")
        return playlist['id']
    raise Exception("🚫 Failed to create Spotify playlist")

def add_tracks_to_spotify_playlist(sp, playlist_id, track_uris):
    for i in range(0, len(track_uris), 100):
        handle_spotify_rate_limits(sp.playlist_add_items, playlist_id, track_uris[i:i + 100])

# === YouTube Functions ===
def get_youtube_client():
    creds = None
    if os.path.exists(YOUTUBE_TOKEN_FILE):
        with open(YOUTUBE_TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                YOUTUBE_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(YOUTUBE_TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('youtube', 'v3', credentials=creds)

def get_channel_id(youtube, channel_name=None):
    """Get channel ID from channel name or return authenticated user's channel ID."""
    try:
        if channel_name:
            # Search for channel by name
            response = youtube.search().list(
                q=channel_name,
                type='channel',
                part='id',
                maxResults=1
            ).execute()
            
            if response['items']:
                channel_id = response['items'][0]['id']['channelId']
                print(f"✅ Found channel ID for: {channel_name}")
                return channel_id
            print(f"❌ Channel not found: {channel_name}")
            return None
        else:
            # Get authenticated user's channel ID
            response = youtube.channels().list(
                part='id',
                mine=True
            ).execute()
            
            if response['items']:
                return response['items'][0]['id']
            print("❌ Could not find authenticated user's channel")
            return None
    except HttpError as e:
        print(f"❌ YouTube API error: {e}")
        return None

def create_youtube_playlist(youtube, title, channel_id=None):
    try:
        playlist_body = {
            "snippet": {
                "title": title,
                "description": f"Playlist created from festival lineup: {title}"
            },
            "status": {
                "privacyStatus": "public"
            }
        }
        
        # If channel ID is provided, add it to the playlist creation request
        if channel_id:
            playlist_body["snippet"]["channelId"] = channel_id
        
        playlist_response = youtube.playlists().insert(
            part="snippet,status",
            body=playlist_body
        ).execute()
        
        print(f"✅ YouTube playlist created: {playlist_response['id']}")
        return playlist_response['id']
    except HttpError as e:
        print(f"❌ YouTube API error: {e}")
        return None

def search_youtube_video(query):
    """Search for a YouTube video using Brave Search API."""
    try:
        # Construct search query to find YouTube videos
        search_query = f"site:youtube.com/watch {query} official"
        encoded_query = quote_plus(search_query)
        
        # Make request to Brave Search API
        response = requests.get(
            BRAVE_SEARCH_API_URL,
            headers=BRAVE_SEARCH_HEADERS,
            params={
                "q": search_query,
                "count": 1,
                "safesearch": "moderate"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('web', {}).get('results'):
                # Extract video ID from YouTube URL
                video_url = data['web']['results'][0]['url']
                if 'youtube.com/watch?v=' in video_url:
                    video_id = video_url.split('v=')[1].split('&')[0]
                    return video_id
        return None
    except Exception as e:
        print(f"❌ Brave Search error: {e}")
        return None

def add_video_to_youtube_playlist(youtube, playlist_id, video_id):
    try:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        ).execute()
        return True
    except HttpError as e:
        print(f"❌ YouTube add video error: {e}")
        return False

# === Main Workflow ===
def build_artist_playlist(artist_names):
    progress = load_progress()
    
    # Step 1: Process Spotify
    print("\n=== Processing Spotify ===")
    sp = get_spotify_client()
    all_tracks = []
    
    # Get all tracks from Spotify
    for artist in artist_names:
        print(f"🎤 Processing: {artist}")
        artist_id = get_artist_id(sp, artist)
        if artist_id:
            tracks = get_top_tracks(sp, artist_id, market=MARKET)
            if tracks:
                print(f"🎵 Found {len(tracks)} tracks for {artist}")
                all_tracks.extend(tracks)
    
    # Create and populate Spotify playlist
    if all_tracks:
        if not progress['spotify_playlist_id']:
            progress['spotify_playlist_id'] = create_spotify_playlist(sp, USERNAME, PLAYLIST_NAME)
            add_tracks_to_spotify_playlist(sp, progress['spotify_playlist_id'], [track['uri'] for track in all_tracks])
            print(f"🎧 Added {len(all_tracks)} tracks to Spotify playlist.")
            save_progress(progress)
    else:
        print("❌ No tracks found to add to Spotify playlist.")
        return

    # Step 2: Process YouTube (if enabled)
    if CREATE_YOUTUBE_PLAYLIST:
        print("\n=== Processing YouTube ===")
        try:
            youtube = get_youtube_client()
            
            # Get channel ID if channel name is specified
            channel_id = None
            if YOUTUBE_CHANNEL_NAME:
                print(f"🎯 Looking up channel: {YOUTUBE_CHANNEL_NAME}")
                channel_id = get_channel_id(youtube, YOUTUBE_CHANNEL_NAME)
                if not channel_id:
                    print("⚠️ Proceeding with authenticated user's channel")
            
            # Create or get existing YouTube playlist
            if not progress['youtube_playlist_id']:
                if check_quota_limit(progress, YOUTUBE_QUOTA_PER_PLAYLIST_CREATE):
                    progress['youtube_playlist_id'] = create_youtube_playlist(youtube, PLAYLIST_NAME, channel_id)
                    update_quota_usage(progress, YOUTUBE_QUOTA_PER_PLAYLIST_CREATE)
                    save_progress(progress)
                else:
                    print("⚠️ Skipping YouTube playlist creation due to quota limits")
                    return
            
            if progress['youtube_playlist_id']:
                # Process only new tracks
                new_tracks = [track for track in all_tracks if track['uri'] not in progress['processed_tracks']]
                for track in new_tracks:
                    if not check_quota_limit(progress, YOUTUBE_QUOTA_PER_PLAYLIST_ITEM):
                        print("⚠️ Reached daily quota limit. Progress saved. Run again tomorrow.")
                        break
                    
                    search_query = f"{track['artist']} - {track['name']}"
                    video_id = search_youtube_video(search_query)
                    
                    if video_id:
                        if add_video_to_youtube_playlist(youtube, progress['youtube_playlist_id'], video_id):
                            print(f"✅ Added to YouTube playlist: {track['name']}")
                            progress['processed_tracks'].append(track['uri'])
                            update_quota_usage(progress, YOUTUBE_QUOTA_PER_PLAYLIST_ITEM)
                            save_progress(progress)
                        time.sleep(1)  # Respect YouTube API rate limits
                    else:
                        print(f"⚠️ Could not find YouTube video for: {track['name']}")
                        progress['processed_tracks'].append(track['uri'])  # Mark as processed even if not found
                        save_progress(progress)
        except Exception as e:
            print(f"⚠️ Failed to process YouTube playlist: {e}")
            save_progress(progress)

# === Input List ===
with open(ARTIST_LIST_FILE, "r") as f:
    artists = json.load(f)

# === Run ===
if __name__ == "__main__":
    build_artist_playlist(artists)
