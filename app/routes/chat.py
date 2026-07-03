from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.copilot_agent import ask_copilot

router = APIRouter()


class ChatRequest(BaseModel):
    query: str


@router.post("/agent/chat")
def chat_with_copilot(request: ChatRequest):
    """Natural language interface endpoint."""
    answer = ask_copilot(request.query)
    return {"query": request.query, "response": answer}