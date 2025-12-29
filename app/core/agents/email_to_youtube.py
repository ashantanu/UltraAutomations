import os
from datetime import datetime
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langfuse import observe
from app.core.agents.ai_news_summarizer import generate_ai_news_summary, probe_email_availability
from app.core.agents.text_to_youtube import text_to_youtube
from app.utils.logging_utils import get_logger
from app.utils.image_utils import add_text_overlay
from app.utils.config import config

# Initialize logger
logger = get_logger(__name__)

class AgentState(TypedDict):
    """State for the LangGraph agent."""
    summary: Optional[dict]
    video_result: Optional[dict]
    thumbnail_path: Optional[str]
    error: Optional[str]
    playlist_name: Optional[str]
    create_playlist_if_not_exists: bool = False
    target_date: Optional[datetime]

async def generate_summary_node(state: AgentState) -> AgentState:
    """Node for generating news summary."""
    try:
        logger.info("Generating news summary...")
        summary_result = await generate_ai_news_summary(date=state.get("target_date"))
        
        if not summary_result:
            raise Exception("Failed to generate news summary")
        
        state["summary"] = {
            "title": summary_result.summary.title,
            "audio_script": summary_result.summary.audio_script,
            "description": summary_result.summary.description,
        }
        return state
    except Exception as e:
        logger.error(f"Error in generate_summary_node: {str(e)}", exc_info=True)
        state["error"] = str(e)
        return state

def generate_thumbnail_node(state: AgentState) -> AgentState:
    """Node for generating YouTube thumbnail."""
    try:
        logger.info("Generating YouTube thumbnail...")
        if not state["summary"]:
            raise Exception("No summary available for thumbnail generation")
        
        # Create output directory if it doesn't exist
        os.makedirs(config.output_dir, exist_ok=True)
        
        # Generate thumbnail path using timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        thumbnail_path = os.path.join(config.output_dir, f"thumbnail_{timestamp}.png")
        
        # Use the template image and generate thumbnail
        add_text_overlay(config.template_thumbnail_path, thumbnail_path)
        
        state["thumbnail_path"] = thumbnail_path
        return state
    except Exception as e:
        logger.error(f"Error in generate_thumbnail_node: {str(e)}", exc_info=True)
        state["error"] = str(e)
        return state

def create_video_node(state: AgentState) -> AgentState:
    """Node for creating and uploading YouTube video."""
    try:
        logger.info("Creating and uploading YouTube video...")
        if not state["summary"]:
            raise Exception("No summary available for video creation")
        
        if not state["thumbnail_path"]:
            logger.warning("No thumbnail available - proceeding with video creation without thumbnail")
        
        video_result = text_to_youtube(
            text=state["summary"]["audio_script"],
            title=state["summary"]["title"],
            description=state["summary"]["description"],
            thumbnail_path=state["thumbnail_path"],  # Add thumbnail to upload
            playlist_name=state["playlist_name"],
            create_playlist_if_not_exists=state["create_playlist_if_not_exists"]
        )
        
        state["video_result"] = video_result
        return state
    except Exception as e:
        logger.error(f"Error in create_video_node: {str(e)}", exc_info=True)
        state["error"] = str(e)
        return state

def build_graph() -> StateGraph:
    """Build the LangGraph workflow."""
    logger.info("Building workflow graph")
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("generate_summary", generate_summary_node)
    workflow.add_node("generate_thumbnail", generate_thumbnail_node)
    workflow.add_node("create_video", create_video_node)
    
    # Add edges
    workflow.add_edge("generate_summary", "generate_thumbnail")
    workflow.add_edge("generate_thumbnail", "create_video")
    workflow.add_edge("create_video", END)
    
    # Set entry point
    workflow.set_entry_point("generate_summary")
    
    # Compile the graph
    logger.info("Compiling workflow graph")
    return workflow.compile()

# Initialize the graph
graph = build_graph()

@observe(name="email_to_youtube_flow")
async def email_to_youtube(date: Optional[datetime] = None):
    """
    Orchestrates the flow from email reading to YouTube video creation.
    Combines AI news summarizer with text-to-youtube functionality.
    
    Args:
        date (Optional[datetime]): The date to process emails for. If not provided,
            defaults to today's PST date.
    
    Returns:
        dict: A dictionary containing the result of the operation
    """
    start_time = datetime.now()
    logger.info("🎬 STARTING EMAIL-TO-YOUTUBE FLOW 🎬")
    if date:
        logger.info(f"Processing emails for date: {date.isoformat()}")
    
    try:
        # Preflight: if there's truly no email for the window, skip the expensive pipeline.
        availability = probe_email_availability(target_date=date, max_results=1)
        for item in availability:
            if item.get("error", "").startswith("missing_gmail_env:"):
                raise Exception(f"Gmail credentials missing: {item['error']}")
        for item in availability:
            logger.info(
                "Email preflight: source=%s window=%s count=%s query=%s",
                item.get("source"),
                item.get("window"),
                item.get("count"),
                item.get("query"),
            )
        total_found = sum(item.get("count", 0) for item in availability)
        if total_found == 0:
            logger.info("No matching emails found; skipping Email-to-YouTube flow.")
            return {
                "status": "skipped",
                "reason": "no_emails",
                "email_probe": availability,
            }

        # Initialize state
        state: AgentState = {
            "summary": None,
            "video_result": None,
            "thumbnail_path": None,
            "error": None,
            "playlist_name": config.youtube_playlist_name,
            "create_playlist_if_not_exists": config.create_playlist_if_not_exists,
            "target_date": date
        }
        # Run the graph
        callbacks = []
        try:
            from langfuse.langchain import CallbackHandler  # type: ignore

            callbacks = [CallbackHandler(public_key=os.getenv("LANGFUSE_PUBLIC_KEY"))]
        except Exception as e:
            logger.info(f"Langfuse callback handler unavailable; continuing without callbacks ({e})")

        final_state = await graph.ainvoke(state, 
            config={
                "callbacks": callbacks,
                "run_name": "email_to_youtube"
            })
        
        if final_state["error"]:
            raise Exception(final_state["error"])
        
        logger.info("🎉 Email-to-YouTube flow completed successfully!")
        return {
            "status": "success",
            "summary": final_state["summary"],
            "video": final_state["video_result"],
            "thumbnail": final_state["thumbnail_path"]
        }
    except Exception as e:
        logger.error(f"❌ Email-to-YouTube flow failed: {e}")
        raise
    finally:
        duration = datetime.now() - start_time
        logger.info(f"⏱️ Total time: {duration.total_seconds():.2f} seconds") 