import os
import logging
from typing import Optional, Dict, Any, List
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64

# Configure logging
logging.basicConfig(
    filename='gmail_reader.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GmailReader:
    def __init__(self):
        """Initialize the Gmail reader using environment variables."""
        self.gmail = None
        self.credentials = None
        self._load_config()

    def _load_config(self) -> bool:
        """Load configuration from environment variables."""
        try:
            # Get credentials from environment variables
            refresh_token = os.getenv('GMAIL_REFRESH_TOKEN')
            client_id = os.getenv('GMAIL_CLIENT_ID')
            client_secret = os.getenv('GMAIL_CLIENT_SECRET')

            if not all([refresh_token, client_id, client_secret]):
                missing = []
                if not refresh_token: missing.append('GMAIL_REFRESH_TOKEN')
                if not client_id: missing.append('GMAIL_CLIENT_ID')
                if not client_secret: missing.append('GMAIL_CLIENT_SECRET')
                logger.error(f"Missing required environment variables: {', '.join(missing)}")
                return False

            self.credentials = Credentials(
                None,  # No access token initially
                refresh_token=refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=client_id,
                client_secret=client_secret,
                scopes=['https://www.googleapis.com/auth/gmail.readonly']
            )
            return True
        except Exception as e:
            logger.error(f"Failed to load config from environment: {str(e)}")
            return False

    def authenticate(self) -> bool:
        """Authenticate with Gmail API using refresh token."""
        try:
            if not self.credentials:
                if not self._load_config():
                    return False

            # Refresh the token if needed
            if not self.credentials.valid:
                self.credentials.refresh(Request())

            self.gmail = build('gmail', 'v1', credentials=self.credentials)
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False

    def get_emails(
        self,
        query: str = "in:inbox",
        max_results: int = 10,
        include_spam_trash: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails from Gmail based on specified criteria.
        
        Args:
            query: Gmail search query (default: "in:inbox")
            max_results: Maximum number of emails to fetch (default: 10)
            include_spam_trash: Whether to include spam and trash (default: False)
            
        Returns:
            List of dictionaries containing email details
        """
        if not self.gmail:
            if not self.authenticate():
                return []

        try:
            # Get list of messages matching the query
            results = self.gmail.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results,
                includeSpamTrash=include_spam_trash
            ).execute()

            messages = results.get('messages', [])
            emails = []

            for message in messages:
                # Get full message details
                msg = self.gmail.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()

                # Extract headers
                headers = msg['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
                sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
                date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')

                # Get email body
                body = ''
                if 'parts' in msg['payload']:
                    for part in msg['payload']['parts']:
                        if part['mimeType'] == 'text/plain':
                            body = base64.urlsafe_b64decode(part['body']['data']).decode()
                            break
                elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                    body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode()

                emails.append({
                    'id': message['id'],
                    'subject': subject,
                    'sender': sender,
                    'date': date,
                    'body': body,
                    'snippet': msg.get('snippet', '')
                })

            return emails

        except Exception as e:
            logger.error(f"Failed to fetch emails: {str(e)}")
            return []

def get_emails_from_gmail(
    query: str = "in:inbox",
    max_results: int = 10,
    include_spam_trash: bool = False
) -> List[Dict[str, Any]]:
    """
    Convenience function to fetch emails from Gmail using environment variables.
    
    Args:
        query: Gmail search query (default: "in:inbox")
        max_results: Maximum number of emails to fetch (default: 10)
        include_spam_trash: Whether to include spam and trash (default: False)
        
    Returns:
        List of dictionaries containing email details
    """
    reader = GmailReader()
    return reader.get_emails(
        query=query,
        max_results=max_results,
        include_spam_trash=include_spam_trash
    ) 