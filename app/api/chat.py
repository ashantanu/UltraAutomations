from fastapi import APIRouter
from pydantic import BaseModel
from app.core.langgraph_setup import create_workflow

router = APIRouter()
workflow = create_workflow()

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat(request: ChatRequest):
    result = workflow.invoke({"message": request.message})
    return {"response": result["response"]} 