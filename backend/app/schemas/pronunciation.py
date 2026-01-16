"""
Pronunciation Schemas
Request and response schemas for pronunciation API endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== REQUEST SCHEMAS ====================

class PronunciationExerciseRequest(BaseModel):
    """Request for a new pronunciation exercise."""
    sound_id: Optional[str] = Field(
        default=None,
        description="Specific sound ID to practice (optional)"
    )
    difficulty: Optional[str] = Field(
        default=None,
        description="Difficulty filter (low, medium, high)"
    )
    exercise_type: str = Field(
        default="shadowing",
        description="Exercise type: shadowing, minimal_pair, word_practice"
    )


class ShadowingSubmitRequest(BaseModel):
    """Request to submit audio for shadowing exercise."""
    sound_id: str = Field(..., description="Sound ID being practiced")
    word: str = Field(..., description="Word that was spoken")
    reference_text: str = Field(..., description="Expected text for comparison")
    audio_base64: str = Field(
        ...,
        min_length=100,
        description="Base64 encoded audio data (WAV format)"
    )
    attempt_number: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Current attempt number (max 5)"
    )


class MinimalPairRequest(BaseModel):
    """Request for minimal pair exercise."""
    sound_id: str = Field(..., description="Sound ID to practice")
    pair_index: int = Field(default=0, ge=0, description="Index of minimal pair to use")


class PronunciationAssessmentRequest(BaseModel):
    """Request for pronunciation assessment."""
    reference_text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The expected text to be pronounced"
    )
    audio_base64: str = Field(
        ...,
        min_length=100,
        description="Base64 encoded audio data"
    )
    granularity: str = Field(
        default="phoneme",
        description="Assessment granularity: phoneme or word"
    )


# ==================== RESPONSE SCHEMAS ====================

class MouthPositionInfo(BaseModel):
    """Mouth position guidance for a phoneme."""
    tongue: str = Field(..., description="Tongue position")
    lips: str = Field(..., description="Lips position")
    teeth: Optional[str] = Field(default=None, description="Teeth position")
    jaw: Optional[str] = Field(default=None, description="Jaw position")
    airflow: Optional[str] = Field(default=None, description="Airflow description")
    voicing: Optional[str] = Field(default=None, description="Voicing (voiced/voiceless)")


class MinimalPairInfo(BaseModel):
    """Minimal pair information."""
    target: str = Field(..., description="Target word with the sound")
    contrast: str = Field(..., description="Contrasting word")
    difference: str = Field(..., description="Description of the difference")


class PhoneticSoundContent(BaseModel):
    """Full phonetic sound content for exercises."""
    id: str
    phoneme: str = Field(..., description="IPA symbol")
    ipa: str = Field(..., description="Full IPA representation")
    name: str = Field(..., description="Sound name (e.g., voiceless dental fricative)")
    exists_in_portuguese: bool
    difficulty: str
    mouth_position: MouthPositionInfo
    example_words: list[str] = Field(default_factory=list)
    minimal_pairs: list[MinimalPairInfo] = Field(default_factory=list)
    common_mistake: str
    portuguese_similar: Optional[str] = None
    tip: str


class PronunciationExerciseContent(BaseModel):
    """Content of a pronunciation exercise."""
    exercise_type: str = Field(..., description="shadowing, minimal_pair, word_practice")
    sound: PhoneticSoundContent
    target_word: str = Field(..., description="Word to practice")
    target_sentence: Optional[str] = Field(default=None, description="Sentence for context")
    reference_audio_base64: Optional[str] = Field(
        default=None,
        description="Reference audio for shadowing"
    )
    instructions: str = Field(..., description="Exercise instructions in Portuguese")


class PronunciationExerciseResponse(BaseModel):
    """Response containing a pronunciation exercise."""
    type: str = Field(default="pronunciation_exercise")
    status: str = Field(..., description="success, no_sounds, or error")
    activity_id: Optional[str] = Field(default=None, description="Activity ID")
    exercise: Optional[PronunciationExerciseContent] = Field(
        default=None,
        description="Exercise content"
    )
    user_progress: Optional[dict] = Field(
        default=None,
        description="User's progress on this sound"
    )
    attempts_remaining: int = Field(
        default=3,
        description="Attempts remaining for this exercise"
    )
    message: Optional[str] = Field(default=None, description="Status message")


class PhonemeScore(BaseModel):
    """Score for a single phoneme."""
    phoneme: str
    accuracy_score: float = Field(..., ge=0, le=100)
    word: Optional[str] = None


class WordScore(BaseModel):
    """Score for a single word."""
    word: str
    accuracy_score: float = Field(..., ge=0, le=100)
    error_type: Optional[str] = None
    phonemes: list[PhonemeScore] = Field(default_factory=list)


class PronunciationScores(BaseModel):
    """Pronunciation assessment scores."""
    accuracy: float = Field(..., ge=0, le=100, description="Accuracy score")
    fluency: float = Field(..., ge=0, le=100, description="Fluency score")
    completeness: float = Field(..., ge=0, le=100, description="Completeness score")
    pronunciation: float = Field(..., ge=0, le=100, description="Overall pronunciation score")


class PronunciationFeedback(BaseModel):
    """Human-readable pronunciation feedback."""
    overall: str = Field(..., description="Overall feedback message")
    accuracy_feedback: Optional[str] = None
    fluency_feedback: Optional[str] = None
    suggestions: list[str] = Field(default_factory=list)


class ShadowingResultResponse(BaseModel):
    """Response after submitting shadowing audio."""
    type: str = Field(default="shadowing_result")
    status: str = Field(..., description="success or error")
    sound_id: str
    word: str
    recognized_text: str = Field(..., description="What was actually recognized")
    reference_text: str = Field(..., description="What was expected")
    scores: Optional[PronunciationScores] = None
    words_detail: list[WordScore] = Field(default_factory=list)
    phonemes_detail: list[PhonemeScore] = Field(default_factory=list)
    feedback: Optional[PronunciationFeedback] = None
    passed: bool = Field(
        default=False,
        description="Whether pronunciation met minimum threshold (85%)"
    )
    attempt_number: int = Field(..., description="Current attempt number")
    attempts_remaining: int = Field(..., description="Attempts left")
    mastery_updated: bool = Field(
        default=False,
        description="Whether mastery level changed"
    )
    new_mastery_level: Optional[str] = None
    next_review_days: Optional[int] = None
    message: Optional[str] = None


class PronunciationProgressResponse(BaseModel):
    """Response containing pronunciation progress statistics."""
    total_sounds: int = Field(default=0, description="Total sounds in progress")
    mastered: int = Field(default=0, description="Sounds at mastery level (>= 85%)")
    practicing: int = Field(default=0, description="Sounds being practiced")
    needs_work: int = Field(default=0, description="Sounds needing more practice (<70%)")
    not_started: int = Field(default=0, description="Sounds not yet attempted")
    due_for_review: int = Field(default=0, description="Sounds due for SRS review")
    average_accuracy: float = Field(default=0.0, description="Average accuracy across all sounds")
    total_practice_count: int = Field(default=0, description="Total practice attempts")
    hardest_sounds: list[str] = Field(
        default_factory=list,
        description="Phonemes with lowest accuracy"
    )
    best_sounds: list[str] = Field(
        default_factory=list,
        description="Phonemes with highest accuracy"
    )


class SoundToReview(BaseModel):
    """A sound that needs review."""
    sound_id: str
    phoneme: str
    name: str
    difficulty: str
    average_accuracy: float = 0
    practice_count: int = 0
    last_practiced: Optional[str] = None
    days_since_practice: Optional[int] = None


class SoundsToReviewResponse(BaseModel):
    """Response containing list of sounds to review."""
    sounds: list[SoundToReview]
    total_due: int
    srs_due: int = Field(default=0, description="Due by SRS algorithm")
    low_accuracy_due: int = Field(default=0, description="Due to low accuracy")
    low_frequency_due: int = Field(default=0, description="Due to infrequent practice")


class PhoneticSoundSummary(BaseModel):
    """Summary of a phonetic sound for listing."""
    id: str
    phoneme: str
    name: str
    difficulty: str
    exists_in_portuguese: bool
    example_words: list[str] = Field(default_factory=list)
    user_accuracy: Optional[float] = None
    practice_count: Optional[int] = None
    mastered: Optional[bool] = None


class PhoneticSoundsListResponse(BaseModel):
    """Response containing list of phonetic sounds."""
    sounds: list[PhoneticSoundSummary]
    total: int
    difficulties: list[str] = Field(
        default_factory=list,
        description="Available difficulty levels"
    )


class PhonemeGuidanceResponse(BaseModel):
    """Response containing guidance for a specific phoneme."""
    phoneme: str
    name: str
    ipa: str
    mouth_position: MouthPositionInfo
    example_words: list[str]
    common_mistake: str
    tip: str
    portuguese_similar: Optional[str] = None
    video_url: Optional[str] = None
    diagram_url: Optional[str] = None
