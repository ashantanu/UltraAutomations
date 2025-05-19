# Getting Started with OFA Server

This guide will help you set up and run the OFA Server on your local machine.

## Prerequisites

- Python 3.9 or higher
- Git
- A Gmail account with access to newsletters
- OpenAI API key
- Langfuse account (for prompt management)
- YouTube Data API credentials (for video uploads)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ofa-server.git
cd ofa-server
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Update the `.env` file with your credentials:
```env
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

### Setting up Gmail OAuth

1. Go to the [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Go to Credentials → Create Credentials → OAuth client ID
5. Set up the OAuth consent screen
6. Create OAuth 2.0 Client ID credentials
7. Use the client ID and client secret in your environment variables
8. Generate a refresh token using the provided script:
```bash
python scripts/get_gmail_token.py
```

### Setting up Langfuse

1. Create a Langfuse account at [cloud.langfuse.com](https://cloud.langfuse.com)
2. Get your API keys from the dashboard
3. Upload the prompts to Langfuse:
```bash
python scripts/upload_prompts.py
```

## Running the Server

1. Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

2. The server will be available at `http://localhost:8000`

3. Access the API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Basic Usage

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

### 3. Access Protected Routes

Include the access token in the Authorization header:

```bash
curl http://localhost:8000/protected-route \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Next Steps

- Read the [API Reference](../api/README.md) for detailed endpoint documentation
- Check out the [Examples](../examples/README.md) for usage patterns
- Learn about [Development](../development/README.md) for contributing

## Troubleshooting

### Common Issues

1. **Gmail Authentication Fails**
   - Ensure your OAuth credentials are correct
   - Check if the Gmail API is enabled
   - Verify the refresh token is valid

2. **YouTube Upload Fails**
   - Confirm YouTube API credentials
   - Check quota limits
   - Verify video format and size

3. **Langfuse Integration Issues**
   - Verify API keys
   - Check prompt versions
   - Ensure proper network connectivity

For more help, see the [FAQ](faq.md) or create an issue on GitHub. 