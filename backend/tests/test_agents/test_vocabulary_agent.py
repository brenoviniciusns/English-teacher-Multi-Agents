"""
Tests for VocabularyAgent
Tests vocabulary exercise generation, answer processing, and SRS integration.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.agents.vocabulary_agent import VocabularyAgent, vocabulary_agent
from app.agents.state import create_initial_state


@pytest.fixture
def mock_vocabulary_agent(mock_settings, mock_cosmos_service, mock_openai_service):
    """Create a vocabulary agent with mocked services."""
    agent = VocabularyAgent(settings=mock_settings)
    agent.db_service = mock_cosmos_service
    agent.openai_service = mock_openai_service
    return agent


@pytest.fixture
def sample_word_data():
    """Sample word data for tests."""
    return {
        "id": "word_001",
        "word": "algorithm",
        "part_of_speech": "noun",
        "definition": "A step-by-step procedure for solving a problem",
        "example_sentence": "The sorting algorithm improved performance significantly.",
        "ipa_pronunciation": "/ˈælɡəˌrɪðəm/",
        "category": "technical",
        "subcategory": "programming",
        "difficulty": "intermediate",
        "frequency_rank": 1,
        "portuguese_translation": "algoritmo"
    }


@pytest.fixture
def sample_exercise():
    """Sample exercise data."""
    return {
        "sentence": "The data scientist developed a new ___ to process customer data.",
        "options": ["algorithm", "database", "server", "variable"],
        "correct_answer": "algorithm",
        "correct_index": 0,
        "explanation": "An algorithm is a step-by-step procedure, perfect for data processing.",
        "example_usage": "Machine learning uses algorithms to learn from data."
    }


class TestVocabularyAgentProperties:
    """Test VocabularyAgent basic properties."""

    def test_agent_name(self, mock_vocabulary_agent):
        """Test agent name property."""
        assert mock_vocabulary_agent.name == "vocabulary"

    def test_agent_description(self, mock_vocabulary_agent):
        """Test agent description property."""
        assert "vocabulary" in mock_vocabulary_agent.description.lower()
        assert "SRS" in mock_vocabulary_agent.description


class TestWordSelection:
    """Test word selection logic."""

    @pytest.mark.asyncio
    async def test_select_due_word_first(self, mock_vocabulary_agent, sample_word_data):
        """Test that SRS due words are selected first."""
        # Setup: word due for review
        mock_vocabulary_agent.db_service.get_vocabulary_due_for_review.return_value = [
            {"wordId": "word_001", "srsData": {"nextReview": datetime.utcnow().isoformat()}}
        ]
        mock_vocabulary_agent._words_cache = {"word_001": sample_word_data}

        # Execute
        word = await mock_vocabulary_agent._select_word("user123", "beginner", "general")

        # Assert
        assert word is not None
        assert word["id"] == "word_001"

    @pytest.mark.asyncio
    async def test_select_low_frequency_word(self, mock_vocabulary_agent, sample_word_data):
        """Test selection of low frequency words when no SRS due."""
        # Setup: no SRS due, but low frequency word
        mock_vocabulary_agent.db_service.get_vocabulary_due_for_review.return_value = []
        mock_vocabulary_agent.db_service.get_vocabulary_low_frequency.return_value = [
            {"wordId": "word_001"}
        ]
        mock_vocabulary_agent._words_cache = {"word_001": sample_word_data}

        # Execute
        word = await mock_vocabulary_agent._select_word("user123", "beginner", "general")

        # Assert
        assert word is not None
        assert word["id"] == "word_001"

    @pytest.mark.asyncio
    async def test_select_new_word(self, mock_vocabulary_agent, sample_word_data):
        """Test selection of new word when no due or low frequency."""
        # Setup: no SRS due, no low frequency
        mock_vocabulary_agent.db_service.get_vocabulary_due_for_review.return_value = []
        mock_vocabulary_agent.db_service.get_vocabulary_low_frequency.return_value = []
        mock_vocabulary_agent.db_service.get_vocabulary_progress.return_value = []
        mock_vocabulary_agent._words_cache = {"word_001": sample_word_data}

        # Execute
        word = await mock_vocabulary_agent._get_new_word("user123", "intermediate", "general")

        # Assert
        assert word is not None


class TestExerciseGeneration:
    """Test exercise generation."""

    @pytest.mark.asyncio
    async def test_generate_exercise_success(
        self, mock_vocabulary_agent, sample_word_data, sample_exercise, sample_user_data
    ):
        """Test successful exercise generation."""
        # Setup
        mock_vocabulary_agent.db_service.get_vocabulary_due_for_review.return_value = [
            {"wordId": "word_001", "srsData": {"nextReview": datetime.utcnow().isoformat()}}
        ]
        mock_vocabulary_agent._words_cache = {"word_001": sample_word_data}
        mock_vocabulary_agent.openai_service.generate_vocabulary_exercise.return_value = sample_exercise

        state = create_initial_state("user123", "vocabulary_exercise", sample_user_data)

        # Execute
        result_state = await mock_vocabulary_agent._generate_exercise(state)

        # Assert
        assert result_state["response"]["status"] == "success"
        assert result_state["response"]["word"] == "algorithm"
        assert "exercise" in result_state["response"]
        assert result_state["current_activity"]["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_generate_fallback_exercise(self, mock_vocabulary_agent, sample_word_data):
        """Test fallback exercise generation when GPT-4 fails."""
        # Execute
        exercise = mock_vocabulary_agent._create_fallback_exercise(sample_word_data)

        # Assert
        assert "sentence" in exercise
        assert "options" in exercise
        assert sample_word_data["word"] in exercise["options"]
        assert exercise["correct_answer"] == sample_word_data["word"]


class TestAnswerProcessing:
    """Test answer processing logic."""

    def test_check_answer_correct_by_text(self, mock_vocabulary_agent):
        """Test correct answer check by text."""
        result = mock_vocabulary_agent._check_answer("algorithm", "algorithm", None)
        assert result is True

    def test_check_answer_correct_by_index(self, mock_vocabulary_agent):
        """Test correct answer check by index."""
        result = mock_vocabulary_agent._check_answer("0", "algorithm", 0)
        assert result is True

    def test_check_answer_incorrect(self, mock_vocabulary_agent):
        """Test incorrect answer check."""
        result = mock_vocabulary_agent._check_answer("database", "algorithm", 0)
        assert result is False

    def test_check_answer_case_insensitive(self, mock_vocabulary_agent):
        """Test case insensitive answer check."""
        result = mock_vocabulary_agent._check_answer("Algorithm", "algorithm", None)
        assert result is True

    @pytest.mark.asyncio
    async def test_process_correct_answer(
        self, mock_vocabulary_agent, sample_exercise, sample_user_data
    ):
        """Test processing a correct answer."""
        # Setup
        mock_vocabulary_agent.db_service.get_vocabulary_progress.return_value = {
            "wordId": "word_001",
            "practiceCount": 5,
            "correctCount": 3,
            "srsData": {
                "easeFactor": 2.5,
                "interval": 6,
                "repetitions": 2,
                "nextReview": datetime.utcnow().isoformat()
            }
        }
        mock_vocabulary_agent.db_service.update_vocabulary_progress.return_value = {}

        state = create_initial_state("user123", "vocabulary_exercise", sample_user_data)
        state["activity_input"] = {
            "answer": "algorithm",
            "word_id": "word_001",
            "response_time_ms": 3000
        }
        state["current_activity"] = {
            "activity_id": "test_activity",
            "content": {
                "word_id": "word_001",
                "word": "algorithm",
                "exercise": sample_exercise
            }
        }

        # Execute
        result_state = await mock_vocabulary_agent._process_answer(state)

        # Assert
        assert result_state["response"]["correct"] is True
        assert result_state["current_activity"]["status"] == "completed"


class TestMasteryLevel:
    """Test mastery level calculation."""

    def test_mastery_level_new(self, mock_vocabulary_agent):
        """Test mastery level for new word."""
        level = mock_vocabulary_agent._calculate_mastery_level(
            repetitions=0, correct_count=0, practice_count=0
        )
        assert level == "new"

    def test_mastery_level_learning(self, mock_vocabulary_agent):
        """Test mastery level for learning word."""
        level = mock_vocabulary_agent._calculate_mastery_level(
            repetitions=1, correct_count=2, practice_count=3
        )
        assert level == "learning"

    def test_mastery_level_reviewing(self, mock_vocabulary_agent):
        """Test mastery level for reviewing word."""
        level = mock_vocabulary_agent._calculate_mastery_level(
            repetitions=3, correct_count=8, practice_count=10
        )
        assert level == "reviewing"

    def test_mastery_level_mastered(self, mock_vocabulary_agent):
        """Test mastery level for mastered word."""
        level = mock_vocabulary_agent._calculate_mastery_level(
            repetitions=5, correct_count=9, practice_count=10
        )
        assert level == "mastered"


class TestContextDetermination:
    """Test context determination from learning goals."""

    def test_context_data_engineering(self, mock_vocabulary_agent):
        """Test data engineering context."""
        context = mock_vocabulary_agent._determine_context(["general", "data_engineering"])
        assert context == "data_engineering"

    def test_context_ai(self, mock_vocabulary_agent):
        """Test AI context."""
        context = mock_vocabulary_agent._determine_context(["ai"])
        assert context == "ai"

    def test_context_technology(self, mock_vocabulary_agent):
        """Test technology context."""
        context = mock_vocabulary_agent._determine_context(["technology"])
        assert context == "technology"

    def test_context_general(self, mock_vocabulary_agent):
        """Test general context."""
        context = mock_vocabulary_agent._determine_context(["general"])
        assert context == "general"


class TestProgressUpdate:
    """Test progress update logic."""

    @pytest.mark.asyncio
    async def test_update_progress_new_word(self, mock_vocabulary_agent):
        """Test progress update for a new word."""
        # Setup: no existing progress
        mock_vocabulary_agent.db_service.get_vocabulary_progress.return_value = None
        mock_vocabulary_agent.db_service.update_vocabulary_progress.return_value = {}

        # Execute
        result = await mock_vocabulary_agent._update_progress(
            user_id="user123",
            word_id="word_001",
            word="algorithm",
            is_correct=True,
            quality=4,
            response_time_ms=3000
        )

        # Assert
        assert result["mastery_level"] == "learning"
        assert result["streak"] >= 0

    @pytest.mark.asyncio
    async def test_update_progress_existing_word(self, mock_vocabulary_agent):
        """Test progress update for an existing word."""
        # Setup: existing progress
        mock_vocabulary_agent.db_service.get_vocabulary_progress.return_value = {
            "wordId": "word_001",
            "practiceCount": 5,
            "correctCount": 4,
            "averageResponseTimeMs": 3500,
            "srsData": {
                "easeFactor": 2.5,
                "interval": 6,
                "repetitions": 3,
                "nextReview": datetime.utcnow().isoformat()
            }
        }
        mock_vocabulary_agent.db_service.update_vocabulary_progress.return_value = {}

        # Execute
        result = await mock_vocabulary_agent._update_progress(
            user_id="user123",
            word_id="word_001",
            word="algorithm",
            is_correct=True,
            quality=5,
            response_time_ms=2000
        )

        # Assert
        assert result["streak"] >= 3  # Should increase
        assert "next_review_days" in result


class TestVocabularyStats:
    """Test vocabulary statistics."""

    @pytest.mark.asyncio
    async def test_get_user_vocabulary_stats_empty(self, mock_vocabulary_agent):
        """Test stats for user with no progress."""
        mock_vocabulary_agent.db_service.get_vocabulary_progress.return_value = []
        mock_vocabulary_agent.db_service.get_vocabulary_due_for_review.return_value = []

        stats = await mock_vocabulary_agent.get_user_vocabulary_stats("user123")

        assert stats["total_words"] == 0
        assert stats["mastered"] == 0
        assert stats["average_accuracy"] == 0

    @pytest.mark.asyncio
    async def test_get_user_vocabulary_stats_with_progress(self, mock_vocabulary_agent):
        """Test stats for user with progress."""
        mock_vocabulary_agent.db_service.get_vocabulary_progress.return_value = [
            {"masteryLevel": "mastered", "practiceCount": 10, "correctCount": 9},
            {"masteryLevel": "learning", "practiceCount": 5, "correctCount": 3},
            {"masteryLevel": "reviewing", "practiceCount": 8, "correctCount": 7}
        ]
        mock_vocabulary_agent.db_service.get_vocabulary_due_for_review.return_value = [
            {"wordId": "word_001"}
        ]

        stats = await mock_vocabulary_agent.get_user_vocabulary_stats("user123")

        assert stats["total_words"] == 3
        assert stats["mastered"] == 1
        assert stats["learning"] == 1
        assert stats["reviewing"] == 1
        assert stats["due_for_review"] == 1
        assert stats["average_accuracy"] > 0


class TestProcessMethod:
    """Test the main process method."""

    @pytest.mark.asyncio
    async def test_process_exercise_request(
        self, mock_vocabulary_agent, sample_word_data, sample_exercise, sample_user_data
    ):
        """Test processing an exercise request."""
        # Setup
        mock_vocabulary_agent.db_service.get_vocabulary_due_for_review.return_value = [
            {"wordId": "word_001", "srsData": {"nextReview": datetime.utcnow().isoformat()}}
        ]
        mock_vocabulary_agent._words_cache = {"word_001": sample_word_data}
        mock_vocabulary_agent.openai_service.generate_vocabulary_exercise.return_value = sample_exercise

        state = create_initial_state("user123", "vocabulary_exercise", sample_user_data)

        # Execute
        result_state = await mock_vocabulary_agent.process(state)

        # Assert
        assert result_state["response"]["type"] == "vocabulary_exercise"
        assert result_state["response"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_process_unknown_request_type(self, mock_vocabulary_agent, sample_user_data):
        """Test processing an unknown request type."""
        state = create_initial_state("user123", "unknown_type", sample_user_data)

        result_state = await mock_vocabulary_agent.process(state)

        assert result_state["has_error"] is True
