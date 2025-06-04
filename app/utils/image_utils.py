from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os
import requests
import tempfile
from pathlib import Path
import pytz
from app.utils.logging_utils import get_logger

# Set up logging
logger = get_logger(__name__)

def download_google_font(font_name, font_style="regular"):
    """
    Download a Google Font and return the path to the downloaded font file.
    
    Args:
        font_name (str): Name of the Google Font (e.g., 'Roboto', 'OpenSans')
        font_style (str): Font style (e.g., 'regular', 'bold', 'black')
    
    Returns:
        str: Path to the downloaded font file
    """
    # Create a temporary directory for fonts if it doesn't exist
    font_dir = Path(tempfile.gettempdir()) / "google_fonts"
    font_dir.mkdir(exist_ok=True)
    
    # Map font styles to Google Fonts weights
    weight_map = {
        "regular": "400",
        "medium": "500",
        "semibold": "600",
        "bold": "700",
        "extrabold": "800",
        "black": "900"
    }
    
    weight = weight_map.get(font_style.lower(), "400")
    
    # Convert font name to Google Fonts URL format
    font_url_name = font_name.replace(" ", "+")
    
    # Direct download URL for the font file
    url = f"https://fonts.googleapis.com/css2?family={font_url_name}:wght@{weight}&display=swap"
    
    logger.info(f"Fetching font CSS from: {url}")
    
    # Get the CSS file
    response = requests.get(url)
    if response.status_code != 200:
        logger.error(f"Failed to download font {font_name}: {response.status_code}")
        return None
    
    # Extract the font URL from the CSS
    css_content = response.text
    font_url = None
    
    # Look for the font URL in the CSS content
    for line in css_content.split('\n'):
        if 'src: url(' in line:
            # Extract URL between url( and )
            start = line.find('url(') + 4
            end = line.find(')', start)
            if start > 4 and end > start:
                font_url = line[start:end].strip("'\"")
                if 'woff2' in font_url:
                    break
    
    if not font_url:
        logger.error(f"Could not find font URL for {font_name}. CSS content: {css_content}")
        return None
    
    # Download the font file
    font_path = font_dir / f"{font_name}_{font_style}.woff2"
    if not font_path.exists():
        logger.info(f"Downloading font from: {font_url}")
        font_response = requests.get(font_url)
        if font_response.status_code == 200:
            with open(font_path, 'wb') as f:
                f.write(font_response.content)
            logger.info(f"Font downloaded successfully to: {font_path}")
        else:
            logger.error(f"Failed to download font file for {font_name}: {font_response.status_code}")
            return None
    
    return str(font_path)

def add_text_overlay(image_path, output_path=None):
    """
    Add text overlays to an image with title, date, and watermark.
    Ensures the output meets YouTube thumbnail requirements.
    
    Args:
        image_path (str): Path to the input image
        output_path (str, optional): Path to save the output image. If None, will overwrite input image.
    
    Returns:
        str: Path to the output image
    """
    logger.info(f"Processing image: {image_path}")
    
    # Open the image
    img = Image.open(image_path)
    logger.info(f"Original image size: {img.size}, mode: {img.mode}")
    
    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
        logger.info("Converted image to RGB mode")
    
    # Resize to YouTube recommended dimensions (1280x720) while maintaining aspect ratio
    target_width = 1280
    target_height = 720
    
    # Calculate new dimensions maintaining aspect ratio
    img_ratio = img.width / img.height
    target_ratio = target_width / target_height
    
    if img_ratio > target_ratio:
        # Image is wider than target
        new_width = target_width
        new_height = int(target_width / img_ratio)
    else:
        # Image is taller than target
        new_height = target_height
        new_width = int(target_height * img_ratio)
    
    logger.info(f"Resizing image to: {new_width}x{new_height}")
    
    # Resize image
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Create a new image with target dimensions and black background
    final_img = Image.new('RGB', (target_width, target_height), 'black')
    
    # Paste the resized image in the center
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2
    final_img.paste(img, (paste_x, paste_y))
    
    draw = ImageDraw.Draw(final_img)
    
    # Download and load Google Fonts
    logger.info("Downloading fonts")
    title_font_path = download_google_font("Roboto", "black")
    date_font_path = download_google_font("Roboto", "regular")
    watermark_font_path = download_google_font("Roboto", "extrabold")
    
    try:
        title_font = ImageFont.truetype(title_font_path, 120)
        date_font = ImageFont.truetype(date_font_path, 70)
        watermark_font = ImageFont.truetype(watermark_font_path, 80)
        logger.info("Successfully loaded Google Fonts")
    except Exception as e:
        logger.warning(f"Failed to load Google Fonts: {str(e)}")
        title_font = ImageFont.load_default()
        date_font = ImageFont.load_default()
        watermark_font = ImageFont.load_default()
        logger.info("Using default fonts")
    
    # Add title text with shadow for better visibility
    title = "UltraSummary\nAI Recap"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    
    # Position title at left side with some padding
    title_x = 60
    title_y = 60
    
    # Add shadow effect for better visibility
    shadow_offset = 3
    draw.text((title_x + shadow_offset, title_y + shadow_offset), title, font=title_font, fill="black")
    draw.text((title_x, title_y), title, font=title_font, fill="white")
    
    # Add date with shadow
    today = datetime.now(pytz.timezone('US/Pacific')).strftime("%b - %d - %y")
    date_bbox = draw.textbbox((0, 0), today, font=date_font)
    date_width = date_bbox[2] - date_bbox[0]
    
    # Position date below title
    date_x = title_x
    date_y = title_y + title_height + 50
    
    # Add shadow effect for date
    draw.text((date_x + shadow_offset, date_y + shadow_offset), today, font=date_font, fill="black")
    draw.text((date_x, date_y), today, font=date_font, fill="white")
    
    # Add watermark with shadow
    watermark = "[OFA]"
    watermark_bbox = draw.textbbox((0, 0), watermark, font=watermark_font)
    watermark_width = watermark_bbox[2] - watermark_bbox[0]
    
    # Position watermark at bottom right
    watermark_x = target_width - watermark_width - 40
    watermark_y = target_height - 120
    
    # Add shadow effect for watermark
    draw.text((watermark_x + shadow_offset, watermark_y + shadow_offset), watermark, font=watermark_font, fill="black")
    draw.text((watermark_x, watermark_y), watermark, font=watermark_font, fill="white")
    
    # Save the image
    if output_path is None:
        output_path = image_path
    
    # Save as PNG with optimization
    final_img.save(output_path, "PNG", optimize=True)
    
    # Check file size
    file_size = os.path.getsize(output_path) / (1024 * 1024)  # Convert to MB
    if file_size > 2:
        print(f"Warning: Output file size ({file_size:.2f} MB) exceeds YouTube's 2MB limit")
    
    return output_path 