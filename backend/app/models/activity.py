"""
Activity Models
Defines activity and exercise tracking structures.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class ActivityType(str, Enum):
    """Type of learning activity"""
    VOCABULARY_EXERCISE = "vocabulary_exercise"
    GRAMMAR_LESSON = "grammar_lesson"
    GRAMMAR_EXERCISE = "grammar_exercise"
    GRAMMAR_EXPLANATION = "grammar_explanation"
    PRONUNCIATION_EXERCISE = "pronunciation_exercise"
    SHADOWING = "shadowing"
    SPEAKING_SESSION = "speaking_session"
    ASSESSMENT = "assessment"
    REVIEW = "review"


class ActivityStatus(str, Enum):
    """Activity completion status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class Pillar(str, Enum):
    """Learning pillar"""
    VOCABULARY = "vocabulary"
    GRAMMAR = "grammar"
    PRONUNCIATION = "pronunciation"
    SPEAKING = "speaking"


class ActivitySource(str, Enum):
    """How the activity was created"""
    SCHEDULED = "scheduled"  # From SRS scheduler
    ERROR_GENERATED = "error_generated"  # From error in speaking
    USER_SELECTED = "user_selected"  # User chose this activity
    ASSESSMENT = "assessment"  # From assessment
    SYSTEM = "system"  # System recommendation


class Activity(BaseModel):
    """Learning activity"""
    id: str
    user_id: str
    partition_key: str  # Same as user_id

    # Activity info
    type: ActivityType
    pillar: Pillar
    status: ActivityStatus = ActivityStatus.PENDING

    # Source and context
    source: ActivitySource = ActivitySource.SCHEDULED
    source_error_id: Optional[str] = None  # If generated from an error
    source_session_id: Optional[str] = None  # If from a speaking session

    # Content
    content: dict = Field(
        default_factory=dict,
        description="Activity-specific content (word_id, rule_id, etc.)"
    )

    # Priority
    priority: str = Field(default="normal", description="high, normal, low")

    # Result
    result: Optional[dict] = Field(
        default=None,
        description="Result data when completed"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class ActivityCreate(BaseModel):
    """Model for creating a new activity"""
    type: ActivityType
    pillar: Pillar
    source: ActivitySource = ActivitySource.SYSTEM
    source_error_id: Optional[str] = None
    source_session_id: Optional[str] = None
    content: dict = Field(default_factory=dict)
    priority: str = "normal"

    class Config:
        use_enum_values = True


class ActivityResult(BaseModel):
    """Result of completing an activity"""
    activity_id: str
    correct: Optional[bool] = None
    score: Optional[float] = None
    response_time_ms: Optional[int] = None
    user_answer: Optional[Any] = None
    correct_answer: Optional[Any] = None
    feedback: Optional[str] = None
    additional_data: dict = Field(default_factory=dict)


class SpeakingSession(BaseModel):
    """A speaking/conversation session"""
    id: str
    user_id: str
    partition_key: str

    # Session info
    topic: str
    level: str

    # Conversation
    exchanges: list[dict] = Field(
        default_factory=list,
        description="List of {turn, speaker, text, audio_url?, errors?}"
    )

    # Error tracking
    errors_detected: list[dict] = Field(default_factory=list)
    grammar_errors_count: int = Field(default=0)
    pronunciation_errors_count: int = Field(default=0)

    # Generated activities
    generated_activity_ids: list[str] = Field(default_factory=list)

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

    # Summary (filled when session ends)
    summary: Optional[dict] = None


class SpeakingExchange(BaseModel):
    """A single exchange in a speaking session"""
    turn: int
    speaker: str = Field(..., description="agent or user")
    text: str
    audio_url: Optional[str] = None
    audio_base64: Optional[str] = None
    errors: list[dict] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SpeakingSessionSummary(BaseModel):
    """Summary of a completed speaking session"""
    total_turns: int
    duration_seconds: int
    topics_covered: list[str]
    grammar_errors: list[dict]
    pronunciation_errors: list[dict]
    new_activities_count: int
    overall_fluency: float = Field(..., ge=0, le=100)
    feedback: str