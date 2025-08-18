import json
import logging
from typing import Any, AsyncGenerator, Dict

from src.agents.stream_events import UserAgentStreamEvent

logger = logging.getLogger(__name__)


async def stream_agent_response(
    agent_stream: AsyncGenerator[UserAgentStreamEvent, None],
) -> AsyncGenerator[str, None]:
    """
    Convert UserAgent stream events to Server-Sent Events format.

    Args:
        agent_stream: AsyncGenerator from UserAgent.chat()

    Yields:
        str: SSE formatted messages
    """
    async for event in agent_stream:
        yield format_sse_event(event.model_dump())

    # Send completion event when stream ends
    yield format_sse_event({"type": "done"})


def format_sse_event(data: Dict[str, Any]) -> str:
    """
    Format data as Server-Sent Event.

    Args:
        data: Dictionary to send as JSON

    Returns:
        str: SSE formatted string
    """
    json_data = json.dumps(data, default=str)
    return f"data: {json_data}\n\n"


async def create_error_stream(
    error_message: str, error_type: str = "error"
) -> AsyncGenerator[str, None]:
    """
    Create an async generator that yields a single SSE error event.

    Args:
        error_message: Error message to send
        error_type: Type of error (default: "error")

    Yields:
        str: SSE formatted error event
    """
    error_event = {"type": error_type, "error": error_message}
    yield format_sse_event(error_event)
