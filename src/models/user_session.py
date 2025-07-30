from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.db import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    message_history: Mapped[Optional[Dict[Any, Any]]] = mapped_column(
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

    def set_message_history(self, messages: Any):
        self.message_history = messages

    def get_message_history(self) -> Optional[Dict[Any, Any]]:
        return self.message_history
