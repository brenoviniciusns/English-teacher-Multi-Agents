"""
Tests for Core Agents (Phase 3)
Tests the base agent, state, assessment, scheduler, progress, and orchestrator.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Import agents and state
from app.agents.state import (
    AppState,
    create_initial_state,
    add_agent_message,
    get_pillar_from_request_type
)
from app.agents.base_agent import BaseAgent, AgentResult, AgentContext


class TestState:
    """Tests for agent state management."""

    def test_create_initial_state(self):
        """Test creating initial state."""
        state = create_initial_state(
            user_id="test_user_123",
            request_type="get_progress"
        )

        assert state["user"]["user_id"] == "test_user_123"
        assert state["request_type"] == "get_progress"
        assert state["is_complete"] is False
        assert state["has_error"] is False
        assert "request_id" in state
        assert "timestamp" in state

    def test_create_initial_state_with_user_data(self, sample_user_data):
        """Test creating initial state with user data."""
        state = create_initial_state(
            user_id="test_user_123",
            request_type="vocabulary_exercise",
            user_data=sample_user_data
        )

        assert state["user"]["email"] == "test@example.com"
        assert state["user"]["name"] == "Test User"
        assert state["user"]["current_level"] == "beginner"
        assert state["pillar_scores"]["vocabulary"] == 60.0

    def test_add_agent_message(self):
        """Test adding agent message to state."""
        state = create_initial_state("user123", "test")
        state = add_agent_message(
            state,
            agent="test_agent",
            message="Test message",
            data={"key": "value"}
        )

        assert len(state["messages"]) == 1
        assert state["messages"][0]["agent"] == "test_agent"
        assert state["messages"][0]["message"] == "Test message"
        assert state["messages"][0]["data"] == {"key": "value"}

    def test_get_pillar_from_request_type(self):
        """Test extracting pillar from request type."""
        assert get_pillar_from_request_type("vocabulary_exercise") == "vocabulary"
        assert get_pillar_from_request_type("grammar_lesson") == "grammar"
        assert get_pillar_from_request_type("pronunciation_exercise") == "pronunciation"
        assert get_pillar_from_request_type("speaking_session") == "speaking"
        assert get_pillar_from_request_type("unknown") is None


class TestAgentResult:
    """Tests for AgentResult class."""

    def test_success_result(self):
        """Test creating success result."""
        result = AgentResult.success_result(
            data={"score": 85},
            agent_name="test_agent"
        )

        assert result.success is True
        assert result.data == {"score": 85}
        assert result.agent_name == "test_agent"
        assert result.error is None

    def test_error_result(self):
        """Test creating error result."""
        result = AgentResult.error_result(
            error="Something went wrong",
            agent_name="test_agent"
        )

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.agent_name == "test_agent"

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = AgentResult.success_result(
            data={"test": "data"},
            agent_name="agent"
        )
        result_dict = result.to_dict()

        assert "success" in result_dict
        assert "data" in result_dict
        assert "timestamp" in result_dict


class TestAgentContext:
    """Tests for AgentContext class."""

    def test_create_context(self):
        """Test creating agent context."""
        context = AgentContext(
            user_id="user123",
            session_id="session456",
            request_type="vocabulary_exercise",
            pillar="vocabulary"
        )

        assert context.user_id == "user123"
        assert context.session_id == "session456"
        assert context.request_type == "vocabulary_exercise"
        assert context.pillar == "vocabulary"

    def test_context_to_dict(self):
        """Test converting context to dictionary."""
        context = AgentContext(
            user_id="user123",
            metadata={"extra": "info"}
        )
        context_dict = context.to_dict()

        assert context_dict["user_id"] == "user123"
        assert context_dict["metadata"] == {"extra": "info"}


class TestAssessmentAgent:
    """Tests for AssessmentAgent."""

    @pytest.fixture
    def assessment_agent(self, mock_settings, mock_cosmos_service, mock_openai_service):
        """Create assessment agent with mocks."""
        from app.agents.assessment_agent import AssessmentAgent
        agent = AssessmentAgent(
            settings=mock_settings,
            db_service=mock_cosmos_service,
            openai_service=mock_openai_service
        )
        return agent

    def test_agent_properties(self, assessment_agent):
        """Test agent name and description."""
        assert assessment_agent.name == "assessment"
        assert "proficiency" in assessment_agent.description.lower()

    def test_should_run_assessment_false(self, assessment_agent):
        """Test that assessment is not needed when sessions < threshold."""
        state = create_initial_state("user123", "vocabulary_exercise")
        state["user"]["initial_assessment_completed"] = True
        state["user"]["sessions_since_last_assessment"] = 2  # Below threshold (5)

        result = assessment_agent._should_run_assessment(state)
        assert result is False

    def test_should_run_assessment_true(self, assessment_agent):
        """Test that assessment is needed when sessions >= threshold."""
        state = create_initial_state("user123", "vocabulary_exercise")
        state["user"]["initial_assessment_completed"] = True
        state["user"]["sessions_since_last_assessment"] = 5  # At threshold

        result = assessment_agent._should_run_assessment(state)
        assert result is True

    def test_calculate_score(self, assessment_agent):
        """Test score calculation from results."""
        results = [
            {"correct": True},
            {"correct": True},
            {"correct": False},
            {"correct": True},
            {"correct": False}
        ]
        score = assessment_agent._calculate_score(results)
        assert score == 60.0  # 3/5 = 60%

    def test_calculate_score_empty(self, assessment_agent):
        """Test score calculation with empty results."""
        score = assessment_agent._calculate_score([])
        assert score == 0.0

    def test_determine_level_change_upgrade(self, assessment_agent):
        """Test level change determination for upgrade."""
        scores = {
            "vocabulary": 90,
            "grammar": 88,
            "pronunciation": 87,
            "speaking": 86
        }
        new_level, should_change = assessment_agent._determine_level_change(
            "beginner", scores
        )
        assert new_level == "intermediate"
        assert should_change is True

    def test_determine_level_change_no_change(self, assessment_agent):
        """Test level change when not ready."""
        scores = {
            "vocabulary": 70,
            "grammar": 65,
            "pronunciation": 60,
            "speaking": 55
        }
        new_level, should_change = assessment_agent._determine_level_change(
            "beginner", scores
        )
        assert new_level == "beginner"
        assert should_change is False

    def test_generate_recommendations(self, assessment_agent):
        """Test recommendation generation."""
        scores = {
            "vocabulary": 50,  # Weak
            "grammar": 75,     # OK
            "pronunciation": 90,  # Strong
            "speaking": 60     # Weak
        }
        recommendations = assessment_agent._generate_recommendations(scores, "beginner")

        assert len(recommendations) > 0
        # Should have recommendation for vocabulary (50%)
        vocab_rec = [r for r in recommendations if "vocabulary" in r.lower()]
        assert len(vocab_rec) > 0


class TestSchedulerAgent:
    """Tests for SchedulerAgent."""

    @pytest.fixture
    def scheduler_agent(self, mock_settings, mock_cosmos_service):
        """Create scheduler agent with mocks."""
        from app.agents.scheduler_agent import SchedulerAgent
        agent = SchedulerAgent(
            settings=mock_settings,
            db_service=mock_cosmos_service
        )
        return agent

    def test_agent_properties(self, scheduler_agent):
        """Test agent name and description."""
        assert scheduler_agent.name == "scheduler"
        assert "srs" in scheduler_agent.description.lower() or "scheduling" in scheduler_agent.description.lower()

    @pytest.mark.asyncio
    async def test_refresh_srs_state(self, scheduler_agent, mock_cosmos_service):
        """Test refreshing SRS state."""
        # Setup mock returns
        mock_cosmos_service.get_vocabulary_due_for_review.return_value = [
            {"wordId": "word1", "srsData": {"nextReview": datetime.utcnow().isoformat()}}
        ]
        mock_cosmos_service.get_grammar_due_for_review.return_value = []
        mock_cosmos_service.get_pronunciation_needs_practice.return_value = []
        mock_cosmos_service.get_vocabulary_low_frequency.return_value = []

        state = create_initial_state("user123", "get_schedule")
        result = await scheduler_agent._refresh_srs_state(state)

        assert result["srs"]["items_due_today"] == 1
        assert len(result["srs"]["items_due_vocabulary"]) == 1

    def test_get_highest_priority_item(self, scheduler_agent):
        """Test getting highest priority item."""
        vocab_due = [{"wordId": "w1", "pillar": "vocabulary"}]
        grammar_due = []
        pronun_due = []
        low_freq = []

        item = scheduler_agent._get_highest_priority_item(
            vocab_due, grammar_due, pronun_due, low_freq
        )

        assert item is not None
        assert item["pillar"] == "vocabulary"

    def test_get_highest_priority_item_empty(self, scheduler_agent):
        """Test getting highest priority when no items."""
        item = scheduler_agent._get_highest_priority_item([], [], [], [])
        assert item is None

    def test_get_learning_suggestions(self, scheduler_agent):
        """Test getting learning suggestions."""
        state = create_initial_state("user123", "get_next_activity")
        state["user"]["learning_goals"] = ["data_engineering"]
        state["pillar_scores"] = {
            "vocabulary": 80,
            "grammar": 60,  # Weakest
            "pronunciation": 70,
            "speaking": 75
        }

        suggestions = scheduler_agent._get_learning_suggestions(state)

        assert len(suggestions) > 0
        # Should suggest grammar as weakest
        grammar_suggestion = [s for s in suggestions if s.get("pillar") == "grammar"]
        assert len(grammar_suggestion) > 0


class TestProgressAgent:
    """Tests for ProgressAgent."""

    @pytest.fixture
    def progress_agent(self, mock_settings, mock_cosmos_service):
        """Create progress agent with mocks."""
        from app.agents.progress_agent import ProgressAgent
        agent = ProgressAgent(
            settings=mock_settings,
            db_service=mock_cosmos_service
        )
        return agent

    def test_agent_properties(self, progress_agent):
        """Test agent name and description."""
        assert progress_agent.name == "progress"
        assert "track" in progress_agent.description.lower() or "metric" in progress_agent.description.lower()

    def test_calculate_streak_active(self, progress_agent):
        """Test streak calculation when active."""
        user = {
            "last_activity_date": datetime.utcnow().isoformat(),
            "current_streak_days": 5
        }
        streak = progress_agent._calculate_streak(user)
        assert streak == 5

    def test_calculate_streak_broken(self, progress_agent):
        """Test streak calculation when broken."""
        user = {
            "last_activity_date": (datetime.utcnow() - timedelta(days=3)).isoformat(),
            "current_streak_days": 5
        }
        streak = progress_agent._calculate_streak(user)
        assert streak == 0

    def test_check_level_up_readiness_true(self, progress_agent):
        """Test level up readiness when ready."""
        pillars = {
            "vocabulary": 90,
            "grammar": 88,
            "pronunciation": 87,
            "speaking": 86
        }
        ready = progress_agent._check_level_up_readiness("beginner", pillars)
        assert ready is True

    def test_check_level_up_readiness_false(self, progress_agent):
        """Test level up readiness when not ready."""
        pillars = {
            "vocabulary": 90,
            "grammar": 70,  # Below threshold
            "pronunciation": 87,
            "speaking": 86
        }
        ready = progress_agent._check_level_up_readiness("beginner", pillars)
        assert ready is False

    def test_check_level_up_already_intermediate(self, progress_agent):
        """Test level up when already intermediate."""
        pillars = {"vocabulary": 95, "grammar": 95, "pronunciation": 95, "speaking": 95}
        ready = progress_agent._check_level_up_readiness("intermediate", pillars)
        assert ready is False

    def test_get_achievements(self, progress_agent):
        """Test getting achievements."""
        user = {"current_streak_days": 7, "longest_streak_days": 10}
        stats = {
            "vocabulary": {"mastered": 150},
            "speaking": {"sessions_last_30_days": 12}
        }
        achievements = progress_agent._get_achievements(user, stats)

        assert len(achievements) > 0
        # Should have streak achievement
        streak_achievement = [a for a in achievements if "streak" in a.lower()]
        assert len(streak_achievement) > 0


class TestOrchestrator:
    """Tests for Orchestrator."""

    @pytest.fixture
    def orchestrator_instance(self, mock_settings, mock_cosmos_service):
        """Create orchestrator with mocks."""
        with patch("app.agents.orchestrator.cosmos_db_service", mock_cosmos_service):
            from app.agents.orchestrator import Orchestrator
            return Orchestrator(settings=mock_settings)

    def test_orchestrator_properties(self, orchestrator_instance):
        """Test orchestrator name and description."""
        assert orchestrator_instance.name == "orchestrator"
        assert "coordinate" in orchestrator_instance.description.lower()

    def test_orchestrator_has_graph(self, orchestrator_instance):
        """Test that orchestrator builds a graph."""
        assert orchestrator_instance.graph is not None
        assert orchestrator_instance.compiled_graph is not None

    @pytest.mark.asyncio
    async def test_router_node_progress(self, orchestrator_instance):
        """Test router routes to progress for get_progress request."""
        state = create_initial_state("user123", "get_progress")
        result = await orchestrator_instance._router_node(state)

        assert result["route_decision"] == "progress"

    @pytest.mark.asyncio
    async def test_router_node_assessment(self, orchestrator_instance):
        """Test router routes to assessment."""
        state = create_initial_state("user123", "assessment_initial")
        result = await orchestrator_instance._router_node(state)

        assert result["route_decision"] == "assessment"

    @pytest.mark.asyncio
    async def test_router_node_scheduler(self, orchestrator_instance):
        """Test router routes to scheduler."""
        state = create_initial_state("user123", "get_schedule")
        result = await orchestrator_instance._router_node(state)

        assert result["route_decision"] == "scheduler"

    @pytest.mark.asyncio
    async def test_router_node_vocabulary(self, orchestrator_instance):
        """Test router routes to vocabulary."""
        state = create_initial_state("user123", "vocabulary_exercise")
        result = await orchestrator_instance._router_node(state)

        assert result["route_decision"] == "vocabulary"

    @pytest.mark.asyncio
    async def test_router_node_unknown(self, orchestrator_instance):
        """Test router handles unknown request type."""
        state = create_initial_state("user123", "unknown_type")
        result = await orchestrator_instance._router_node(state)

        assert result["route_decision"] == "complete"
        assert "error" in result["response"]

    @pytest.mark.asyncio
    async def test_finalize_node(self, orchestrator_instance):
        """Test finalize node marks state as complete."""
        state = create_initial_state("user123", "get_progress")
        state["response"] = {"test": "data"}

        result = await orchestrator_instance._finalize_node(state)

        assert result["is_complete"] is True
        assert "timestamp" in result["response"]
        assert "request_id" in result["response"]
