from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    message: str = Field(
        ..., min_length=1, description="User message to send to the agent"
    )


class ChatHistoryMessage(BaseModel):
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        None, description="Tool calls made during this message"
    )


class ChatHistoryResponse(BaseModel):
    messages: List[ChatHistoryMessage] = Field(..., description="Conversation history")
    session_id: str = Field(..., description="Current session ID")
    total_messages: int = Field(..., description="Total number of messages")
