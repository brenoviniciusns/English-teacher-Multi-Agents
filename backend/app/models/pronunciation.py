"""
Pronunciation Models
Defines phonetic sound and pronunciation progress structures.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class SoundDifficulty(str, Enum):
    """Phonetic sound difficulty for Portuguese speakers"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MouthPosition(BaseModel):
    """Mouth position description for a phoneme"""
    tongue: str
    lips: str
    teeth: Optional[str] = None
    jaw: Optional[str] = None
    airflow: Optional[str] = None
    voicing: Optional[str] = None


class PhoneticSound(BaseModel):
    """Phonetic sound definition"""
    id: str
    phoneme: str = Field(..., description="IPA symbol (e.g., θ, ð, æ)")
    ipa: str
    name: str = Field(..., description="Full name (e.g., voiceless dental fricative)")

    # Classification
    exists_in_portuguese: bool
    difficulty: SoundDifficulty = SoundDifficulty.MEDIUM

    # Articulation
    mouth_position: MouthPosition

    # Examples
    example_words: list[str] = Field(default_factory=list)
    minimal_pairs: list[dict] = Field(
        default_factory=list,
        description="Pairs showing contrast (e.g., {θ: 'think', s: 'sink'})"
    )

    # Common mistakes
    common_mistake: str
    portuguese_similar: Optional[str] = Field(
        None,
        description="Similar sound in Portuguese, if any"
    )

    # Learning resources
    tip: str
    diagram_url: Optional[str] = None
    video_url: Optional[str] = None

    class Config:
        use_enum_values = True


class PronunciationAttempt(BaseModel):
    """A single pronunciation attempt"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    word: str
    reference_text: str
    recognized_text: str
    accuracy_score: float = Field(..., ge=0, le=100)
    phonemes_detected: list[str] = Field(default_factory=list)
    feedback: Optional[str] = None


class PronunciationSRSData(BaseModel):
    """SRS data for pronunciation sounds"""
    ease_factor: float = Field(default=2.5, ge=1.3)
    interval: int = Field(default=1, ge=1)
    repetitions: int = Field(default=0, ge=0)
    next_review: datetime = Field(default_factory=datetime.utcnow)
    last_review: Optional[datetime] = None


class PronunciationProgress(BaseModel):
    """User's progress on a specific phonetic sound"""
    id: str  # pronun_{user_id}_{sound_id}
    user_id: str
    sound_id: str
    phoneme: str  # Denormalized
    partition_key: str  # Same as user_id

    # Progress tracking
    practice_count: int = Field(default=0, ge=0)
    last_practiced: Optional[datetime] = None

    # Accuracy tracking
    average_accuracy: float = Field(default=0, ge=0, le=100)
    best_accuracy: float = Field(default=0, ge=0, le=100)
    recent_accuracies: list[float] = Field(
        default_factory=list,
        description="Last 10 accuracy scores"
    )

    # Attempt history (last 20 attempts)
    practice_history: list[PronunciationAttempt] = Field(default_factory=list)

    # SRS data
    srs_data: PronunciationSRSData = Field(default_factory=PronunciationSRSData)

    # Status
    mastered: bool = Field(
        default=False,
        description="True if average_accuracy >= 85"
    )
    needs_mouth_position_review: bool = Field(default=True)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PronunciationExercise(BaseModel):
    """A pronunciation (shadowing) exercise"""
    sound_id: str
    phoneme: str
    exercise_type: str = Field(default="shadowing", description="shadowing, minimal_pair, etc.")
    word: str
    sentence: Optional[str] = None
    reference_audio_url: Optional[str] = None
    reference_audio_base64: Optional[str] = None
    mouth_position: Optional[MouthPosition] = None
    tip: Optional[str] = None


class PronunciationExerciseResult(BaseModel):
    """Result of a pronunciation exercise"""
    sound_id: str
    word: str
    recognized_text: str
    accuracy_score: float
    fluency_score: float
    completeness_score: float
    pronunciation_score: float
    words_detail: list[dict] = Field(default_factory=list)
    phonemes_detail: list[dict] = Field(default_factory=list)
    feedback: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ShadowingRequest(BaseModel):
    """Request for shadowing exercise audio submission"""
    sound_id: str
    word: str
    reference_text: str
    audio_base64: str = Field(..., description="Base64 encoded audio data")


class PronunciationAssessmentRequest(BaseModel):
    """Request for pronunciation assessment"""
    reference_text: str
    audio_base64: str
    granularity: str = Field(default="phoneme", description="phoneme or word")