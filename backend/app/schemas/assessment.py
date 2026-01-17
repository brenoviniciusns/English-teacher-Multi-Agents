"""
Assessment API Schemas
Request and response models for assessment endpoints.
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# ==================== REQUEST SCHEMAS ====================

class StartAssessmentRequest(BaseModel):
    """Request to start an assessment"""
    assessment_type: str = Field(
        default="initial",
        description="Type of assessment: initial or continuous"
    )


class SubmitAssessmentAnswerRequest(BaseModel):
    """Request to submit an answer for an assessment question"""
    assessment_id: str = Field(..., description="Assessment session ID")
    step: int = Field(..., ge=1, le=4, description="Current step number (1-4)")
    step_name: str = Field(..., description="Step name: vocabulary, grammar, pronunciation, speaking")
    answers: list[dict] = Field(..., description="List of answers for current step")


class CompleteAssessmentRequest(BaseModel):
    """Request to complete an assessment"""
    assessment_id: str = Field(..., description="Assessment session ID")


# ==================== RESPONSE SCHEMAS ====================

class VocabularyAssessmentItem(BaseModel):
    """Single vocabulary item in assessment"""
    word: str
    difficulty: int = Field(ge=1, le=4)


class GrammarAssessmentItem(BaseModel):
    """Single grammar item in assessment"""
    id: str
    rule: str
    example: str
    question: str


class PronunciationAssessmentItem(BaseModel):
    """Single pronunciation item in assessment"""
    id: str
    phoneme: str
    words: list[str]
    difficulty: str


class AssessmentStepContent(BaseModel):
    """Content for an assessment step"""
    type: str = Field(..., description="Step type: vocabulary, grammar, pronunciation, speaking")
    items: Optional[list[Any]] = Field(default=None, description="Items to assess")
    prompts: Optional[list[str]] = Field(default=None, description="Speaking prompts")
    instructions: str = Field(..., description="Instructions for this step")


class StartAssessmentResponse(BaseModel):
    """Response when starting an assessment"""
    assessment_id: str = Field(..., description="Unique assessment session ID")
    assessment_type: str = Field(..., description="Type: initial or continuous")
    step: int = Field(..., description="Current step number")
    step_name: str = Field(..., description="Step name")
    total_steps: int = Field(..., description="Total number of steps")
    content: AssessmentStepContent = Field(..., description="Content for current step")
    instructions: str = Field(..., description="Instructions for current step")


class SubmitAssessmentAnswerResponse(BaseModel):
    """Response after submitting assessment answers"""
    assessment_id: str = Field(..., description="Assessment session ID")
    step_completed: int = Field(..., description="Step that was completed")
    step_name: str = Field(..., description="Name of completed step")
    step_score: float = Field(..., ge=0, le=100, description="Score for this step")
    next_step: Optional[int] = Field(default=None, description="Next step number (None if complete)")
    next_step_name: Optional[str] = Field(default=None, description="Next step name")
    next_content: Optional[AssessmentStepContent] = Field(default=None, description="Content for next step")
    is_complete: bool = Field(default=False, description="Whether assessment is complete")


class PillarScores(BaseModel):
    """Scores for each learning pillar"""
    vocabulary: float = Field(ge=0, le=100)
    grammar: float = Field(ge=0, le=100)
    pronunciation: float = Field(ge=0, le=100)
    speaking: float = Field(ge=0, le=100)


class AssessmentResultResponse(BaseModel):
    """Final assessment result"""
    assessment_id: str = Field(..., description="Assessment session ID")
    assessment_type: str = Field(..., description="Type: initial or continuous")
    scores: PillarScores = Field(..., description="Scores for each pillar")
    overall_score: float = Field(..., ge=0, le=100, description="Overall average score")
    determined_level: str = Field(..., description="Determined user level: beginner or intermediate")
    previous_level: Optional[str] = Field(default=None, description="Previous level (for continuous)")
    level_changed: bool = Field(default=False, description="Whether level changed")
    weakest_pillar: str = Field(..., description="Pillar that needs most improvement")
    recommendations: list[str] = Field(..., description="Personalized recommendations")
    message: str = Field(..., description="User-friendly result message")
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class AssessmentStatusResponse(BaseModel):
    """Current assessment status"""
    has_active_assessment: bool = Field(..., description="Whether there's an active assessment")
    assessment_id: Optional[str] = Field(default=None, description="Active assessment ID")
    assessment_type: Optional[str] = Field(default=None, description="Type of active assessment")
    current_step: Optional[int] = Field(default=None, description="Current step")
    total_steps: Optional[int] = Field(default=None, description="Total steps")
    step_scores: Optional[dict[str, float]] = Field(default=None, description="Scores for completed steps")
    initial_assessment_completed: bool = Field(..., description="Whether initial assessment is done")
    last_assessment_date: Optional[datetime] = Field(default=None, description="Date of last assessment")
    sessions_since_last_assessment: Optional[int] = Field(default=None)
