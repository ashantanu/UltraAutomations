import os
from datetime import datetime
from typing import List, Optional, TypedDict, Union
from pydantic import BaseModel, Field
from openai import OpenAI
from app.utils.gmail_oauth import get_emails_from_gmail
from app.utils.logging_utils import get_logger
from dotenv import load_dotenv
from langgraph.graph import Graph, StateGraph, END
from langfuse.callback import CallbackHandler
from langfuse import Langfuse
from pydantic_ai import Agent
import logfire
from app.utils.date_utils import get_pst_date
logfire.configure()


# Initialize logger
logger = get_logger(__name__)

# Load environment variables
load_dotenv()
EMAIL_BODY_CHAR_LIMIT = 2000
MODEL = 'openai:gpt-4.1'
MODEL_PROVIDER = "openai"
AUDIO_SCRIPT_DELIMITER = "==="
AUDIO_SCRIPT_ITEM_DELIMITER = "<item>"

# Initialize clients
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

langfuse_client = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

# Constants
SOURCES = ['news@smol.ai']
PROMPT_NAME = "news_summarizer"  # Name of the prompt in Langfuse


class EmailContent(BaseModel):
    """Model for structured email content."""
    sender: str
    subject: str
    date: datetime
    body: str
    source: str = Field(...,
                        description="Source of the email (smol.ai or alphasignal.ai)")


class AudioScriptModel(BaseModel):
    """Model for the audio script."""
    opening: str = Field(..., description="Opening statement")
    news_items: List[str] = Field(..., description="List of news items")
    closing: str = Field(..., description="Closing statement")


class SummaryOutput(BaseModel):
    """Model for the OpenAI-generated summary."""
    title: str = Field(...,
                       description="Title of the summary in format 'OFA Daily Summary [DATE]'")
    audio_script: Union[AudioScriptModel, str] = Field(
        ..., description="5-minute podcast script summarizing the key points")
    description: str = Field(...,
                             description="YouTube video description with citations")


def format_audio_script(script: AudioScriptModel) -> str:
    """Format an AudioScriptModel into a structured string with delimiters.

    Args:
        script: AudioScriptModel instance containing opening, news items, and closing

    Returns:
        Formatted string with opening, news items list, and closing separated by delimiters
    """
    if not isinstance(script, AudioScriptModel):
        raise TypeError("Input must be an AudioScriptModel instance")

    formatted_items = "\n".join(
        f"{AUDIO_SCRIPT_ITEM_DELIMITER} {item}" for item in script.news_items)

    return f"{script.opening}\n{AUDIO_SCRIPT_DELIMITER}\n{formatted_items}\n{AUDIO_SCRIPT_DELIMITER}\n{script.closing}"


class FinalOutput(BaseModel):
    """Model for the final combined output."""
    date: datetime
    emails_processed: int
    summary: SummaryOutput


class AgentState(TypedDict):
    """State for the LangGraph agent."""
    emails: List[EmailContent]
    summary: Optional[SummaryOutput]
    error: Optional[str]
    trace_id: str
    target_date: Optional[datetime]


def fetch_emails_node(state: AgentState) -> AgentState:
    """Node for fetching emails."""
    try:
        logger.info("Starting email fetch process")
        # Calculate date range based on provided date or last 24 hours
        end_date = state.get("target_date", get_pst_date())
        
        # Format date for Gmail query
        date_query = f"after:{end_date.strftime('%Y/%m/%d')}"
        logger.debug(f"Date query: {date_query}")

        all_emails = []
        for source in SOURCES:
            logger.info(f"Fetching emails from source: {source} with query: {f'from:{source} {date_query}'}")
            # Get emails from each source
            emails = get_emails_from_gmail(
                query=f'from:{source} {date_query}',
                max_results=10
            )

            # Convert to EmailContent model
            for email in emails:
                all_emails.append(EmailContent(
                    sender=email['sender'],
                    subject=email['subject'],
                    date=datetime.strptime(
                        email['date'], '%a, %d %b %Y %H:%M:%S %z'),
                    body=email['body'],
                    source=source
                ))
            logger.info(f"Found {len(emails)} emails from {source}")

        if not all_emails:
            logger.warning(f"No emails found for date: {end_date.strftime('%Y/%m/%d')}")
            raise ValueError(f"No emails found for date: {end_date.strftime('%Y/%m/%d')}")

        logger.info(f"Total emails fetched: {len(all_emails)}")
        state["emails"] = all_emails
        return state

    except Exception as e:
        logger.error(f"Error in fetch_emails_node: {str(e)}", exc_info=True)
        state["error"] = str(e)
        return state


