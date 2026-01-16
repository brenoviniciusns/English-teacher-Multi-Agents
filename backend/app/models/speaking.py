"""
Speaking Models
Defines speaking session and conversation structures.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Speaking session status"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class TopicDifficulty(str, Enum):
    """Conversation topic difficulty"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ErrorType(str, Enum):
    """Type of error detected"""
    GRAMMAR = "grammar"
    PRONUNCIATION = "pronunciation"
    VOCABULARY = "vocabulary"


class ConversationTopic(BaseModel):
    """A conversation topic for speaking practice"""
    id: str
    name: str
    name_pt: str = Field(..., description="Topic name in Portuguese")
    description: str
    description_pt: str = Field(..., description="Description in Portuguese")
    difficulty: TopicDifficulty = TopicDifficulty.BEGINNER
    category: str = Field(default="general", description="Topic category")
    sample_questions: list[str] = Field(default_factory=list)
    vocabulary_hints: list[str] = Field(default_factory=list)
    grammar_focus: list[str] = Field(default_factory=list, description="Grammar rules relevant to topic")
    opening_prompts: list[str] = Field(default_factory=list, description="Possible opening lines")

    class Config:
        use_enum_values = True


class ConversationExchange(BaseModel):
    """A single exchange in a conversation"""
    turn_number: int
    speaker: str = Field(..., description="'user' or 'agent'")
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # For user turns
    original_audio_id: Optional[str] = None  # Reference to stored audio if any
    transcription_confidence: Optional[float] = None

    # For agent turns
    audio_generated: bool = False

    # Error tracking (for user turns only)
    grammar_errors: list[dict] = Field(default_factory=list)
    pronunciation_errors: list[dict] = Field(default_factory=list)


class DetectedError(BaseModel):
    """An error detected during conversation"""
    id: str
    type: ErrorType
    turn_number: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Common fields
    original_text: str = Field(..., description="What user said")

    # Grammar error specific
    incorrect_text: Optional[str] = None
    correction: Optional[str] = None
    grammar_rule: Optional[str] = None
    explanation: Optional[str] = None

    # Pronunciation error specific
    word: Optional[str] = None
    phoneme: Optional[str] = None
    accuracy_score: Optional[float] = None
    expected_phoneme: Optional[str] = None
    detected_phoneme: Optional[str] = None

    # For activity generation
    activity_generated: bool = False
    activity_id: Optional[str] = None

    class Config:
        use_enum_values = True


class SpeakingSession(BaseModel):
    """A speaking/conversation session"""
    id: str  # session_{user_id}_{timestamp}
    user_id: str
    partition_key: str  # Same as user_id

    # Session info
    status: SessionStatus = SessionStatus.ACTIVE
    topic_id: str
    topic_name: str
    topic_difficulty: TopicDifficulty

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    duration_seconds: int = 0

    # Conversation data
    exchanges: list[ConversationExchange] = Field(default_factory=list)
    current_turn: int = 0

    # Error tracking
    all_errors: list[DetectedError] = Field(default_factory=list)
    grammar_errors: list[dict] = Field(default_factory=list)
    pronunciation_errors: list[dict] = Field(default_factory=list)

    # Generated activities
    generated_activity_ids: list[str] = Field(default_factory=list)

    # Summary (populated when session ends)
    summary: Optional[dict] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class SpeakingProgress(BaseModel):
    """User's overall speaking progress"""
    id: str  # speaking_progress_{user_id}
    user_id: str
    partition_key: str  # Same as user_id

    # Session statistics
    total_sessions: int = 0
    completed_sessions: int = 0
    total_conversation_time_minutes: int = 0
    total_turns: int = 0

    # Error patterns
    total_grammar_errors: int = 0
    total_pronunciation_errors: int = 0
    common_grammar_mistakes: dict[str, int] = Field(default_factory=dict)  # rule -> count
    problematic_phonemes: dict[str, int] = Field(default_factory=dict)  # phoneme -> count

    # Improvement tracking
    sessions_by_week: dict[str, int] = Field(default_factory=dict)  # week_string -> count
    error_rate_by_week: dict[str, float] = Field(default_factory=dict)  # week -> avg errors per turn

    # Recent activity
    last_session_at: Optional[datetime] = None
    last_session_id: Optional[str] = None
    recent_topics: list[str] = Field(default_factory=list)  # Last 10 topics

    # Current streak
    current_streak_days: int = 0
    last_practice_date: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GeneratedActivity(BaseModel):
    """An activity generated from conversation errors"""
    id: str  # activity_{user_id}_{timestamp}
    user_id: str
    partition_key: str  # Same as user_id

    # Source
    source_session_id: str
    source_turn_number: int
    source_error_type: ErrorType

    # Activity details
    pillar: str = Field(..., description="Target pillar: grammar or pronunciation")
    activity_type: str = Field(..., description="Type of activity")

    # For grammar activities
    grammar_rule: Optional[str] = None
    incorrect_example: Optional[str] = None
    correct_example: Optional[str] = None

    # For pronunciation activities
    target_phoneme: Optional[str] = None
    target_word: Optional[str] = None

    # Status
    status: str = "pending"  # pending, completed, skipped
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None

    # Priority
    priority: int = Field(default=1, ge=1, le=10, description="Higher = more urgent")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
