import os
import logging
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    filename='gmail_oauth.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GmailOAuthReader:
    def __init__(self):
        """Initialize the Gmail OAuth reader using environment variables."""
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

    def _extract_body_from_parts(self, parts: List[Dict]) -> tuple[str, str]:
        """Extract both plain text and HTML content from email parts."""
        plain_text = ''
        html_text = ''
        
        for part in parts:
            if part['mimeType'] == 'text/plain':
                if 'data' in part['body']:
                    plain_text = base64.urlsafe_b64decode(part['body']['data']).decode()
            elif part['mimeType'] == 'text/html':
                if 'data' in part['body']:
                    html_text = base64.urlsafe_b64decode(part['body']['data']).decode()
            elif 'parts' in part:
                sub_plain, sub_html = self._extract_body_from_parts(part['parts'])
                plain_text = plain_text or sub_plain
                html_text = html_text or sub_html
                
        return plain_text, html_text

    def _clean_html(self, html_content: str) -> str:
        """Clean HTML content and extract readable text."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            # Get text
            text = soup.get_text(separator='\n')
            # Break into lines and remove leading and trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            return text
        except Exception as e:
            logger.error(f"Error cleaning HTML: {str(e)}")
            return html_content

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
                plain_text = ''
                html_text = ''
                
                if 'parts' in msg['payload']:
                    plain_text, html_text = self._extract_body_from_parts(msg['payload']['parts'])
                elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                    if msg['payload']['mimeType'] == 'text/plain':
                        plain_text = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode()
                    elif msg['payload']['mimeType'] == 'text/html':
                        html_text = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode()

                # Clean HTML content if available
                if html_text:
                    body = self._clean_html(html_text)
                else:
                    body = plain_text

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
    Convenience function to fetch emails from Gmail using OAuth2.
    
    Args:
        query: Gmail search query (default: "in:inbox")
        max_results: Maximum number of emails to fetch (default: 10)
        include_spam_trash: Whether to include spam and trash (default: False)
        
    Returns:
        List of dictionaries containing email details
    """
    reader = GmailOAuthReader()
    return reader.get_emails(
        query=query,
        max_results=max_results,
        include_spam_trash=include_spam_trash
    ) 