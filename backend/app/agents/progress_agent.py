"""
Progress Agent
Tracks and reports user progress across all learning pillars.

Responsibilities:
- Calculate progress metrics for each pillar
- Track study streaks
- Generate progress reports
- Identify areas needing focus
- Determine readiness for level advancement
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.state import AppState, add_agent_message
from app.models.progress import (
    OverallProgress,
    PillarProgress,
    WeeklyReport
)


logger = logging.getLogger(__name__)


class ProgressAgent(BaseAgent[AppState]):
    """
    Progress Agent for tracking and reporting user progress.

    Aggregates data from all pillars and provides comprehensive
    progress insights to the user.
    """

    @property
    def name(self) -> str:
        return "progress"

    @property
    def description(self) -> str:
        return "Tracks metrics, calculates progress, and generates reports"

    async def process(self, state: AppState) -> AppState:
        """Process progress request"""
        self.log_start({"user_id": state["user"]["user_id"]})

        try:
            request_type = state.get("request_type", "")

            if request_type == "get_progress":
                return await self._get_overall_progress(state)
            else:
                # Default: update progress after activity
                return await self._update_progress(state)

        except Exception as e:
            self.log_error(e)
            state["has_error"] = True
            state["error_message"] = f"Progress error: {str(e)}"
            return state

    async def _get_overall_progress(self, state: AppState) -> AppState:
        """
        Get comprehensive progress for user.

        Calculates metrics for each pillar and overall progress.
        """
        user_id = state["user"]["user_id"]
        self.log_debug("Getting overall progress", {"user_id": user_id})

        # Get user statistics
        stats = await self.db_service.get_user_statistics(user_id)

        # Get user data
        user = await self.db_service.get_user(user_id)
        if not user:
            state["has_error"] = True
            state["error_message"] = "User not found"
            return state

        # Calculate pillar progress
        vocabulary_progress = await self._calculate_vocabulary_progress(user_id, stats)
        grammar_progress = await self._calculate_grammar_progress(user_id, stats)
        pronunciation_progress = await self._calculate_pronunciation_progress(user_id, stats)
        speaking_progress = await self._calculate_speaking_progress(user_id, stats)

        # Calculate overall metrics
        pillar_scores = [
            vocabulary_progress.average_score,
            grammar_progress.average_score,
            pronunciation_progress.average_accuracy,
            speaking_progress.average_score
        ]
        overall_score = sum(pillar_scores) / 4 if pillar_scores else 0

        # Determine weakest pillar
        pillars = {
            "vocabulary": vocabulary_progress.average_score,
            "grammar": grammar_progress.average_score,
            "pronunciation": pronunciation_progress.average_accuracy,
            "speaking": speaking_progress.average_score
        }
        weakest_pillar = min(pillars, key=pillars.get)

        # Check if ready for level up
        ready_for_level_up = self._check_level_up_readiness(
            user.get("current_level", "beginner"),
            pillars
        )

        # Calculate streak
        current_streak = self._calculate_streak(user)

        # Create overall progress
        progress = OverallProgress(
            user_id=user_id,
            current_level=user.get("current_level", "beginner"),
            vocabulary=vocabulary_progress,
            grammar=grammar_progress,
            pronunciation=pronunciation_progress,
            speaking=speaking_progress,
            overall_score=overall_score,
            total_study_time_minutes=user.get("total_study_time_minutes", 0),
            total_activities_completed=self._count_total_activities(stats),
            current_streak_days=current_streak,
            longest_streak_days=user.get("longest_streak_days", 0),
            last_activity_date=datetime.fromisoformat(user["last_activity_date"])
            if user.get("last_activity_date") else None,
            initial_assessment_completed=user.get("initial_assessment_completed", False),
            last_assessment_date=datetime.fromisoformat(user["last_assessment_date"])
            if user.get("last_assessment_date") else None,
            ready_for_level_up=ready_for_level_up,
            weakest_pillar=weakest_pillar,
            daily_goal_minutes=user.get("profile", {}).get("daily_goal_minutes", 30)
        )

        # Update state
        state["progress"] = {
            "total_study_time_minutes": progress.total_study_time_minutes,
            "today_study_minutes": progress.today_study_minutes,
            "today_activities_completed": progress.today_activities_completed,
            "current_streak_days": progress.current_streak_days,
            "pillar_progress": {
                "vocabulary": vocabulary_progress.model_dump(),
                "grammar": grammar_progress.model_dump(),
                "pronunciation": pronunciation_progress.model_dump(),
                "speaking": speaking_progress.model_dump()
            },
            "weakest_pillar": weakest_pillar,
            "ready_for_level_up": ready_for_level_up
        }

        state["pillar_scores"] = pillars

        state["response"] = {
            "type": "progress",
            "progress": progress.model_dump(),
            "message": self._generate_progress_message(progress)
        }

        state = add_agent_message(
            state,
            self.name,
            f"Progress calculated: {overall_score:.0f}% overall",
            {"weakest": weakest_pillar, "streak": current_streak}
        )

        self.log_complete({"overall_score": overall_score})
        return state

    async def _update_progress(self, state: AppState) -> AppState:
        """
        Update progress after an activity is completed.

        Updates:
        - Pillar-specific metrics
        - Study time
        - Streak
        - Activity count
        """
        user_id = state["user"]["user_id"]
        activity_result = state.get("activity_output", {})

        if not activity_result:
            return state

        self.log_debug("Updating progress after activity", {
            "user_id": user_id,
            "activity_type": activity_result.get("type")
        })

        # Get current user data
        user = await self.db_service.get_user(user_id)
        if not user:
            return state

        # Calculate updates
        updates = {}

        # Update activity count
        sessions_count = user.get("sessions_since_last_assessment", 0) + 1
        updates["sessions_since_last_assessment"] = sessions_count

        # Update study time
        time_spent = activity_result.get("time_spent_seconds", 0) // 60
        total_time = user.get("total_study_time_minutes", 0) + time_spent
        updates["total_study_time_minutes"] = total_time

        # Update last activity date
        today = datetime.utcnow()
        updates["last_activity_date"] = today.isoformat()

        # Update streak
        last_activity = user.get("last_activity_date")
        if last_activity:
            last_date = datetime.fromisoformat(last_activity).date()
            today_date = today.date()
            yesterday = today_date - timedelta(days=1)

            if last_date == yesterday:
                # Consecutive day - increment streak
                new_streak = user.get("current_streak_days", 0) + 1
                updates["current_streak_days"] = new_streak
                if new_streak > user.get("longest_streak_days", 0):
                    updates["longest_streak_days"] = new_streak
            elif last_date != today_date:
                # Missed a day - reset streak
                updates["current_streak_days"] = 1
        else:
            updates["current_streak_days"] = 1

        # Update pillar score if provided
        pillar = activity_result.get("pillar")
        score = activity_result.get("score")
        if pillar and score is not None:
            score_key = f"{pillar}_score"
            # Weighted average with existing score
            existing_score = user.get(score_key, 0)
            new_score = int((existing_score * 0.7) + (score * 0.3))
            updates[score_key] = new_score

        # Apply updates
        await self.db_service.update_user(user_id, updates)

        # Update state
        state["progress"]["today_activities_completed"] = (
            state["progress"].get("today_activities_completed", 0) + 1
        )
        state["progress"]["today_study_minutes"] = (
            state["progress"].get("today_study_minutes", 0) + time_spent
        )
        state["progress"]["current_streak_days"] = updates.get(
            "current_streak_days",
            state["progress"].get("current_streak_days", 0)
        )

        state = add_agent_message(
            state,
            self.name,
            f"Progress updated: +{time_spent}min study time"
        )

        return state

    async def _calculate_vocabulary_progress(
        self,
        user_id: str,
        stats: dict
    ) -> PillarProgress:
        """Calculate vocabulary pillar progress"""
        vocab_stats = stats.get("vocabulary", {})

        # Get due items count
        due_items = await self.db_service.get_vocabulary_due_for_review(user_id)
        low_freq = await self.db_service.get_vocabulary_low_frequency(user_id)

        total = vocab_stats.get("total_words", 0)
        mastered = vocab_stats.get("mastered", 0)
        learning = vocab_stats.get("learning", 0)

        # Calculate average score
        avg_score = (mastered / total * 100) if total > 0 else 0

        return PillarProgress(
            pillar="vocabulary",
            total_items=total,
            mastered_items=mastered,
            learning_items=learning,
            average_score=avg_score,
            average_accuracy=avg_score,  # Same for vocabulary
            items_due_for_review=len(due_items),
            items_low_frequency=len(low_freq)
        )

    async def _calculate_grammar_progress(
        self,
        user_id: str,
        stats: dict
    ) -> PillarProgress:
        """Calculate grammar pillar progress"""
        grammar_stats = stats.get("grammar", {})

        # Get due items count
        due_items = await self.db_service.get_grammar_due_for_review(user_id)

        total = grammar_stats.get("total_rules", 0)
        avg_score = grammar_stats.get("average_score", 0)

        # Estimate mastered (score >= 85)
        mastered = int(total * (avg_score / 100)) if total > 0 else 0

        return PillarProgress(
            pillar="grammar",
            total_items=total,
            mastered_items=mastered,
            learning_items=total - mastered,
            average_score=avg_score,
            average_accuracy=avg_score,
            items_due_for_review=len(due_items)
        )

    async def _calculate_pronunciation_progress(
        self,
        user_id: str,
        stats: dict
    ) -> PillarProgress:
        """Calculate pronunciation pillar progress"""
        pronun_stats = stats.get("pronunciation", {})

        # Get items needing practice
        needs_practice = await self.db_service.get_pronunciation_needs_practice(user_id)

        total = pronun_stats.get("total_sounds", 0)
        avg_accuracy = pronun_stats.get("average_accuracy", 0)

        # Mastered = accuracy >= 85%
        mastered = int(total * (avg_accuracy / 100)) if total > 0 else 0

        return PillarProgress(
            pillar="pronunciation",
            total_items=total,
            mastered_items=mastered,
            learning_items=total - mastered,
            average_score=avg_accuracy,
            average_accuracy=avg_accuracy,
            items_due_for_review=len(needs_practice)
        )

    async def _calculate_speaking_progress(
        self,
        user_id: str,
        stats: dict
    ) -> PillarProgress:
        """Calculate speaking pillar progress"""
        speaking_stats = stats.get("speaking", {})

        sessions = speaking_stats.get("sessions_last_30_days", 0)

        # Score based on activity (more sessions = higher score)
        # Target: 20 sessions/month = 100%
        avg_score = min(sessions * 5, 100)

        return PillarProgress(
            pillar="speaking",
            total_items=sessions,  # Sessions count as items
            mastered_items=0,  # Not applicable for speaking
            learning_items=0,
            average_score=avg_score,
            average_accuracy=avg_score
        )

    def _calculate_streak(self, user: dict) -> int:
        """Calculate current streak based on last activity"""
        last_activity = user.get("last_activity_date")
        if not last_activity:
            return 0

        last_date = datetime.fromisoformat(last_activity).date()
        today = datetime.utcnow().date()

        # If last activity was today or yesterday, streak is valid
        if last_date >= today - timedelta(days=1):
            return user.get("current_streak_days", 0)

        return 0

    def _check_level_up_readiness(
        self,
        current_level: str,
        pillars: dict[str, float]
    ) -> bool:
        """Check if user is ready for level advancement"""
        if current_level != "beginner":
            return False

        threshold = self.settings.INTERMEDIATE_UPGRADE_THRESHOLD

        # All pillars must be at or above threshold
        return all(score >= threshold for score in pillars.values())

    def _count_total_activities(self, stats: dict) -> int:
        """Count total activities from stats"""
        total = 0
        total += stats.get("vocabulary", {}).get("total_words", 0)
        total += stats.get("grammar", {}).get("total_rules", 0)
        total += stats.get("pronunciation", {}).get("total_sounds", 0)
        total += stats.get("speaking", {}).get("sessions_last_30_days", 0)
        return total

    def _generate_progress_message(self, progress: OverallProgress) -> str:
        """Generate a user-friendly progress message"""
        messages = []

        # Level and overall score
        messages.append(
            f"Level: {progress.current_level.capitalize()} | "
            f"Overall: {progress.overall_score:.0f}%"
        )

        # Streak
        if progress.current_streak_days > 0:
            messages.append(f"🔥 {progress.current_streak_days} day streak!")

        # Weakest area
        if progress.weakest_pillar:
            messages.append(f"Focus area: {progress.weakest_pillar}")

        # Level up readiness
        if progress.ready_for_level_up:
            messages.append("⭐ Ready for intermediate level!")

        return " | ".join(messages)

    async def generate_weekly_report(
        self,
        user_id: str,
        week_start: Optional[datetime] = None
    ) -> WeeklyReport:
        """
        Generate a comprehensive weekly report.

        Args:
            user_id: User ID
            week_start: Start of week (defaults to 7 days ago)

        Returns:
            WeeklyReport with all metrics
        """
        if not week_start:
            week_start = datetime.utcnow() - timedelta(days=7)

        week_end = week_start + timedelta(days=6)

        # Get statistics
        stats = await self.db_service.get_user_statistics(user_id)
        user = await self.db_service.get_user(user_id)

        # Get weekly schedule data
        schedules = await self.db_service.get_week_schedule(user_id)

        # Calculate metrics
        total_minutes = sum(
            s.get("daily_goal_progress", {}).get("minutesStudied", 0)
            for s in schedules
        )
        activities_completed = sum(
            len(s.get("completed_reviews", []))
            for s in schedules
        )

        # Daily breakdown
        daily_breakdown = [
            {
                "date": s.get("date"),
                "minutes": s.get("daily_goal_progress", {}).get("minutesStudied", 0),
                "activities": len(s.get("completed_reviews", []))
            }
            for s in schedules
        ]

        return WeeklyReport(
            user_id=user_id,
            week_start=week_start.strftime("%Y-%m-%d"),
            week_end=week_end.strftime("%Y-%m-%d"),
            total_study_minutes=total_minutes,
            daily_breakdown=daily_breakdown,
            activities_completed=activities_completed,
            activities_by_pillar={
                "vocabulary": stats.get("vocabulary", {}).get("total_words", 0),
                "grammar": stats.get("grammar", {}).get("total_rules", 0),
                "pronunciation": stats.get("pronunciation", {}).get("total_sounds", 0),
                "speaking": stats.get("speaking", {}).get("sessions_last_30_days", 0)
            },
            words_learned=stats.get("vocabulary", {}).get("mastered", 0),
            words_reviewed=stats.get("vocabulary", {}).get("total_words", 0),
            grammar_rules_practiced=stats.get("grammar", {}).get("total_rules", 0),
            pronunciation_sounds_practiced=stats.get("pronunciation", {}).get("total_sounds", 0),
            speaking_sessions=stats.get("speaking", {}).get("sessions_last_30_days", 0),
            average_vocabulary_accuracy=stats.get("vocabulary", {}).get("mastered", 0) /
                max(stats.get("vocabulary", {}).get("total_words", 1), 1) * 100,
            average_grammar_accuracy=stats.get("grammar", {}).get("average_score", 0),
            average_pronunciation_accuracy=stats.get("pronunciation", {}).get("average_accuracy", 0),
            streak_maintained=user.get("current_streak_days", 0) >= 7,
            current_streak=user.get("current_streak_days", 0),
            achievements=self._get_achievements(user, stats),
            areas_to_improve=self._get_areas_to_improve(stats)
        )

    def _get_achievements(self, user: dict, stats: dict) -> list[str]:
        """Get achievements for the week"""
        achievements = []

        # Streak achievements
        streak = user.get("current_streak_days", 0)
        if streak >= 7:
            achievements.append(f"🔥 Week-long streak: {streak} days!")
        elif streak >= 3:
            achievements.append(f"🔥 {streak} day streak!")

        # Vocabulary achievements
        vocab_mastered = stats.get("vocabulary", {}).get("mastered", 0)
        if vocab_mastered >= 100:
            achievements.append(f"📚 Mastered {vocab_mastered} words!")
        elif vocab_mastered >= 50:
            achievements.append(f"📖 Learning {vocab_mastered} words!")

        # Speaking achievements
        sessions = stats.get("speaking", {}).get("sessions_last_30_days", 0)
        if sessions >= 10:
            achievements.append(f"🗣️ {sessions} speaking sessions!")

        return achievements[:5]

    def _get_areas_to_improve(self, stats: dict) -> list[str]:
        """Identify areas needing improvement"""
        areas = []

        # Check vocabulary
        vocab_stats = stats.get("vocabulary", {})
        if vocab_stats.get("total_words", 0) < 100:
            areas.append("Build your vocabulary foundation")

        # Check pronunciation
        pronun_stats = stats.get("pronunciation", {})
        if pronun_stats.get("average_accuracy", 0) < 70:
            areas.append("Focus on pronunciation accuracy")

        # Check grammar
        grammar_stats = stats.get("grammar", {})
        if grammar_stats.get("average_score", 0) < 70:
            areas.append("Practice grammar rules more frequently")

        # Check speaking
        speaking_stats = stats.get("speaking", {})
        if speaking_stats.get("sessions_last_30_days", 0) < 5:
            areas.append("Increase speaking practice frequency")

        return areas[:3]


# Singleton instance
progress_agent = ProgressAgent()
