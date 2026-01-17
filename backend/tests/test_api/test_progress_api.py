"""
Tests for Progress API endpoints.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app


client = TestClient(app)


@pytest.fixture
def mock_run_orchestrator():
    """Mock the run_orchestrator function."""
    with patch("app.api.v1.endpoints.progress.run_orchestrator") as mock:
        yield mock


@pytest.fixture
def mock_progress_agent():
    """Mock the progress agent."""
    with patch("app.api.v1.endpoints.progress.progress_agent") as mock:
        yield mock


@pytest.fixture
def mock_scheduler_agent():
    """Mock the scheduler agent."""
    with patch("app.api.v1.endpoints.progress.scheduler_agent") as mock:
        yield mock


@pytest.fixture
def mock_cosmos_db():
    """Mock the cosmos db service."""
    with patch("app.api.v1.endpoints.progress.cosmos_db_service") as mock:
        yield mock


class TestDashboardEndpoint:
    """Tests for GET /progress/dashboard/{user_id}"""

    def test_get_dashboard_success(self, mock_run_orchestrator):
        """Test successful dashboard retrieval."""
        # Setup mock response
        mock_run_orchestrator.return_value = {
            "response": {
                "type": "progress",
                "progress": {
                    "user_id": "test_user",
                    "current_level": "beginner",
                    "vocabulary": {
                        "pillar": "vocabulary",
                        "total_items": 100,
                        "mastered_items": 50,
                        "learning_items": 30,
                        "average_score": 75.0,
                        "average_accuracy": 75.0,
                        "items_due_for_review": 5
                    },
                    "grammar": {
                        "pillar": "grammar",
                        "total_items": 20,
                        "mastered_items": 10,
                        "learning_items": 8,
                        "average_score": 70.0,
                        "average_accuracy": 70.0,
                        "items_due_for_review": 2
                    },
                    "pronunciation": {
                        "pillar": "pronunciation",
                        "total_items": 15,
                        "mastered_items": 5,
                        "learning_items": 8,
                        "average_score": 65.0,
                        "average_accuracy": 65.0,
                        "items_due_for_review": 3
                    },
                    "speaking": {
                        "pillar": "speaking",
                        "total_items": 8,
                        "mastered_items": 0,
                        "learning_items": 0,
                        "average_score": 60.0,
                        "average_accuracy": 60.0,
                        "items_due_for_review": 0
                    },
                    "overall_score": 67.5,
                    "total_study_time_minutes": 120,
                    "total_activities_completed": 50,
                    "current_streak_days": 5,
                    "longest_streak_days": 10,
                    "weakest_pillar": "speaking",
                    "ready_for_level_up": False,
                    "daily_goal_minutes": 30,
                    "today_study_minutes": 15,
                    "today_activities_completed": 3
                },
                "message": "Level: Beginner | Overall: 68%"
            }
        }

        response = client.get("/api/v1/progress/dashboard/test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test_user"
        assert data["current_level"] == "beginner"
        assert data["overall_score"] == 67.5
        assert data["weakest_pillar"] == "speaking"
        assert data["vocabulary"]["total_items"] == 100

    def test_get_dashboard_with_weekly_report(self, mock_run_orchestrator):
        """Test dashboard retrieval with weekly report flag."""
        mock_run_orchestrator.return_value = {
            "response": {
                "type": "progress",
                "progress": {
                    "user_id": "test_user",
                    "current_level": "beginner",
                    "vocabulary": {"pillar": "vocabulary", "total_items": 0, "mastered_items": 0, "learning_items": 0, "average_score": 0, "average_accuracy": 0},
                    "grammar": {"pillar": "grammar", "total_items": 0, "mastered_items": 0, "learning_items": 0, "average_score": 0, "average_accuracy": 0},
                    "pronunciation": {"pillar": "pronunciation", "total_items": 0, "mastered_items": 0, "learning_items": 0, "average_score": 0, "average_accuracy": 0},
                    "speaking": {"pillar": "speaking", "total_items": 0, "mastered_items": 0, "learning_items": 0, "average_score": 0, "average_accuracy": 0},
                    "overall_score": 0
                }
            }
        }

        response = client.get(
            "/api/v1/progress/dashboard/test_user",
            params={"include_weekly_report": True}
        )

        assert response.status_code == 200
        # Verify orchestrator was called with correct params
        mock_run_orchestrator.assert_called_once()


class TestPillarProgressEndpoint:
    """Tests for GET /progress/pillar/{user_id}/{pillar}"""

    def test_get_vocabulary_progress(self, mock_cosmos_db):
        """Test getting vocabulary pillar progress."""
        mock_cosmos_db.get_user_statistics.return_value = {
            "vocabulary": {
                "total_words": 100,
                "mastered": 50,
                "learning": 30
            }
        }
        mock_cosmos_db.get_vocabulary_due_for_review.return_value = [
            {"wordId": "word1"},
            {"wordId": "word2"}
        ]

        response = client.get("/api/v1/progress/pillar/test_user/vocabulary")

        assert response.status_code == 200
        data = response.json()
        assert data["pillar"] == "vocabulary"
        assert data["total_items"] == 100
        assert data["items_due_for_review"] == 2

    def test_get_invalid_pillar(self, mock_cosmos_db):
        """Test getting progress for invalid pillar."""
        response = client.get("/api/v1/progress/pillar/test_user/invalid")

        assert response.status_code == 400
        assert "Pilar inválido" in response.json()["detail"]


class TestScheduleEndpoints:
    """Tests for schedule-related endpoints."""

    def test_get_today_schedule_new(self, mock_run_orchestrator):
        """Test getting today's schedule when it doesn't exist."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        mock_run_orchestrator.return_value = {
            "response": {
                "type": "schedule",
                "date": today,
                "schedule": {
                    "date": today,
                    "scheduled_reviews": [
                        {
                            "id": "review_0",
                            "type": "vocabulary_review",
                            "pillar": "vocabulary",
                            "item_id": "word1",
                            "reason": "srs_due",
                            "priority": "high",
                            "estimated_minutes": 2
                        }
                    ],
                    "completed_reviews": [],
                    "daily_goal_progress": {
                        "minutesStudied": 0,
                        "activitiesCompleted": 0,
                        "goalMinutes": 30,
                        "totalActivities": 1
                    }
                },
                "message": "Schedule created with 1 activities"
            }
        }

        response = client.get("/api/v1/progress/schedule/today/test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == today
        assert len(data["scheduled_reviews"]) == 1
        assert data["scheduled_reviews"][0]["type"] == "vocabulary_review"

    def test_get_week_schedule(self, mock_cosmos_db):
        """Test getting week's schedule."""
        today = datetime.utcnow()
        mock_cosmos_db.get_week_schedule.return_value = [
            {
                "date": (today + timedelta(days=i)).strftime("%Y-%m-%d"),
                "scheduled_reviews": [],
                "completed_reviews": [],
                "daily_goal_progress": {
                    "minutesStudied": 15 if i < 3 else 0,
                    "activitiesCompleted": 2 if i < 3 else 0,
                    "goalMinutes": 30,
                    "totalActivities": 5
                }
            }
            for i in range(7)
        ]

        response = client.get("/api/v1/progress/schedule/week/test_user")

        assert response.status_code == 200
        data = response.json()
        assert len(data["schedules"]) == 7
        assert "week_summary" in data

    def test_complete_scheduled_review(self, mock_cosmos_db):
        """Test completing a scheduled review."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        mock_cosmos_db.get_daily_schedule.return_value = {
            "date": today,
            "scheduled_reviews": [
                {
                    "id": "review_1",
                    "type": "vocabulary_review",
                    "pillar": "vocabulary",
                    "item_id": "word1",
                    "reason": "srs_due",
                    "priority": "high",
                    "estimated_minutes": 2
                }
            ],
            "completed_reviews": [],
            "daily_goal_progress": {
                "minutesStudied": 0,
                "activitiesCompleted": 0,
                "goalMinutes": 30
            }
        }

        response = client.post(
            "/api/v1/progress/schedule/complete-review/test_user",
            json={"review_id": "review_1", "result": {"correct": True}}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_complete_review_not_found(self, mock_cosmos_db):
        """Test completing a review that doesn't exist."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        mock_cosmos_db.get_daily_schedule.return_value = {
            "date": today,
            "scheduled_reviews": [],
            "completed_reviews": [],
            "daily_goal_progress": {}
        }

        response = client.post(
            "/api/v1/progress/schedule/complete-review/test_user",
            json={"review_id": "nonexistent", "result": {}}
        )

        assert response.status_code == 404


