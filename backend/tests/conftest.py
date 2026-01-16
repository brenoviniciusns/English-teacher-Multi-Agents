"""
Pytest configuration and fixtures for tests.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Configure pytest for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for tests."""
    settings = MagicMock()
    settings.AZURE_OPENAI_API_KEY = "test-key"
    settings.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com"
    settings.AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4"
    settings.AZURE_SPEECH_KEY = "test-speech-key"
    settings.AZURE_SPEECH_REGION = "eastus"
    settings.COSMOS_DB_ENDPOINT = "https://test.documents.azure.com"
    settings.COSMOS_DB_KEY = "test-cosmos-key"
    settings.COSMOS_DB_DATABASE_NAME = "test_db"
    settings.SRS_INITIAL_INTERVAL_DAYS = 1
    settings.SRS_SECOND_INTERVAL_DAYS = 6
    settings.SRS_INITIAL_EASE_FACTOR = 2.5
    settings.SRS_MIN_EASE_FACTOR = 1.3
    settings.SRS_LOW_FREQUENCY_THRESHOLD_DAYS = 7
    settings.SRS_LOW_ACCURACY_THRESHOLD = 80
    settings.INTERMEDIATE_UPGRADE_THRESHOLD = 85
    settings.INITIAL_ASSESSMENT_VOCABULARY_COUNT = 20
    settings.INITIAL_ASSESSMENT_GRAMMAR_COUNT = 5
    settings.INITIAL_ASSESSMENT_PRONUNCIATION_COUNT = 5
    settings.CONTINUOUS_ASSESSMENT_FREQUENCY = 5
    return settings


@pytest.fixture
def mock_cosmos_service():
    """Mock Cosmos DB service."""
    service = AsyncMock()

    # Default user
    service.get_user.return_value = {
        "id": "test_user_123",
        "email": "test@example.com",
        "name": "Test User",
        "current_level": "beginner",
        "initial_assessment_completed": True,
        "sessions_since_last_assessment": 3,
        "vocabulary_score": 60,
        "grammar_score": 55,
        "pronunciation_score": 50,
        "speaking_score": 45,
        "total_study_time_minutes": 120,
        "current_streak_days": 5,
        "longest_streak_days": 10,
        "last_activity_date": datetime.utcnow().isoformat(),
        "profile": {
            "daily_goal_minutes": 30,
            "learning_goals": ["general", "data_engineering"],
            "voice_preference": "american_female"
        }
    }

    # Default statistics
    service.get_user_statistics.return_value = {
        "vocabulary": {
            "total_words": 100,
            "mastered": 50,
            "learning": 30
        },
        "grammar": {
            "total_rules": 20,
            "average_score": 70
        },
        "pronunciation": {
            "total_sounds": 15,
            "average_accuracy": 65
        },
        "speaking": {
            "sessions_last_30_days": 8
        }
    }

    # Empty due items by default
    service.get_vocabulary_due_for_review.return_value = []
    service.get_grammar_due_for_review.return_value = []
    service.get_pronunciation_needs_practice.return_value = []
    service.get_vocabulary_low_frequency.return_value = []
    service.get_pending_activities.return_value = []

    # Schedule
    service.get_daily_schedule.return_value = None

    return service


@pytest.fixture
def mock_openai_service():
    """Mock Azure OpenAI service."""
    service = AsyncMock()
    service.chat_completion.return_value = "Test response"
    service.generate_vocabulary_exercise.return_value = {
        "word": "test",
        "definition": "a procedure",
        "example": "Run a test"
    }
    return service


@pytest.fixture
def mock_speech_service():
    """Mock Azure Speech service."""
    service = AsyncMock()
    service.text_to_speech.return_value = b"audio_bytes"
    service.speech_to_text.return_value = "recognized text"
    service.assess_pronunciation.return_value = {
        "accuracy_score": 85,
        "fluency_score": 80,
        "completeness_score": 90,
        "pronunciation_score": 85
    }
    return service


@pytest.fixture
def sample_user_data():
    """Sample user data for tests."""
    return {
        "id": "test_user_123",
        "email": "test@example.com",
        "name": "Test User",
        "current_level": "beginner",
        "initial_assessment_completed": True,
        "sessions_since_last_assessment": 3,
        "vocabulary_score": 60,
        "grammar_score": 55,
        "pronunciation_score": 50,
        "speaking_score": 45,
        "total_study_time_minutes": 120,
        "current_streak_days": 5,
        "last_activity_date": datetime.utcnow().isoformat(),
        "profile": {
            "daily_goal_minutes": 30,
            "learning_goals": ["general", "data_engineering"],
            "voice_preference": "american_female"
        }
    }


@pytest.fixture
def sample_vocab_progress():
    """Sample vocabulary progress data."""
    return [
        {
            "id": "vocab_test_user_123_word1",
            "wordId": "word1",
            "userId": "test_user_123",
            "masteryLevel": "learning",
            "practiceCount": 5,
            "correctCount": 3,
            "srsData": {
                "easeFactor": 2.5,
                "interval": 1,
                "repetitions": 2,
                "nextReview": datetime.utcnow().isoformat(),
                "lastReview": datetime.utcnow().isoformat()
            }
        }
    ]
