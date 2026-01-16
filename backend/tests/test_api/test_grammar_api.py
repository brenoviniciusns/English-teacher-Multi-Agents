"""
Tests for Grammar API Endpoints
Tests for the REST API endpoints for grammar functionality.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.agents.grammar_agent import grammar_agent


# ==================== FIXTURES ====================

@pytest.fixture
def mock_services():
    """Mock all external services for API tests."""
    with patch.object(grammar_agent, 'db_service') as mock_db, \
         patch.object(grammar_agent, 'openai_service') as mock_openai:

        # Mock DB service
        mock_db.get_grammar_progress = AsyncMock(return_value=None)
        mock_db.update_grammar_progress = AsyncMock(return_value={})
        mock_db.get_grammar_due_for_review = AsyncMock(return_value=[])
        mock_db.get_grammar_low_frequency = AsyncMock(return_value=[])

        # Mock OpenAI service
        mock_openai.evaluate_grammar_explanation = AsyncMock(return_value={
            "accuracy_score": 85.0,
            "completeness_score": 80.0,
            "understanding_score": 82.0,
            "overall_score": 82.0,
            "feedback": "Boa explicação!",
            "missing_points": [],
            "suggestions": "Continue praticando."
        })
        mock_openai.generate_grammar_exercises = AsyncMock(return_value=[
            {
                "type": "fill_in_blank",
                "instruction": "Complete the sentence",
                "sentence": "She ___ to work.",
                "options": ["go", "goes", "went"],
                "correct_answer": "goes",
                "correct_index": 1,
                "explanation": "Third person singular"
            }
        ])

        yield mock_db, mock_openai


@pytest_asyncio.fixture
async def async_client():
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


# ==================== ENDPOINT TESTS ====================

class TestGetNextLesson:
    """Test GET /api/v1/grammar/next-lesson endpoint."""

    @pytest.mark.asyncio
    async def test_get_next_lesson_success(self, async_client, mock_services):
        """Test successful lesson retrieval."""
        # Load rules first
        await grammar_agent._load_rules()

        response = await async_client.get(
            "/api/v1/grammar/next-lesson",
            params={"user_id": "test_user"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["type"] == "grammar_lesson"
        assert "rule" in data
        assert data["rule"]["id"] is not None
        assert data["rule"]["name"] is not None

    @pytest.mark.asyncio
    async def test_get_next_lesson_with_rule_id(self, async_client, mock_services):
        """Test lesson retrieval for specific rule."""
        await grammar_agent._load_rules()

        response = await async_client.get(
            "/api/v1/grammar/next-lesson",
            params={"user_id": "test_user", "rule_id": "rule_001"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["rule"]["id"] == "rule_001"

    @pytest.mark.asyncio
    async def test_get_next_lesson_with_category(self, async_client, mock_services):
        """Test lesson retrieval filtered by category."""
        await grammar_agent._load_rules()

        response = await async_client.get(
            "/api/v1/grammar/next-lesson",
            params={"user_id": "test_user", "category": "tense"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["rule"]["category"] == "tense"

    @pytest.mark.asyncio
    async def test_get_next_lesson_missing_user_id(self, async_client, mock_services):
        """Test error when user_id is missing."""
        response = await async_client.get("/api/v1/grammar/next-lesson")
        assert response.status_code == 422  # Validation error


class TestSubmitExplanation:
    """Test POST /api/v1/grammar/submit-explanation endpoint."""

    @pytest.mark.asyncio
    async def test_submit_explanation_success(self, async_client, mock_services):
        """Test successful explanation submission."""
        await grammar_agent._load_rules()

        response = await async_client.post(
            "/api/v1/grammar/submit-explanation",
            params={"user_id": "test_user"},
            json={
                "rule_id": "rule_001",
                "explanation": "O Present Simple é usado para hábitos e rotinas. Adicionamos -s ou -es na terceira pessoa."
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["type"] == "grammar_explanation"
        assert "evaluation" in data
        assert data["evaluation"]["overall_score"] > 0

    @pytest.mark.asyncio
    async def test_submit_explanation_too_short(self, async_client, mock_services):
        """Test error for short explanation."""
        response = await async_client.post(
            "/api/v1/grammar/submit-explanation",
            params={"user_id": "test_user"},
            json={
                "rule_id": "rule_001",
                "explanation": "Short"
            }
        )

        # Should fail validation (min_length=10)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_explanation_missing_rule_id(self, async_client, mock_services):
        """Test error when rule_id is missing."""
        response = await async_client.post(
            "/api/v1/grammar/submit-explanation",
            params={"user_id": "test_user"},
            json={
                "explanation": "Esta é uma explicação detalhada."
            }
        )

        assert response.status_code == 422


class TestGetExercises:
    """Test GET /api/v1/grammar/exercises endpoint."""

    @pytest.mark.asyncio
    async def test_get_exercises_success(self, async_client, mock_services):
        """Test successful exercise retrieval."""
        await grammar_agent._load_rules()

        response = await async_client.get(
            "/api/v1/grammar/exercises",
            params={"user_id": "test_user", "rule_id": "rule_001"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["type"] == "grammar_exercises"
        assert len(data["exercises"]) > 0

    @pytest.mark.asyncio
    async def test_get_exercises_with_count(self, async_client, mock_services):
        """Test exercise retrieval with count parameter."""
        await grammar_agent._load_rules()

        response = await async_client.get(
            "/api/v1/grammar/exercises",
            params={"user_id": "test_user", "rule_id": "rule_001", "count": 3}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_exercises_missing_rule_id(self, async_client, mock_services):
        """Test error when rule_id is missing."""
        response = await async_client.get(
            "/api/v1/grammar/exercises",
            params={"user_id": "test_user"}
        )

        assert response.status_code == 422


class TestGetProgress:
    """Test GET /api/v1/grammar/progress endpoint."""

    @pytest.mark.asyncio
    async def test_get_progress_success(self, async_client, mock_services):
        """Test successful progress retrieval."""
        await grammar_agent._load_rules()

        response = await async_client.get(
            "/api/v1/grammar/progress",
            params={"user_id": "test_user"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_rules" in data
        assert "mastered" in data
        assert "learning" in data
        assert "not_started" in data


class TestGetReviewList:
    """Test GET /api/v1/grammar/review-list endpoint."""

    @pytest.mark.asyncio
    async def test_get_review_list_success(self, async_client, mock_services):
        """Test successful review list retrieval."""
        await grammar_agent._load_rules()

        response = await async_client.get(
            "/api/v1/grammar/review-list",
            params={"user_id": "test_user"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert "total_due" in data


class TestListRules:
    """Test GET /api/v1/grammar/rules endpoint."""

    @pytest.mark.asyncio
    async def test_list_rules_success(self, async_client, mock_services):
        """Test successful rules listing."""
        await grammar_agent._load_rules()

        response = await async_client.get("/api/v1/grammar/rules")

        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert "total" in data
        assert "categories" in data
        assert len(data["rules"]) > 0

    @pytest.mark.asyncio
    async def test_list_rules_with_category_filter(self, async_client, mock_services):
        """Test rules listing with category filter."""
        await grammar_agent._load_rules()

        response = await async_client.get(
            "/api/v1/grammar/rules",
            params={"category": "tense"}
        )

        assert response.status_code == 200
        data = response.json()
        assert all(r["category"] == "tense" for r in data["rules"])

    @pytest.mark.asyncio
    async def test_list_rules_with_difficulty_filter(self, async_client, mock_services):
        """Test rules listing with difficulty filter."""
        await grammar_agent._load_rules()

        response = await async_client.get(
            "/api/v1/grammar/rules",
            params={"difficulty": "beginner"}
        )

        assert response.status_code == 200
        data = response.json()
        assert all(r["difficulty"] == "beginner" for r in data["rules"])

    @pytest.mark.asyncio
    async def test_list_rules_with_user_progress(self, async_client, mock_services):
        """Test rules listing includes user progress."""
        await grammar_agent._load_rules()

        response = await async_client.get(
            "/api/v1/grammar/rules",
            params={"user_id": "test_user"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "rules" in data


class TestGetRule:
    """Test GET /api/v1/grammar/rule/{rule_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_rule_success(self, async_client, mock_services):
        """Test successful single rule retrieval."""
        await grammar_agent._load_rules()

        response = await async_client.get("/api/v1/grammar/rule/rule_001")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["rule"]["id"] == "rule_001"

    @pytest.mark.asyncio
    async def test_get_rule_not_found(self, async_client, mock_services):
        """Test error for non-existent rule."""
        await grammar_agent._load_rules()

        response = await async_client.get("/api/v1/grammar/rule/invalid_rule")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_rule_with_user_progress(self, async_client, mock_services):
        """Test rule retrieval includes user progress."""
        await grammar_agent._load_rules()

        response = await async_client.get(
            "/api/v1/grammar/rule/rule_001",
            params={"user_id": "test_user"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestListCategories:
    """Test GET /api/v1/grammar/categories endpoint."""

    @pytest.mark.asyncio
    async def test_list_categories_success(self, async_client, mock_services):
        """Test successful categories listing."""
        await grammar_agent._load_rules()

        response = await async_client.get("/api/v1/grammar/categories")

        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "counts" in data
        assert "total_categories" in data
        assert len(data["categories"]) > 0


# ==================== RESPONSE FORMAT TESTS ====================

class TestResponseFormats:
    """Test that responses match expected schema formats."""

    @pytest.mark.asyncio
    async def test_lesson_response_format(self, async_client, mock_services):
        """Test lesson response has all required fields."""
        await grammar_agent._load_rules()

        response = await async_client.get(
            "/api/v1/grammar/next-lesson",
            params={"user_id": "test_user"}
        )

        data = response.json()
        assert "type" in data
        assert "status" in data
        assert "rule" in data

        rule = data["rule"]
        assert "id" in rule
        assert "name" in rule
        assert "category" in rule
        assert "difficulty" in rule
        assert "english_explanation" in rule
        assert "comparison" in rule
        assert "examples" in rule

    @pytest.mark.asyncio
    async def test_exercise_response_format(self, async_client, mock_services):
        """Test exercises response has all required fields."""
        await grammar_agent._load_rules()

        response = await async_client.get(
            "/api/v1/grammar/exercises",
            params={"user_id": "test_user", "rule_id": "rule_001"}
        )

        data = response.json()
        assert "type" in data
        assert "status" in data
        assert "exercises" in data
        assert "total_exercises" in data
        assert "rule_id" in data
        assert "rule_name" in data

        if data["exercises"]:
            exercise = data["exercises"][0]
            assert "index" in exercise
            assert "type" in exercise
            assert "instruction" in exercise
            assert "sentence" in exercise

    @pytest.mark.asyncio
    async def test_progress_response_format(self, async_client, mock_services):
        """Test progress response has all required fields."""
        await grammar_agent._load_rules()

        response = await async_client.get(
            "/api/v1/grammar/progress",
            params={"user_id": "test_user"}
        )

        data = response.json()
        assert "total_rules" in data
        assert "mastered" in data
        assert "reviewing" in data
        assert "learning" in data
        assert "not_started" in data
        assert "due_for_review" in data
        assert "average_score" in data
