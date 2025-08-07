import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    UserPromptPart,
)
from sqlalchemy.orm import Session

from src.agents.user_agent import UserAgent
from src.api.deps import CurrentUser, get_db
from src.api.exceptions import ChatMessageException, ChatSessionException
from src.api.schemas.chat import (
    ChatHistoryMessage,
    ChatHistoryResponse,
    ChatMessageRequest,
)
from src.api.utils.sse import create_error_sse_event, stream_agent_response
from src.models.user_session import UserSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """
    Send a message to the agent and stream the response via Server-Sent Events.

    The session is automatically created or loaded for the authenticated user.
    """
    try:
        # Validate message
        if not request.message.strip():
            raise ChatMessageException("Message cannot be empty")

        # Initialize UserAgent (automatically handles session management)
        user_agent = UserAgent(db_session=db, user=current_user)

        logger.info(f"Processing message for user {current_user.id}")

        # Get agent response stream
        agent_stream = user_agent.chat(user_prompt=request.message)

        # Stream response as SSE
        response_stream = stream_agent_response(agent_stream)

        return StreamingResponse(
            response_stream,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )

    except ValueError as e:
        # Handle validation errors from UserAgent
        logger.error(f"Validation error in chat message: {e}")
        error_stream = async_error_stream(str(e), "validation_error")
        return StreamingResponse(
            error_stream,
            media_type="text/event-stream",
            status_code=400,
        )

    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        error_stream = async_error_stream(
            f"Agent processing failed: {str(e)}", "agent_error"
        )
        return StreamingResponse(
            error_stream,
            media_type="text/event-stream",
            status_code=500,
        )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> ChatHistoryResponse:
    """
    Get the conversation history for the current user's session.
    """
    try:
        # Get user session
        user_session = db.query(UserSession).filter_by(user_id=current_user.id).first()

        if not user_session or not user_session.session_id:
            # No session exists yet - return empty history
            return ChatHistoryResponse(
                messages=[],
                session_id="",
                total_messages=0,
            )

        # Get message history
        message_history = user_session.get_message_history() or []

        # Convert pydantic-ai messages to API format
        api_messages: List[ChatHistoryMessage] = []
        for message in message_history:
            try:
                # Handle ModelRequest (user messages)
                if isinstance(message, ModelRequest) and message.parts:
                    part = message.parts[0]
                    if isinstance(part, UserPromptPart):
                        # Assume content is always a string for our use case
                        content = str(part.content) if part.content else ""
                        api_message = ChatHistoryMessage(
                            role="user",
                            content=content,
                            tool_calls=None,
                            timestamp=None,
                        )
                        api_messages.append(api_message)

                # Handle ModelResponse (assistant messages)
                elif isinstance(message, ModelResponse) and message.parts:
                    # Collect all text content from response parts
                    text_content: List[str] = []
                    tool_calls: List[Dict[str, Any]] = []

                    for part in message.parts:
                        # Handle specific part types we know about
                        if isinstance(part, TextPart):
                            text_content.append(part.content)
                        elif isinstance(part, ToolCallPart):
                            tool_calls.append(
                                {
                                    "tool_name": part.tool_name,
                                    "args": (
                                        part.args
                                        if isinstance(part.args, dict)
                                        else str(part.args)
                                    ),
                                }
                            )

                    # Create assistant message
                    if text_content or tool_calls:
                        api_message = ChatHistoryMessage(
                            role="assistant",
                            content=" ".join(text_content) if text_content else "",
                            tool_calls=tool_calls if tool_calls else None,
                            timestamp=None,
                        )
                        api_messages.append(api_message)

            except Exception as e:
                logger.warning(f"Failed to parse message: {e}")
                # Skip malformed messages rather than failing entirely
                continue

        return ChatHistoryResponse(
            messages=api_messages,
            session_id=user_session.session_id,
            total_messages=len(api_messages),
        )

    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        raise ChatSessionException(f"Failed to retrieve chat history: {str(e)}")


async def async_error_stream(error_message: str, error_type: str):
    """Async generator for streaming error responses"""
    yield create_error_sse_event(error_message)
