"""
User Models
Defines user-related data structures.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserLevel(str, Enum):
    """User proficiency level"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"


class UserProfile(BaseModel):
    """User profile settings"""
    learning_goals: list[str] = Field(
        default=["general"],
        description="Learning goals (e.g., general, data_engineering, ai)"
    )
    native_language: str = Field(default="pt-BR", description="User's native language")
    preferred_study_time: str = Field(default="evening", description="Preferred study time")
    daily_goal_minutes: int = Field(default=30, ge=5, le=180, description="Daily study goal in minutes")
    notifications_enabled: bool = Field(default=True)
    voice_preference: str = Field(default="american_female", description="Preferred TTS voice")


class UserCreate(BaseModel):
    """Model for creating a new user"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=2)
    profile: Optional[UserProfile] = None


class User(BaseModel):
    """User model"""
    id: str
    email: EmailStr
    name: str
    password_hash: str
    current_level: UserLevel = Field(default=UserLevel.BEGINNER)
    profile: UserProfile = Field(default_factory=UserProfile)

    # Progress tracking
    total_study_time_minutes: int = Field(default=0)
    current_streak_days: int = Field(default=0)
    longest_streak_days: int = Field(default=0)
    last_activity_date: Optional[datetime] = None

    # Assessment data
    initial_assessment_completed: bool = Field(default=False)
    last_assessment_date: Optional[datetime] = None
    sessions_since_last_assessment: int = Field(default=0)

    # Pillar scores (0-100)
    vocabulary_score: int = Field(default=0, ge=0, le=100)
    grammar_score: int = Field(default=0, ge=0, le=100)
    pronunciation_score: int = Field(default=0, ge=0, le=100)
    speaking_score: int = Field(default=0, ge=0, le=100)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    partition_key: Optional[str] = None

    class Config:
        use_enum_values = True


class UserResponse(BaseModel):
    """User response model (without sensitive data)"""
    id: str
    email: EmailStr
    name: str
    current_level: UserLevel
    profile: UserProfile
    total_study_time_minutes: int
    current_streak_days: int
    vocabulary_score: int
    grammar_score: int
    pronunciation_score: int
    speaking_score: int
    initial_assessment_completed: bool

    class Config:
        use_enum_values = True


class UserLogin(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse