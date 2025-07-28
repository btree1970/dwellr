from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.models.user import User


@dataclass
class UserAgentDependencies:
    db: Session
    user: User
