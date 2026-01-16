"""
Grammar Schemas
Request and response schemas for grammar API endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== REQUEST SCHEMAS ====================

class GrammarLessonRequest(BaseModel):
    """Request for a new grammar lesson."""
    rule_id: Optional[str] = Field(
        default=None,
        description="Specific rule ID to study (optional)"
    )
    category: Optional[str] = Field(
        default=None,
        description="Category filter (tense, article, preposition, etc.)"
    )


class GrammarExplanationRequest(BaseModel):
    """Request to submit user's explanation of a grammar rule."""
    rule_id: str = Field(..., description="Rule ID being explained")
    explanation: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="User's explanation of the rule in their own words"
    )


class GrammarExerciseAnswerRequest(BaseModel):
    """Request to submit an answer for a grammar exercise."""
    activity_id: str = Field(..., description="Activity ID from the exercise")
    rule_id: str = Field(..., description="Rule ID being practiced")
    exercise_index: int = Field(..., ge=0, description="Index of the exercise being answered")
    answer: str = Field(..., description="User's answer (text or index)")
    response_time_ms: int = Field(
        default=5000,
        ge=0,
        le=300000,
        description="Response time in milliseconds"
    )


class GrammarExerciseRequest(BaseModel):
    """Request for grammar exercises."""
    rule_id: str = Field(..., description="Rule ID to generate exercises for")
    count: int = Field(default=5, ge=1, le=10, description="Number of exercises")


# ==================== RESPONSE SCHEMAS ====================

class PortugueseComparison(BaseModel):
    """Portuguese comparison information."""
    exists_in_portuguese: bool = Field(..., description="Whether rule exists in Portuguese")
    portuguese_equivalent: Optional[str] = Field(default=None, description="Portuguese equivalent name")
    similarities: list[str] = Field(default_factory=list, description="Similarities with Portuguese")
    differences: list[str] = Field(default_factory=list, description="Differences from Portuguese")


class GrammarExample(BaseModel):
    """Example sentence pair."""
    english: str
    portuguese: str


class CommonError(BaseModel):
    """Common error example."""
    incorrect: str
    correct: str
    explanation: str


class GrammarRuleContent(BaseModel):
    """Full grammar rule content for lessons."""
    id: str
    name: str
    category: str
    difficulty: str
    english_explanation: str
    portuguese_explanation: Optional[str] = None
    comparison: PortugueseComparison
    common_mistakes: list[str] = Field(default_factory=list)
    memory_tips: list[str] = Field(default_factory=list)
    examples: list[GrammarExample] = Field(default_factory=list)
    common_errors: list[CommonError] = Field(default_factory=list)


class GrammarLessonResponse(BaseModel):
    """Response containing a grammar lesson."""
    type: str = Field(default="grammar_lesson")
    status: str = Field(..., description="success, no_rules, or error")
    activity_id: Optional[str] = Field(default=None, description="Activity ID")
    rule: Optional[GrammarRuleContent] = Field(default=None, description="Grammar rule content")
    user_progress: Optional[dict] = Field(default=None, description="User's progress on this rule")
    message: Optional[str] = Field(default=None, description="Status message")


class ExplanationEvaluation(BaseModel):
    """Evaluation of user's grammar explanation."""
    accuracy_score: float = Field(..., ge=0, le=100, description="How correct the explanation is")
    completeness_score: float = Field(..., ge=0, le=100, description="Coverage of key points")
    understanding_score: float = Field(..., ge=0, le=100, description="True understanding level")
    overall_score: float = Field(..., ge=0, le=100, description="Overall score")
    feedback: str = Field(..., description="Feedback in Portuguese")
    missing_points: list[str] = Field(default_factory=list, description="Points not covered")
    suggestions: str = Field(default="", description="Suggestions for improvement")


