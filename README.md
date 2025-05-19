# FastAPI Server with Supabase Authentication

This is a FastAPI server with Supabase JWT authentication middleware and YouTube video upload capabilities.

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
4. Update the `.env` file with your credentials:
   ```
   # Supabase
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_KEY=your_supabase_anon_key

   # OpenAI
   OPENAI_API_KEY=your_openai_api_key

   # Gmail OAuth
   GMAIL_CLIENT_ID=your_gmail_client_id
   GMAIL_CLIENT_SECRET=your_gmail_client_secret
   GMAIL_REFRESH_TOKEN=your_gmail_refresh_token

   # Langfuse
   LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
   LANGFUSE_SECRET_KEY=your_langfuse_secret_key
   LANGFUSE_HOST=https://cloud.langfuse.com  # Optional, defaults to this value
   ```

5. Get Gmail OAuth credentials:
   ```bash
   python scripts/get_gmail_token.py
   ```

6. Upload prompts to Langfuse:
   ```bash
   python scripts/upload_prompts.py
   ```

## Authentication Flow

### 1. Register a New User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your-secure-password"
  }'
```

### 2. Login to Get Access Token

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your-secure-password"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Access Protected Routes

Include the access token in the Authorization header:

```bash
curl http://localhost:8000/protected-route \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 4. Logout

```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get access token
- `POST /auth/logout` - Logout and invalidate token

### Protected Routes
- `GET /protected-route` - Example protected route
- `GET /health` - Health check endpoint (public)

## Project Structure

```
.
├── .env.example
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── auth.py
│   ├── core/
│   │   ├── agents/
│   │   │   ├── text_to_video.py
│   │   │   └── text_to_youtube.py
│   │   └── ...
│   └── utils/
│       ├── __init__.py
│       ├── youtube.py
│       └── ...
├── test_youtube_upload.py
└── requirements.txt
```

## Features

### Authentication
- JWT-based authentication using Supabase
- Protected routes with middleware
- User registration and login

### YouTube Integration
- Upload videos to YouTube
- Create and manage playlists
- Automatic playlist creation
- Video thumbnail support
- Comprehensive logging

### Gmail Integration
- Read emails from Gmail using OAuth2
- Support for various search criteria
- Automatic email decoding and parsing
- Comprehensive logging

To use the Gmail OAuth functionality, set up the following environment variables:
```bash
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret
GMAIL_REFRESH_TOKEN=your_refresh_token
```

To set up Gmail OAuth credentials:
1. Go to the [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Go to Credentials → Create Credentials → OAuth client ID
5. Set up the OAuth consent screen
6. Create OAuth 2.0 Client ID credentials
7. Use the client ID and client secret in your environment variables
8. Generate a refresh token using the OAuth 2.0 Playground or your own OAuth flow

Example usage:
```python
from app.utils.gmail_oauth import get_emails_from_gmail

# Get unread emails
emails = get_emails_from_gmail(
    query="is:unread",
    max_results=10
)

# Get emails from a specific sender
emails = get_emails_from_gmail(
    query='from:specific@email.com',
    max_results=5
)

# Get emails with specific subject
emails = get_emails_from_gmail(
    query='subject:"Important"',
    max_results=10
)
```

Available search criteria:
- `is:unread` - Unread emails
- `is:read` - Read emails
- `from:email@example.com` - Emails from specific sender
- `to:email@example.com` - Emails sent to specific address
- `subject:"text"` - Emails with specific subject
- `after:2024/01/01` - Emails after specific date
- `before:2024/01/01` - Emails before specific date
- `larger:1M` - Emails larger than size
- `smaller:1M` - Emails smaller than size
- `has:attachment` - Emails with attachments
- `label:important` - Emails with specific label

Each email in the returned list contains:
- `id`: The Gmail message ID
- `subject`: Email subject
- `sender`: Sender's email address
- `date`: Email date
- `body`: Email body text
- `snippet`: A short preview of the email content

### Text-to-YouTube Agent
The text-to-youtube agent combines text-to-video generation with YouTube upload in a single flow:

```python
from app.core.agents.text_to_youtube import text_to_youtube

result = text_to_youtube(
    text="Your text content here",
    title="Video Title",
    description="Video Description"
)

# Result includes:
{
    "status": "success",
    "video_path": "path/to/generated/video.mp4",
    "title": "Video Title",
    "description": "Video Description",
    "youtube_video_id": "youtube_video_id",
    "youtube_video_url": "https://www.youtube.com/watch?v=youtube_video_id",
    "upload_details": {
        # Additional upload details from YouTube API
    }
}
```

For detailed YouTube upload functionality documentation, see [README_YOUTUBE.md](README_YOUTUBE.md).

## Running the Server

```bash
uvicorn app.main:app --reload
```

The server will be available at `http://localhost:8000`

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

# OFA Server

A server for generating AI news summaries from email newsletters.

## Features

- Fetches emails from Gmail using OAuth2
- Generates AI-powered news summaries
- Creates podcast scripts and YouTube descriptions
- Uses LangGraph for workflow orchestration
- Integrates with Langfuse for prompt management and tracing

## Prerequisites

- Python 3.9+
- Gmail account with access to the newsletters
- OpenAI API key
- Langfuse account

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ofa-server.git
cd ofa-server
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables in `.env`:
```bash
# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Gmail OAuth
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
GMAIL_REFRESH_TOKEN=your_gmail_refresh_token

# Langfuse
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com  # Optional, defaults to this value
```

4. Get Gmail OAuth credentials:
```bash
python scripts/get_gmail_token.py
```

5. Upload prompts to Langfuse:
```bash
python scripts/upload_prompts.py
```

## Usage

1. Test the news summarizer:
```bash
python scripts/test_ai_news_summarizer.py
```

2. The script will:
   - Fetch emails from the last 24 hours
   - Generate a summary using OpenAI
   - Save the output to a JSON file
   - Log the process in Langfuse

## Deployment

Before deploying the application:

1. Ensure all environment variables are set in your deployment environment
2. Run the prompt upload script to set up Langfuse:
```bash
python scripts/upload_prompts.py
```

3. Verify the prompts are available in your Langfuse dashboard

4. Test the deployment with:
```bash
python scripts/test_ai_news_summarizer.py
```

## Monitoring

- Check the Langfuse dashboard for:
  - Prompt performance
  - Token usage
  - Error rates
  - Response times

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License

## Prompt Management

The application uses Langfuse for prompt management and monitoring. Before deploying:

1. Ensure you have a Langfuse account and API credentials
2. Run the prompt upload script:
   ```bash
   python scripts/upload_prompts.py
   ```
3. Verify the prompts are available in your Langfuse dashboard
4. Monitor prompt performance and usage in the Langfuse dashboard

The following prompts are managed through Langfuse:
- `news_summarizer`: Generates daily AI news summaries in podcast format

To update prompts:
1. Modify the prompts in `scripts/upload_prompts.py`
2. Run the upload script again
3. The new version will be tracked in Langfuse