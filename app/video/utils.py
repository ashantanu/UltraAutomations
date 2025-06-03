import os
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)

def validate_paths_and_permissions(
    paths: Dict[str, Path],
    min_free_space_gb: float
) -> Tuple[bool, Optional[str]]:
    """
    Validate file paths, permissions, and disk space.
    
    Args:
        paths: Dictionary of path types and their corresponding Path objects
        min_free_space_gb: Minimum required free space in GB
        
    Returns:
        Tuple[bool, Optional[str]]: (Success status, Error message if any)
    """
    # Check if output directory exists and is writable
    output_dir = paths.get('output').parent
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
    if not os.access(output_dir, os.W_OK):
        return False, f"No write permission for directory: {output_dir}"

    # Check if all input files exist
    for file_type, file_path in paths.items():
        if file_type != 'output' and file_path is not None and not file_path.exists():
            return False, f"{file_type} file not found: {file_path}"

    # Check available disk space
    free_space = shutil.disk_usage(output_dir).free
    min_space_bytes = min_free_space_gb * 1024 * 1024 * 1024
    if free_space < min_space_bytes:
        return False, f"Insufficient disk space. Only {free_space / (1024*1024*1024):.2f}GB available"

    return True, None

def get_ffmpeg_params() -> list:
    """Get optimized FFmpeg parameters for video processing."""
    return [
        '-max_muxing_queue_size', '1024',
        '-thread_queue_size', '512',
        '-max_error_rate', '0.1',
        '-err_detect', 'ignore_err',
        '-max_interleave_delta', '0',
        '-vsync', '0',
        '-async', '1'
    ] 