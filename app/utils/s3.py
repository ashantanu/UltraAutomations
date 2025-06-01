import os
import boto3
from pathlib import Path
from typing import List, Optional
from botocore.exceptions import ClientError
from app.utils.logging_utils import get_logger

# Configure logging
logger = get_logger(__name__)

# Constants
ASSETS_PREFIX = "app-assets"  # This will be the prefix for all assets in S3
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".mp3", ".wav", ".mp4"}

def get_s3_client():
    """Get an S3 client using environment credentials."""
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION', 'us-east-1')
    )

def upload_to_s3(
    local_path: str,
    bucket: str,
    prefix: str = ASSETS_PREFIX,
    file_extension: Optional[str] = None
) -> bool:
    """
    Upload a file to S3.
    
    Args:
        local_path: Path to the local file
        bucket: S3 bucket name
        prefix: S3 key prefix (default: app-assets)
        file_extension: Optional file extension to filter by
        
    Returns:
        bool: True if upload was successful, False otherwise
    """
    try:
        s3_client = get_s3_client()
        file_path = Path(local_path)
        
        if not file_path.exists():
            logger.error(f"File not found: {local_path}")
            return False
            
        if file_extension and not str(file_path).endswith(file_extension):
            logger.info(f"Skipping {local_path} - not matching extension {file_extension}")
            return False
            
        # Construct S3 key
        s3_key = f"{prefix}/{file_path.name}"
        
        # Upload file
        s3_client.upload_file(
            str(file_path),
            bucket,
            s3_key,
            ExtraArgs={'ContentType': get_content_type(file_path.suffix)}
        )
        
        logger.info(f"Successfully uploaded {local_path} to s3://{bucket}/{s3_key}")
        return True
        
    except ClientError as e:
        logger.error(f"Error uploading to S3: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def download_from_s3(
    bucket: str,
    local_dir: str,
    prefix: str = ASSETS_PREFIX,
    file_extensions: Optional[List[str]] = None
) -> bool:
    """
    Download files from S3 to local directory.
    
    Args:
        bucket: S3 bucket name
        local_dir: Local directory to save files
        prefix: S3 key prefix (default: app-assets)
        file_extensions: Optional list of file extensions to filter by
        
    Returns:
        bool: True if download was successful, False otherwise
    """
    try:
        s3_client = get_s3_client()
        local_path = Path(local_dir)
        local_path.mkdir(parents=True, exist_ok=True)
        
        # List objects in bucket with prefix
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                key = obj['Key']
                file_path = Path(key)
                
                # Skip if not matching file extensions
                if file_extensions and file_path.suffix.lower() not in file_extensions:
                    continue
                    
                # Download file
                local_file = local_path / file_path.name
                s3_client.download_file(bucket, key, str(local_file))
                logger.info(f"Downloaded s3://{bucket}/{key} to {local_file}")
                
        return True
        
    except ClientError as e:
        logger.error(f"Error downloading from S3: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def get_content_type(extension: str) -> str:
    """Get the appropriate content type for a file extension."""
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.mp4': 'video/mp4'
    }
    return content_types.get(extension.lower(), 'application/octet-stream') 