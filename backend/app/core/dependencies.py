"""
FastAPI Dependencies
Dependency injection for authentication and authorization.
"""
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import verify_token
from app.services.cosmos_db_service import cosmos_db_service
from app.models.user import User, UserResponse


logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Get current user from JWT token (optional).

    Returns None if no token is provided or token is invalid.
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    # Get user from database
    user_data = await cosmos_db_service.get_user(user_id)
    return user_data


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Get current user from JWT token (required).

    Raises 401 if token is missing or invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    # Get user from database
    user_data = await cosmos_db_service.get_user(user_id)
    if not user_data:
        raise credentials_exception

    return user_data


async def get_current_user_response(
    current_user: dict = Depends(get_current_user)
) -> UserResponse:
    """
    Get current user as UserResponse model.

    Filters out sensitive data like password hash.
    """
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        current_level=current_user.get("current_level", "beginner"),
        profile=current_user.get("profile", {}),
        total_study_time_minutes=current_user.get("total_study_time_minutes", 0),
        current_streak_days=current_user.get("current_streak_days", 0),
        vocabulary_score=current_user.get("vocabulary_score", 0),
        grammar_score=current_user.get("grammar_score", 0),
        pronunciation_score=current_user.get("pronunciation_score", 0),
        speaking_score=current_user.get("speaking_score", 0),
        initial_assessment_completed=current_user.get("initial_assessment_completed", False)
    )
