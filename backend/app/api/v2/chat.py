from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import get_optional_user
from app.core.gpt_client import BOQChatClient
from app.core.ollama_client import OllamaClient

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    language: Optional[str] = "en"
    engine: Optional[str] = "auto"


class ChatResponse(BaseModel):
    success: bool
    content: str
    tokens_used: int = 0
    engine: str = "rule-based"


class ChatModelItem(BaseModel):
    id: str
    name: str
    provider: str
    available: bool


chat_client = BOQChatClient()
ollama_client = OllamaClient()


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, user: dict = Depends(get_optional_user)):
    try:
        if req.engine in ("auto", "ollama"):
            if await ollama_client.is_available():
                r = await ollama_client.chat(req.messages, req.language)
                if r["success"]:
                    return ChatResponse(**r)

        r = await chat_client.chat(
            user_id=user.get("id", ""),
            messages=req.messages,
            language=req.language,
        )
        return ChatResponse(
            success=r["success"],
            content=r["content"],
            tokens_used=r.get("tokens_used", 0),
            engine=r.get("engine", "rule-based"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/models", response_model=List[ChatModelItem])
async def list_models(user: dict = Depends(get_optional_user)):
    ollama_available = await ollama_client.is_available()
    ollama_models = []
    if ollama_available:
        ollama_models = await ollama_client.list_models()
    models: List[ChatModelItem] = []
    if ollama_available:
        for m in ollama_models:
            models.append(ChatModelItem(id=m.get("name", m), name=m.get("name", m), provider="ollama", available=True))
    if chat_client.use_openai:
        models.append(ChatModelItem(id="gpt-4o", name="GPT-4o", provider="openai", available=True))
    if chat_client.use_anthropic:
        models.append(ChatModelItem(id="claude-3-sonnet", name="Claude 3 Sonnet", provider="anthropic", available=True))
    if not models:
        models.append(ChatModelItem(id="rule-based", name="Rule-Based Engine", provider="built-in", available=True))
    return models