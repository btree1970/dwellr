import json
import logging
from typing import Any, AsyncGenerator, Dict

from pydantic_ai.messages import (
    AgentStreamEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ToolCallPartDelta,
)

from src.api.schemas.chat import ChatMessageEvent

logger = logging.getLogger(__name__)


async def stream_agent_response(
    agent_stream: AsyncGenerator[AgentStreamEvent, None],
) -> AsyncGenerator[str, None]:
    """
    Convert pydantic-ai agent stream events to Server-Sent Events format.

    Args:
        agent_stream: AsyncGenerator from UserAgent.chat()

    Yields:
        str: SSE formatted messages
    """
    try:
        # Send session start event
        start_event = ChatMessageEvent(
            type="start", content=None, tool=None, error=None, session_id=None
        )
        yield format_sse_event(start_event.model_dump())

        async for event in agent_stream:
            try:
                # Handle different event types from pydantic-ai ModelRequestNode
                if isinstance(event, PartStartEvent):
                    # New part starting (text or tool call)
                    start_event = ChatMessageEvent(
                        type="part_start",
                        content=f"Starting {event.part.__class__.__name__}",
                        tool=None,
                        error=None,
                        session_id=None,
                    )
                    yield format_sse_event(start_event.model_dump())

                elif isinstance(event, PartDeltaEvent):
                    if isinstance(event.delta, TextPartDelta):
                        # Streaming text content
                        content_event = ChatMessageEvent(
                            type="content",
                            content=event.delta.content_delta,
                            tool=None,
                            error=None,
                            session_id=None,
                        )
                        yield format_sse_event(content_event.model_dump())

                    elif isinstance(event.delta, ToolCallPartDelta):
                        # Tool call arguments being built
                        tool_event = ChatMessageEvent(
                            type="tool_call_delta",
                            content=(
                                str(event.delta.args_delta)
                                if event.delta.args_delta is not None
                                else ""
                            ),
                            tool=None,
                            error=None,
                            session_id=None,
                        )
                        yield format_sse_event(tool_event.model_dump())

                else:
                    final_event = ChatMessageEvent(
                        type="model_complete",
                        content="Model finished generating response",
                        tool=None,
                        error=None,
                        session_id=None,
                    )
                    yield format_sse_event(final_event.model_dump())

            except Exception as e:
                logger.error(f"Error processing agent event: {e}")
                error_event = ChatMessageEvent(
                    type="error",
                    content=None,
                    tool=None,
                    error=f"Stream processing error: {str(e)}",
                    session_id=None,
                )
                yield format_sse_event(error_event.model_dump())

        # Send completion event
        done_event = ChatMessageEvent(
            type="done", content=None, tool=None, error=None, session_id=None
        )
        yield format_sse_event(done_event.model_dump())

    except Exception as e:
        logger.error(f"Error in agent response stream: {e}")
        error_event = ChatMessageEvent(
            type="error",
            content=None,
            tool=None,
            error=f"Agent stream error: {str(e)}",
            session_id=None,
        )
        yield format_sse_event(error_event.model_dump())


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


def create_error_sse_event(error_message: str) -> str:
    """
    Create an SSE formatted error event.

    Args:
        error_message: Error message to send

    Returns:
        str: SSE formatted error event
    """
    error_event = ChatMessageEvent(
        type="error", content=None, tool=None, error=error_message, session_id=None
    )
    return format_sse_event(error_event.model_dump())
