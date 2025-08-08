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
    try:
        async for event in agent_stream:
            try:
                yield format_sse_event(event.model_dump())
            except Exception as e:
                logger.error(f"Error processing agent event: {e}")
                error_event = {
                    "type": "error",
                    "error": f"Stream processing error: {str(e)}",
                }
                yield format_sse_event(error_event)

        # Send completion event
        done_event = {"type": "done"}
        yield format_sse_event(done_event)

    except Exception as e:
        logger.error(f"Error in agent response stream: {e}")
        error_event = {"type": "error", "error": f"Agent stream error: {str(e)}"}
        yield format_sse_event(error_event)


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
