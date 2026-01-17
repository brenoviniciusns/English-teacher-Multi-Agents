"""
Tests for Speaking API Endpoints
Tests the REST API endpoints for speaking/conversation functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_orchestrator():
    """Mock the orchestrator run function."""
    with patch("app.api.v1.endpoints.speaking.run_orchestrator") as mock:
        yield mock


@pytest.fixture
def mock_speaking_agent():
    """Mock the speaking agent."""
    with patch("app.api.v1.endpoints.speaking.speaking_agent") as mock:
        yield mock


@pytest.fixture
def mock_error_integration_agent():
    """Mock the error integration agent."""
    with patch("app.api.v1.endpoints.speaking.error_integration_agent") as mock:
        yield mock


class TestStartSessionEndpoint:
    """Test POST /speaking/start-session endpoint."""

    def test_start_session_success(self, client, mock_orchestrator):
        """Test successful session start."""
        mock_orchestrator.return_value = {
            "response": {
                "status": "success",
                "session_id": "session_123",
                "topic": "Daily Routine",
                "topic_description": "Talk about your daily activities",
                "initial_prompt": "Hi! What time do you wake up?",
                "initial_prompt_audio": "base64_audio_data",
                "suggested_responses": ["I wake up at 7 AM"]
            },
            "has_error": False
        }

        response = client.post(
            "/api/v1/speaking/start-session?user_id=test_user",
            json={}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["session_id"] == "session_123"
        assert data["topic"] == "Daily Routine"
        assert data["initial_prompt"] is not None

    def test_start_session_with_topic(self, client, mock_orchestrator):
        """Test session start with specific topic."""
        mock_orchestrator.return_value = {
            "response": {
                "status": "success",
                "session_id": "session_456",
                "topic": "Travel Experiences"
            },
            "has_error": False
        }

        response = client.post(
            "/api/v1/speaking/start-session?user_id=test_user",
            json={"topic": "travel_experiences"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["topic"] == "Travel Experiences"

    def test_start_session_error(self, client, mock_orchestrator):
        """Test session start with error."""
        mock_orchestrator.return_value = {
            "response": {},
            "has_error": True,
            "error_message": "Failed to start session"
        }

        response = client.post(
            "/api/v1/speaking/start-session?user_id=test_user",
            json={}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"


class TestConversationTurnEndpoint:
    """Test POST /speaking/turn endpoint."""

    def test_process_turn_success(self, client, mock_orchestrator):
        """Test successful conversation turn."""
        mock_orchestrator.return_value = {
            "response": {
                "status": "success",
                "session_id": "session_123",
                "turn_number": 1,
                "user_input": "I wake up at 7 AM.",
                "agent_response": "That's early! What do you do after waking up?",
                "agent_audio_base64": "base64_audio",
                "grammar_errors": [],
                "pronunciation_errors": [],
                "conversation_continuing": True
            },
            "has_error": False
        }

        response = client.post(
            "/api/v1/speaking/turn?user_id=test_user",
            json={
                "session_id": "session_123",
                "user_text": "I wake up at 7 AM."
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["agent_response"] is not None
        assert data["turn_number"] == 1

    def test_process_turn_with_errors(self, client, mock_orchestrator):
        """Test turn processing with detected errors."""
        mock_orchestrator.return_value = {
            "response": {
                "status": "success",
                "session_id": "session_123",
                "turn_number": 2,
                "user_input": "I waked up early.",
                "agent_response": "Great! And what did you have for breakfast?",
                "grammar_errors": [{
                    "type": "grammar",
                    "incorrect_text": "waked",
                    "correction": "woke",
                    "rule": "irregular_past_tense"
                }],
                "pronunciation_errors": [],
                "conversation_continuing": True
            },
            "has_error": False
        }

        response = client.post(
            "/api/v1/speaking/turn?user_id=test_user",
            json={
                "session_id": "session_123",
                "user_text": "I waked up early."
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["grammar_errors"]) == 1
        assert data["grammar_errors"][0]["rule"] == "irregular_past_tense"

    def test_process_turn_missing_session(self, client, mock_orchestrator):
        """Test turn without session ID."""
        response = client.post(
            "/api/v1/speaking/turn?user_id=test_user",
            json={
                "user_text": "Hello"
            }
        )

        assert response.status_code == 422  # Validation error


class TestAudioTurnEndpoint:
    """Test POST /speaking/turn-audio endpoint."""

    def test_process_audio_turn_success(self, client, mock_orchestrator):
        """Test successful audio turn processing."""
        mock_orchestrator.return_value = {
            "response": {
                "status": "success",
                "session_id": "session_123",
                "turn_number": 1,
                "user_input": "I usually wake up at seven.",
                "agent_response": "That sounds reasonable!",
                "grammar_errors": [],
                "pronunciation_errors": [],
                "conversation_continuing": True
            },
            "has_error": False
        }

        response = client.post(
            "/api/v1/speaking/turn-audio?user_id=test_user",
            json={
                "session_id": "session_123",
                "audio_base64": "fake_base64_audio_data"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestEndSessionEndpoint:
    """Test POST /speaking/end-session endpoint."""

    def test_end_session_success(self, client, mock_orchestrator):
        """Test successful session end."""
        mock_orchestrator.return_value = {
            "response": {
                "status": "success",
                "session_id": "session_123",
                "summary": {
                    "total_turns": 5,
                    "duration_seconds": 300,
                    "grammar_error_count": 2,
                    "pronunciation_error_count": 1,
                    "overall_feedback": "Good session!"
                },
                "grammar_errors": [],
                "pronunciation_errors": [],
                "generated_activities": ["activity_1", "activity_2"]
            },
            "has_error": False
        }

        response = client.post(
            "/api/v1/speaking/end-session?user_id=test_user",
            json={"session_id": "session_123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["summary"]["total_turns"] == 5
        assert data["summary"]["grammar_error_count"] == 2


class TestActiveSessionEndpoint:
    """Test GET /speaking/active-session endpoint."""

    def test_get_active_session_exists(self, client, mock_speaking_agent):
        """Test getting existing active session."""
        mock_speaking_agent.get_active_session = AsyncMock(return_value={
            "id": "session_123",
            "topicName": "Daily Routine",
            "currentTurn": 3,
            "startedAt": datetime.utcnow().isoformat()
        })

        response = client.get("/api/v1/speaking/active-session?user_id=test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["has_active_session"] is True
        assert data["session_id"] == "session_123"

    def test_get_active_session_none(self, client, mock_speaking_agent):
        """Test when no active session exists."""
        mock_speaking_agent.get_active_session = AsyncMock(return_value=None)

        response = client.get("/api/v1/speaking/active-session?user_id=test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["has_active_session"] is False


class TestTopicsEndpoint:
    """Test GET /speaking/topics endpoint."""

    def test_get_all_topics(self, client, mock_speaking_agent):
        """Test getting all topics."""
        mock_speaking_agent.get_available_topics = AsyncMock(return_value=[
            {
                "id": "daily_routine",
                "name": "Daily Routine",
                "description": "Talk about your day",
                "difficulty": "beginner",
                "sample_questions": ["What time do you wake up?"]
            },
            {
                "id": "travel",
                "name": "Travel",
                "description": "Discuss travel experiences",
                "difficulty": "intermediate",
                "sample_questions": ["Have you traveled abroad?"]
            }
        ])

        response = client.get("/api/v1/speaking/topics")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["topics"]) == 2

    def test_get_topics_by_difficulty(self, client, mock_speaking_agent):
        """Test filtering topics by difficulty."""
        mock_speaking_agent.get_available_topics = AsyncMock(return_value=[
            {
                "id": "daily_routine",
                "name": "Daily Routine",
                "description": "Talk about your day",
                "difficulty": "beginner",
                "sample_questions": []
            }
        ])

        response = client.get("/api/v1/speaking/topics?difficulty=beginner")

        assert response.status_code == 200
        data = response.json()
        assert all(t["difficulty"] == "beginner" for t in data["topics"])


class TestProgressEndpoint:
    """Test GET /speaking/progress endpoint."""

    def test_get_speaking_progress(self, client, mock_speaking_agent):
        """Test getting speaking progress."""
        mock_speaking_agent.get_user_speaking_stats = AsyncMock(return_value={
            "total_sessions": 10,
            "total_conversation_time_minutes": 50,
            "average_turns_per_session": 5.5,
            "total_grammar_errors": 15,
            "total_pronunciation_errors": 8,
            "most_common_grammar_errors": ["past_tense", "articles"],
            "problematic_phonemes": ["θ", "ð"]
        })

        response = client.get("/api/v1/speaking/progress?user_id=test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 10
        assert data["total_conversation_time_minutes"] == 50


class TestHistoryEndpoint:
    """Test GET /speaking/history endpoint."""

    def test_get_session_history(self, client):
        """Test getting session history."""
        with patch("app.api.v1.endpoints.speaking.cosmos_db_service") as mock_db:
            mock_db.get_speaking_sessions_history = AsyncMock(return_value=[
                {
                    "id": "session_1",
                    "topicName": "Daily Routine",
                    "status": "completed",
                    "currentTurn": 5,
                    "durationSeconds": 300,
                    "grammarErrors": [{}],
                    "pronunciationErrors": [],
                    "startedAt": "2024-01-01T10:00:00",
                    "endedAt": "2024-01-01T10:05:00"
                }
            ])

            response = client.get("/api/v1/speaking/history?user_id=test_user")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["sessions"][0]["session_id"] == "session_1"


class TestCorrectiveActivitiesEndpoint:
    """Test GET /speaking/corrective-activities endpoint."""

    def test_get_corrective_activities(self, client, mock_error_integration_agent):
        """Test getting corrective activities."""
        mock_error_integration_agent.get_pending_corrective_activities = AsyncMock(return_value=[
            {
                "id": "activity_1",
                "pillar": "grammar",
                "grammarRule": "irregular_past_tense",
                "status": "pending",
                "priority": 3
            }
        ])

        response = client.get("/api/v1/speaking/corrective-activities?user_id=test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["activities"][0]["pillar"] == "grammar"


class TestErrorStatisticsEndpoint:
    """Test GET /speaking/error-statistics endpoint."""

    def test_get_error_statistics(self, client, mock_error_integration_agent):
        """Test getting error statistics."""
        mock_error_integration_agent.get_error_statistics = AsyncMock(return_value={
            "total_activities": 20,
            "pending_activities": 5,
            "completed_activities": 15,
            "grammar_activities": 12,
            "pronunciation_activities": 8,
            "most_common_grammar_errors": [("past_tense", 5), ("articles", 3)],
            "most_common_pronunciation_issues": [("θ", 4), ("ð", 2)]
        })

        response = client.get("/api/v1/speaking/error-statistics?user_id=test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["total_activities"] == 20
        assert data["pending_activities"] == 5
