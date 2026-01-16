"""
Agents Module
Multi-agent system for English learning using LangGraph.

This module contains:
- Base agent class and utilities
- Shared state definition
- Specialized agents for each learning pillar
- Orchestrator for coordinating all agents

Available Agents:
- Orchestrator: Central coordinator using LangGraph
- Assessment: Initial and continuous proficiency evaluation
- Scheduler: SRS-based activity scheduling
- Progress: Progress tracking and reporting
- Vocabulary: Vocabulary learning (Phase 4)
- Grammar: Grammar learning (Phase 5)
- Pronunciation: Pronunciation practice (Phase 6)
- Speaking: Conversation practice (Phase 7)
- ErrorIntegration: Error detection and activity generation (Phase 7)
"""

# Base classes and utilities
from app.agents.base_agent import (
    BaseAgent,
    AgentResult,
    AgentContext
)

# Shared state
from app.agents.state import (
    AppState,
    UserState,
    PillarScores,
    ActivityState,
    SRSState,
    AssessmentState,
    SpeakingState,
    ProgressState,
    ErrorState,
    AgentMessage,
    create_initial_state,
    add_agent_message,
    get_pillar_from_request_type
)

# Core agents (Phase 3)
from app.agents.assessment_agent import (
    AssessmentAgent,
    assessment_agent
)

from app.agents.scheduler_agent import (
    SchedulerAgent,
    scheduler_agent
)

from app.agents.progress_agent import (
    ProgressAgent,
    progress_agent
)

# Pillar agents (Phase 4+)
from app.agents.vocabulary_agent import (
    VocabularyAgent,
    vocabulary_agent
)

# Orchestrator
from app.agents.orchestrator import (
    Orchestrator,
    orchestrator,
    run_orchestrator
)


__all__ = [
    # Base classes
    "BaseAgent",
    "AgentResult",
    "AgentContext",

    # State types
    "AppState",
    "UserState",
    "PillarScores",
    "ActivityState",
    "SRSState",
    "AssessmentState",
    "SpeakingState",
    "ProgressState",
    "ErrorState",
    "AgentMessage",

    # State utilities
    "create_initial_state",
    "add_agent_message",
    "get_pillar_from_request_type",

    # Core Agents
    "AssessmentAgent",
    "assessment_agent",
    "SchedulerAgent",
    "scheduler_agent",
    "ProgressAgent",
    "progress_agent",
    "Orchestrator",
    "orchestrator",

    # Pillar Agents
    "VocabularyAgent",
    "vocabulary_agent",

    # Convenience functions
    "run_orchestrator"
]
