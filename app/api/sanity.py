from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.utils.image_utils import add_text_overlay
import os
from pathlib import Path

router = APIRouter(prefix="/sanity")

class ImageRequest(BaseModel):
    template_path: str

@router.post("/process-image")
async def process_image(request: ImageRequest):
    try:
        base_dir = Path(__file__).parent.parent.parent
        template_path = base_dir / "assets" / request.template_path
        
        if not template_path.exists():
            raise HTTPException(status_code=404, detail="Template image not found")
            
        # Create output path in assets directory
        output_filename = f"processed_{Path(request.template_path).name}"
        output_path = base_dir / "assets" / output_filename
        
        # Process the image
        result_path = add_text_overlay(str(template_path), str(output_path))
        
        if not result_path or not os.path.exists(result_path):
            raise HTTPException(status_code=500, detail="Failed to process image")
            
        # Return the actual image file
        return FileResponse(
            path=result_path,
            media_type="image/png",
            filename=output_filename
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 