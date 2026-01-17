"""
Progress Schemas
Request and response schemas for progress API endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== REQUEST SCHEMAS ====================

class ProgressRequest(BaseModel):
    """Request for user progress data."""
    include_weekly_report: bool = Field(
        default=False,
        description="Include weekly report in response"
    )


class ScheduleRequest(BaseModel):
    """Request for schedule data."""
    date: Optional[str] = Field(
        default=None,
        description="Date in YYYY-MM-DD format (defaults to today)"
    )
    include_week: bool = Field(
        default=False,
        description="Include full week schedule"
    )


class UpdateProgressRequest(BaseModel):
    """Request to update progress after an activity."""
    pillar: str = Field(..., description="vocabulary, grammar, pronunciation, speaking")
    item_id: str = Field(..., description="ID of the item completed")
    correct: bool = Field(..., description="Whether the answer was correct")
    accuracy: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Accuracy percentage (for pronunciation)"
    )
    time_spent_seconds: int = Field(
        default=0,
        ge=0,
        description="Time spent on the activity in seconds"
    )


class CompleteScheduledReviewRequest(BaseModel):
    """Request to mark a scheduled review as completed."""
    review_id: str = Field(..., description="ID of the scheduled review")
    result: dict = Field(default_factory=dict, description="Result data from the activity")


# ==================== RESPONSE SCHEMAS ====================

class PillarProgressResponse(BaseModel):
    """Progress for a specific learning pillar."""
    pillar: str
    total_items: int = 0
    mastered_items: int = 0
    learning_items: int = 0
    average_score: float = 0.0
    average_accuracy: float = 0.0
    study_time_minutes: int = 0
    items_due_for_review: int = 0
    items_low_frequency: int = 0
    last_activity: Optional[str] = None
    streak_days: int = 0


class OverallProgressResponse(BaseModel):
    """Complete user progress response."""
    user_id: str
    current_level: str = "beginner"

    # Pillar progress
    vocabulary: PillarProgressResponse
    grammar: PillarProgressResponse
    pronunciation: PillarProgressResponse
    speaking: PillarProgressResponse

    # Overall metrics
    overall_score: float = 0.0
    total_study_time_minutes: int = 0
    total_activities_completed: int = 0

    # Streak tracking
    current_streak_days: int = 0
    longest_streak_days: int = 0
    last_activity_date: Optional[str] = None

    # Assessment info
    initial_assessment_completed: bool = False
    ready_for_level_up: bool = False

    # Focus area
    weakest_pillar: Optional[str] = None

    # Daily goals
    daily_goal_minutes: int = 30
    today_study_minutes: int = 0
    today_activities_completed: int = 0

    # Message
    message: Optional[str] = None


class ScheduledReviewItem(BaseModel):
    """A single scheduled review item."""
    id: str
    type: str = Field(..., description="vocabulary_review, grammar_review, etc.")
    pillar: str
    item_id: Optional[str] = None
    reason: str = Field(..., description="srs_due, low_frequency, low_accuracy, daily_practice")
    priority: str = "normal"
    estimated_minutes: int = 0
    completed: bool = False
    completed_at: Optional[str] = None


class DailyGoalProgress(BaseModel):
    """Progress towards daily goal."""
    minutes_studied: int = 0
    activities_completed: int = 0
    goal_minutes: int = 30
    total_activities: int = 0
    percentage_complete: float = 0.0


class DailyScheduleResponse(BaseModel):
    """Response containing daily schedule."""
    date: str
    user_id: str
    scheduled_reviews: list[ScheduledReviewItem] = []
    completed_reviews: list[ScheduledReviewItem] = []
    daily_goal_progress: DailyGoalProgress
    message: Optional[str] = None


class WeekScheduleResponse(BaseModel):
    """Response containing week schedule."""
    schedules: list[DailyScheduleResponse]
    week_summary: dict = Field(default_factory=dict)


class DailyBreakdown(BaseModel):
    """Daily breakdown for weekly report."""
    date: str
    minutes: int = 0
    activities: int = 0


class WeeklyReportResponse(BaseModel):
    """Weekly progress report response."""
    user_id: str
    week_start: str
    week_end: str

    # Time spent
    total_study_minutes: int = 0
    daily_breakdown: list[DailyBreakdown] = []

    # Activities
    activities_completed: int = 0
    activities_by_pillar: dict = Field(default_factory=dict)

    # Progress
    words_learned: int = 0
    words_reviewed: int = 0
    grammar_rules_practiced: int = 0
    pronunciation_sounds_practiced: int = 0
    speaking_sessions: int = 0

    # Accuracy
    average_vocabulary_accuracy: float = 0.0
    average_grammar_accuracy: float = 0.0
    average_pronunciation_accuracy: float = 0.0

    # Streak
    streak_maintained: bool = False
    current_streak: int = 0

    # Highlights
    achievements: list[str] = []
    areas_to_improve: list[str] = []


class ProgressUpdateResponse(BaseModel):
    """Response after updating progress."""
    status: str = "success"
    message: str
    updated_streak: int = 0
    today_minutes: int = 0
    today_activities: int = 0
    srs_updated: bool = False
    next_review_days: Optional[int] = None


class NextActivityResponse(BaseModel):
    """Response containing next recommended activity."""
    has_activity: bool
    activity_type: Optional[str] = None
    pillar: Optional[str] = None
    item_id: Optional[str] = None
    source: str = Field(..., description="srs, pending, low_frequency, none")
    reason: Optional[str] = None
    suggestions: list[dict] = []
    message: Optional[str] = None