"""
Agent State
Defines the shared state structure for the LangGraph multi-agent system.
All agents read from and write to this state.
"""
from datetime import datetime
from typing import Optional, Any, Literal
from typing_extensions import TypedDict


class UserState(TypedDict, total=False):
    """User-related state"""
    user_id: str
    email: str
    name: str
    current_level: Literal["beginner", "intermediate"]
    daily_goal_minutes: int
    learning_goals: list[str]
    voice_preference: str
    initial_assessment_completed: bool
    sessions_since_last_assessment: int


class PillarScores(TypedDict, total=False):
    """Scores for each learning pillar"""
    vocabulary: float
    grammar: float
    pronunciation: float
    speaking: float


class ActivityState(TypedDict, total=False):
    """Current activity state"""
    activity_id: str
    activity_type: str
    pillar: str
    content: dict
    started_at: str
    status: Literal["pending", "in_progress", "completed", "failed"]
    result: Optional[dict]


class SRSState(TypedDict, total=False):
    """Spaced Repetition System state"""
    items_due_today: int
    items_due_vocabulary: list[dict]
    items_due_grammar: list[dict]
    items_due_pronunciation: list[dict]
    low_frequency_items: list[dict]
    next_item: Optional[dict]


class AssessmentState(TypedDict, total=False):
    """Assessment state"""
    is_initial: bool
    is_continuous: bool
    current_step: int
    total_steps: int
    vocabulary_results: list[dict]
    grammar_results: list[dict]
    pronunciation_results: list[dict]
    speaking_results: list[dict]
    final_scores: Optional[PillarScores]
    determined_level: Optional[str]
    recommendations: list[str]


class SpeakingState(TypedDict, total=False):
    """Speaking/conversation session state"""
    session_id: str
    topic: str
    exchanges: list[dict]
    current_turn: int
    errors_detected: list[dict]
    grammar_errors: list[dict]
    pronunciation_errors: list[dict]
    is_active: bool


class ProgressState(TypedDict, total=False):
    """Progress tracking state"""
    total_study_time_minutes: int
    today_study_minutes: int
    today_activities_completed: int
    current_streak_days: int
    pillar_progress: dict[str, dict]
    weakest_pillar: Optional[str]
    ready_for_level_up: bool


class ErrorState(TypedDict, total=False):
    """Error tracking for activity generation"""
    has_errors: bool
    pending_errors: list[dict]
    activities_to_generate: list[dict]
    generated_activity_ids: list[str]


class AgentMessage(TypedDict):
    """Message from an agent"""
    agent: str
    message: str
    timestamp: str
    data: Optional[dict]


class AppState(TypedDict, total=False):
    """
    Main application state shared across all agents.

    This TypedDict defines all possible state keys that agents can read/write.
    LangGraph uses this for state management between nodes.
    """

    # ==================== REQUEST CONTEXT ====================
    # Set at the beginning of each request
    request_id: str
    request_type: Literal[
        "assessment_initial",
        "assessment_continuous",
        "vocabulary_exercise",
        "grammar_lesson",
        "grammar_exercise",
        "pronunciation_exercise",
        "shadowing",
        "speaking_session",
        "get_next_activity",
        "get_progress",
        "get_schedule"
    ]
    timestamp: str

    # ==================== USER STATE ====================
    user: UserState
    pillar_scores: PillarScores

    # ==================== CURRENT ACTIVITY ====================
    current_activity: ActivityState
    activity_input: dict  # User input for current activity
    activity_output: dict  # Agent output for current activity

    # ==================== SRS / SCHEDULING ====================
    srs: SRSState
    daily_schedule: dict
    schedule_date: str

    # ==================== ASSESSMENT ====================
    assessment: AssessmentState

    # ==================== SPEAKING ====================
    speaking: SpeakingState

    # ==================== PROGRESS ====================
    progress: ProgressState

    # ==================== ERROR INTEGRATION ====================
    errors: ErrorState

    # ==================== AGENT COORDINATION ====================
    # Which agent should process next
    next_agent: Optional[str]
    # Route decision made by orchestrator
    route_decision: Optional[str]
    # History of agent messages for debugging
    messages: list[AgentMessage]
    # Final response to return to user
    response: dict

    # ==================== CONTROL FLAGS ====================
    # Whether processing is complete
    is_complete: bool
    # Whether an error occurred
    has_error: bool
    error_message: Optional[str]


