"""
Progress Models
Defines progress tracking and SRS structures.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SRSData(BaseModel):
    """Generic Spaced Repetition System data (SM-2 algorithm)"""
    ease_factor: float = Field(
        default=2.5,
        ge=1.3,
        description="Ease factor (minimum 1.3)"
    )
    interval: int = Field(
        default=1,
        ge=1,
        description="Days until next review"
    )
    repetitions: int = Field(
        default=0,
        ge=0,
        description="Number of successful reviews"
    )
    next_review: datetime = Field(default_factory=datetime.utcnow)
    last_review: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "easeFactor": self.ease_factor,
            "interval": self.interval,
            "repetitions": self.repetitions,
            "nextReview": self.next_review.isoformat(),
            "lastReview": self.last_review.isoformat() if self.last_review else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SRSData":
        """Create from dictionary"""
        return cls(
            ease_factor=data.get("easeFactor", 2.5),
            interval=data.get("interval", 1),
            repetitions=data.get("repetitions", 0),
            next_review=datetime.fromisoformat(data["nextReview"]) if data.get("nextReview") else datetime.utcnow(),
            last_review=datetime.fromisoformat(data["lastReview"]) if data.get("lastReview") else None
        )


class PillarProgress(BaseModel):
    """Progress for a specific learning pillar"""
    pillar: str = Field(..., description="vocabulary, grammar, pronunciation, speaking")
    total_items: int = Field(default=0, description="Total items studied")
    mastered_items: int = Field(default=0, description="Items mastered")
    learning_items: int = Field(default=0, description="Items currently learning")
    average_score: float = Field(default=0, ge=0, le=100)
    average_accuracy: float = Field(default=0, ge=0, le=100)
    study_time_minutes: int = Field(default=0)
    last_activity: Optional[datetime] = None
    streak_days: int = Field(default=0)

    # Review status
    items_due_for_review: int = Field(default=0)
    items_low_frequency: int = Field(default=0)


class OverallProgress(BaseModel):
    """Overall user progress across all pillars"""
    user_id: str
    current_level: str = Field(default="beginner")

    # Pillar progress
    vocabulary: PillarProgress = Field(default_factory=lambda: PillarProgress(pillar="vocabulary"))
    grammar: PillarProgress = Field(default_factory=lambda: PillarProgress(pillar="grammar"))
    pronunciation: PillarProgress = Field(default_factory=lambda: PillarProgress(pillar="pronunciation"))
    speaking: PillarProgress = Field(default_factory=lambda: PillarProgress(pillar="speaking"))

    # Overall metrics
    overall_score: float = Field(default=0, ge=0, le=100)
    total_study_time_minutes: int = Field(default=0)
    total_activities_completed: int = Field(default=0)

    # Streak tracking
    current_streak_days: int = Field(default=0)
    longest_streak_days: int = Field(default=0)
    last_activity_date: Optional[datetime] = None

    # Assessment
    initial_assessment_completed: bool = Field(default=False)
    last_assessment_date: Optional[datetime] = None
    ready_for_level_up: bool = Field(default=False)

    # Weakest pillar (needs focus)
    weakest_pillar: Optional[str] = None

    # Daily goals
    daily_goal_minutes: int = Field(default=30)
    today_study_minutes: int = Field(default=0)
    today_activities_completed: int = Field(default=0)

    # Metadata
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DailySchedule(BaseModel):
    """Daily study schedule"""
    id: str  # schedule_{user_id}_{date}
    user_id: str
    partition_key: str
    date: str = Field(..., description="Date in YYYY-MM-DD format")

    # Scheduled reviews
    scheduled_reviews: list[dict] = Field(
        default_factory=list,
        description="List of {time, type, item_id, reason}"
    )

    # Completed
    completed_reviews: list[dict] = Field(default_factory=list)

    # Progress
    daily_goal_progress: dict = Field(
        default_factory=lambda: {
            "minutesStudied": 0,
            "activitiesCompleted": 0,
            "goalMinutes": 30
        }
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProgressUpdate(BaseModel):
    """Model for updating progress after an activity"""
    pillar: str
    item_id: str
    correct: bool
    quality_response: int = Field(
        ...,
        ge=0,
        le=5,
        description="Quality of response (0=blackout, 5=perfect)"
    )
    response_time_ms: Optional[int] = None
    additional_data: dict = Field(default_factory=dict)


class AssessmentResult(BaseModel):
    """Result of an assessment (initial or continuous)"""
    user_id: str
    assessment_type: str = Field(..., description="initial or continuous")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Scores by pillar
    vocabulary_score: float = Field(default=0, ge=0, le=100)
    grammar_score: float = Field(default=0, ge=0, le=100)
    pronunciation_score: float = Field(default=0, ge=0, le=100)
    speaking_score: float = Field(default=0, ge=0, le=100)

    # Overall
    overall_score: float = Field(default=0, ge=0, le=100)

    # Determined level
    determined_level: str = Field(default="beginner")
    previous_level: Optional[str] = None
    level_changed: bool = Field(default=False)

    # Recommendations
    weakest_pillar: str
    recommendations: list[str] = Field(default_factory=list)
    focus_areas: list[dict] = Field(default_factory=list)


class WeeklyReport(BaseModel):
    """Weekly progress report"""
    user_id: str
    week_start: str
    week_end: str

    # Time spent
    total_study_minutes: int
    daily_breakdown: list[dict] = Field(
        default_factory=list,
        description="Minutes per day"
    )

    # Activities
    activities_completed: int
    activities_by_pillar: dict = Field(default_factory=dict)

    # Progress
    words_learned: int
    words_reviewed: int
    grammar_rules_practiced: int
    pronunciation_sounds_practiced: int
    speaking_sessions: int

    # Accuracy
    average_vocabulary_accuracy: float
    average_grammar_accuracy: float
    average_pronunciation_accuracy: float

    # Streak
    streak_maintained: bool
    current_streak: int

    # Highlights
    achievements: list[str] = Field(default_factory=list)
    areas_to_improve: list[str] = Field(default_factory=list)