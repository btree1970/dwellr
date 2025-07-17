from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.user import User


class UserServiceException(Exception):
    pass


class UserNotFound(UserServiceException):
    pass


class UserValidationError(UserServiceException):
    pass


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, name: str, email: str, **kwargs: Any) -> User:
        try:
            user = User(name=name, email=email, **kwargs)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user

        except IntegrityError as e:
            self.db.rollback()
            if "email" in str(e):
                raise UserValidationError(f"Email {email} already exists")
            raise UserValidationError(f"Database constraint violation: {e}")
        except Exception as e:
            self.db.rollback()
            raise UserServiceException(f"Error creating user: {e}")

    def get_user_by_id(self, user_id: str) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFound(f"User with ID {user_id} not found")
        return user
