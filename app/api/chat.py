from fastapi import APIRouter
from pydantic import BaseModel
from openai import OpenAI
import os

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(request: ChatRequest):
    """Simple chat endpoint using OpenAI."""
    response = client.chat.completions.create(
        model="gpt-5.2-instant",
        messages=[{"role": "user", "content": request.message}]
    )
    return {"response": response.choices[0].message.content}
