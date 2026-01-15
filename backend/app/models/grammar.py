"""
Grammar Models
Defines grammar rule and progress structures.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class GrammarCategory(str, Enum):
    """Grammar rule category"""
    TENSE = "tense"
    ARTICLE = "article"
    PREPOSITION = "preposition"
    PRONOUN = "pronoun"
    CONJUNCTION = "conjunction"
    MODAL = "modal"
    CONDITIONAL = "conditional"
    PASSIVE = "passive"
    RELATIVE_CLAUSE = "relative_clause"
    WORD_ORDER = "word_order"
    QUESTION_FORMATION = "question_formation"
    NEGATION = "negation"
    OTHER = "other"


class GrammarDifficulty(str, Enum):
    """Grammar rule difficulty"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class GrammarRule(BaseModel):
    """Grammar rule definition"""
    id: str
    name: str
    category: GrammarCategory
    difficulty: GrammarDifficulty = GrammarDifficulty.BEGINNER

    # Explanation
    english_explanation: str
    portuguese_explanation: Optional[str] = None

    # Portuguese comparison
    exists_in_portuguese: bool
    portuguese_equivalent: Optional[str] = None
    similarities: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)
    memory_tips: list[str] = Field(default_factory=list)

    # Examples
    examples: list[dict] = Field(
        default_factory=list,
        description="List of {english: str, portuguese: str} examples"
    )

    # Common errors
    common_errors: list[dict] = Field(
        default_factory=list,
        description="List of {incorrect: str, correct: str, explanation: str}"
    )

    # Related rules
    related_rules: list[str] = Field(default_factory=list)
    prerequisite_rules: list[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class UserExplanation(BaseModel):
    """User's explanation of a grammar rule"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    explanation: str
    evaluation_score: float = Field(..., ge=0, le=100)
    feedback: Optional[str] = None
    missing_points: list[str] = Field(default_factory=list)


class GrammarSRSData(BaseModel):
    """SRS data for grammar rules"""
    ease_factor: float = Field(default=2.5, ge=1.3)
    interval: int = Field(default=1, ge=1)
    repetitions: int = Field(default=0, ge=0)
    next_review: datetime = Field(default_factory=datetime.utcnow)
    last_review: Optional[datetime] = None


class GrammarProgress(BaseModel):
    """User's progress on a specific grammar rule"""
    id: str  # grammar_{user_id}_{rule_id}
    user_id: str
    rule_id: str
    rule_name: str  # Denormalized
    partition_key: str  # Same as user_id

    # Progress tracking
    practice_count: int = Field(default=0, ge=0)
    correct_count: int = Field(default=0, ge=0)
    last_practiced: Optional[datetime] = None
    last_score: float = Field(default=0, ge=0, le=100)

    # User explanations history
    user_explanations: list[UserExplanation] = Field(default_factory=list)
    best_explanation_score: float = Field(default=0, ge=0, le=100)

    # SRS data
    srs_data: GrammarSRSData = Field(default_factory=GrammarSRSData)

    # Error tracking
    error_patterns: list[str] = Field(default_factory=list)
    needs_comparison_review: bool = Field(
        default=False,
        description="Needs to review PT-EN comparison"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GrammarExercise(BaseModel):
    """A grammar exercise"""
    rule_id: str
    exercise_type: str = Field(..., description="fill_in_blank, error_correction, etc.")
    instruction: str
    sentence: str
    options: Optional[list[str]] = None
    correct_answer: str
    correct_index: Optional[int] = None
    explanation: str


class GrammarExerciseResult(BaseModel):
    """Result of a grammar exercise"""
    rule_id: str
    correct: bool
    user_answer: str
    correct_answer: str
    response_time_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GrammarExplanationRequest(BaseModel):
    """Request for evaluating user's grammar explanation"""
    rule_id: str
    user_explanation: str


class GrammarExplanationResult(BaseModel):
    """Result of evaluating user's grammar explanation"""
    rule_id: str
    accuracy_score: float
    completeness_score: float
    understanding_score: float
    overall_score: float
    feedback: str
    missing_points: list[str]
    suggestions: str