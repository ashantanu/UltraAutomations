import os
from pathlib import Path
import logging
from app.utils.s3 import download_from_s3, ASSETS_PREFIX

# Configure logging
logger = logging.getLogger(__name__)

# Constants
ASSETS_DIR = Path("assets")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")

async def download_required_assets() -> bool:
    """
    Download required assets from S3 during application startup.
    
    Returns:
        bool: True if download was successful, False otherwise
    """
    if not S3_BUCKET:
        logger.error("S3_BUCKET_NAME environment variable not set")
        return False
    
    # Create assets directory if it doesn't exist
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download assets from S3
    logger.info(f"Downloading assets from s3://{S3_BUCKET}/{ASSETS_PREFIX}")
    success = download_from_s3(
        bucket=S3_BUCKET,
        local_dir=str(ASSETS_DIR),
        prefix=ASSETS_PREFIX,
        file_extensions=[".jpg", ".jpeg", ".png", ".gif", ".mp3", ".wav", ".mp4"]
    )
    
    if not success:
        logger.error("Failed to download assets from S3")
        return False
    
    logger.info("Asset download complete")
    return True 