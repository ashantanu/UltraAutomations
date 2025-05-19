import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube'
]

def get_refresh_token():
    """Get a refresh token and save it for server use."""
    creds = None
    
    # Load existing token if available
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials available, let's get a new one
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Use web application flow instead of desktop
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json',
                SCOPES,
                redirect_uri='http://localhost:8080'  # This URL doesn't need to be real
            )
            creds = flow.run_local_server(port=8080)

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Print the environment variables for server use
    if creds and creds.refresh_token:
        print("\n=== IMPORTANT: Add these environment variables to your server ===")
        print(f"export YOUTUBE_REFRESH_TOKEN='{creds.refresh_token}'")
        print(f"export YOUTUBE_CLIENT_ID='{creds.client_id}'")
        print(f"export YOUTUBE_CLIENT_SECRET='{creds.client_secret}'")
        print("=============================================================\n")
        
        # Also save to a .env file for convenience
        with open('.env.youtube', 'w') as f:
            f.write(f"YOUTUBE_REFRESH_TOKEN={creds.refresh_token}\n")
            f.write(f"YOUTUBE_CLIENT_ID={creds.client_id}\n")
            f.write(f"YOUTUBE_CLIENT_SECRET={creds.client_secret}\n")
        print("Environment variables also saved to .env.youtube")
    else:
        print("No refresh token obtained. Please try again.")

if __name__ == '__main__':
    get_refresh_token() 