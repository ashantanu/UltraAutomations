# System Architecture

```mermaid
graph TB
    subgraph System Architecture
        Client[Client Applications]
        API[FastAPI Server]
        Auth[Authentication Service]
        Gmail[Gmail API]
        YouTube[YouTube API]
        AI[AI Services]
        Storage[File Storage]
        
        Client -->|HTTP| API
        API -->|OAuth2| Auth
        API -->|OAuth2| Gmail
        API -->|OAuth2| YouTube
        API -->|API Calls| AI
        API -->|Read/Write| Storage
    end
```

## Components Description

1. **Client Applications**
   - Web clients
   - API consumers
   - Command-line tools

2. **FastAPI Server**
   - Main application server
   - REST API endpoints
   - Background task processing
   - Request handling

3. **Authentication Service**
   - JWT-based authentication
   - Supabase integration
   - User management
   - Session handling

4. **Gmail API**
   - Email fetching
   - OAuth2 integration
   - Email processing

5. **YouTube API**
   - Video upload
   - Playlist management
   - OAuth2 integration

6. **AI Services**
   - OpenAI integration
   - Text processing
   - Summary generation
   - Video generation

7. **File Storage**
   - Temporary file management
   - Video storage
   - Thumbnail storage 