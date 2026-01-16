"""
Scheduler Agent
Manages the Spaced Repetition System (SRS) and daily study schedules.

Responsibilities:
- Identify items due for review based on SM-2 algorithm
- Detect low-frequency items (not used in 7 days)
- Create and manage daily study schedules
- Prioritize activities: SRS due > Low frequency > New items
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.state import AppState, add_agent_message
from app.utils.srs_algorithm import (
    srs_algorithm,
    calculate_next_review,
    should_review_low_frequency,
    SRSData
)
from app.models.progress import DailySchedule


logger = logging.getLogger(__name__)


class SchedulerAgent(BaseAgent[AppState]):
    """
    Scheduler Agent for managing SRS and daily schedules.

    Uses the SM-2 algorithm to determine optimal review times
    and creates personalized daily study schedules.
    """

    @property
    def name(self) -> str:
        return "scheduler"

    @property
    def description(self) -> str:
        return "Manages spaced repetition scheduling and daily study plans"

    async def process(self, state: AppState) -> AppState:
        """Process scheduling request"""
        self.log_start({"user_id": state["user"]["user_id"]})

        try:
            request_type = state.get("request_type", "")

            if request_type == "get_schedule":
                return await self._get_daily_schedule(state)
            elif request_type == "get_next_activity":
                return await self._get_next_activity(state)
            else:
                # Default: refresh SRS data in state
                return await self._refresh_srs_state(state)

        except Exception as e:
            self.log_error(e)
            state["has_error"] = True
            state["error_message"] = f"Scheduler error: {str(e)}"
            return state

    async def _refresh_srs_state(self, state: AppState) -> AppState:
        """
        Refresh SRS data in state.

        Queries database for items due for review and low-frequency items.
        """
        user_id = state["user"]["user_id"]
        self.log_debug("Refreshing SRS state", {"user_id": user_id})

        # Get items due for review from each pillar
        vocab_due = await self.db_service.get_vocabulary_due_for_review(user_id)
        grammar_due = await self.db_service.get_grammar_due_for_review(user_id)
        pronun_needs_practice = await self.db_service.get_pronunciation_needs_practice(
            user_id,
            self.settings.SRS_LOW_ACCURACY_THRESHOLD
        )

        # Get low frequency vocabulary items
        low_freq_vocab = await self.db_service.get_vocabulary_low_frequency(
            user_id,
            self.settings.SRS_LOW_FREQUENCY_THRESHOLD_DAYS
        )

        # Update SRS state
        state["srs"]["items_due_vocabulary"] = vocab_due
        state["srs"]["items_due_grammar"] = grammar_due
        state["srs"]["items_due_pronunciation"] = pronun_needs_practice
        state["srs"]["low_frequency_items"] = low_freq_vocab
        state["srs"]["items_due_today"] = len(vocab_due) + len(grammar_due) + len(pronun_needs_practice)

        # Determine next item to review
        next_item = self._get_highest_priority_item(
            vocab_due, grammar_due, pronun_needs_practice, low_freq_vocab
        )
        state["srs"]["next_item"] = next_item

        state = add_agent_message(
            state,
            self.name,
            f"SRS refreshed: {state['srs']['items_due_today']} items due today",
            {"vocab_due": len(vocab_due), "grammar_due": len(grammar_due)}
        )

        return state

    async def _get_daily_schedule(self, state: AppState) -> AppState:
        """
        Get or create daily schedule for user.

        Creates a schedule that respects user's daily goal and prioritizes
        items based on SRS status.
        """
        user_id = state["user"]["user_id"]
        today = datetime.utcnow().strftime("%Y-%m-%d")

        self.log_debug("Getting daily schedule", {"user_id": user_id, "date": today})

        # Try to get existing schedule
        existing_schedule = await self.db_service.get_daily_schedule(user_id, today)

        if existing_schedule:
            state["daily_schedule"] = existing_schedule
            state["response"] = {
                "type": "schedule",
                "date": today,
                "schedule": existing_schedule
            }
            return state

        # Create new schedule
        schedule = await self._create_daily_schedule(state, today)
        state["daily_schedule"] = schedule
        state["schedule_date"] = today

        state["response"] = {
            "type": "schedule",
            "date": today,
            "schedule": schedule,
            "message": f"Schedule created with {len(schedule.get('scheduled_reviews', []))} activities"
        }

        state = add_agent_message(
            state,
            self.name,
            f"Created daily schedule for {today}"
        )

        self.log_complete({"activities": len(schedule.get("scheduled_reviews", []))})
        return state

    async def _create_daily_schedule(
        self,
        state: AppState,
        date: str
    ) -> dict:
        """
        Create a daily study schedule.

        Prioritizes:
        1. SRS items due for review (highest priority)
        2. Low frequency items (need practice)
        3. New items based on learning goals
        """
        user_id = state["user"]["user_id"]
        daily_goal = state["user"].get("daily_goal_minutes", 30)

        # Refresh SRS data if not already done
        if not state["srs"]["items_due_today"]:
            state = await self._refresh_srs_state(state)

        scheduled_reviews = []
        estimated_minutes = 0
        activity_id = 0

        # Average time per activity type (in minutes)
        time_estimates = {
            "vocabulary": 2,
            "grammar": 5,
            "pronunciation": 3,
            "speaking": 10
        }

        # 1. Add SRS due items (highest priority)
        for item in state["srs"]["items_due_vocabulary"][:10]:  # Limit to 10
            if estimated_minutes >= daily_goal:
                break
            scheduled_reviews.append({
                "id": f"review_{activity_id}",
                "type": "vocabulary_review",
                "pillar": "vocabulary",
                "item_id": item.get("wordId"),
                "reason": "srs_due",
                "priority": "high",
                "estimated_minutes": time_estimates["vocabulary"]
            })
            estimated_minutes += time_estimates["vocabulary"]
            activity_id += 1

        for item in state["srs"]["items_due_grammar"][:5]:
            if estimated_minutes >= daily_goal:
                break
            scheduled_reviews.append({
                "id": f"review_{activity_id}",
                "type": "grammar_review",
                "pillar": "grammar",
                "item_id": item.get("ruleId"),
                "reason": "srs_due",
                "priority": "high",
                "estimated_minutes": time_estimates["grammar"]
            })
            estimated_minutes += time_estimates["grammar"]
            activity_id += 1

        for item in state["srs"]["items_due_pronunciation"][:5]:
            if estimated_minutes >= daily_goal:
                break
            scheduled_reviews.append({
                "id": f"review_{activity_id}",
                "type": "pronunciation_review",
                "pillar": "pronunciation",
                "item_id": item.get("soundId"),
                "reason": "low_accuracy",
                "priority": "high",
                "estimated_minutes": time_estimates["pronunciation"]
            })
            estimated_minutes += time_estimates["pronunciation"]
            activity_id += 1

        # 2. Add low frequency items
        for item in state["srs"]["low_frequency_items"][:5]:
            if estimated_minutes >= daily_goal:
                break
            scheduled_reviews.append({
                "id": f"review_{activity_id}",
                "type": "vocabulary_practice",
                "pillar": "vocabulary",
                "item_id": item.get("wordId"),
                "reason": "low_frequency",
                "priority": "normal",
                "estimated_minutes": time_estimates["vocabulary"]
            })
            estimated_minutes += time_estimates["vocabulary"]
            activity_id += 1

        # 3. Add speaking session if time allows
        if estimated_minutes + time_estimates["speaking"] <= daily_goal:
            scheduled_reviews.append({
                "id": f"review_{activity_id}",
                "type": "speaking_session",
                "pillar": "speaking",
                "reason": "daily_practice",
                "priority": "normal",
                "estimated_minutes": time_estimates["speaking"]
            })
            estimated_minutes += time_estimates["speaking"]

        # Create schedule document
        schedule_data = {
            "id": f"schedule_{user_id}_{date}",
            "userId": user_id,
            "date": date,
            "scheduled_reviews": scheduled_reviews,
            "completed_reviews": [],
            "daily_goal_progress": {
                "minutesStudied": 0,
                "activitiesCompleted": 0,
                "goalMinutes": daily_goal,
                "totalActivities": len(scheduled_reviews)
            }
        }

        # Save to database
        await self.db_service.create_or_update_schedule(
            user_id, date, schedule_data
        )

        return schedule_data

    async def _get_next_activity(self, state: AppState) -> AppState:
        """
        Get the next recommended activity for the user.

        Considers:
        - SRS items due
        - Pending activities from errors
        - User preferences
        """
        user_id = state["user"]["user_id"]
        self.log_debug("Getting next activity", {"user_id": user_id})

        # Refresh SRS state
        state = await self._refresh_srs_state(state)

        # Check for pending activities first (from error integration)
        pending = await self.db_service.get_pending_activities(user_id)
        if pending:
            next_activity = pending[0]
            state["current_activity"] = {
                "activity_id": next_activity["id"],
                "activity_type": next_activity["type"],
                "pillar": next_activity.get("pillar"),
                "content": next_activity.get("content", {}),
                "status": "pending"
            }
            state["response"] = {
                "type": "next_activity",
                "activity": next_activity,
                "source": "pending"
            }
            return state

        # Get highest priority SRS item
        next_item = state["srs"].get("next_item")
        if next_item:
            state["current_activity"] = {
                "activity_id": next_item.get("id"),
                "activity_type": next_item.get("type", "review"),
                "pillar": next_item.get("pillar"),
                "content": next_item,
                "status": "pending"
            }
            state["response"] = {
                "type": "next_activity",
                "activity": next_item,
                "source": "srs"
            }
            state = add_agent_message(
                state,
                self.name,
                f"Next activity: {next_item.get('type')} - {next_item.get('pillar')}"
            )
            return state

        # No items due - suggest new learning
        state["response"] = {
            "type": "next_activity",
            "activity": None,
            "source": "none",
            "message": "No reviews due! Ready for new learning.",
            "suggestions": self._get_learning_suggestions(state)
        }

        return state

    def _get_highest_priority_item(
        self,
        vocab_due: list,
        grammar_due: list,
        pronun_due: list,
        low_freq: list
    ) -> Optional[dict]:
        """
        Get the highest priority item to review.

        Priority order:
        1. Very overdue items (> 7 days)
        2. Due items by pillar rotation
        3. Low frequency items
        """
        # Combine all due items with priority
        all_items = []

        for item in vocab_due:
            srs_data = self._extract_srs_data(item)
            priority = srs_algorithm.get_priority(srs_data) if srs_data else "normal"
            all_items.append({
                **item,
                "pillar": "vocabulary",
                "type": "vocabulary_review",
                "priority_level": 0 if priority == "high" else 1
            })

        for item in grammar_due:
            srs_data = self._extract_srs_data(item)
            priority = srs_algorithm.get_priority(srs_data) if srs_data else "normal"
            all_items.append({
                **item,
                "pillar": "grammar",
                "type": "grammar_review",
                "priority_level": 0 if priority == "high" else 1
            })

        for item in pronun_due:
            all_items.append({
                **item,
                "pillar": "pronunciation",
                "type": "pronunciation_review",
                "priority_level": 1  # Lower than overdue SRS
            })

        for item in low_freq:
            all_items.append({
                **item,
                "pillar": "vocabulary",
                "type": "vocabulary_practice",
                "priority_level": 2  # Lowest priority
            })

        if not all_items:
            return None

        # Sort by priority and return highest
        all_items.sort(key=lambda x: x.get("priority_level", 99))
        return all_items[0]

    def _extract_srs_data(self, item: dict) -> Optional[SRSData]:
        """Extract SRS data from an item"""
        srs_dict = item.get("srsData")
        if not srs_dict:
            return None

        try:
            return SRSData(
                ease_factor=srs_dict.get("easeFactor", 2.5),
                interval=srs_dict.get("interval", 1),
                repetitions=srs_dict.get("repetitions", 0),
                next_review=datetime.fromisoformat(srs_dict["nextReview"])
                if srs_dict.get("nextReview") else datetime.utcnow()
            )
        except Exception:
            return None

    def _get_learning_suggestions(self, state: AppState) -> list[dict]:
        """Get suggestions for new learning when nothing is due"""
        level = state["user"].get("current_level", "beginner")
        goals = state["user"].get("learning_goals", ["general"])
        scores = state.get("pillar_scores", {})

        suggestions = []

        # Suggest weakest pillar
        if scores:
            weakest = min(scores, key=scores.get)
            suggestions.append({
                "type": f"{weakest}_exercise",
                "pillar": weakest,
                "reason": f"Strengthen your weakest area: {weakest}"
            })

        # Suggest based on goals
        if "data_engineering" in goals or "ai" in goals:
            suggestions.append({
                "type": "vocabulary_exercise",
                "pillar": "vocabulary",
                "category": "technical",
                "reason": "Learn technical vocabulary for your field"
            })

        # Always suggest speaking practice
        suggestions.append({
            "type": "speaking_session",
            "pillar": "speaking",
            "reason": "Practice conversation skills"
        })

        return suggestions[:3]

    async def update_after_activity(
        self,
        state: AppState,
        activity_result: dict
    ) -> AppState:
        """
        Update SRS data after an activity is completed.

        Calculates new review interval based on performance.
        """
        user_id = state["user"]["user_id"]
        pillar = activity_result.get("pillar")
        item_id = activity_result.get("item_id")
        correct = activity_result.get("correct", False)
        accuracy = activity_result.get("accuracy", 0)

        # Calculate quality from accuracy
        quality = srs_algorithm.quality_from_accuracy(accuracy if accuracy else (100 if correct else 0))

        self.log_debug("Updating SRS after activity", {
            "pillar": pillar,
            "item_id": item_id,
            "quality": quality
        })

        # Get current SRS data based on pillar
        if pillar == "vocabulary":
            progress = await self.db_service.get_vocabulary_progress(user_id, item_id)
        elif pillar == "grammar":
            progress = await self.db_service.get_grammar_progress(user_id, item_id)
        else:
            progress = None

        if progress and progress.get("srsData"):
            # Calculate new SRS values
            new_srs = calculate_next_review(progress["srsData"], quality)

            # Update in database
            if pillar == "vocabulary":
                await self.db_service.update_vocabulary_progress(
                    user_id, item_id, {"srsData": new_srs}
                )
            elif pillar == "grammar":
                await self.db_service.update_grammar_progress(
                    user_id, item_id, {"srsData": new_srs}
                )

            self.log_debug("SRS updated", {
                "new_interval": new_srs["interval"],
                "next_review": new_srs["nextReview"]
            })

        return state


# Singleton instance
scheduler_agent = SchedulerAgent()
