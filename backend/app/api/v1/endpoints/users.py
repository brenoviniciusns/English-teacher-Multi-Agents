"""
Users API Endpoints
REST API for user registration, authentication, and profile management.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
import uuid

from app.models.user import (
    UserCreate,
    User,
    UserResponse,
    UserLogin,
    Token,
    UserProfile,
    UserLevel
)
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.dependencies import get_current_user, get_current_user_response
from app.services.cosmos_db_service import cosmos_db_service


logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== AUTHENTICATION ENDPOINTS ====================

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate):
    """
    Register a new user.

    Creates a new user account with the provided details.
    Returns a JWT token for immediate authentication.
    """
    try:
        # Check if email already exists
        existing_user = await cosmos_db_service.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado"
            )

        # Generate unique user ID
        user_id = str(uuid.uuid4())

        # Create user object
        user = User(
            id=user_id,
            email=user_data.email,
            name=user_data.name,
            password_hash=get_password_hash(user_data.password),
            current_level=UserLevel.BEGINNER,
            profile=user_data.profile or UserProfile(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            partition_key=user_id
        )

        # Save to database
        user_dict = user.model_dump()
        user_dict["partitionKey"] = user_id  # Cosmos DB partition key
        await cosmos_db_service.create_user(user_dict)

        # Create access token
        access_token = create_access_token(data={"sub": user_id})

        # Create user response (without sensitive data)
        user_response = UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            current_level=user.current_level,
            profile=user.profile,
            total_study_time_minutes=user.total_study_time_minutes,
            current_streak_days=user.current_streak_days,
            vocabulary_score=user.vocabulary_score,
            grammar_score=user.grammar_score,
            pronunciation_score=user.pronunciation_score,
            speaking_score=user.speaking_score,
            initial_assessment_completed=user.initial_assessment_completed
        )

        logger.info(f"New user registered: {user.email}")

        return Token(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao registrar usuário: {str(e)}"
        )


@router.post("/login", response_model=Token)
async def login_user(credentials: UserLogin):
    """
    Authenticate a user and return a JWT token.
    """
    try:
        # Find user by email
        user_data = await cosmos_db_service.get_user_by_email(credentials.email)

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )

        # Verify password
        if not verify_password(credentials.password, user_data.get("password_hash", "")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )

        # Create access token
        access_token = create_access_token(data={"sub": user_data["id"]})

        # Create user response
        user_response = UserResponse(
            id=user_data["id"],
            email=user_data["email"],
            name=user_data["name"],
            current_level=user_data.get("current_level", "beginner"),
            profile=user_data.get("profile", {}),
            total_study_time_minutes=user_data.get("total_study_time_minutes", 0),
            current_streak_days=user_data.get("current_streak_days", 0),
            vocabulary_score=user_data.get("vocabulary_score", 0),
            grammar_score=user_data.get("grammar_score", 0),
            pronunciation_score=user_data.get("pronunciation_score", 0),
            speaking_score=user_data.get("speaking_score", 0),
            initial_assessment_completed=user_data.get("initial_assessment_completed", False)
        )

        logger.info(f"User logged in: {credentials.email}")

        return Token(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao fazer login: {str(e)}"
        )


# ==================== USER PROFILE ENDPOINTS ====================

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: UserResponse = Depends(get_current_user_response)
):
    """
    Get current authenticated user's profile.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    profile_update: UserProfile,
    current_user: dict = Depends(get_current_user)
):
    """
    Update current user's profile settings.
    """
    try:
        # Update profile
        updated_user = await cosmos_db_service.update_user(
            current_user["id"],
            {
                "profile": profile_update.model_dump(),
                "updated_at": datetime.utcnow().isoformat()
            }
        )

        return UserResponse(
            id=updated_user["id"],
            email=updated_user["email"],
            name=updated_user["name"],
            current_level=updated_user.get("current_level", "beginner"),
            profile=updated_user.get("profile", {}),
            total_study_time_minutes=updated_user.get("total_study_time_minutes", 0),
            current_streak_days=updated_user.get("current_streak_days", 0),
            vocabulary_score=updated_user.get("vocabulary_score", 0),
            grammar_score=updated_user.get("grammar_score", 0),
            pronunciation_score=updated_user.get("pronunciation_score", 0),
            speaking_score=updated_user.get("speaking_score", 0),
            initial_assessment_completed=updated_user.get("initial_assessment_completed", False)
        )

    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar perfil: {str(e)}"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a user by ID.

    Note: In a production app, you might want to restrict this
    to only return the user's own data or require admin privileges.
    """
    try:
        # For security, only allow users to view their own profile
        if current_user["id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado"
            )

        user_data = await cosmos_db_service.get_user(user_id)

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )

        return UserResponse(
            id=user_data["id"],
            email=user_data["email"],
            name=user_data["name"],
            current_level=user_data.get("current_level", "beginner"),
            profile=user_data.get("profile", {}),
            total_study_time_minutes=user_data.get("total_study_time_minutes", 0),
            current_streak_days=user_data.get("current_streak_days", 0),
            vocabulary_score=user_data.get("vocabulary_score", 0),
            grammar_score=user_data.get("grammar_score", 0),
            pronunciation_score=user_data.get("pronunciation_score", 0),
            speaking_score=user_data.get("speaking_score", 0),
            initial_assessment_completed=user_data.get("initial_assessment_completed", False)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar usuário: {str(e)}"
        )
