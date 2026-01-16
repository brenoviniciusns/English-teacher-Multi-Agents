"""
Vocabulary Schemas
Request and response schemas for vocabulary API endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== REQUEST SCHEMAS ====================

class VocabularyExerciseRequest(BaseModel):
    """Request for a new vocabulary exercise."""
    context: Optional[str] = Field(
        default="general",
        description="Context for exercise (general, data_engineering, ai, technology)"
    )
    word_id: Optional[str] = Field(
        default=None,
        description="Specific word ID to practice (optional)"
    )


class VocabularyAnswerRequest(BaseModel):
    """Request to submit an answer for a vocabulary exercise."""
    activity_id: str = Field(..., description="Activity ID from the exercise")
    word_id: str = Field(..., description="Word ID being answered")
    answer: str = Field(..., description="User's answer (text or index)")
    response_time_ms: int = Field(
        default=5000,
        ge=0,
        le=300000,
        description="Response time in milliseconds"
    )


# ==================== RESPONSE SCHEMAS ====================

class ExerciseContent(BaseModel):
    """Content of a vocabulary exercise."""
    type: str = Field(default="fill_in_blank", description="Exercise type")
    sentence: str = Field(..., description="Sentence with blank")
    options: list[str] = Field(..., description="Multiple choice options")
    context: str = Field(default="general", description="Exercise context")


class VocabularyExerciseResponse(BaseModel):
    """Response containing a vocabulary exercise."""
    type: str = Field(default="vocabulary_exercise")
    status: str = Field(..., description="success, no_words, or error")
    activity_id: Optional[str] = Field(default=None, description="Activity ID")
    word_id: Optional[str] = Field(default=None, description="Word ID")
    word: Optional[str] = Field(default=None, description="The vocabulary word")
    part_of_speech: Optional[str] = Field(default=None, description="Part of speech")
    ipa_pronunciation: Optional[str] = Field(default=None, description="IPA pronunciation")
    exercise: Optional[ExerciseContent] = Field(default=None, description="Exercise content")
    message: Optional[str] = Field(default=None, description="Status message")


class VocabularyAnswerResponse(BaseModel):
    """Response after submitting a vocabulary answer."""
    type: str = Field(default="vocabulary_answer")
    status: str = Field(..., description="success or error")
    correct: bool = Field(..., description="Whether the answer was correct")
    user_answer: str = Field(..., description="User's submitted answer")
    correct_answer: str = Field(..., description="The correct answer")
    explanation: Optional[str] = Field(default=None, description="Explanation of the answer")
    example_usage: Optional[str] = Field(default=None, description="Example usage of the word")
    mastery_level: Optional[str] = Field(default=None, description="Updated mastery level")
    next_review_days: Optional[int] = Field(default=None, description="Days until next review")
    streak: Optional[int] = Field(default=0, description="Current streak")
    message: Optional[str] = Field(default=None, description="Error message if any")


class VocabularyProgressResponse(BaseModel):
    """Response containing vocabulary progress statistics."""
    total_words: int = Field(default=0, description="Total words in progress")
    mastered: int = Field(default=0, description="Words at mastery level")
    reviewing: int = Field(default=0, description="Words being reviewed")
    learning: int = Field(default=0, description="Words being learned")
    new_words: int = Field(default=0, description="New words")
    due_for_review: int = Field(default=0, description="Words due for SRS review")
    average_accuracy: float = Field(default=0.0, description="Average accuracy percentage")


class WordToReview(BaseModel):
    """A word that needs review."""
    word_id: str
    word: str
    definition: str
    mastery_level: str
    last_practiced: Optional[str] = None


class ReviewListResponse(BaseModel):
    """Response containing list of words to review."""
    words: list[WordToReview]
    total_due: int


class WordDetail(BaseModel):
    """Detailed word information."""
    id: str
    word: str
    part_of_speech: str
    definition: str
    example_sentence: str
    ipa_pronunciation: str
    portuguese_translation: Optional[str] = None
    category: str = "common"
    difficulty: str = "beginner"
    # Progress info (if user has progress)
    mastery_level: Optional[str] = None
    practice_count: Optional[int] = None
    correct_count: Optional[int] = None
    last_practiced: Optional[str] = None
    next_review: Optional[str] = None


class WordDetailResponse(BaseModel):
    """Response containing word details."""
    word: WordDetail
    has_progress: bool = False
