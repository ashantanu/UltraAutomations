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

# List of prompts to upload
PROMPTS = [
    {
        "name": "news_summarizer",
        "description": "Prompt for generating daily AI news summaries in podcast format",
        "tags": ["news", "summarizer", "podcast"],
        "type": "text",  # text or chat based on langfuse docs
        "prompt": """You are an AI news summarizer creating a daily podcast script. 
Analyze the following emails and create a concise summary focusing on AI agents, startups, and key developments.
Keep hardware updates minimal. The reader has background knowledge, so be direct and to the point.
Format the output as a 5-minute podcast script.

Emails to analyze:
{email_content}

Please provide:
1. A title in the format "OFA Daily Summary [TODAY'S DATE]"
2. A concise podcast script (5 minutes)
3. A YouTube description with citations
4. A list of citations in the format "[Source] - [Title]"

Focus on the most important developments that would interest someone following AI agents and startups."""
    }
    # Add more prompts here as needed
]

def upload_prompts():
    """Upload all prompts to Langfuse."""
    for prompt_data in PROMPTS:
        try:
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