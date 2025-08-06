from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from supabase._async.client import AsyncClient

from src.core.database import get_db_session
from src.core.supabase import get_supabase_client
from src.models.user import User

# Security scheme for JWT token extraction
security = HTTPBearer()

# Type aliases for dependencies
SessionDep = Annotated[Session, Depends(get_db_session)]
SupabaseDep = Annotated[AsyncClient, Depends(get_supabase_client)]
TokenDep = Annotated[HTTPAuthorizationCredentials, Depends(security)]


async def get_current_user(
    token: TokenDep, supabase: SupabaseDep, session: SessionDep
) -> User:
    """Validate JWT token and return User model from database"""
    try:
        # Validate token with Supabase
        user_response = await supabase.auth.get_user(jwt=token.credentials)
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )

        supabase_user_id = user_response.user.id

        # Find user in your database by auth_user_id (we'll add this field)
        # For now, let's find by email as fallback
        user_email = user_response.user.email
        user = session.query(User).filter(User.email == user_email).first()

        if not user:
            # Create user if doesn't exist (first login after Supabase signup)
            user = User(
                email=user_email,
                name=user_response.user.user_metadata.get("name", ""),
                # We'll add auth_user_id field later
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        return user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )


CurrentUser = Annotated[User, Depends(get_current_user)]