class TestWeeklyReportEndpoint:
    """Tests for GET /progress/weekly-report/{user_id}"""

    def test_get_weekly_report(self, mock_progress_agent, mock_cosmos_db):
        """Test getting weekly report."""
        # Mock the weekly report
        mock_report = MagicMock()
        mock_report.week_start = "2024-01-08"
        mock_report.week_end = "2024-01-14"
        mock_report.total_study_minutes = 180
        mock_report.daily_breakdown = [
            {"date": "2024-01-08", "minutes": 30, "activities": 5},
            {"date": "2024-01-09", "minutes": 25, "activities": 4}
        ]
        mock_report.activities_completed = 25
        mock_report.activities_by_pillar = {"vocabulary": 10, "grammar": 8, "pronunciation": 5, "speaking": 2}
        mock_report.words_learned = 20
        mock_report.words_reviewed = 50
        mock_report.grammar_rules_practiced = 8
        mock_report.pronunciation_sounds_practiced = 5
        mock_report.speaking_sessions = 2
        mock_report.average_vocabulary_accuracy = 85.0
        mock_report.average_grammar_accuracy = 78.0
        mock_report.average_pronunciation_accuracy = 72.0
        mock_report.streak_maintained = True
        mock_report.current_streak = 7
        mock_report.achievements = ["7 day streak!"]
        mock_report.areas_to_improve = ["Focus on pronunciation"]

        mock_progress_agent.generate_weekly_report = AsyncMock(return_value=mock_report)

        response = client.get("/api/v1/progress/weekly-report/test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["total_study_minutes"] == 180
        assert data["current_streak"] == 7
        assert len(data["achievements"]) == 1


class TestNextActivityEndpoint:
    """Tests for GET /progress/next-activity/{user_id}"""

    def test_get_next_activity_with_due_items(self, mock_run_orchestrator):
        """Test getting next activity when items are due."""
        mock_run_orchestrator.return_value = {
            "response": {
                "type": "next_activity",
                "activity": {
                    "type": "vocabulary_review",
                    "pillar": "vocabulary",
                    "wordId": "word1",
                    "reason": "srs_due"
                },
                "source": "srs"
            }
        }

        response = client.get("/api/v1/progress/next-activity/test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["has_activity"] is True
        assert data["activity_type"] == "vocabulary_review"
        assert data["source"] == "srs"

    def test_get_next_activity_no_items_due(self, mock_run_orchestrator):
        """Test getting next activity when nothing is due."""
        mock_run_orchestrator.return_value = {
            "response": {
                "type": "next_activity",
                "activity": None,
                "source": "none",
                "message": "No reviews due!",
                "suggestions": [
                    {"type": "vocabulary_exercise", "pillar": "vocabulary", "reason": "Strengthen weakest area"}
                ]
            }
        }

        response = client.get("/api/v1/progress/next-activity/test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["has_activity"] is False
        assert data["source"] == "none"
        assert len(data["suggestions"]) == 1


class TestUpdateProgressEndpoint:
    """Tests for POST /progress/update/{user_id}"""

    def test_update_progress_success(self, mock_cosmos_db, mock_progress_agent, mock_scheduler_agent):
        """Test successful progress update."""
        mock_cosmos_db.get_user.return_value = {
            "id": "test_user",
            "current_level": "beginner",
            "total_study_time_minutes": 100,
            "current_streak_days": 5
        }

        mock_progress_agent.process = AsyncMock(return_value={
            "progress": {
                "current_streak_days": 5,
                "today_study_minutes": 10,
                "today_activities_completed": 1
            }
        })

        mock_scheduler_agent.update_after_activity = AsyncMock()

        response = client.post(
            "/api/v1/progress/update/test_user",
            json={
                "pillar": "vocabulary",
                "item_id": "word1",
                "correct": True,
                "accuracy": 100,
                "time_spent_seconds": 60
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_update_progress_user_not_found(self, mock_cosmos_db):
        """Test progress update for nonexistent user."""
        mock_cosmos_db.get_user.return_value = None

        response = client.post(
            "/api/v1/progress/update/nonexistent_user",
            json={
                "pillar": "vocabulary",
                "item_id": "word1",
                "correct": True,
                "time_spent_seconds": 60
            }
        )

        assert response.status_code == 404


class TestStreakEndpoint:
    """Tests for GET /progress/streak/{user_id}"""

    def test_get_streak_active(self, mock_cosmos_db):
        """Test getting active streak."""
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
        mock_cosmos_db.get_user.return_value = {
            "id": "test_user",
            "current_streak_days": 5,
            "longest_streak_days": 10,
            "last_activity_date": yesterday
        }

        response = client.get("/api/v1/progress/streak/test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["current_streak"] == 5
        assert data["longest_streak"] == 10
        assert data["streak_active"] is True

    def test_get_streak_broken(self, mock_cosmos_db):
        """Test getting broken streak."""
        three_days_ago = (datetime.utcnow() - timedelta(days=3)).isoformat()
        mock_cosmos_db.get_user.return_value = {
            "id": "test_user",
            "current_streak_days": 5,
            "longest_streak_days": 10,
            "last_activity_date": three_days_ago
        }

        response = client.get("/api/v1/progress/streak/test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["current_streak"] == 0  # Reset because streak is broken
        assert data["streak_active"] is False

    def test_get_streak_user_not_found(self, mock_cosmos_db):
        """Test getting streak for nonexistent user."""
        mock_cosmos_db.get_user.return_value = None

        response = client.get("/api/v1/progress/streak/nonexistent_user")

        assert response.status_code == 404