"""
Tests for Grammar Agent
Tests for grammar lessons, explanations, exercises, and progress tracking.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.grammar_agent import grammar_agent, GrammarAgent
from app.agents.state import create_initial_state, AppState


# ==================== FIXTURES ====================

@pytest.fixture
def mock_db_service():
    """Mock Cosmos DB service."""
    with patch.object(grammar_agent, 'db_service') as mock:
        mock.get_grammar_progress = AsyncMock(return_value=None)
        mock.update_grammar_progress = AsyncMock(return_value={})
        mock.get_grammar_due_for_review = AsyncMock(return_value=[])
        mock.get_grammar_low_frequency = AsyncMock(return_value=[])
        yield mock


@pytest.fixture
def mock_openai_service():
    """Mock Azure OpenAI service."""
    with patch.object(grammar_agent, 'openai_service') as mock:
        mock.evaluate_grammar_explanation = AsyncMock(return_value={
            "accuracy_score": 85.0,
            "completeness_score": 80.0,
            "understanding_score": 82.0,
            "overall_score": 82.0,
            "feedback": "Boa explicação! Você demonstrou bom entendimento da regra.",
            "missing_points": ["Could mention irregular verbs"],
            "suggestions": "Pratique mais exemplos com verbos irregulares."
        })
        mock.generate_grammar_exercises = AsyncMock(return_value=[
            {
                "type": "fill_in_blank",
                "instruction": "Complete the sentence with the correct verb form",
                "sentence": "She ___ to the store yesterday.",
                "options": ["go", "went", "goes", "going"],
                "correct_answer": "went",
                "correct_index": 1,
                "explanation": "We use 'went' because it's the past tense of 'go'."
            },
            {
                "type": "error_correction",
                "instruction": "Choose the correct sentence",
                "sentence": "Which sentence is correct?",
                "options": ["He goed home.", "He went home."],
                "correct_answer": "He went home.",
                "correct_index": 1,
                "explanation": "'Go' has an irregular past tense: went, not goed."
            }
        ])
        yield mock


@pytest.fixture
def sample_user_state() -> AppState:
    """Create a sample user state for testing."""
    state = create_initial_state(
        user_id="test_user_123",
        request_type="grammar_lesson"
    )
    state["user"]["current_level"] = "beginner"
    return state


@pytest.fixture
def sample_grammar_rule():
    """Sample grammar rule for testing."""
    return {
        "id": "rule_003",
        "name": "Simple Past",
        "category": "tense",
        "difficulty": "beginner",
        "english_explanation": "Used for completed actions in the past.",
        "portuguese_explanation": "Usado para ações completas no passado.",
        "exists_in_portuguese": True,
        "portuguese_equivalent": "Pretérito Perfeito",
        "similarities": ["Both express completed past actions"],
        "differences": ["English regular verbs all end in -ed"],
        "common_mistakes": ["Using base form with did: 'Did you went?'"],
        "memory_tips": ["Regular = add -ED"],
        "examples": [
            {"english": "I worked yesterday.", "portuguese": "Eu trabalhei ontem."}
        ],
        "common_errors": [
            {
                "incorrect": "I goed to school.",
                "correct": "I went to school.",
                "explanation": "Go is irregular: go-went-gone"
            }
        ]
    }


# ==================== UNIT TESTS ====================

class TestGrammarAgentInit:
    """Test GrammarAgent initialization."""

    def test_agent_properties(self):
        """Test agent name and description."""
        assert grammar_agent.name == "grammar"
        assert "grammar" in grammar_agent.description.lower()

    def test_empty_cache_on_init(self):
        """Test that caches are empty on initialization."""
        agent = GrammarAgent()
        assert agent._rules_cache == {}
        assert agent._rules_by_category == {}


class TestLoadRules:
    """Test grammar rules loading."""

    @pytest.mark.asyncio
    async def test_load_rules_success(self):
        """Test loading grammar rules from JSON file."""
        # Clear cache first
        grammar_agent._rules_cache = {}
        grammar_agent._rules_by_category = {}

        await grammar_agent._load_rules()

        assert len(grammar_agent._rules_cache) > 0
        assert len(grammar_agent._rules_by_category) > 0

    @pytest.mark.asyncio
    async def test_load_rules_categories(self):
        """Test that rules are indexed by category."""
        await grammar_agent._load_rules()

        categories = grammar_agent.get_available_categories()
        assert len(categories) > 0
        assert "tense" in categories


class TestGenerateLesson:
    """Test grammar lesson generation."""

    @pytest.mark.asyncio
    async def test_generate_lesson_success(
        self,
        mock_db_service,
        sample_user_state
    ):
        """Test successful lesson generation."""
        # Clear and reload rules
        grammar_agent._rules_cache = {}
        await grammar_agent._load_rules()

        result_state = await grammar_agent.process(sample_user_state)

        assert result_state["response"]["status"] == "success"
        assert result_state["response"]["type"] == "grammar_lesson"
        assert result_state["response"]["rule"] is not None
        assert "id" in result_state["response"]["rule"]
        assert "name" in result_state["response"]["rule"]
        assert "english_explanation" in result_state["response"]["rule"]
        assert "comparison" in result_state["response"]["rule"]

    @pytest.mark.asyncio
    async def test_generate_lesson_with_specific_rule(
        self,
        mock_db_service,
        sample_user_state
    ):
        """Test lesson generation for a specific rule."""
        await grammar_agent._load_rules()

        sample_user_state["activity_input"] = {"rule_id": "rule_001"}
        result_state = await grammar_agent.process(sample_user_state)

        assert result_state["response"]["status"] == "success"
        assert result_state["response"]["rule"]["id"] == "rule_001"

    @pytest.mark.asyncio
    async def test_generate_lesson_with_category_filter(
        self,
        mock_db_service,
        sample_user_state
    ):
        """Test lesson generation filtered by category."""
        await grammar_agent._load_rules()

        sample_user_state["activity_input"] = {"category": "tense"}
        result_state = await grammar_agent.process(sample_user_state)

        assert result_state["response"]["status"] == "success"
        rule = result_state["response"]["rule"]
        assert rule["category"] == "tense"

    @pytest.mark.asyncio
    async def test_generate_lesson_prioritizes_due_items(
        self,
        mock_db_service,
        sample_user_state
    ):
        """Test that SRS due items are prioritized."""
        await grammar_agent._load_rules()

        # Mock a due item
        mock_db_service.get_grammar_due_for_review.return_value = [
            {"ruleId": "rule_002", "srsData": {"nextReview": "2020-01-01"}}
        ]

        result_state = await grammar_agent.process(sample_user_state)

        assert result_state["response"]["status"] == "success"
        assert result_state["response"]["rule"]["id"] == "rule_002"


class TestProcessExplanation:
    """Test user explanation processing."""

    @pytest.mark.asyncio
    async def test_process_explanation_success(
        self,
        mock_db_service,
        mock_openai_service,
        sample_user_state
    ):
        """Test successful explanation processing."""
        await grammar_agent._load_rules()

        sample_user_state["activity_input"] = {
            "rule_id": "rule_001",
            "explanation": "O Present Simple é usado para expressar hábitos, rotinas e verdades gerais. Em inglês, adicionamos -s ou -es na terceira pessoa do singular."
        }
        sample_user_state["current_activity"] = {
            "content": {"rule_id": "rule_001"}
        }

        result_state = await grammar_agent.process(sample_user_state)

        assert result_state["response"]["status"] == "success"
        assert result_state["response"]["type"] == "grammar_explanation"
        assert "evaluation" in result_state["response"]
        assert result_state["response"]["evaluation"]["overall_score"] >= 0

    @pytest.mark.asyncio
    async def test_process_explanation_too_short(
        self,
        mock_db_service,
        sample_user_state
    ):
        """Test rejection of too short explanations."""
        sample_user_state["activity_input"] = {
            "rule_id": "rule_001",
            "explanation": "Short"
        }

        result_state = await grammar_agent.process(sample_user_state)

        assert result_state["response"]["status"] == "error"
        assert "curta" in result_state["response"]["message"].lower()

    @pytest.mark.asyncio
    async def test_process_explanation_updates_progress(
        self,
        mock_db_service,
        mock_openai_service,
        sample_user_state
    ):
        """Test that explanation updates progress."""
        await grammar_agent._load_rules()

        sample_user_state["activity_input"] = {
            "rule_id": "rule_001",
            "explanation": "Esta regra é sobre o tempo verbal presente simples que usamos para falar sobre hábitos e rotinas diárias."
        }

        await grammar_agent.process(sample_user_state)

        # Verify progress was updated
        mock_db_service.update_grammar_progress.assert_called()


class TestGenerateExercises:
    """Test grammar exercise generation."""

    @pytest.mark.asyncio
    async def test_generate_exercises_success(
        self,
        mock_db_service,
        mock_openai_service,
        sample_user_state
    ):
        """Test successful exercise generation."""
        await grammar_agent._load_rules()

        sample_user_state["request_type"] = "grammar_exercise"
        sample_user_state["activity_input"] = {
            "rule_id": "rule_001",
            "count": 3
        }

        result_state = await grammar_agent.process(sample_user_state)

        assert result_state["response"]["status"] == "success"
        assert result_state["response"]["type"] == "grammar_exercises"
        assert len(result_state["response"]["exercises"]) > 0

    @pytest.mark.asyncio
    async def test_generate_exercises_missing_rule_id(
        self,
        mock_db_service,
        sample_user_state
    ):
        """Test error when rule_id is missing."""
        sample_user_state["request_type"] = "grammar_exercise"
        sample_user_state["activity_input"] = {}

        result_state = await grammar_agent.process(sample_user_state)

        assert result_state["response"]["status"] == "error"
        assert "obrigatório" in result_state["response"]["message"].lower()

    @pytest.mark.asyncio
    async def test_generate_exercises_fallback(
        self,
        mock_db_service,
        sample_user_state
    ):
        """Test fallback exercise generation when GPT-4 fails."""
        await grammar_agent._load_rules()

        # Make OpenAI return empty list (simulating failure)
        with patch.object(grammar_agent, 'openai_service') as mock:
            mock.generate_grammar_exercises = AsyncMock(return_value=[])

            sample_user_state["request_type"] = "grammar_exercise"
            sample_user_state["activity_input"] = {"rule_id": "rule_001"}

            result_state = await grammar_agent.process(sample_user_state)

            # Should still succeed with fallback exercises
            assert result_state["response"]["status"] == "success"
            assert len(result_state["response"]["exercises"]) > 0


class TestProcessExerciseAnswer:
    """Test exercise answer processing."""

    @pytest.mark.asyncio
    async def test_process_correct_answer(
        self,
        mock_db_service,
        sample_user_state
    ):
        """Test processing a correct answer."""
        await grammar_agent._load_rules()

        sample_user_state["request_type"] = "grammar_exercise"
        sample_user_state["current_activity"] = {
            "content": {
                "rule_id": "rule_001",
                "exercises": [
                    {
                        "type": "fill_in_blank",
                        "sentence": "She ___ to work every day.",
                        "options": ["go", "goes", "went", "going"],
                        "correct_answer": "goes",
                        "correct_index": 1,
                        "explanation": "Third person singular uses -es"
                    }
                ],
                "current_index": 0,
                "correct_count": 0
            }
        }
        sample_user_state["activity_input"] = {
            "rule_id": "rule_001",
            "answer": "1",  # Index of "goes"
            "exercise_index": 0
        }

        result_state = await grammar_agent.process(sample_user_state)

        assert result_state["response"]["status"] == "success"
        assert result_state["response"]["correct"] == True
        assert result_state["response"]["correct_answer"] == "goes"

    @pytest.mark.asyncio
    async def test_process_incorrect_answer(
        self,
        mock_db_service,
        sample_user_state
    ):
        """Test processing an incorrect answer."""
        await grammar_agent._load_rules()

        sample_user_state["request_type"] = "grammar_exercise"
        sample_user_state["current_activity"] = {
            "content": {
                "rule_id": "rule_001",
                "exercises": [
                    {
                        "type": "fill_in_blank",
                        "sentence": "She ___ to work every day.",
                        "options": ["go", "goes", "went", "going"],
                        "correct_answer": "goes",
                        "correct_index": 1,
                        "explanation": "Third person singular uses -es"
                    }
                ],
                "current_index": 0,
                "correct_count": 0
            }
        }
        sample_user_state["activity_input"] = {
            "rule_id": "rule_001",
            "answer": "0",  # Index of "go" (wrong)
            "exercise_index": 0
        }

        result_state = await grammar_agent.process(sample_user_state)

        assert result_state["response"]["status"] == "success"
        assert result_state["response"]["correct"] == False


class TestMasteryCalculation:
    """Test mastery level calculations."""

    def test_calculate_mastery_not_started(self):
        """Test mastery level for unpracticed rule."""
        level = grammar_agent._calculate_mastery_level(
            repetitions=0,
            best_score=0,
            practice_count=0
        )
        assert level == "not_started"

    def test_calculate_mastery_new(self):
        """Test mastery level for new learner."""
        level = grammar_agent._calculate_mastery_level(
            repetitions=0,
            best_score=50,
            practice_count=1
        )
        assert level == "new"

    def test_calculate_mastery_learning(self):
        """Test mastery level for learning phase."""
        level = grammar_agent._calculate_mastery_level(
            repetitions=1,
            best_score=75,
            practice_count=3
        )
        assert level == "learning"

    def test_calculate_mastery_reviewing(self):
        """Test mastery level for reviewing phase."""
        level = grammar_agent._calculate_mastery_level(
            repetitions=3,
            best_score=80,
            practice_count=5
        )
        assert level == "reviewing"

    def test_calculate_mastery_mastered(self):
        """Test mastery level for mastered rule."""
        level = grammar_agent._calculate_mastery_level(
            repetitions=5,
            best_score=90,
            practice_count=10
        )
        assert level == "mastered"


class TestScoreToQuality:
    """Test score to SRS quality conversion."""

    def test_perfect_score(self):
        """Test perfect score (95+) gives quality 5."""
        assert grammar_agent._score_to_quality(95) == 5
        assert grammar_agent._score_to_quality(100) == 5

    def test_good_score(self):
        """Test good score (85-94) gives quality 4."""
        assert grammar_agent._score_to_quality(85) == 4
        assert grammar_agent._score_to_quality(94) == 4

    def test_ok_score(self):
        """Test OK score (70-84) gives quality 3."""
        assert grammar_agent._score_to_quality(70) == 3
        assert grammar_agent._score_to_quality(84) == 3

    def test_poor_score(self):
        """Test poor score (50-69) gives quality 2."""
        assert grammar_agent._score_to_quality(50) == 2
        assert grammar_agent._score_to_quality(69) == 2

    def test_bad_score(self):
        """Test bad score (30-49) gives quality 1."""
        assert grammar_agent._score_to_quality(30) == 1
        assert grammar_agent._score_to_quality(49) == 1

    def test_blackout_score(self):
        """Test blackout score (<30) gives quality 0."""
        assert grammar_agent._score_to_quality(0) == 0
        assert grammar_agent._score_to_quality(29) == 0


class TestHelperMethods:
    """Test helper methods for external use."""

    @pytest.mark.asyncio
    async def test_get_user_grammar_stats(self, mock_db_service):
        """Test getting user grammar statistics."""
        await grammar_agent._load_rules()

        mock_db_service.get_grammar_progress.return_value = [
            {"ruleId": "rule_001", "masteryLevel": "mastered", "bestExplanationScore": 90},
            {"ruleId": "rule_002", "masteryLevel": "learning", "bestExplanationScore": 70},
            {"ruleId": "rule_003", "masteryLevel": "reviewing", "bestExplanationScore": 80}
        ]

        stats = await grammar_agent.get_user_grammar_stats("test_user")

        assert stats["mastered"] == 1
        assert stats["learning"] == 1
        assert stats["reviewing"] == 1
        assert stats["average_score"] > 0

    @pytest.mark.asyncio
    async def test_get_rules_to_review(self, mock_db_service):
        """Test getting rules due for review."""
        await grammar_agent._load_rules()

        mock_db_service.get_grammar_due_for_review.return_value = [
            {
                "ruleId": "rule_001",
                "masteryLevel": "reviewing",
                "lastPracticed": "2024-01-01",
                "bestExplanationScore": 75,
                "srsData": {"nextReview": "2024-01-05"}
            }
        ]

        rules = await grammar_agent.get_rules_to_review("test_user", limit=5)

        assert len(rules) == 1
        assert rules[0]["rule_id"] == "rule_001"

    @pytest.mark.asyncio
    async def test_get_all_rules(self, mock_db_service):
        """Test getting all grammar rules."""
        await grammar_agent._load_rules()

        rules = await grammar_agent.get_all_rules()

        assert len(rules) > 0
        assert all("id" in r for r in rules)
        assert all("name" in r for r in rules)

    @pytest.mark.asyncio
    async def test_get_all_rules_with_user_progress(self, mock_db_service):
        """Test getting all rules with user progress."""
        await grammar_agent._load_rules()

        mock_db_service.get_grammar_progress.return_value = [
            {"ruleId": "rule_001", "masteryLevel": "learning", "practiceCount": 5, "bestExplanationScore": 75}
        ]

        rules = await grammar_agent.get_all_rules(user_id="test_user")

        # Find rule_001
        rule = next((r for r in rules if r["id"] == "rule_001"), None)
        assert rule is not None
        assert rule.get("user_mastery_level") == "learning"
        assert rule.get("user_practice_count") == 5

    @pytest.mark.asyncio
    async def test_get_available_categories(self):
        """Test getting available categories."""
        # First ensure rules are loaded
        await grammar_agent._load_rules()

        categories = grammar_agent.get_available_categories()

        assert len(categories) > 0
        assert "tense" in categories


# ==================== INTEGRATION TESTS ====================

class TestGrammarAgentIntegration:
    """Integration tests for Grammar Agent flow."""

    @pytest.mark.asyncio
    async def test_full_lesson_flow(
        self,
        mock_db_service,
        mock_openai_service,
        sample_user_state
    ):
        """Test complete lesson flow: get lesson -> explain -> exercises -> answer."""
        await grammar_agent._load_rules()

        # Step 1: Get a lesson
        result = await grammar_agent.process(sample_user_state)
        assert result["response"]["status"] == "success"
        rule_id = result["response"]["rule"]["id"]
        rule_name = result["response"]["rule"]["name"]

        # Step 2: Submit explanation
        sample_user_state["activity_input"] = {
            "rule_id": rule_id,
            "explanation": "Esta regra gramatical é muito importante. Ela descreve como formamos sentenças e quando devemos usar cada forma verbal corretamente no inglês."
        }
        sample_user_state["current_activity"] = result["current_activity"]

        result = await grammar_agent.process(sample_user_state)
        assert result["response"]["status"] == "success"
        assert result["response"]["type"] == "grammar_explanation"
        passed = result["response"]["passed"]

        # Step 3: Get exercises
        sample_user_state["request_type"] = "grammar_exercise"
        sample_user_state["activity_input"] = {
            "rule_id": rule_id,
            "count": 3
        }

        result = await grammar_agent.process(sample_user_state)
        assert result["response"]["status"] == "success"
        assert len(result["response"]["exercises"]) > 0

        # Step 4: Answer exercise
        sample_user_state["current_activity"] = result["current_activity"]
        sample_user_state["activity_input"] = {
            "rule_id": rule_id,
            "answer": "1",
            "exercise_index": 0
        }

        result = await grammar_agent.process(sample_user_state)
        assert result["response"]["status"] == "success"
        assert "correct" in result["response"]

    @pytest.mark.asyncio
    async def test_srs_progression(
        self,
        mock_db_service,
        mock_openai_service,
        sample_user_state
    ):
        """Test SRS interval progression with good scores."""
        await grammar_agent._load_rules()

        # First practice - should set initial SRS values
        sample_user_state["activity_input"] = {
            "rule_id": "rule_001",
            "explanation": "Esta é uma explicação detalhada da regra gramatical que demonstra bom entendimento do conceito."
        }

        result = await grammar_agent.process(sample_user_state)

        # Verify progress was updated
        assert mock_db_service.update_grammar_progress.called
        call_args = mock_db_service.update_grammar_progress.call_args
        progress_data = call_args[0][2]  # Third argument is progress_data

        assert "srsData" in progress_data
        assert progress_data["srsData"]["interval"] >= 1
