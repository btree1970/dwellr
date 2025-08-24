from dataclasses import dataclass
from typing import Any, List, Literal, Optional

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    UserPromptPart,
)


@dataclass
class ChatToolCall:
    """Standardized tool call format for chat messages."""

    tool_name: str
    args: str


@dataclass
class ChatMessage:
    """Clean chat message format for both CLI and API consumption."""

    role: Literal["user", "assistant"]
    content: str
    tool_calls: Optional[List[ChatToolCall]] = None


class MessageHistoryFormatter:
    def __init__(self, truncate_content: int = 0, truncate_args: int = 0):
        """
        Initialize formatter with truncation limits.

        Args:
            truncate_content: Max length for message content (0 = no truncation)
            truncate_args: Max length for tool call args (0 = no truncation)
        """
        self.truncate_content = truncate_content
        self.truncate_args = truncate_args

    def format_history(self, messages: List[ModelMessage]) -> List[ChatMessage]:
        """
        Convert list of ModelMessage to ChatMessage.

        Args:
            messages: Raw pydantic-ai message history

        Returns:
            List of ChatMessage objects
        """
        chat_messages: List[ChatMessage] = []

        for message in messages:
            try:
                if isinstance(message, ModelRequest) and message.parts:
                    # Handle user messages
                    part = message.parts[0]
                    if isinstance(part, UserPromptPart):
                        content = self._extract_content(part.content)
                        content = self._truncate_text(content, self.truncate_content)

                        chat_message = ChatMessage(role="user", content=content)
                        chat_messages.append(chat_message)

                elif isinstance(message, ModelResponse) and message.parts:
                    # Handle assistant messages
                    text_parts: List[str] = []
                    tool_calls: List[ChatToolCall] = []

                    for part in message.parts:
                        if hasattr(part, "content") and getattr(part, "content", None):
                            content = self._extract_content(getattr(part, "content"))
                            text_parts.append(content)

                        elif isinstance(part, ToolCallPart):
                            args_str = self._format_tool_args(part.args)
                            args_str = self._truncate_text(args_str, self.truncate_args)

                            tool_call = ChatToolCall(
                                tool_name=part.tool_name, args=args_str
                            )
                            tool_calls.append(tool_call)

                    # Combine text content
                    content = " ".join(text_parts) if text_parts else ""
                    content = self._truncate_text(content, self.truncate_content)

                    chat_message = ChatMessage(
                        role="assistant",
                        content=content,
                        tool_calls=tool_calls if tool_calls else None,
                    )
                    chat_messages.append(chat_message)

            except (IndexError, AttributeError, TypeError):
                # Skip malformed messages
                continue

        return chat_messages

    def _extract_content(self, content: Any) -> str:
        """Extract string content from various content types."""
        if isinstance(content, str):
            return content
        elif isinstance(content, (list, tuple)):
            # Handle list of content parts - join them
            # We're intentionally handling Any type here
            return " ".join(str(item) for item in content if item)  # type: ignore
        else:
            return str(content) if content else ""

    def _format_tool_args(self, args: Any) -> str:
        """Format tool arguments for display."""
        if args is None:
            return ""
        else:
            return str(args)

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text if it exceeds max_length."""
        if max_length <= 0 or len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."
