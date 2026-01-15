"""
Vocabulary Models
Defines vocabulary word and progress structures.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class WordCategory(str, Enum):
    """Vocabulary word category"""
    COMMON = "common"
    TECHNICAL = "technical"
    ACADEMIC = "academic"
    IDIOM = "idiom"


class WordDifficulty(str, Enum):
    """Word difficulty level"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class MasteryLevel(str, Enum):
    """Word mastery level"""
    NEW = "new"
    LEARNING = "learning"
    REVIEWING = "reviewing"
    MASTERED = "mastered"


class VocabularyWord(BaseModel):
    """Vocabulary word definition"""
    id: str
    word: str
    part_of_speech: str = Field(..., description="Noun, verb, adjective, etc.")
    definition: str
    example_sentence: str
    ipa_pronunciation: str = Field(..., description="IPA phonetic transcription")
    audio_url: Optional[str] = None

    # Classification
    category: WordCategory = WordCategory.COMMON
    subcategory: Optional[str] = None  # e.g., "data_engineering", "ai"
    difficulty: WordDifficulty = WordDifficulty.BEGINNER
    frequency_rank: int = Field(..., ge=1, description="Frequency rank (1 = most common)")

    # Portuguese translation
    portuguese_translation: Optional[str] = None
    portuguese_example: Optional[str] = None

    # Additional info
    synonyms: list[str] = Field(default_factory=list)
    antonyms: list[str] = Field(default_factory=list)
    related_words: list[str] = Field(default_factory=list)
    usage_notes: Optional[str] = None

    class Config:
        use_enum_values = True


class SRSData(BaseModel):
    """Spaced Repetition System data"""
    ease_factor: float = Field(default=2.5, ge=1.3, description="SM-2 ease factor")
    interval: int = Field(default=1, ge=1, description="Days until next review")
    repetitions: int = Field(default=0, ge=0, description="Number of successful reviews")
    next_review: datetime = Field(default_factory=datetime.utcnow)
    last_review: Optional[datetime] = None


class VocabularyProgress(BaseModel):
    """User's progress on a specific vocabulary word"""
    id: str  # vocab_{user_id}_{word_id}
    user_id: str
    word_id: str
    word: str  # Denormalized for convenience
    partition_key: str  # Same as user_id

    # Progress tracking
    mastery_level: MasteryLevel = MasteryLevel.NEW
    practice_count: int = Field(default=0, ge=0)
    correct_count: int = Field(default=0, ge=0)
    last_practiced: Optional[datetime] = None
    last_7_days_usage: int = Field(default=0, ge=0, description="Usage count in last 7 days")

    # SRS data
    srs_data: SRSData = Field(default_factory=SRSData)

    # Quality tracking
    average_response_time_ms: Optional[int] = None
    error_patterns: list[str] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class VocabularyExercise(BaseModel):
    """A vocabulary exercise"""
    word_id: str
    word: str
    exercise_type: str = Field(..., description="fill_in_blank, multiple_choice, etc.")
    sentence: str
    options: list[str]
    correct_answer: str
    correct_index: int
    explanation: str
    example_usage: Optional[str] = None
    context: str = Field(default="general", description="general, data_engineering, ai")


class VocabularyExerciseResult(BaseModel):
    """Result of a vocabulary exercise"""
    word_id: str
    correct: bool
    user_answer: str
    correct_answer: str
    response_time_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)