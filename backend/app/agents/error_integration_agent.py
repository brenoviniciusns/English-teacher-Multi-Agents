"""
Error Integration Agent
Analyzes errors from conversation sessions and generates corrective activities.

Responsibilities:
- Process grammar errors from speaking sessions
- Process pronunciation errors from speaking sessions
- Generate corrective activities in the appropriate pillar (Grammar/Pronunciation)
- Deduplicate and prioritize errors
- Track activity generation
"""
import logging
from datetime import datetime
from typing import Optional

from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.state import AppState, add_agent_message
from app.config import Settings, get_settings
from app.models.speaking import ErrorType, GeneratedActivity


logger = logging.getLogger(__name__)


# Priority levels for different error types
GRAMMAR_PRIORITY = 2  # Grammar errors are important but common
PRONUNCIATION_PRIORITY = 3  # Pronunciation errors need more practice

# Maximum activities to generate per session
MAX_ACTIVITIES_PER_SESSION = 10


class ErrorIntegrationAgent(BaseAgent[AppState]):
    """
    Error Integration Agent - Creates corrective activities from conversation errors.

    Features:
    - Analyzes grammar errors and creates Grammar pillar activities
    - Analyzes pronunciation errors and creates Pronunciation pillar activities
    - Deduplicates repeated errors
    - Prioritizes errors based on frequency and severity
    - Links activities back to source sessions
    """

    def __init__(self, settings: Settings | None = None):
        super().__init__(settings=settings)

    @property
    def name(self) -> str:
        return "error_integration"

    @property
    def description(self) -> str:
        return "Analyzes errors from conversations and generates corrective activities"

    async def process(self, state: AppState) -> AppState:
        """
        Process errors and generate corrective activities.

        Reads from state["errors"] and creates activities in Cosmos DB.
        """
        self.log_start({
            "user_id": state["user"]["user_id"],
            "has_errors": state.get("errors", {}).get("has_errors", False)
        })

        try:
            errors_state = state.get("errors", {})

            if not errors_state.get("has_errors"):
                self.log_debug("No errors to process")
                state = add_agent_message(
                    state,
                    self.name,
                    "No errors to process"
                )
                return state

            pending_errors = errors_state.get("pending_errors", [])
            if not pending_errors:
                self.log_debug("No pending errors")
                return state

            # Process errors and generate activities
            generated_ids = await self._generate_activities(
                user_id=state["user"]["user_id"],
                errors=pending_errors,
                session_id=state.get("speaking", {}).get("session_id")
            )

            # Update state
            state["errors"]["generated_activity_ids"] = generated_ids
            state["errors"]["pending_errors"] = []  # Clear processed errors

            # Add to response if not already present
            if "response" in state and isinstance(state["response"], dict):
                state["response"]["generated_activities"] = generated_ids
                state["response"]["activities_count"] = len(generated_ids)

            state = add_agent_message(
                state,
                self.name,
                f"Generated {len(generated_ids)} corrective activities from {len(pending_errors)} errors"
            )

            self.log_complete({"activities_generated": len(generated_ids)})
            return state

        except Exception as e:
            self.log_error(e)
            state["has_error"] = True
            state["error_message"] = f"Error integration agent error: {str(e)}"
            return state

    async def _generate_activities(
        self,
        user_id: str,
        errors: list[dict],
        session_id: Optional[str] = None
    ) -> list[str]:
        """
        Generate corrective activities from errors.

        Args:
            user_id: User ID
            errors: List of error dictionaries
            session_id: Source session ID

        Returns:
            List of generated activity IDs
        """
        generated_ids = []

        # Separate and deduplicate errors
        grammar_errors = self._deduplicate_grammar_errors(
            [e for e in errors if e.get("type") == "grammar"]
        )
        pronunciation_errors = self._deduplicate_pronunciation_errors(
            [e for e in errors if e.get("type") == "pronunciation"]
        )

        # Calculate how many activities to generate (limit total)
        total_errors = len(grammar_errors) + len(pronunciation_errors)
        if total_errors > MAX_ACTIVITIES_PER_SESSION:
            # Prioritize pronunciation errors slightly
            pronunciation_limit = min(len(pronunciation_errors), MAX_ACTIVITIES_PER_SESSION // 2 + 1)
            grammar_limit = MAX_ACTIVITIES_PER_SESSION - pronunciation_limit
            grammar_errors = grammar_errors[:grammar_limit]
            pronunciation_errors = pronunciation_errors[:pronunciation_limit]

        # Generate grammar activities
        for error in grammar_errors:
            activity_id = await self._create_grammar_activity(
                user_id=user_id,
                error=error,
                session_id=session_id
            )
            if activity_id:
                generated_ids.append(activity_id)

        # Generate pronunciation activities
        for error in pronunciation_errors:
            activity_id = await self._create_pronunciation_activity(
                user_id=user_id,
                error=error,
                session_id=session_id
            )
            if activity_id:
                generated_ids.append(activity_id)

        return generated_ids

    def _deduplicate_grammar_errors(self, errors: list[dict]) -> list[dict]:
        """
        Deduplicate grammar errors by rule.

        Keeps the most informative example for each rule.
        """
        if not errors:
            return []

        # Group by rule
        by_rule: dict[str, list[dict]] = {}
        for error in errors:
            rule = error.get("rule", "unknown")
            if rule not in by_rule:
                by_rule[rule] = []
            by_rule[rule].append(error)

        # Take the first (or best) example of each rule
        deduplicated = []
        for rule, rule_errors in by_rule.items():
            # Sort by most complete information
            rule_errors.sort(
                key=lambda e: (
                    len(e.get("explanation", "")),
                    len(e.get("incorrect_text", ""))
                ),
                reverse=True
            )
            # Take the best example and add count
            best = rule_errors[0].copy()
            best["occurrence_count"] = len(rule_errors)
            deduplicated.append(best)

        # Sort by occurrence count (most common first)
        deduplicated.sort(key=lambda e: e.get("occurrence_count", 1), reverse=True)

        return deduplicated

    def _deduplicate_pronunciation_errors(self, errors: list[dict]) -> list[dict]:
        """
        Deduplicate pronunciation errors by phoneme/word.
        """
        if not errors:
            return []

        # Group by phoneme (prioritize) or word
        by_key: dict[str, list[dict]] = {}
        for error in errors:
            key = error.get("phoneme") or error.get("word", "unknown")
            if key not in by_key:
                by_key[key] = []
            by_key[key].append(error)

        # Take the worst score for each key
        deduplicated = []
        for key, key_errors in by_key.items():
            # Sort by accuracy (lowest first - worst pronunciation)
            key_errors.sort(key=lambda e: e.get("accuracy_score", 100))
            best = key_errors[0].copy()
            best["occurrence_count"] = len(key_errors)
            # Calculate average accuracy across occurrences
            avg_accuracy = sum(e.get("accuracy_score", 0) for e in key_errors) / len(key_errors)
            best["average_accuracy"] = round(avg_accuracy, 1)
            deduplicated.append(best)

        # Sort by accuracy (worst first for higher priority)
        deduplicated.sort(key=lambda e: e.get("average_accuracy", 100))

        return deduplicated

    async def _create_grammar_activity(
        self,
        user_id: str,
        error: dict,
        session_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a grammar corrective activity.
        """
        try:
            activity_id = f"activity_{user_id}_{datetime.utcnow().timestamp()}"

            activity_data = {
                "id": activity_id,
                "userId": user_id,
                "partitionKey": user_id,
                "sourceSessionId": session_id,
                "sourceTurnNumber": error.get("turn_number", 0),
                "sourceErrorType": ErrorType.GRAMMAR.value,
                "pillar": "grammar",
                "activityType": "grammar_correction",
                "grammarRule": error.get("rule"),
                "incorrectExample": error.get("incorrect_text"),
                "correctExample": error.get("correction"),
                "explanation": error.get("explanation"),
                "occurrenceCount": error.get("occurrence_count", 1),
                "status": "pending",
                "priority": GRAMMAR_PRIORITY + min(error.get("occurrence_count", 1), 5),
                "createdAt": datetime.utcnow().isoformat(),
                "updatedAt": datetime.utcnow().isoformat()
            }

            await self.db_service.create_activity(user_id, activity_data)
            self.log_debug(f"Created grammar activity: {activity_id} for rule: {error.get('rule')}")
            return activity_id

        except Exception as e:
            self.log_error(e, {"context": "create_grammar_activity"})
            return None

    async def _create_pronunciation_activity(
        self,
        user_id: str,
        error: dict,
        session_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a pronunciation corrective activity.
        """
        try:
            activity_id = f"activity_{user_id}_{datetime.utcnow().timestamp()}"

            activity_data = {
                "id": activity_id,
                "userId": user_id,
                "partitionKey": user_id,
                "sourceSessionId": session_id,
                "sourceTurnNumber": error.get("turn_number", 0),
                "sourceErrorType": ErrorType.PRONUNCIATION.value,
                "pillar": "pronunciation",
                "activityType": "pronunciation_practice",
                "targetPhoneme": error.get("phoneme"),
                "targetWord": error.get("word"),
                "accuracyScore": error.get("accuracy_score"),
                "averageAccuracy": error.get("average_accuracy"),
                "occurrenceCount": error.get("occurrence_count", 1),
                "status": "pending",
                "priority": PRONUNCIATION_PRIORITY + min(error.get("occurrence_count", 1), 5),
                "createdAt": datetime.utcnow().isoformat(),
                "updatedAt": datetime.utcnow().isoformat()
            }

            await self.db_service.create_activity(user_id, activity_data)
            self.log_debug(f"Created pronunciation activity: {activity_id} for phoneme: {error.get('phoneme')}")
            return activity_id

        except Exception as e:
            self.log_error(e, {"context": "create_pronunciation_activity"})
            return None

    # ==================== PUBLIC HELPER METHODS ====================

    async def get_pending_corrective_activities(
        self,
        user_id: str,
        pillar: Optional[str] = None,
        limit: int = 10
    ) -> list[dict]:
        """
        Get pending corrective activities for a user.

        Args:
            user_id: User ID
            pillar: Filter by pillar (grammar/pronunciation) or None for all
            limit: Maximum number of activities to return

        Returns:
            List of pending activity dictionaries
        """
        try:
            activities = await self.db_service.get_pending_activities(user_id, pillar)

            # Sort by priority (higher first)
            activities.sort(key=lambda a: a.get("priority", 0), reverse=True)

            return activities[:limit]

        except Exception as e:
            self.log_error(e, {"context": "get_pending_corrective_activities"})
            return []

    async def get_activities_from_session(
        self,
        user_id: str,
        session_id: str
    ) -> list[dict]:
        """
        Get all corrective activities generated from a specific session.
        """
        try:
            query = """
                SELECT * FROM c
                WHERE c.partitionKey = @user_id
                AND c.sourceSessionId = @session_id
                ORDER BY c.priority DESC
            """
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@session_id", "value": session_id}
            ]

            activities = await self.db_service.query_items(
                "activities",
                query,
                parameters,
                user_id
            )

            return activities

        except Exception as e:
            self.log_error(e, {"context": "get_activities_from_session"})
            return []

    async def mark_activity_completed(
        self,
        user_id: str,
        activity_id: str,
        result: Optional[dict] = None
    ) -> bool:
        """
        Mark a corrective activity as completed.
        """
        try:
            await self.db_service.complete_activity(
                user_id,
                activity_id,
                result or {"completed_at": datetime.utcnow().isoformat()}
            )
            self.log_debug(f"Marked activity {activity_id} as completed")
            return True

        except Exception as e:
            self.log_error(e, {"context": "mark_activity_completed"})
            return False

    async def get_error_statistics(self, user_id: str) -> dict:
        """
        Get statistics about user's errors and corrective activities.
        """
        try:
            # Get all activities
            all_activities = await self.db_service.query_items(
                "activities",
                """
                SELECT c.pillar, c.status, c.grammarRule, c.targetPhoneme,
                       c.occurrenceCount, c.createdAt
                FROM c
                WHERE c.partitionKey = @user_id
                """,
                [{"name": "@user_id", "value": user_id}],
                user_id
            )

            if not all_activities:
                return {
                    "total_activities": 0,
                    "pending_activities": 0,
                    "completed_activities": 0,
                    "grammar_activities": 0,
                    "pronunciation_activities": 0,
                    "most_common_grammar_errors": [],
                    "most_common_pronunciation_issues": []
                }

            pending = sum(1 for a in all_activities if a.get("status") == "pending")
            completed = sum(1 for a in all_activities if a.get("status") == "completed")
            grammar = [a for a in all_activities if a.get("pillar") == "grammar"]
            pronunciation = [a for a in all_activities if a.get("pillar") == "pronunciation"]

            # Count grammar rules
            grammar_rules = {}
            for a in grammar:
                rule = a.get("grammarRule", "unknown")
                grammar_rules[rule] = grammar_rules.get(rule, 0) + a.get("occurrenceCount", 1)

            # Count phonemes
            phonemes = {}
            for a in pronunciation:
                phoneme = a.get("targetPhoneme", "unknown")
                phonemes[phoneme] = phonemes.get(phoneme, 0) + a.get("occurrenceCount", 1)

            return {
                "total_activities": len(all_activities),
                "pending_activities": pending,
                "completed_activities": completed,
                "grammar_activities": len(grammar),
                "pronunciation_activities": len(pronunciation),
                "most_common_grammar_errors": sorted(
                    grammar_rules.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5],
                "most_common_pronunciation_issues": sorted(
                    phonemes.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
            }

        except Exception as e:
            self.log_error(e, {"context": "get_error_statistics"})
            return {}


# Singleton instance
error_integration_agent = ErrorIntegrationAgent()
