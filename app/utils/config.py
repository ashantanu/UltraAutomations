import os
import configparser
from typing import Optional, Tuple
from pathlib import Path

class Config:
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Load configuration from settings.ini"""
        self._config = configparser.ConfigParser()
        
        # Get the project root directory (where config/ is located)
        project_root = Path(__file__).parent.parent.parent
        
        # Path to settings.ini
        config_path = project_root / "config" / "settings.ini"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
        
        self._config.read(config_path)
    
    @property
    def youtube_playlist_name(self) -> str:
        """Get the YouTube playlist name from config"""
        return self._config.get("youtube", "playlist_name")
    
    @property
    def youtube_privacy_status(self) -> str:
        """Get the YouTube privacy status from config"""
        return self._config.get("youtube", "privacy_status")
    
    @property
    def create_playlist_if_not_exists(self) -> bool:
        """Get whether to create playlist if it doesn't exist"""
        return self._config.getboolean("youtube", "create_playlist_if_not_exists")
    
    @property
    def template_thumbnail_path(self) -> str:
        """Get the template thumbnail path from config"""
        return self._config.get("paths", "template_thumbnail")
    
    @property
    def output_dir(self) -> str:
        """Get the output directory from config"""
        return self._config.get("paths", "output_dir")

    @property
    def background_music_path(self) -> Path:
        """Get the background music path from config"""
        return self._config.get("paths", "background_music")
    
    
    # Thumbnail text settings
    @property
    def thumbnail_title_text(self) -> str:
        """Get the title text for thumbnails"""
        return self._config.get("thumbnail", "title_text")
    
    @property
    def thumbnail_watermark_text(self) -> str:
        """Get the watermark text for thumbnails"""
        return self._config.get("thumbnail", "watermark_text")
    
    @property
    def thumbnail_date_format(self) -> str:
        """Get the date format for thumbnails"""
        return self._config.get("thumbnail", "date_format")
    
    # Font settings
    @property
    def thumbnail_font_family(self) -> str:
        """Get the font family for thumbnails"""
        return self._config.get("thumbnail.fonts", "font_family")
    
    @property
    def thumbnail_title_size(self) -> int:
        """Get the title font size for thumbnails"""
        return self._config.getint("thumbnail.fonts", "title_size")
    
    @property
    def thumbnail_date_size(self) -> int:
        """Get the date font size for thumbnails"""
        return self._config.getint("thumbnail.fonts", "date_size")
    
    @property
    def thumbnail_watermark_size(self) -> int:
        """Get the watermark font size for thumbnails"""
        return self._config.getint("thumbnail.fonts", "watermark_size")
    
    # Color settings
    @property
    def thumbnail_text_color(self) -> str:
        """Get the text color for thumbnails"""
        return self._config.get("thumbnail.colors", "text_color")
    
    @property
    def thumbnail_shadow_color(self) -> str:
        """Get the shadow color for thumbnails"""
        return self._config.get("thumbnail.colors", "shadow_color")
    
    @property
    def thumbnail_background_color(self) -> str:
        """Get the background color for thumbnails"""
        return self._config.get("thumbnail.colors", "background_color")
    
    # Layout settings
    @property
    def thumbnail_title_position(self) -> Tuple[int, int]:
        """Get the title position for thumbnails"""
        x = self._config.getint("thumbnail.layout", "title_x")
        y = self._config.getint("thumbnail.layout", "title_y")
        return (x, y)
    
    @property
    def thumbnail_shadow_offset(self) -> int:
        """Get the shadow offset for thumbnails"""
        return self._config.getint("thumbnail.layout", "shadow_offset")
    
    @property
    def thumbnail_watermark_padding(self) -> int:
        """Get the watermark padding for thumbnails"""
        return self._config.getint("thumbnail.layout", "watermark_padding")
    
    def get(self, section: str, option: str, fallback: Optional[str] = None) -> str:
        """Get a configuration value with optional fallback"""
        return self._config.get(section, option, fallback=fallback)

# Create a singleton instance
config = Config() 