"""
Orchestrator Agent
Central coordinator for the multi-agent system using LangGraph.

Responsibilities:
- Route requests to appropriate agents
- Manage agent workflow and state transitions
- Coordinate multi-step operations
- Handle errors and fallbacks
"""
import logging
from typing import Literal, Annotated
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.state import (
    AppState,
    create_initial_state,
    add_agent_message,
    get_pillar_from_request_type
)
from app.agents.assessment_agent import assessment_agent
from app.agents.scheduler_agent import scheduler_agent
from app.agents.progress_agent import progress_agent
from app.agents.vocabulary_agent import vocabulary_agent
from app.agents.grammar_agent import grammar_agent
from app.config import Settings, get_settings
from app.services.cosmos_db_service import cosmos_db_service


logger = logging.getLogger(__name__)


# Define route types for type safety
RouteType = Literal[
    "assessment",
    "scheduler",
    "progress",
    "vocabulary",
    "grammar",
    "pronunciation",
    "speaking",
    "error_integration",
    "complete"
]


class Orchestrator(BaseAgent[AppState]):
    """
    Orchestrator Agent - Central coordinator for all agents.

    Uses LangGraph to define agent workflows and manage state
    transitions between agents.
    """

    def __init__(self, settings: Settings | None = None):
        super().__init__(settings=settings)
        self.graph = self._build_graph()
        self.compiled_graph = self.graph.compile()

    @property
    def name(self) -> str:
        return "orchestrator"

    @property
    def description(self) -> str:
        return "Coordinates all agents and manages workflow execution"

    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow.

        Graph structure:
        START -> router -> [agent nodes] -> progress -> END
        """
        # Create graph with AppState
        graph = StateGraph(AppState)

        # Add nodes for each agent
        graph.add_node("router", self._router_node)
        graph.add_node("assessment", self._assessment_node)
        graph.add_node("scheduler", self._scheduler_node)
        graph.add_node("progress", self._progress_node)
        graph.add_node("vocabulary", self._vocabulary_node)
        graph.add_node("grammar", self._grammar_node)
        graph.add_node("pronunciation", self._pronunciation_node)
        graph.add_node("speaking", self._speaking_node)
        graph.add_node("error_integration", self._error_integration_node)
        graph.add_node("finalize", self._finalize_node)

        # Set entry point
        graph.set_entry_point("router")

        # Add conditional edges from router
        graph.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "assessment": "assessment",
                "scheduler": "scheduler",
                "progress": "progress",
                "vocabulary": "vocabulary",
                "grammar": "grammar",
                "pronunciation": "pronunciation",
                "speaking": "speaking",
                "error_integration": "error_integration",
                "complete": "finalize"
            }
        )

        # Add edges from agent nodes
        # Assessment can loop back to itself or go to progress
        graph.add_conditional_edges(
            "assessment",
            self._post_assessment_route,
            {
                "continue": "assessment",
                "progress": "progress",
                "complete": "finalize"
            }
        )

        # Scheduler goes to progress or directly to complete
        graph.add_conditional_edges(
            "scheduler",
            self._post_scheduler_route,
            {
                "progress": "progress",
                "complete": "finalize"
            }
        )

        # Pillar agents go to error_integration then progress
        for pillar in ["vocabulary", "grammar", "pronunciation"]:
            graph.add_conditional_edges(
                pillar,
                self._post_pillar_route,
                {
                    "error_integration": "error_integration",
                    "progress": "progress",
                    "complete": "finalize"
                }
            )

        # Speaking goes to error_integration
        graph.add_conditional_edges(
            "speaking",
            self._post_speaking_route,
            {
                "error_integration": "error_integration",
                "progress": "progress",
                "complete": "finalize"
            }
        )

        # Error integration goes to progress
        graph.add_edge("error_integration", "progress")

        # Progress goes to finalize
        graph.add_edge("progress", "finalize")

        # Finalize ends the graph
        graph.add_edge("finalize", END)

        return graph

    async def process(self, state: AppState) -> AppState:
        """
        Process a request through the agent workflow.

        This is the main entry point for the orchestrator.
        """
        self.log_start({
            "request_type": state.get("request_type"),
            "user_id": state["user"]["user_id"]
        })

        try:
            # Run the compiled graph
            final_state = await self.compiled_graph.ainvoke(state)

            self.log_complete({
                "is_complete": final_state.get("is_complete"),
                "has_error": final_state.get("has_error")
            })

            return final_state

        except Exception as e:
            self.log_error(e)
            state["has_error"] = True
            state["error_message"] = f"Orchestrator error: {str(e)}"
            state["is_complete"] = True
            return state

    async def run(
        self,
        user_id: str,
        request_type: str,
        input_data: dict | None = None
    ) -> AppState:
        """
        Run the orchestrator with a new request.

        Args:
            user_id: User making the request
            request_type: Type of request
            input_data: Additional input data

        Returns:
            Final state after processing
        """
        # Get user data from database
        user_data = await cosmos_db_service.get_user(user_id)

        # Create initial state
        state = create_initial_state(user_id, request_type, user_data)

        # Add input data if provided
        if input_data:
            state["activity_input"] = input_data

        # Process through the graph
        return await self.process(state)

    # ==================== ROUTER NODE ====================

    async def _router_node(self, state: AppState) -> AppState:
        """
        Router node - decides which agent to invoke.

        Routes based on request_type and current state.
        """
        self.log_debug("Router processing", {"request_type": state.get("request_type")})

        request_type = state.get("request_type", "")

        # Determine route based on request type
        if request_type in ["assessment_initial", "assessment_continuous"]:
            state["route_decision"] = "assessment"

        elif request_type in ["get_schedule", "get_next_activity"]:
            state["route_decision"] = "scheduler"

        elif request_type == "get_progress":
            state["route_decision"] = "progress"

        elif request_type == "vocabulary_exercise":
            state["route_decision"] = "vocabulary"

        elif request_type in ["grammar_lesson", "grammar_exercise"]:
            state["route_decision"] = "grammar"

        elif request_type in ["pronunciation_exercise", "shadowing"]:
            state["route_decision"] = "pronunciation"

        elif request_type == "speaking_session":
            state["route_decision"] = "speaking"

        else:
            # Unknown request - go to complete
            state["route_decision"] = "complete"
            state["response"] = {
                "error": f"Unknown request type: {request_type}"
            }

        state = add_agent_message(
            state,
            self.name,
            f"Routing to: {state['route_decision']}"
        )

        return state

    def _route_decision(self, state: AppState) -> RouteType:
        """Get routing decision from state"""
        return state.get("route_decision", "complete")

    # ==================== AGENT NODES ====================

    async def _assessment_node(self, state: AppState) -> AppState:
        """Assessment agent node"""
        self.log_debug("Assessment node processing")
        return await assessment_agent.process(state)

    async def _scheduler_node(self, state: AppState) -> AppState:
        """Scheduler agent node"""
        self.log_debug("Scheduler node processing")
        return await scheduler_agent.process(state)

    async def _progress_node(self, state: AppState) -> AppState:
        """Progress agent node"""
        self.log_debug("Progress node processing")

        # Determine if we need to update or get progress
        if state.get("activity_output"):
            # Update progress after activity
            return await progress_agent._update_progress(state)
        else:
            # Get progress if explicitly requested
            if state.get("request_type") == "get_progress":
                return await progress_agent._get_overall_progress(state)
            return state

    async def _vocabulary_node(self, state: AppState) -> AppState:
        """
        Vocabulary agent node.

        Handles vocabulary exercises through the VocabularyAgent.
        Supports exercise generation and answer processing.
        """
        self.log_debug("Vocabulary node processing")
        return await vocabulary_agent.process(state)

    async def _grammar_node(self, state: AppState) -> AppState:
        """
        Grammar agent node.

        Handles grammar lessons and exercises through the GrammarAgent.
        Supports lesson presentation, explanation evaluation, and exercises.
        """
        self.log_debug("Grammar node processing")
        return await grammar_agent.process(state)

    async def _pronunciation_node(self, state: AppState) -> AppState:
        """
        Pronunciation agent node (placeholder for Phase 6).

        Will be fully implemented in the Pronunciation Pillar phase.
        """
        self.log_debug("Pronunciation node processing")

        # Placeholder response
        state["response"] = {
            "type": "pronunciation_exercise",
            "status": "not_implemented",
            "message": "Pronunciation agent will be implemented in Phase 6"
        }
        state["is_complete"] = True

        return state

    async def _speaking_node(self, state: AppState) -> AppState:
        """
        Speaking agent node (placeholder for Phase 7).

        Will be fully implemented in the Speaking Pillar phase.
        """
        self.log_debug("Speaking node processing")

        # Placeholder response
        state["response"] = {
            "type": "speaking_session",
            "status": "not_implemented",
            "message": "Speaking agent will be implemented in Phase 7"
        }
        state["is_complete"] = True

        return state

    async def _error_integration_node(self, state: AppState) -> AppState:
        """
        Error integration agent node (placeholder for Phase 7).

        Will be fully implemented alongside Speaking Pillar.
        """
        self.log_debug("Error integration node processing")

        # Check if there are errors to process
        if state["errors"].get("has_errors"):
            # Placeholder - will generate activities from errors
            state["errors"]["generated_activity_ids"] = []

        return state

    async def _finalize_node(self, state: AppState) -> AppState:
        """
        Finalize node - prepare final response.

        Marks processing as complete and prepares response.
        """
        self.log_debug("Finalize node processing")

        state["is_complete"] = True

        # Add timestamp to response
        if "response" in state:
            state["response"]["timestamp"] = datetime.utcnow().isoformat()
            state["response"]["request_id"] = state.get("request_id")

        state = add_agent_message(
            state,
            self.name,
            "Processing complete"
        )

        return state

    # ==================== CONDITIONAL ROUTING ====================

    def _post_assessment_route(
        self,
        state: AppState
    ) -> Literal["continue", "progress", "complete"]:
        """Route after assessment node"""
        assessment_state = state.get("assessment", {})

        # Check if assessment is multi-step and not complete
        if (assessment_state.get("is_initial") and
            assessment_state.get("current_step", 0) < assessment_state.get("total_steps", 0)):
            return "continue"

        # Assessment complete - go to progress
        if assessment_state.get("final_scores"):
            return "progress"

        return "complete"

    def _post_scheduler_route(
        self,
        state: AppState
    ) -> Literal["progress", "complete"]:
        """Route after scheduler node"""
        # If getting next activity, might need progress update
        if state.get("request_type") == "get_next_activity":
            return "complete"  # Don't update progress just for getting next item

        return "complete"

    def _post_pillar_route(
        self,
        state: AppState
    ) -> Literal["error_integration", "progress", "complete"]:
        """Route after pillar activity nodes"""
        activity_output = state.get("activity_output", {})

        # Check if there are errors to process
        if activity_output.get("errors"):
            state["errors"]["has_errors"] = True
            state["errors"]["pending_errors"] = activity_output["errors"]
            return "error_integration"

        # No errors - go directly to progress
        if activity_output:
            return "progress"

        return "complete"

    def _post_speaking_route(
        self,
        state: AppState
    ) -> Literal["error_integration", "progress", "complete"]:
        """Route after speaking node"""
        speaking_state = state.get("speaking", {})

        # If session ended with errors, go to error integration
        if (not speaking_state.get("is_active") and
            (speaking_state.get("grammar_errors") or speaking_state.get("pronunciation_errors"))):
            state["errors"]["has_errors"] = True
            state["errors"]["pending_errors"] = (
                speaking_state.get("grammar_errors", []) +
                speaking_state.get("pronunciation_errors", [])
            )
            return "error_integration"

        # If session just ended, go to progress
        if not speaking_state.get("is_active"):
            return "progress"

        return "complete"


# Singleton instance
orchestrator = Orchestrator()


# Convenience function to run orchestrator
async def run_orchestrator(
    user_id: str,
    request_type: str,
    input_data: dict | None = None
) -> AppState:
    """
    Run the orchestrator with a request.

    Args:
        user_id: User making the request
        request_type: Type of request (e.g., "get_progress", "vocabulary_exercise")
        input_data: Additional input data for the request

    Returns:
        Final state with response

    Example:
        >>> state = await run_orchestrator(
        ...     user_id="user123",
        ...     request_type="get_progress"
        ... )
        >>> print(state["response"])
    """
    return await orchestrator.run(user_id, request_type, input_data)
