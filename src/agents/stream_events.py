from typing import Literal, Union

from pydantic import BaseModel


class TextStartEvent(BaseModel):
    """Event emitted when text response begins."""

    type: Literal["text_start"] = "text_start"
    content: str


class TextChunkEvent(BaseModel):
    """Event emitted for each chunk of streaming text."""

    type: Literal["text_chunk"] = "text_chunk"
    content: str


class ToolCallEvent(BaseModel):
    """Event emitted when a tool is being called."""

    type: Literal["tool_call"] = "tool_call"
    tool_name: str


UserAgentStreamEvent = Union[TextStartEvent, TextChunkEvent, ToolCallEvent]
