"""
AI News Summarizer - Simplified

Fetches emails and generates AI summaries without LangGraph complexity.
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from email.utils import parsedate_to_datetime
import pytz
from dotenv import load_dotenv

from app.utils.gmail_oauth import get_emails_from_gmail
from app.utils.logging_utils import get_logger
from app.utils.date_utils import get_pst_date

logger = get_logger(__name__)
load_dotenv()

# Configuration
EMAIL_BODY_CHAR_LIMIT = 2000
MODEL = 'openai:gpt-5.2'
SOURCES = ['news@smol.ai', 'a.shantanu08@gmail.com']
PROMPT_NAME = "news_summarizer"
AUDIO_SCRIPT_DELIMITER = "==="
AUDIO_SCRIPT_ITEM_DELIMITER = "<item>"


def _pst_tz():
    return pytz.timezone("US/Pacific")


# =============================================================================
# Pydantic Models
# =============================================================================

class EmailContent(BaseModel):
    """Structured email content."""
    sender: str
    subject: str
    date: datetime
    body: str
    source: str


class AudioScriptModel(BaseModel):
    """Audio script with structured sections."""
    opening: str
    news_items: List[str]
    closing: str


class SummaryOutput(BaseModel):
    """AI-generated summary output."""
    title: str = Field(..., description="Title in format 'OFA Daily Summary [DATE]'")
    audio_script: Union[AudioScriptModel, str] = Field(..., description="Podcast script")
    description: str = Field(..., description="YouTube description with citations")


class FinalOutput(BaseModel):
    """Final pipeline output."""
    date: datetime
    emails_processed: int
    summary: SummaryOutput


# =============================================================================
# Helper Functions
# =============================================================================

def _compute_gmail_time_window(target_date: Optional[datetime]) -> tuple[int, int, str]:
    """Compute Gmail search time window as epoch seconds."""
    if target_date is not None:
        pst_dt = get_pst_date(target_date)
        start_of_day = pst_dt.astimezone(_pst_tz()).replace(hour=0, minute=0, second=0, microsecond=0)
        start_next_day = start_of_day + timedelta(days=1)
        return int(start_of_day.timestamp()), int(start_next_day.timestamp()), start_of_day.strftime("%Y-%m-%d PST")

    now_pst = get_pst_date()
    after = now_pst - timedelta(hours=24)
    return int(after.timestamp()), int(now_pst.timestamp()) + 1, "last_24_hours"


def build_gmail_query(source: str, target_date: Optional[datetime]) -> tuple[str, dict]:
    """Build a Gmail query for a source + time window."""
    after_epoch, before_epoch, window_label = _compute_gmail_time_window(target_date)
    query = f"in:inbox from:{source} after:{after_epoch} before:{before_epoch}"
    meta = {
        "source": source,
        "window": window_label,
        "after_epoch": after_epoch,
        "before_epoch": before_epoch,
        "query": query,
    }
    return query, meta


def format_audio_script(script: AudioScriptModel) -> str:
    """Format AudioScriptModel into delimited string."""
    formatted_items = "\n".join(
        f"{AUDIO_SCRIPT_ITEM_DELIMITER} {item}" for item in script.news_items
    )
    return f"{script.opening}\n{AUDIO_SCRIPT_DELIMITER}\n{formatted_items}\n{AUDIO_SCRIPT_DELIMITER}\n{script.closing}"


# =============================================================================
# Core Functions
# =============================================================================

def probe_email_availability(
    target_date: Optional[datetime],
    sources: Optional[List[str]] = None,
    max_results: int = 3,
) -> List[dict]:
    """
    Lightweight Gmail probe for dry-run/preflight.
    Returns per-source counts without calling OpenAI.
    """
    sources = sources or SOURCES
    after_epoch, before_epoch, window_label = _compute_gmail_time_window(target_date)

    missing = [
        k for k in ("GMAIL_REFRESH_TOKEN", "GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET")
        if not os.getenv(k)
    ]
    if missing:
        logger.error("Gmail probe missing env vars: %s", ", ".join(missing))
        return [
            {
                "source": s,
                "window": window_label,
                "query": build_gmail_query(source=s, target_date=target_date)[0],
                "count": 0,
                "samples": [],
                "error": f"missing_gmail_env:{','.join(missing)}",
            }
            for s in sources
        ]

    report = []
    for source in sources:
        query, meta = build_gmail_query(source=source, target_date=target_date)
        logger.info("Gmail probe: source=%s query=%s", source, query)
        emails = get_emails_from_gmail(query=query, max_results=max_results)
        samples = [
            {
                "id": e.get("id"),
                "subject": e.get("subject"),
                "date": e.get("date"),
                "sender": e.get("sender"),
                "snippet": e.get("snippet"),
                "body_len": len(e.get("body") or ""),
            }
            for e in emails
        ]
        report.append({**meta, "count": len(emails), "samples": samples})
    return report


def fetch_emails(target_date: Optional[datetime] = None) -> List[EmailContent]:
    """Fetch emails from configured sources."""
    logger.info("📧 Fetching emails...")
    after_epoch, before_epoch, window_label = _compute_gmail_time_window(target_date)
    logger.info(f"Time window: {window_label}")

    all_emails = []
    for source in SOURCES:
        query, _ = build_gmail_query(source=source, target_date=target_date)
        logger.info(f"Querying: {query}")
        
        emails = get_emails_from_gmail(query=query, max_results=10)
        
        for email in emails:
            # Parse date robustly
            parsed_dt = None
            raw_date = (email.get("date") or "").strip()
            if raw_date:
                try:
                    parsed_dt = parsedate_to_datetime(raw_date)
                except Exception:
                    pass
            if parsed_dt is None:
                logger.warning(f"Could not parse date: {raw_date!r}")
                parsed_dt = get_pst_date()

            all_emails.append(EmailContent(
                sender=email['sender'],
                subject=email['subject'],
                date=parsed_dt,
                body=email['body'],
                source=source
            ))
        
        logger.info(f"Found {len(emails)} emails from {source}")

    if not all_emails:
        raise ValueError("No emails found for requested window")

    logger.info(f"✅ Total emails fetched: {len(all_emails)}")
    return all_emails


async def generate_summary(emails: List[EmailContent]) -> SummaryOutput:
    """Generate AI summary from emails using Pydantic AI."""
    from langfuse import Langfuse
    from pydantic_ai import Agent

    logger.info("🤖 Generating AI summary...")

    # Prepare email content
    email_content = "\n\n".join([
        f"From: {email.source}\n"
        f"Subject: {email.subject}\n"
        f"Date: {email.date}\n"
        f"Content: {email.body[:EMAIL_BODY_CHAR_LIMIT] + ('...' if len(email.body) > EMAIL_BODY_CHAR_LIMIT else '')}"
        for email in emails
    ])

    if not email_content:
        raise ValueError("No email content to process")

    # Get prompt from Langfuse
    langfuse = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    )
    prompt_obj = langfuse.get_prompt(PROMPT_NAME)
    if not prompt_obj:
        raise ValueError(f"Prompt '{PROMPT_NAME}' not found in Langfuse")

    # Generate summary
    agent = Agent(MODEL, output_type=SummaryOutput, instructions=prompt_obj.prompt, instrument=True)
    result = await agent.run(f"\n\nemail_content: {email_content}\n\nGenerate the script as per the instructions.")
    summary = result.output

    # Format audio script if structured
    if isinstance(summary.audio_script, AudioScriptModel):
        summary.audio_script = format_audio_script(summary.audio_script)

    logger.info(f"✅ Summary generated: {summary.title}")
    return summary


async def generate_ai_news_summary(date: Optional[datetime] = None) -> FinalOutput:
    """
    Main entry point: fetch emails and generate AI summary.
    
    Args:
        date: Target date for emails. Defaults to last 24 hours.
    
    Returns:
        FinalOutput with summary and metadata.
    """
    logger.info("🚀 Starting AI news summary generation...")
    
    # Step 1: Fetch emails
    emails = fetch_emails(target_date=date)
    
    # Step 2: Generate summary
    summary = await generate_summary(emails)
    
    output = FinalOutput(
        date=date or get_pst_date(),
        emails_processed=len(emails),
        summary=summary
    )
    
    logger.info(f"🎉 Summary complete: {output.emails_processed} emails processed")
    return output
