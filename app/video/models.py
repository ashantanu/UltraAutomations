from typing import Optional
from pydantic import BaseModel, Field, validator
from pathlib import Path

class VideoConfig(BaseModel):
    """Configuration for video processing."""
    fps: int = Field(default=24, ge=1, le=60, description="Frames per second")
    video_bitrate: str = Field(default='1000k', pattern=r'^\d+k$', description="Video bitrate (e.g., '1000k')")
    audio_bitrate: str = Field(default='128k', pattern=r'^\d+k$', description="Audio bitrate (e.g., '128k')")
    min_free_space_gb: float = Field(default=1.0, gt=0, description="Minimum required free space in GB")
    preset: str = Field(default='ultrafast', description="FFmpeg preset for encoding")
    threads: int = Field(default=2, ge=1, le=8, description="Number of threads for encoding")

class AudioConfig(BaseModel):
    """Configuration for audio processing."""
    main_audio_volume: float = Field(default=1.0, ge=0.0, le=1.0, description="Volume level for main audio (0.0 to 1.0)")
    background_music_volume: float = Field(default=0.025, ge=0.0, le=1.0, description="Volume level for background music (0.0 to 1.0)")

class VideoInput(BaseModel):
    """Input parameters for video creation."""
    main_audio_path: Path
    image_path: Path
    output_path: Path
    background_music_path: Optional[Path] = None
    
    @validator('main_audio_path', 'image_path', 'output_path', 'background_music_path')
    def validate_paths(cls, v):
        if v is not None:
            if not v.parent.exists():
                v.parent.mkdir(parents=True, exist_ok=True)
        return v

class VideoProcessingResult(BaseModel):
    """Result of video processing."""
    success: bool
    message: str
    output_path: Optional[Path] = None
    error: Optional[str] = None 