"""
Tests for Speaking Agent
Tests conversation session management, turn processing, and error detection.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.agents.speaking_agent import SpeakingAgent, speaking_agent
from app.agents.state import create_initial_state, AppState


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock()
    settings.AZURE_OPENAI_API_KEY = "test-key"
    settings.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com"
    settings.AZURE_SPEECH_KEY = "test-speech-key"
    settings.AZURE_SPEECH_REGION = "eastus"
    return settings


@pytest.fixture
def mock_openai_service():
    """Mock Azure OpenAI service."""
    service = MagicMock()
    service.generate_conversation_response = AsyncMock(
        return_value="That's interesting! Tell me more about it."
    )
    service.detect_grammar_errors = AsyncMock(
        return_value={
            "errors": [],
            "error_count": 0,
            "overall_assessment": "Good job!"
        }
    )
    return service


@pytest.fixture
def mock_speech_service():
    """Mock Azure Speech service."""
    service = MagicMock()
    service.text_to_speech = MagicMock(return_value=b"fake_audio_bytes")
    service.speech_to_text = MagicMock(
        return_value={"text": "I wake up at seven in the morning."}
    )
    service.pronunciation_assessment = MagicMock(
        return_value={
            "success": True,
            "scores": {"accuracy": 85, "fluency": 80},
            "words": [],
            "phonemes": []
        }
    )
    return service


@pytest.fixture
def mock_db_service():
    """Mock Cosmos DB service."""
    service = MagicMock()
    service.create_speaking_session = AsyncMock(return_value={"id": "session_test_123"})
    service.get_speaking_session = AsyncMock(return_value={
        "id": "session_test_123",
        "status": "active",
        "topicName": "Daily Routine",
        "currentTurn": 1,
        "exchanges": [{
            "turn_number": 0,
            "speaker": "agent",
            "text": "Hi! What time do you wake up?",
            "timestamp": datetime.utcnow().isoformat()
        }],
        "grammarErrors": [],
        "pronunciationErrors": []
    })
    service.update_speaking_session = AsyncMock(return_value={})
    service.end_speaking_session = AsyncMock(return_value={})
    service.query_items = AsyncMock(return_value=[])
    return service


@pytest.fixture
def speaking_agent_instance(mock_settings, mock_openai_service, mock_speech_service, mock_db_service):
    """Create a SpeakingAgent instance with mocked services."""
    agent = SpeakingAgent(settings=mock_settings)
    agent.openai_service = mock_openai_service
    agent.speech_service = mock_speech_service
    agent.db_service = mock_db_service
    return agent


class TestSpeakingAgentProperties:
    """Test SpeakingAgent properties."""

    def test_agent_name(self, speaking_agent_instance):
        """Test agent name property."""
        assert speaking_agent_instance.name == "speaking"

    def test_agent_description(self, speaking_agent_instance):
        """Test agent description property."""
        assert "conversation" in speaking_agent_instance.description.lower()


class TestStartSession:
    """Test session start functionality."""

    @pytest.mark.asyncio
    async def test_start_session_success(self, speaking_agent_instance):
        """Test successful session start."""
        state = create_initial_state(
            user_id="test_user",
            request_type="speaking_session"
        )
        state["activity_input"] = {"action": "start"}

        result = await speaking_agent_instance.process(state)

        assert result["response"]["status"] == "success"
        assert "session_id" in result["response"]
        assert result["speaking"]["is_active"] is True

    @pytest.mark.asyncio
    async def test_start_session_with_topic(self, speaking_agent_instance):
        """Test session start with specific topic."""
        state = create_initial_state(
            user_id="test_user",
            request_type="speaking_session"
        )
        state["activity_input"] = {
            "action": "start",
            "topic_id": "daily_routine"
        }

        result = await speaking_agent_instance.process(state)

        assert result["response"]["status"] == "success"
        assert result["response"].get("topic") is not None

    @pytest.mark.asyncio
    async def test_start_session_generates_opening_prompt(self, speaking_agent_instance):
        """Test that session start generates an opening prompt."""
        state = create_initial_state(
            user_id="test_user",
            request_type="speaking_session"
        )
        state["activity_input"] = {"action": "start"}

        result = await speaking_agent_instance.process(state)

        assert result["response"]["initial_prompt"] is not None
        assert len(result["response"]["initial_prompt"]) > 0


class TestProcessTurn:
    """Test conversation turn processing."""

    @pytest.mark.asyncio
    async def test_process_text_turn(self, speaking_agent_instance):
        """Test processing a text turn."""
        state = create_initial_state(
            user_id="test_user",
            request_type="speaking_session"
        )
        state["activity_input"] = {
            "action": "turn",
            "session_id": "session_test_123",
            "user_text": "I usually wake up at 7 AM."
        }
        state["speaking"] = {"session_id": "session_test_123"}

        result = await speaking_agent_instance.process(state)

        assert result["response"]["status"] == "success"
        assert result["response"]["agent_response"] is not None
        assert result["response"]["turn_number"] >= 1

    @pytest.mark.asyncio
    async def test_process_turn_without_session(self, speaking_agent_instance):
        """Test processing turn without session ID fails."""
        state = create_initial_state(
            user_id="test_user",
            request_type="speaking_session"
        )
        state["activity_input"] = {
            "action": "turn",
            "user_text": "Hello"
        }

        result = await speaking_agent_instance.process(state)

        assert result["response"]["status"] == "error"
        assert result["has_error"] is True

    @pytest.mark.asyncio
    async def test_process_turn_detects_grammar_errors(self, speaking_agent_instance, mock_openai_service):
        """Test that grammar errors are detected during turn."""
        mock_openai_service.detect_grammar_errors = AsyncMock(
            return_value={
                "errors": [{
                    "type": "grammar",
                    "incorrect_text": "waked",
                    "correction": "woke",
                    "rule": "irregular_past_tense",
                    "explanation": "Wake is irregular"
                }],
                "error_count": 1
            }
        )

        state = create_initial_state(
            user_id="test_user",
            request_type="speaking_session"
        )
        state["activity_input"] = {
            "action": "turn",
            "session_id": "session_test_123",
            "user_text": "I waked up early today."
        }

        result = await speaking_agent_instance.process(state)

        assert result["response"]["status"] == "success"
        assert len(result["response"].get("grammar_errors", [])) > 0


class TestEndSession:
    """Test session end functionality."""

    @pytest.mark.asyncio
    async def test_end_session_success(self, speaking_agent_instance):
        """Test successful session end."""
        state = create_initial_state(
            user_id="test_user",
            request_type="speaking_session"
        )
        state["activity_input"] = {
            "action": "end",
            "session_id": "session_test_123"
        }

        result = await speaking_agent_instance.process(state)

        assert result["response"]["status"] == "success"
        assert result["response"]["summary"] is not None
        assert result["speaking"]["is_active"] is False

    @pytest.mark.asyncio
    async def test_end_session_generates_summary(self, speaking_agent_instance, mock_db_service):
        """Test that ending session generates a summary."""
        mock_db_service.get_speaking_session = AsyncMock(return_value={
            "id": "session_test_123",
            "status": "active",
            "topicName": "Daily Routine",
            "currentTurn": 5,
            "startedAt": datetime.utcnow().isoformat(),
            "exchanges": [],
            "grammarErrors": [{"rule": "past_tense"}],
            "pronunciationErrors": [{"phoneme": "θ"}]
        })

        state = create_initial_state(
            user_id="test_user",
            request_type="speaking_session"
        )
        state["activity_input"] = {
            "action": "end",
            "session_id": "session_test_123"
        }

        result = await speaking_agent_instance.process(state)

        summary = result["response"]["summary"]
        assert summary["total_turns"] == 5
        assert summary["grammar_error_count"] == 1
        assert summary["pronunciation_error_count"] == 1

    @pytest.mark.asyncio
    async def test_end_session_prepares_errors_for_activities(self, speaking_agent_instance, mock_db_service):
        """Test that errors are prepared for activity generation."""
        mock_db_service.get_speaking_session = AsyncMock(return_value={
            "id": "session_test_123",
            "status": "active",
            "topicName": "Daily Routine",
            "currentTurn": 3,
            "startedAt": datetime.utcnow().isoformat(),
            "exchanges": [],
            "grammarErrors": [{"rule": "irregular_past_tense", "incorrect_text": "waked"}],
            "pronunciationErrors": []
        })

        state = create_initial_state(
            user_id="test_user",
            request_type="speaking_session"
        )
        state["activity_input"] = {
            "action": "end",
            "session_id": "session_test_123"
        }

        result = await speaking_agent_instance.process(state)

        assert result["errors"]["has_errors"] is True
        assert len(result["errors"]["pending_errors"]) > 0


class TestTopicManagement:
    """Test topic loading and selection."""

    @pytest.mark.asyncio
    async def test_load_topics(self, speaking_agent_instance):
        """Test loading conversation topics."""
        await speaking_agent_instance._load_topics()

        assert len(speaking_agent_instance._topics_cache) > 0

    @pytest.mark.asyncio
    async def test_get_available_topics(self, speaking_agent_instance):
        """Test getting available topics."""
        topics = await speaking_agent_instance.get_available_topics()

        assert len(topics) > 0
        assert all("id" in t for t in topics)
        assert all("name" in t for t in topics)

    @pytest.mark.asyncio
    async def test_get_topics_by_difficulty(self, speaking_agent_instance):
        """Test filtering topics by difficulty."""
        beginner_topics = await speaking_agent_instance.get_available_topics("beginner")

        assert len(beginner_topics) > 0
        assert all(t.get("difficulty") == "beginner" for t in beginner_topics)


class TestHelperMethods:
    """Test helper methods."""

    @pytest.mark.asyncio
    async def test_get_user_speaking_stats_empty(self, speaking_agent_instance, mock_db_service):
        """Test getting stats for user with no sessions."""
        mock_db_service.query_items = AsyncMock(return_value=[])

        stats = await speaking_agent_instance.get_user_speaking_stats("new_user")

        assert stats["total_sessions"] == 0
        assert stats["total_conversation_time_minutes"] == 0

    @pytest.mark.asyncio
    async def test_get_active_session_none(self, speaking_agent_instance, mock_db_service):
        """Test getting active session when none exists."""
        mock_db_service.query_items = AsyncMock(return_value=[])

        session = await speaking_agent_instance.get_active_session("test_user")

        assert session is None

    def test_extract_pronunciation_errors(self, speaking_agent_instance):
        """Test extraction of pronunciation errors from assessment."""
        assessment = {
            "success": True,
            "words": [
                {"word": "think", "accuracy_score": 50},
                {"word": "about", "accuracy_score": 90}
            ],
            "phonemes": [
                {"phoneme": "θ", "accuracy_score": 40}
            ]
        }

        errors = speaking_agent_instance._extract_pronunciation_errors(assessment, 1)

        assert len(errors) >= 1
        assert any(e.get("word") == "think" for e in errors)


class TestErrorIntegrationAgent:
    """Test Error Integration Agent functionality."""

    @pytest.mark.asyncio
    async def test_process_with_no_errors(self):
        """Test processing when there are no errors."""
        from app.agents.error_integration_agent import ErrorIntegrationAgent

        agent = ErrorIntegrationAgent()
        agent.db_service = MagicMock()

        state = create_initial_state(
            user_id="test_user",
            request_type="speaking_session"
        )
        state["errors"] = {"has_errors": False, "pending_errors": []}

        result = await agent.process(state)

        assert result["errors"]["generated_activity_ids"] == [] or "generated_activity_ids" not in result["errors"]

    @pytest.mark.asyncio
    async def test_deduplicate_grammar_errors(self):
        """Test deduplication of grammar errors."""
        from app.agents.error_integration_agent import ErrorIntegrationAgent

        agent = ErrorIntegrationAgent()

        errors = [
            {"rule": "past_tense", "incorrect_text": "waked", "explanation": "Short"},
            {"rule": "past_tense", "incorrect_text": "goed", "explanation": "Longer explanation here"},
            {"rule": "articles", "incorrect_text": "a apple", "explanation": "Use 'an'"}
        ]

        deduplicated = agent._deduplicate_grammar_errors(errors)

        # Should have 2 unique rules
        assert len(deduplicated) == 2
        # past_tense should have occurrence_count of 2
        past_tense_error = next(e for e in deduplicated if e["rule"] == "past_tense")
        assert past_tense_error["occurrence_count"] == 2

    @pytest.mark.asyncio
    async def test_deduplicate_pronunciation_errors(self):
        """Test deduplication of pronunciation errors."""
        from app.agents.error_integration_agent import ErrorIntegrationAgent

        agent = ErrorIntegrationAgent()

        errors = [
            {"phoneme": "θ", "accuracy_score": 40},
            {"phoneme": "θ", "accuracy_score": 50},
            {"phoneme": "ð", "accuracy_score": 60}
        ]

        deduplicated = agent._deduplicate_pronunciation_errors(errors)

        # Should have 2 unique phonemes
        assert len(deduplicated) == 2
        # θ should have occurrence_count of 2 and average accuracy
        theta_error = next(e for e in deduplicated if e["phoneme"] == "θ")
        assert theta_error["occurrence_count"] == 2
        assert theta_error["average_accuracy"] == 45.0
