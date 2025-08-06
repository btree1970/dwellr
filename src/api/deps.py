from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.supabase import get_supabase_client
from src.models.user import User
from src.services.user_service import UserService
from supabase._async.client import AsyncClient

# Security scheme for JWT token extraction
security = HTTPBearer()

# Type aliases for dependencies
SessionDep = Annotated[Session, Depends(get_db)]
SupabaseDep = Annotated[AsyncClient, Depends(get_supabase_client)]
TokenDep = Annotated[HTTPAuthorizationCredentials, Depends(security)]


async def get_current_user(
    token: TokenDep, supabase: SupabaseDep, session: SessionDep
) -> User:
    """Validate JWT token and return User model from database"""
    try:
        # Validate token with Supabase
        user_response = await supabase.auth.get_user(jwt=token.credentials)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )

        supabase_user = user_response.user
        supabase_user_id = supabase_user.id

        # Use UserService to find or create user
        user_service = UserService(session)
        user_metadata = supabase_user.user_metadata or {}
        user_name = (
            user_metadata.get("full_name") or user_metadata.get("name") or "User"
        )

        user = user_service.find_or_create_user(
            auth_user_id=supabase_user_id,
            name=user_name,
            evaluation_credits=5.0,  # Give new users some starting credits
        )

        return user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )


CurrentUser = Annotated[User, Depends(get_current_user)]