def create_initial_state(
    user_id: str,
    request_type: str,
    user_data: dict | None = None
) -> AppState:
    """
    Create initial state for a new request.

    Args:
        user_id: User ID for the request
        request_type: Type of request being made
        user_data: Optional user data to populate user state

    Returns:
        Initialized AppState
    """
    now = datetime.utcnow().isoformat()

    state: AppState = {
        # Request context
        "request_id": f"req_{user_id}_{datetime.utcnow().timestamp()}",
        "request_type": request_type,
        "timestamp": now,

        # User state
        "user": {
            "user_id": user_id,
            "current_level": "beginner",
            "daily_goal_minutes": 30,
            "learning_goals": ["general"],
            "initial_assessment_completed": False,
            "sessions_since_last_assessment": 0
        },
        "pillar_scores": {
            "vocabulary": 0.0,
            "grammar": 0.0,
            "pronunciation": 0.0,
            "speaking": 0.0
        },

        # Activity state
        "current_activity": {},
        "activity_input": {},
        "activity_output": {},

        # SRS state
        "srs": {
            "items_due_today": 0,
            "items_due_vocabulary": [],
            "items_due_grammar": [],
            "items_due_pronunciation": [],
            "low_frequency_items": [],
            "next_item": None
        },
        "daily_schedule": {},
        "schedule_date": now[:10],  # YYYY-MM-DD

        # Assessment state
        "assessment": {
            "is_initial": False,
            "is_continuous": False,
            "current_step": 0,
            "total_steps": 0,
            "vocabulary_results": [],
            "grammar_results": [],
            "pronunciation_results": [],
            "speaking_results": [],
            "recommendations": []
        },

        # Speaking state
        "speaking": {
            "session_id": "",
            "topic": "",
            "exchanges": [],
            "current_turn": 0,
            "errors_detected": [],
            "grammar_errors": [],
            "pronunciation_errors": [],
            "is_active": False
        },

        # Progress state
        "progress": {
            "total_study_time_minutes": 0,
            "today_study_minutes": 0,
            "today_activities_completed": 0,
            "current_streak_days": 0,
            "pillar_progress": {},
            "weakest_pillar": None,
            "ready_for_level_up": False
        },

        # Error state
        "errors": {
            "has_errors": False,
            "pending_errors": [],
            "activities_to_generate": [],
            "generated_activity_ids": []
        },

        # Agent coordination
        "next_agent": None,
        "route_decision": None,
        "messages": [],
        "response": {},

        # Control flags
        "is_complete": False,
        "has_error": False,
        "error_message": None
    }

    # Populate user data if provided
    if user_data:
        state["user"].update({
            "email": user_data.get("email", ""),
            "name": user_data.get("name", ""),
            "current_level": user_data.get("current_level", "beginner"),
            "daily_goal_minutes": user_data.get("profile", {}).get("daily_goal_minutes", 30),
            "learning_goals": user_data.get("profile", {}).get("learning_goals", ["general"]),
            "voice_preference": user_data.get("profile", {}).get("voice_preference", "american_female"),
            "initial_assessment_completed": user_data.get("initial_assessment_completed", False),
            "sessions_since_last_assessment": user_data.get("sessions_since_last_assessment", 0)
        })
        state["pillar_scores"] = {
            "vocabulary": float(user_data.get("vocabulary_score", 0)),
            "grammar": float(user_data.get("grammar_score", 0)),
            "pronunciation": float(user_data.get("pronunciation_score", 0)),
            "speaking": float(user_data.get("speaking_score", 0))
        }

    return state


def add_agent_message(
    state: AppState,
    agent: str,
    message: str,
    data: dict | None = None
) -> AppState:
    """
    Add a message from an agent to the state.

    Args:
        state: Current state
        agent: Agent name
        message: Message text
        data: Optional additional data

    Returns:
        Updated state
    """
    msg: AgentMessage = {
        "agent": agent,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }
    state["messages"].append(msg)
    return state


def get_pillar_from_request_type(request_type: str) -> str | None:
    """
    Extract pillar from request type.

    Args:
        request_type: Request type string

    Returns:
        Pillar name or None
    """
    mapping = {
        "vocabulary_exercise": "vocabulary",
        "grammar_lesson": "grammar",
        "grammar_exercise": "grammar",
        "pronunciation_exercise": "pronunciation",
        "shadowing": "pronunciation",
        "speaking_session": "speaking"
    }
    return mapping.get(request_type)
