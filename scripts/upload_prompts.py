import os
from dotenv import load_dotenv
from langfuse import Langfuse

# Load environment variables
load_dotenv()

# Initialize Langfuse client
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

def load_prompt_from_file(filepath):
    """Load prompt content from a text file."""
    try:
        with open(filepath, 'r') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error loading prompt from {filepath}: {str(e)}")
        return None

# List of prompts to upload
PROMPTS = [
    {
        "name": "news_summarizer",
        "description": "Prompt for generating daily AI news summaries in podcast format",
        "tags": ["news", "summarizer", "podcast"],
        "type": "text",  # text or chat based on langfuse docs
        "prompt": load_prompt_from_file("scripts/prompts/news_summarizer.txt")

    },
    {
        "name": "news-summary-tts-instructions",
        "description": "Instructions for TTS voice and presentation style for AI news summaries",
        "tags": ["news", "summarizer", "podcast", "tts", "voice"],
        "type": "text",
        "prompt": load_prompt_from_file("scripts/prompts/news-summary-tts-instructions.txt")
    }
    # Add more prompts here as needed
]

def upload_prompts():
    """Upload all prompts to Langfuse."""
    for prompt_data in PROMPTS:
        try:
            if prompt_data["prompt"] is None:
                print(f"Skipping prompt '{prompt_data['name']}' due to missing content")
                continue
                
            prompt_obj = langfuse.create_prompt(
                name=prompt_data["name"],
                prompt=prompt_data["prompt"],
                tags=prompt_data["tags"],
                type=prompt_data["type"],
                labels=['production']
            )
            print(f"Successfully uploaded prompt '{prompt_data['name']}'")
        except Exception as e:
            print(f"Failed to upload prompt '{prompt_data['name']}': {str(e)}")

if __name__ == "__main__":
    upload_prompts() 