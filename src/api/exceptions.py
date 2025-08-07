from fastapi import HTTPException
from starlette import status


class ChatAPIException(HTTPException):
    """Base exception for chat API errors"""

    def __init__(
        self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        super().__init__(status_code=status_code, detail=detail)


class ChatSessionException(ChatAPIException):
    """Exception for session-related errors"""

    def __init__(self, detail: str):
        super().__init__(
            detail=detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class ChatMessageException(ChatAPIException):
    """Exception for message processing errors"""

    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)