class GrammarExplanationResponse(BaseModel):
    """Response after evaluating user's grammar explanation."""
    type: str = Field(default="grammar_explanation")
    status: str = Field(..., description="success or error")
    rule_id: str = Field(..., description="Rule that was explained")
    rule_name: str = Field(..., description="Name of the rule")
    evaluation: Optional[ExplanationEvaluation] = Field(default=None, description="Evaluation results")
    passed: bool = Field(default=False, description="Whether explanation met minimum threshold")
    mastery_level: Optional[str] = Field(default=None, description="Updated mastery level")
    next_review_days: Optional[int] = Field(default=None, description="Days until next review")
    message: Optional[str] = Field(default=None, description="Error message if any")


class GrammarExerciseContent(BaseModel):
    """Content of a grammar exercise."""
    index: int = Field(..., description="Exercise index")
    type: str = Field(..., description="Exercise type (fill_in_blank, error_correction, etc.)")
    instruction: str = Field(..., description="Exercise instruction")
    sentence: str = Field(..., description="Exercise sentence")
    options: Optional[list[str]] = Field(default=None, description="Multiple choice options")


class GrammarExercisesResponse(BaseModel):
    """Response containing grammar exercises."""
    type: str = Field(default="grammar_exercises")
    status: str = Field(..., description="success or error")
    activity_id: Optional[str] = Field(default=None, description="Activity ID")
    rule_id: str = Field(..., description="Rule being practiced")
    rule_name: str = Field(..., description="Name of the rule")
    exercises: list[GrammarExerciseContent] = Field(default_factory=list, description="Exercises")
    total_exercises: int = Field(default=0, description="Total number of exercises")
    message: Optional[str] = Field(default=None, description="Status message")


class GrammarExerciseAnswerResponse(BaseModel):
    """Response after submitting a grammar exercise answer."""
    type: str = Field(default="grammar_exercise_answer")
    status: str = Field(..., description="success or error")
    correct: bool = Field(..., description="Whether the answer was correct")
    user_answer: str = Field(..., description="User's submitted answer")
    correct_answer: str = Field(..., description="The correct answer")
    explanation: str = Field(default="", description="Explanation of the answer")
    exercise_index: int = Field(..., description="Index of the exercise")
    exercises_completed: int = Field(default=0, description="Number of exercises completed")
    exercises_correct: int = Field(default=0, description="Number correct so far")
    mastery_level: Optional[str] = Field(default=None, description="Updated mastery level")
    message: Optional[str] = Field(default=None, description="Error message if any")


class GrammarProgressResponse(BaseModel):
    """Response containing grammar progress statistics."""
    total_rules: int = Field(default=0, description="Total rules in progress")
    mastered: int = Field(default=0, description="Rules at mastery level")
    reviewing: int = Field(default=0, description="Rules being reviewed")
    learning: int = Field(default=0, description="Rules being learned")
    not_started: int = Field(default=0, description="Rules not yet started")
    due_for_review: int = Field(default=0, description="Rules due for SRS review")
    average_score: float = Field(default=0.0, description="Average explanation score")
    best_categories: list[str] = Field(default_factory=list, description="Best performing categories")
    weak_categories: list[str] = Field(default_factory=list, description="Categories needing work")


class RuleToReview(BaseModel):
    """A grammar rule that needs review."""
    rule_id: str
    rule_name: str
    category: str
    difficulty: str
    mastery_level: str
    last_practiced: Optional[str] = None
    best_explanation_score: float = 0


class ReviewListResponse(BaseModel):
    """Response containing list of rules to review."""
    rules: list[RuleToReview]
    total_due: int


class GrammarRuleSummary(BaseModel):
    """Summary of a grammar rule for listing."""
    id: str
    name: str
    category: str
    difficulty: str
    exists_in_portuguese: bool
    mastery_level: Optional[str] = None
    practice_count: Optional[int] = None
    best_explanation_score: Optional[float] = None


class GrammarRulesListResponse(BaseModel):
    """Response containing list of grammar rules."""
    rules: list[GrammarRuleSummary]
    total: int
    categories: list[str] = Field(default_factory=list, description="Available categories")
