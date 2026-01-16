"""
Speaking Schemas
Request and response schemas for speaking/conversation API endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== REQUEST SCHEMAS ====================

class StartSessionRequest(BaseModel):
    """Request to start a new speaking session."""
    topic: Optional[str] = Field(
        default=None,
        description="Conversation topic (if not provided, one will be selected)"
    )
    difficulty: Optional[str] = Field(
        default=None,
        description="Difficulty level override (beginner/intermediate)"
    )


class ConversationTurnRequest(BaseModel):
    """Request for a conversation turn (text input)."""
    session_id: str = Field(..., description="Active session ID")
    user_text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User's spoken text (transcribed)"
    )


class AudioTurnRequest(BaseModel):
    """Request for a conversation turn with audio."""
    session_id: str = Field(..., description="Active session ID")
    audio_base64: str = Field(..., description="Audio data in base64")
    audio_format: str = Field(default="wav", description="Audio format (wav, mp3)")


class EndSessionRequest(BaseModel):
    """Request to end a speaking session."""
    session_id: str = Field(..., description="Session ID to end")


# ==================== RESPONSE SCHEMAS ====================

class ConversationExchange(BaseModel):
    """A single exchange in a conversation."""
    turn_number: int = Field(..., description="Turn number in the conversation")
    speaker: str = Field(..., description="Who spoke (user or agent)")
    text: str = Field(..., description="What was said")
    timestamp: str = Field(..., description="When it was said")
    audio_base64: Optional[str] = Field(default=None, description="TTS audio for agent responses")
    detected_errors: Optional[list[dict]] = Field(default=None, description="Errors detected in user speech")


class GrammarError(BaseModel):
    """A detected grammar error."""
    type: str = Field(default="grammar", description="Error type")
    incorrect_text: str = Field(..., description="The incorrect text")
    correction: str = Field(..., description="The correct version")
    rule: str = Field(..., description="Grammar rule violated")
    explanation: str = Field(..., description="Explanation of the error")


class PronunciationError(BaseModel):
    """A detected pronunciation error."""
    type: str = Field(default="pronunciation", description="Error type")
    word: str = Field(..., description="Word with pronunciation issue")
    phoneme: str = Field(..., description="Problematic phoneme")
    accuracy_score: float = Field(..., description="Pronunciation accuracy score")
    expected: str = Field(..., description="Expected pronunciation")
    detected: str = Field(..., description="Detected pronunciation")


class StartSessionResponse(BaseModel):
    """Response after starting a new speaking session."""
    type: str = Field(default="speaking_session_start")
    status: str = Field(..., description="success or error")
    session_id: Optional[str] = Field(default=None, description="New session ID")
    topic: Optional[str] = Field(default=None, description="Selected conversation topic")
    topic_description: Optional[str] = Field(default=None, description="Description of the topic")
    initial_prompt: Optional[str] = Field(default=None, description="Agent's opening message")
    initial_prompt_audio: Optional[str] = Field(default=None, description="TTS audio for opening")
    suggested_responses: Optional[list[str]] = Field(default=None, description="Suggested user responses")
    message: Optional[str] = Field(default=None, description="Error message if any")


class ConversationTurnResponse(BaseModel):
    """Response after a conversation turn."""
    type: str = Field(default="speaking_turn")
    status: str = Field(..., description="success, error, or session_ended")
    session_id: str = Field(..., description="Session ID")
    turn_number: int = Field(..., description="Current turn number")
    user_input: str = Field(..., description="User's input (transcribed if audio)")
    agent_response: Optional[str] = Field(default=None, description="Agent's response text")
    agent_audio_base64: Optional[str] = Field(default=None, description="TTS audio for response")
    errors_detected: Optional[list[dict]] = Field(default=None, description="Errors in user's speech")
    grammar_errors: Optional[list[GrammarError]] = Field(default=None, description="Grammar errors")
    pronunciation_errors: Optional[list[PronunciationError]] = Field(default=None, description="Pronunciation errors")
    conversation_continuing: bool = Field(default=True, description="Whether conversation continues")
    message: Optional[str] = Field(default=None, description="Additional message or error")


class SessionSummary(BaseModel):
    """Summary of a speaking session."""
    total_turns: int = Field(default=0, description="Total conversation turns")
    duration_seconds: int = Field(default=0, description="Session duration")
    total_errors: int = Field(default=0, description="Total errors detected")
    grammar_error_count: int = Field(default=0, description="Number of grammar errors")
    pronunciation_error_count: int = Field(default=0, description="Number of pronunciation errors")
    unique_grammar_rules_violated: list[str] = Field(default_factory=list, description="Grammar rules violated")
    problematic_phonemes: list[str] = Field(default_factory=list, description="Phonemes that need practice")
    activities_generated: int = Field(default=0, description="Corrective activities generated")
    overall_feedback: Optional[str] = Field(default=None, description="Overall session feedback")


class EndSessionResponse(BaseModel):
    """Response after ending a speaking session."""
    type: str = Field(default="speaking_session_end")
    status: str = Field(..., description="success or error")
    session_id: str = Field(..., description="Session ID")
    summary: Optional[SessionSummary] = Field(default=None, description="Session summary")
    grammar_errors: Optional[list[GrammarError]] = Field(default=None, description="All grammar errors")
    pronunciation_errors: Optional[list[PronunciationError]] = Field(default=None, description="All pronunciation errors")
    generated_activities: Optional[list[dict]] = Field(default=None, description="Generated corrective activities")
    message: Optional[str] = Field(default=None, description="Message or error")


class SpeakingProgressResponse(BaseModel):
    """Response with speaking progress statistics."""
    total_sessions: int = Field(default=0, description="Total speaking sessions")
    total_conversation_time_minutes: int = Field(default=0, description="Total conversation time")
    average_session_turns: float = Field(default=0.0, description="Average turns per session")
    common_grammar_errors: list[str] = Field(default_factory=list, description="Most common grammar errors")
    problematic_phonemes: list[str] = Field(default_factory=list, description="Phonemes needing practice")
    improvement_trend: Optional[str] = Field(default=None, description="Improvement trend")
    sessions_this_week: int = Field(default=0, description="Sessions in the last 7 days")


class TopicInfo(BaseModel):
    """Information about a conversation topic."""
    id: str = Field(..., description="Topic ID")
    name: str = Field(..., description="Topic name")
    description: str = Field(..., description="Topic description")
    difficulty: str = Field(..., description="Topic difficulty")
    sample_questions: list[str] = Field(default_factory=list, description="Sample questions")


class TopicsListResponse(BaseModel):
    """Response with list of available topics."""
    topics: list[TopicInfo] = Field(default_factory=list)
    total: int = Field(default=0)


class ActiveSessionResponse(BaseModel):
    """Response with active session information."""
    has_active_session: bool = Field(default=False, description="Whether user has active session")
    session_id: Optional[str] = Field(default=None, description="Active session ID")
    topic: Optional[str] = Field(default=None, description="Current topic")
    turn_count: Optional[int] = Field(default=None, description="Current turn count")
    started_at: Optional[str] = Field(default=None, description="When session started")