async def generate_summary_node(state: AgentState) -> AgentState:
    """Node for generating summary."""
    return_state = {}
    try:
        logger.info("Starting summary generation")
        # Prepare email content for the prompt
        email_content = "\n\n".join([
            f"From: {email.source}\n"
            f"Subject: {email.subject}\n"
            f"Date: {email.date}\n"
            f"Content: {email.body[:EMAIL_BODY_CHAR_LIMIT] + ('...' if len(email.body) > EMAIL_BODY_CHAR_LIMIT else '')}"
            for email in state["emails"]
        ])
        logger.debug(
            f"Prepared email content with {len(state['emails'])} emails")
        logger.debug(f"Email content length: {len(email_content)} characters")

        if not email_content:
            logger.warning("No email content to process")
            return {}

        # Get the prompt from Langfuse
        logger.info("Fetching prompt from Langfuse")
        prompt_obj = langfuse_client.get_prompt(PROMPT_NAME)
        if not prompt_obj:
            logger.error(f"Prompt '{PROMPT_NAME}' not found in Langfuse")
            raise ValueError(f"Prompt '{PROMPT_NAME}' not found in Langfuse")

        logger.info(f"Retrieved prompt from Langfuse: {PROMPT_NAME}")

        # Format the prompt with the email content
        formatted_prompt = prompt_obj.prompt
        logger.debug(
            f"Formatted prompt length: {len(formatted_prompt)} characters")

        # Use Pydantic AI to get structured output
        logger.info("Generating summary using Pydantic AI")
        logger.debug(f"Initialized Pydantic AI agent with model: {MODEL}")
        agent = Agent(MODEL, output_type=SummaryOutput, instructions=formatted_prompt, instrument=True)
        result = await agent.run(f"\n\nemail_content: {email_content}\n\nGenerate the script as per the instructions.")
        result = result.output

        logger.info("Successfully generated summary")
        logger.debug(f"Generated title: {result.title}")

        # Format the audio script if it's an AudioScriptModel
        if isinstance(result.audio_script, AudioScriptModel):
            logger.debug("Formatting audio script with delimiters")
            result.audio_script = format_audio_script(
                result.audio_script)

        logger.debug(
            f"Audio script formatted: {result.audio_script[:100]}...")

        return_state["summary"] = result
        return return_state

    except Exception as e:
        logger.error(
            f"Error in generate_summary_node: {str(e)}", exc_info=True)
        return_state["error"] = str(e)
        return return_state


def build_graph() -> Graph:
    """Build the LangGraph workflow."""
    logger.info("Building workflow graph")
    # Create the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("fetch_emails", fetch_emails_node)
    workflow.add_node("generate_summary", generate_summary_node)

    # Add edges
    workflow.add_edge("fetch_emails", "generate_summary")
    workflow.add_edge("generate_summary", END)

    # Set entry point
    workflow.set_entry_point("fetch_emails")

    # Compile the graph
    logger.info("Compiling workflow graph")
    return workflow.compile()


# Initialize the graph
graph = build_graph()


async def generate_ai_news_summary(date: Optional[datetime] = None) -> FinalOutput:
    """
    Generate the daily AI news summary.

    Args:
        date (Optional[datetime]): The date to process emails for. If not provided,
            defaults to the last 24 hours.

    Returns:
        FinalOutput containing the summary and metadata
    """
    logger.info("Starting AI news summary generation")
    try:
        # Initialize state with optional date
        state: AgentState = {
            "emails": [],
            "summary": None,
            "error": None,
            "trace_id": None,
            "target_date": date
        }
        logger.debug("Initialized agent state")
        if date:
            logger.info(f"Processing emails for date: {date.isoformat()}")

        # Run the graph
        logger.info("Invoking workflow graph")
        langfuse_handler = CallbackHandler(
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        )
        logger.debug("Initialized Langfuse handler")

        final_state = await graph.ainvoke(
            state,
            config={
                "callbacks": [langfuse_handler],
                "run_name": "ai_news_summary"
            }
        )
        logger.debug(f"Graph execution completed. State: {final_state}")

        if final_state["error"]:
            logger.error(f"Error in workflow: {final_state['error']}")
            raise Exception(final_state["error"])

        # Create final output
        output = FinalOutput(
            date=date or get_pst_date(),
            emails_processed=len(final_state["emails"]),
            summary=final_state["summary"]
        )
        logger.debug(
            f"Created final output with {output.emails_processed} emails processed")

        logger.info(
            f"Successfully generated summary with {output.emails_processed} emails processed")
        return output

    except Exception as e:
        logger.error(
            f"Failed to generate daily summary: {str(e)}", exc_info=True)
        raise Exception(f"Failed to generate daily summary: {str(e)}")
