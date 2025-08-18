import logging
from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.agents.user_agent import UserAgent
from src.api.deps import CurrentUser, get_db
from src.api.schemas.chat import (
    ChatHistoryMessage,
    ChatHistoryResponse,
    ChatMessageRequest,
)
from src.api.utils.sse import create_error_stream, stream_agent_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
}


@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """
    Send a message to the agent and stream the response via Server-Sent Events.

    The session is automatically created or loaded for the authenticated user.
    Empty messages are allowed - the agent will initiate conversation for new sessions.
    """
    try:
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
            headers=SSE_HEADERS,
        )

    except ValueError as e:
        logger.info(f"Value Error: {e}")

        return StreamingResponse(
            create_error_stream(str(e), "validation_error"),
            media_type="text/event-stream",
            status_code=400,
            headers=SSE_HEADERS,
        )

    except Exception as e:
        logger.error(f"Unexpected error processing chat message: {e}", exc_info=True)

        return StreamingResponse(
            create_error_stream(f"Agent processing failed: {str(e)}", "agent_error"),
            media_type="text/event-stream",
            status_code=500,
            headers=SSE_HEADERS,
        )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> ChatHistoryResponse:
    """
    Get the conversation history for the current user's session.

    UserAgent handles session management gracefully:
    - Returns empty history if no session exists
    - Creates new session if existing one can't be loaded
    """
    user_agent = UserAgent(db_session=db, user=current_user)
    chat_messages = user_agent.get_message_history()

    if not chat_messages:
        return ChatHistoryResponse(
            messages=[],
            session_id=user_agent.session_id,
            total_messages=0,
        )

    api_messages: List[ChatHistoryMessage] = []
    for message in chat_messages:
        # Convert tool calls to API format
        tool_calls_dict = None
        if message.tool_calls:
            tool_calls_dict = [
                {"tool_name": tool_call.tool_name, "args": tool_call.args}
                for tool_call in message.tool_calls
            ]

        api_message = ChatHistoryMessage(
            role=message.role,
            content=message.content,
            tool_calls=tool_calls_dict,
            timestamp=None,
        )
        api_messages.append(api_message)

    return ChatHistoryResponse(
        messages=api_messages,
        session_id=user_agent.session_id,
        total_messages=len(api_messages),
    )
