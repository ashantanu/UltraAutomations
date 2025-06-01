#!/usr/bin/env python3

import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import logging
from app.utils.s3 import upload_to_s3, SUPPORTED_EXTENSIONS
from app.utils.logging_utils import get_logger

LOCAL_ASSETS_DIR = Path("assets")


logger = get_logger(__name__)

def check_environment():
    """Check if required environment variables are set."""
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'S3_BUCKET_NAME']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    return True

def upload_assets():
    """Upload all supported files from the assets directory to S3."""
    # Load environment variables from .env
    
    if not check_environment():
        return False
    
    assets_dir = LOCAL_ASSETS_DIR
    if not assets_dir.exists():
        logger.error("assets directory not found")
        return False
    
    bucket = os.getenv('S3_BUCKET_NAME')
    uploaded_count = 0
    skipped_count = 0
    
    # Find all files in assets directory
    for file_path in assets_dir.rglob("*"):
        if not file_path.is_file():
            continue
            
        # Check if file extension is supported
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.info(f"Skipping {file_path} - unsupported file type")
            skipped_count += 1
            continue
        
        # Upload file
        logger.info(f"Uploading {file_path}...")
        if upload_to_s3(str(file_path), bucket):
            uploaded_count += 1
        else:
            skipped_count += 1
    
    logger.info(f"Asset upload complete! Uploaded: {uploaded_count}, Skipped: {skipped_count}")
    return True

if __name__ == "__main__":
    upload_assets() 