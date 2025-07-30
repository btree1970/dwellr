from datetime import datetime, timezone
from typing import Any, Optional

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.db import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    message_history: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSON, nullable=True
    )
    initiated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def set_message_history(self, messages: list[ModelMessage]) -> None:
        self.message_history = ModelMessagesTypeAdapter.dump_python(
            messages, mode="json"
        )

    def get_message_history(self) -> Optional[list[ModelMessage]]:
        if self.message_history:
            return ModelMessagesTypeAdapter.validate_python(self.message_history)
        return None
