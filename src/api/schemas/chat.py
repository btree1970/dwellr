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


class ChatMessageEvent(BaseModel):
    """Server-Sent Event data structure for chat messages"""

    type: str = Field(
        ...,
        description="Event type: start, content, part_start, tool_call_delta, model_complete, error, done",
    )
    content: Optional[str] = Field(None, description="Message content")
    tool: Optional[str] = Field(None, description="Tool name for tool events")
    error: Optional[str] = Field(None, description="Error message for 'error' events")
    session_id: Optional[str] = Field(None, description="Session ID")


class ChatErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    session_id: Optional[str] = Field(None, description="Session ID if available")
