"""
Grammar Agent
Manages grammar learning with active learning methodology.

Responsibilities:
- Present grammar rules with PT-EN comparison
- Evaluate user explanations via GPT-4
- Generate contextual grammar exercises
- Track progress and mastery levels using SRS
"""
import json
import logging
import random
from datetime import datetime
from typing import Optional

from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.state import AppState, add_agent_message
from app.config import Settings, get_settings
from app.models.grammar import (
    GrammarRule,
    GrammarProgress,
    GrammarSRSData,
    GrammarExercise,
    GrammarExerciseResult,
    UserExplanation
)
from app.utils.srs_algorithm import (
    SRSAlgorithm,
    calculate_next_review,
    should_review_low_frequency
)


logger = logging.getLogger(__name__)


# Minimum score to consider a grammar rule explanation acceptable
MIN_EXPLANATION_SCORE = 70.0

# Minimum score to consider a grammar rule mastered
MASTERY_THRESHOLD = 85.0


class GrammarAgent(BaseAgent[AppState]):
    """
    Grammar Agent - Manages grammar learning with active learning methodology.

    Features:
    - Presents grammar rules with Portuguese comparison
    - Validates user explanations via GPT-4
    - Generates practice exercises
    - Tracks progress using SRS algorithm
    """

    def __init__(self, settings: Settings | None = None):
        super().__init__(settings=settings)
        self.srs = SRSAlgorithm()
        self._rules_cache: dict[str, dict] = {}
        self._rules_by_category: dict[str, list[dict]] = {}

    @property
    def name(self) -> str:
        return "grammar"

    @property
    def description(self) -> str:
        return "Manages grammar learning with PT-EN comparison and active explanations"

    async def process(self, state: AppState) -> AppState:
        """
        Process grammar request.

        Handles:
        - grammar_lesson: Present a grammar rule for study
        - grammar_exercise: Generate and serve exercises for a rule
        """
        self.log_start({
            "user_id": state["user"]["user_id"],
            "request_type": state.get("request_type")
        })

        try:
            request_type = state.get("request_type")
            activity_input = state.get("activity_input", {})

            if request_type == "grammar_lesson":
                # Check if submitting an explanation or requesting new lesson
                if activity_input.get("explanation"):
                    state = await self._process_explanation(state)
                else:
                    state = await self._generate_lesson(state)

            elif request_type == "grammar_exercise":
                # Check if submitting an answer or requesting exercises
                if activity_input.get("answer"):
                    state = await self._process_exercise_answer(state)
                else:
                    state = await self._generate_exercises(state)

            else:
                state["response"] = {
                    "error": f"Unknown grammar request type: {request_type}"
                }
                state["has_error"] = True

            self.log_complete({"has_error": state.get("has_error", False)})
            return state

        except Exception as e:
            self.log_error(e)
            state["has_error"] = True
            state["error_message"] = f"Grammar agent error: {str(e)}"
            state["response"] = {"error": str(e)}
            return state

    async def _generate_lesson(self, state: AppState) -> AppState:
        """Generate a grammar lesson for the user."""
        user_id = state["user"]["user_id"]
        user_level = state["user"].get("current_level", "beginner")
        activity_input = state.get("activity_input", {})

        # Check if specific rule requested
        requested_rule_id = activity_input.get("rule_id")
        requested_category = activity_input.get("category")

        # Select rule for lesson
        rule_data = await self._select_rule(
            user_id=user_id,
            level=user_level,
            rule_id=requested_rule_id,
            category=requested_category
        )

        if not rule_data:
            state["response"] = {
                "type": "grammar_lesson",
                "status": "no_rules",
                "message": "Parabéns! Você estudou todas as regras disponíveis para seu nível."
            }
            return state

        # Get user's progress for this rule
        user_progress = await self._get_user_progress(user_id, rule_data["id"])

        # Build comparison data
        comparison = {
            "exists_in_portuguese": rule_data.get("exists_in_portuguese", True),
            "portuguese_equivalent": rule_data.get("portuguese_equivalent"),
            "similarities": rule_data.get("similarities", []),
            "differences": rule_data.get("differences", [])
        }

        # Store current activity in state
        state["current_activity"] = {
            "activity_id": f"grammar_{user_id}_{datetime.utcnow().timestamp()}",
            "activity_type": "grammar_lesson",
            "pillar": "grammar",
            "content": {
                "rule_id": rule_data["id"],
                "rule_name": rule_data["name"]
            },
            "started_at": datetime.utcnow().isoformat(),
            "status": "in_progress"
        }

        # Prepare response
        state["response"] = {
            "type": "grammar_lesson",
            "status": "success",
            "activity_id": state["current_activity"]["activity_id"],
            "rule": {
                "id": rule_data["id"],
                "name": rule_data["name"],
                "category": rule_data.get("category", "other"),
                "difficulty": rule_data.get("difficulty", "beginner"),
                "english_explanation": rule_data.get("english_explanation", ""),
                "portuguese_explanation": rule_data.get("portuguese_explanation", ""),
                "comparison": comparison,
                "common_mistakes": rule_data.get("common_mistakes", []),
                "memory_tips": rule_data.get("memory_tips", []),
                "examples": rule_data.get("examples", []),
                "common_errors": rule_data.get("common_errors", [])
            },
            "user_progress": {
                "practice_count": user_progress.get("practiceCount", 0) if user_progress else 0,
                "best_explanation_score": user_progress.get("bestExplanationScore", 0) if user_progress else 0,
                "mastery_level": user_progress.get("masteryLevel", "not_started") if user_progress else "not_started",
                "last_practiced": user_progress.get("lastPracticed") if user_progress else None
            }
        }

        state = add_agent_message(
            state,
            self.name,
            f"Generated grammar lesson for rule: {rule_data['name']}"
        )

        return state

    async def _process_explanation(self, state: AppState) -> AppState:
        """Process and evaluate user's explanation of a grammar rule."""
        user_id = state["user"]["user_id"]
        activity_input = state.get("activity_input", {})
        current_activity = state.get("current_activity", {})

        # Extract data
        user_explanation = activity_input.get("explanation", "")
        rule_id = activity_input.get("rule_id") or current_activity.get("content", {}).get("rule_id")

        if not rule_id:
            state["response"] = {
                "type": "grammar_explanation",
                "status": "error",
                "message": "ID da regra não encontrado."
            }
            state["has_error"] = True
            return state

        if not user_explanation or len(user_explanation.strip()) < 10:
            state["response"] = {
                "type": "grammar_explanation",
                "status": "error",
                "message": "Explicação muito curta. Por favor, explique a regra com mais detalhes."
            }
            state["has_error"] = True
            return state

        # Get rule data
        rule_data = await self._get_rule_by_id(rule_id)
        if not rule_data:
            state["response"] = {
                "type": "grammar_explanation",
                "status": "error",
                "message": "Regra gramatical não encontrada."
            }
            state["has_error"] = True
            return state

        # Evaluate explanation via GPT-4
        evaluation = await self._evaluate_explanation(
            rule_name=rule_data["name"],
            rule_description=rule_data.get("english_explanation", ""),
            user_explanation=user_explanation
        )

        if not evaluation:
            state["response"] = {
                "type": "grammar_explanation",
                "status": "error",
                "message": "Erro ao avaliar explicação. Tente novamente."
            }
            state["has_error"] = True
            return state

        overall_score = evaluation.get("overall_score", 0)
        passed = overall_score >= MIN_EXPLANATION_SCORE

        # Calculate quality for SRS based on score
        quality = self._score_to_quality(overall_score)

        # Update progress
        progress_update = await self._update_progress(
            user_id=user_id,
            rule_id=rule_id,
            rule_name=rule_data["name"],
            explanation=user_explanation,
            evaluation=evaluation,
            quality=quality
        )

        # Mark activity as completed
        if current_activity:
            state["current_activity"]["status"] = "completed"
            state["current_activity"]["result"] = {
                "passed": passed,
                "score": overall_score,
                "quality": quality
            }

        # Store activity output for progress agent
        state["activity_output"] = {
            "pillar": "grammar",
            "rule_id": rule_id,
            "correct": passed,
            "quality": quality,
            "score": overall_score,
            "srs_update": progress_update.get("srs_data", {})
        }

        # Prepare response
        state["response"] = {
            "type": "grammar_explanation",
            "status": "success",
            "rule_id": rule_id,
            "rule_name": rule_data["name"],
            "evaluation": evaluation,
            "passed": passed,
            "mastery_level": progress_update.get("mastery_level"),
            "next_review_days": progress_update.get("next_review_days")
        }

        state = add_agent_message(
            state,
            self.name,
            f"Evaluated explanation for rule: {rule_data['name']}, score: {overall_score}"
        )

        return state

    async def _generate_exercises(self, state: AppState) -> AppState:
        """Generate grammar exercises for a rule."""
        user_id = state["user"]["user_id"]
        user_level = state["user"].get("current_level", "beginner")
        activity_input = state.get("activity_input", {})

        rule_id = activity_input.get("rule_id")
        count = activity_input.get("count", 5)

        if not rule_id:
            state["response"] = {
                "type": "grammar_exercises",
                "status": "error",
                "message": "ID da regra é obrigatório para gerar exercícios."
            }
            state["has_error"] = True
            return state

        # Get rule data
        rule_data = await self._get_rule_by_id(rule_id)
        if not rule_data:
            state["response"] = {
                "type": "grammar_exercises",
                "status": "error",
                "message": "Regra gramatical não encontrada."
            }
            state["has_error"] = True
            return state

        # Generate exercises via GPT-4
        exercises = await self._create_exercises(
            rule_name=rule_data["name"],
            rule_description=rule_data.get("english_explanation", ""),
            level=user_level,
            count=count
        )

        if not exercises:
            # Fallback to exercises from rule data
            exercises = self._create_fallback_exercises(rule_data)

        # Store current activity
        state["current_activity"] = {
            "activity_id": f"grammar_ex_{user_id}_{datetime.utcnow().timestamp()}",
            "activity_type": "grammar_exercise",
            "pillar": "grammar",
            "content": {
                "rule_id": rule_id,
                "rule_name": rule_data["name"],
                "exercises": exercises,
                "current_index": 0,
                "correct_count": 0
            },
            "started_at": datetime.utcnow().isoformat(),
            "status": "in_progress"
        }

        # Format exercises for response
        formatted_exercises = []
        for i, ex in enumerate(exercises):
            formatted_exercises.append({
                "index": i,
                "type": ex.get("type", "fill_in_blank"),
                "instruction": ex.get("instruction", "Complete the sentence"),
                "sentence": ex.get("sentence", ""),
                "options": ex.get("options")
            })

        state["response"] = {
            "type": "grammar_exercises",
            "status": "success",
            "activity_id": state["current_activity"]["activity_id"],
            "rule_id": rule_id,
            "rule_name": rule_data["name"],
            "exercises": formatted_exercises,
            "total_exercises": len(exercises)
        }

        state = add_agent_message(
            state,
            self.name,
            f"Generated {len(exercises)} exercises for rule: {rule_data['name']}"
        )

        return state

    async def _process_exercise_answer(self, state: AppState) -> AppState:
        """Process user's answer to a grammar exercise."""
        user_id = state["user"]["user_id"]
        activity_input = state.get("activity_input", {})
        current_activity = state.get("current_activity", {})

        user_answer = activity_input.get("answer")
        exercise_index = activity_input.get("exercise_index", 0)
        response_time_ms = activity_input.get("response_time_ms", 5000)
        rule_id = activity_input.get("rule_id") or current_activity.get("content", {}).get("rule_id")

        if not rule_id:
            state["response"] = {
                "type": "grammar_exercise_answer",
                "status": "error",
                "message": "ID da regra não encontrado."
            }
            state["has_error"] = True
            return state

        # Get exercise data
        exercises = current_activity.get("content", {}).get("exercises", [])
        if exercise_index >= len(exercises):
            state["response"] = {
                "type": "grammar_exercise_answer",
                "status": "error",
                "message": "Índice de exercício inválido."
            }
            state["has_error"] = True
            return state

        exercise = exercises[exercise_index]
        correct_answer = exercise.get("correct_answer")
        correct_index = exercise.get("correct_index")

        # Check answer
        is_correct = self._check_answer(user_answer, correct_answer, correct_index)

        # Update activity tracking
        current_index = current_activity.get("content", {}).get("current_index", 0)
        correct_count = current_activity.get("content", {}).get("correct_count", 0)

        if is_correct:
            correct_count += 1

        state["current_activity"]["content"]["current_index"] = exercise_index + 1
        state["current_activity"]["content"]["correct_count"] = correct_count

        # Check if all exercises completed
        all_completed = (exercise_index + 1) >= len(exercises)

        if all_completed:
            # Calculate quality based on accuracy
            accuracy = correct_count / len(exercises) if exercises else 0
            quality = self.srs.quality_from_response_time(
                is_correct=accuracy >= 0.6,
                response_time_ms=response_time_ms
            )

            # Update progress
            progress_update = await self._update_exercise_progress(
                user_id=user_id,
                rule_id=rule_id,
                correct_count=correct_count,
                total_count=len(exercises),
                quality=quality
            )

            state["current_activity"]["status"] = "completed"
            state["activity_output"] = {
                "pillar": "grammar",
                "rule_id": rule_id,
                "correct": accuracy >= 0.6,
                "quality": quality,
                "accuracy": accuracy,
                "srs_update": progress_update.get("srs_data", {})
            }

            mastery_level = progress_update.get("mastery_level")
        else:
            mastery_level = None

        state["response"] = {
            "type": "grammar_exercise_answer",
            "status": "success",
            "correct": is_correct,
            "user_answer": str(user_answer),
            "correct_answer": correct_answer,
            "explanation": exercise.get("explanation", ""),
            "exercise_index": exercise_index,
            "exercises_completed": exercise_index + 1,
            "exercises_correct": correct_count,
            "mastery_level": mastery_level
        }

        state = add_agent_message(
            state,
            self.name,
            f"Processed exercise answer for rule: {rule_id}, correct: {is_correct}"
        )

        return state

    async def _select_rule(
        self,
        user_id: str,
        level: str,
        rule_id: Optional[str] = None,
        category: Optional[str] = None
    ) -> Optional[dict]:
        """
        Select a grammar rule for the lesson.

        Priority:
        1. Specific rule if requested
        2. Rules due for SRS review
        3. Rules with low frequency usage
        4. New rules not yet studied
        """
        await self._load_rules()

        # If specific rule requested
        if rule_id:
            return self._rules_cache.get(rule_id)

        try:
            # 1. Check SRS due items
            due_items = await self.db_service.get_grammar_due_for_review(user_id)
            if due_items:
                self.log_debug(f"Found {len(due_items)} grammar rules due for review")
                due_items.sort(key=lambda x: x.get("srsData", {}).get("nextReview", ""))
                due_rule_id = due_items[0].get("ruleId")
                if due_rule_id and due_rule_id in self._rules_cache:
                    return self._rules_cache[due_rule_id]

            # 2. Check low frequency items
            low_freq_items = await self.db_service.get_grammar_low_frequency(user_id)
            if low_freq_items:
                self.log_debug(f"Found {len(low_freq_items)} low frequency grammar rules")
                item = random.choice(low_freq_items)
                rule_id = item.get("ruleId")
                if rule_id and rule_id in self._rules_cache:
                    return self._rules_cache[rule_id]

            # 3. Get new rule
            self.log_debug("Selecting new grammar rule for user")
            return await self._get_new_rule(user_id, level, category)

        except Exception as e:
            self.log_error(e, {"context": "rule_selection"})
            # Fallback: return random rule
            return await self._get_random_rule(level, category)

    async def _get_rule_by_id(self, rule_id: str) -> Optional[dict]:
        """Get grammar rule data by ID."""
        await self._load_rules()
        return self._rules_cache.get(rule_id)

    async def _get_new_rule(
        self,
        user_id: str,
        level: str,
        category: Optional[str] = None
    ) -> Optional[dict]:
        """Get a new rule that the user hasn't studied yet."""
        await self._load_rules()

        # Get user's existing progress
        existing_progress = await self.db_service.get_grammar_progress(user_id)
        studied_rule_ids = {p.get("ruleId") for p in existing_progress} if existing_progress else set()

        # Filter rules by level and optionally category
        available_rules = []
        for rule_id, rule in self._rules_cache.items():
            if rule_id in studied_rule_ids:
                continue
            if rule.get("difficulty") != level and level != "all":
                continue
            if category and rule.get("category") != category:
                continue
            available_rules.append(rule)

        if not available_rules:
            # Try without level filter
            available_rules = [
                r for r_id, r in self._rules_cache.items()
                if r_id not in studied_rule_ids
                and (not category or r.get("category") == category)
            ]

        if not available_rules:
            return None

        # Prioritize rules that don't exist in Portuguese (harder for learners)
        # but start with ones that do exist (easier)
        available_rules.sort(
            key=lambda x: (not x.get("exists_in_portuguese", True), x.get("name", ""))
        )

        return available_rules[0]

    async def _get_random_rule(
        self,
        level: str,
        category: Optional[str] = None
    ) -> Optional[dict]:
        """Get a random rule as fallback."""
        await self._load_rules()

        rules = [
            r for r in self._rules_cache.values()
            if r.get("difficulty") == level or level == "all"
            and (not category or r.get("category") == category)
        ]

        return random.choice(rules) if rules else None

    async def _load_rules(self):
        """Load grammar rules from JSON file."""
        if self._rules_cache:
            return

        try:
            with open("app/data/grammar_rules.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for rule in data.get("rules", []):
                    self._rules_cache[rule["id"]] = rule
                    # Index by category
                    category = rule.get("category", "other")
                    if category not in self._rules_by_category:
                        self._rules_by_category[category] = []
                    self._rules_by_category[category].append(rule)

            self.log_debug(f"Loaded {len(self._rules_cache)} grammar rules")
        except Exception as e:
            self.log_error(e, {"context": "loading grammar_rules"})

    async def _get_user_progress(self, user_id: str, rule_id: str) -> Optional[dict]:
        """Get user's progress for a specific rule."""
        try:
            return await self.db_service.get_grammar_progress(user_id, rule_id)
        except Exception as e:
            self.log_error(e, {"context": "get_user_progress"})
            return None

    async def _evaluate_explanation(
        self,
        rule_name: str,
        rule_description: str,
        user_explanation: str
    ) -> Optional[dict]:
        """Evaluate user's explanation via GPT-4."""
        try:
            evaluation = await self.openai_service.evaluate_grammar_explanation(
                rule_name=rule_name,
                rule_description=rule_description,
                user_explanation=user_explanation,
                language="pt-BR"
            )
            return evaluation
        except Exception as e:
            self.log_error(e, {"context": "evaluate_explanation", "rule": rule_name})
            return None

    async def _create_exercises(
        self,
        rule_name: str,
        rule_description: str,
        level: str,
        count: int
    ) -> list[dict]:
        """Create grammar exercises via GPT-4."""
        try:
            exercises = await self.openai_service.generate_grammar_exercises(
                rule_name=rule_name,
                rule_description=rule_description,
                level=level,
                count=count
            )
            return exercises
        except Exception as e:
            self.log_error(e, {"context": "create_exercises", "rule": rule_name})
            return []

    def _create_fallback_exercises(self, rule_data: dict) -> list[dict]:
        """Create fallback exercises from rule data when GPT-4 fails."""
        exercises = []

        # Create exercises from common_errors in rule data
        common_errors = rule_data.get("common_errors", [])
        for i, error in enumerate(common_errors[:5]):
            exercises.append({
                "type": "error_correction",
                "instruction": "Escolha a forma correta:",
                "sentence": f"Which is correct?",
                "options": [error.get("incorrect", ""), error.get("correct", "")],
                "correct_answer": error.get("correct", ""),
                "correct_index": 1,
                "explanation": error.get("explanation", "")
            })

        # If not enough exercises, add from examples
        examples = rule_data.get("examples", [])
        for example in examples:
            if len(exercises) >= 5:
                break
            english = example.get("english", "")
            # Create a simple fill-in-blank
            words = english.split()
            if len(words) > 2:
                blank_idx = random.randint(1, len(words) - 1)
                correct_word = words[blank_idx]
                words[blank_idx] = "___"
                exercises.append({
                    "type": "fill_in_blank",
                    "instruction": "Complete a frase:",
                    "sentence": " ".join(words),
                    "options": None,
                    "correct_answer": correct_word,
                    "correct_index": None,
                    "explanation": f"A frase correta é: {english}"
                })

        return exercises if exercises else [{
            "type": "fill_in_blank",
            "instruction": "No exercises available",
            "sentence": "Please try again later.",
            "options": None,
            "correct_answer": "",
            "correct_index": None,
            "explanation": ""
        }]

    def _check_answer(
        self,
        user_answer: str,
        correct_answer: str,
        correct_index: Optional[int]
    ) -> bool:
        """Check if user's answer is correct."""
        if user_answer is None:
            return False

        # Check by index if provided
        if correct_index is not None:
            try:
                return int(user_answer) == correct_index
            except (ValueError, TypeError):
                pass

        # Check by text match (case insensitive)
        if correct_answer:
            return user_answer.lower().strip() == correct_answer.lower().strip()

        return False

    def _score_to_quality(self, score: float) -> int:
        """Convert explanation score to SRS quality (0-5)."""
        if score >= 95:
            return 5  # Perfect
        elif score >= 85:
            return 4  # Good
        elif score >= 70:
            return 3  # OK
        elif score >= 50:
            return 2  # Poor
        elif score >= 30:
            return 1  # Bad
        else:
            return 0  # Blackout

    async def _update_progress(
        self,
        user_id: str,
        rule_id: str,
        rule_name: str,
        explanation: str,
        evaluation: dict,
        quality: int
    ) -> dict:
        """Update grammar progress after explanation evaluation."""
        existing = await self.db_service.get_grammar_progress(user_id, rule_id)
        overall_score = evaluation.get("overall_score", 0)

        if existing:
            # Update existing progress
            srs_data = existing.get("srsData", {
                "easeFactor": 2.5,
                "interval": 1,
                "repetitions": 0,
                "nextReview": datetime.utcnow().isoformat()
            })

            new_srs = calculate_next_review(srs_data, quality)

            practice_count = existing.get("practiceCount", 0) + 1
            best_score = max(existing.get("bestExplanationScore", 0), overall_score)

            # Add new explanation to history
            explanations = existing.get("userExplanations", [])
            explanations.append({
                "timestamp": datetime.utcnow().isoformat(),
                "explanation": explanation,
                "evaluation_score": overall_score,
                "feedback": evaluation.get("feedback", ""),
                "missing_points": evaluation.get("missing_points", [])
            })
            # Keep only last 5 explanations
            explanations = explanations[-5:]

            mastery_level = self._calculate_mastery_level(
                repetitions=new_srs["repetitions"],
                best_score=best_score,
                practice_count=practice_count
            )

            progress_data = {
                "id": f"grammar_{user_id}_{rule_id}",
                "userId": user_id,
                "ruleId": rule_id,
                "ruleName": rule_name,
                "partitionKey": user_id,
                "masteryLevel": mastery_level,
                "practiceCount": practice_count,
                "lastPracticed": datetime.utcnow().isoformat(),
                "lastScore": overall_score,
                "bestExplanationScore": best_score,
                "userExplanations": explanations,
                "srsData": new_srs,
                "updatedAt": datetime.utcnow().isoformat()
            }

            await self.db_service.update_grammar_progress(user_id, rule_id, progress_data)

            return {
                "srs_data": new_srs,
                "mastery_level": mastery_level,
                "next_review_days": new_srs["interval"]
            }

        else:
            # Create new progress
            srs_data = calculate_next_review(
                {"easeFactor": 2.5, "interval": 1, "repetitions": 0,
                 "nextReview": datetime.utcnow().isoformat()},
                quality
            )

            mastery_level = "learning" if overall_score >= MIN_EXPLANATION_SCORE else "new"

            progress_data = {
                "id": f"grammar_{user_id}_{rule_id}",
                "userId": user_id,
                "ruleId": rule_id,
                "ruleName": rule_name,
                "partitionKey": user_id,
                "masteryLevel": mastery_level,
                "practiceCount": 1,
                "lastPracticed": datetime.utcnow().isoformat(),
                "lastScore": overall_score,
                "bestExplanationScore": overall_score,
                "userExplanations": [{
                    "timestamp": datetime.utcnow().isoformat(),
                    "explanation": explanation,
                    "evaluation_score": overall_score,
                    "feedback": evaluation.get("feedback", ""),
                    "missing_points": evaluation.get("missing_points", [])
                }],
                "srsData": srs_data,
                "createdAt": datetime.utcnow().isoformat(),
                "updatedAt": datetime.utcnow().isoformat()
            }

            await self.db_service.update_grammar_progress(user_id, rule_id, progress_data)

            return {
                "srs_data": srs_data,
                "mastery_level": mastery_level,
                "next_review_days": srs_data["interval"]
            }

    async def _update_exercise_progress(
        self,
        user_id: str,
        rule_id: str,
        correct_count: int,
        total_count: int,
        quality: int
    ) -> dict:
        """Update progress after completing exercises."""
        existing = await self.db_service.get_grammar_progress(user_id, rule_id)
        accuracy = correct_count / total_count if total_count > 0 else 0

        if existing:
            srs_data = existing.get("srsData", {
                "easeFactor": 2.5,
                "interval": 1,
                "repetitions": 0,
                "nextReview": datetime.utcnow().isoformat()
            })

            new_srs = calculate_next_review(srs_data, quality)
            practice_count = existing.get("practiceCount", 0) + 1
            correct_total = existing.get("correctCount", 0) + correct_count

            mastery_level = self._calculate_mastery_level(
                repetitions=new_srs["repetitions"],
                best_score=existing.get("bestExplanationScore", accuracy * 100),
                practice_count=practice_count
            )

            progress_data = {
                "id": f"grammar_{user_id}_{rule_id}",
                "userId": user_id,
                "ruleId": rule_id,
                "partitionKey": user_id,
                "masteryLevel": mastery_level,
                "practiceCount": practice_count,
                "correctCount": correct_total,
                "lastPracticed": datetime.utcnow().isoformat(),
                "srsData": new_srs,
                "updatedAt": datetime.utcnow().isoformat()
            }

            await self.db_service.update_grammar_progress(user_id, rule_id, progress_data)

            return {
                "srs_data": new_srs,
                "mastery_level": mastery_level,
                "next_review_days": new_srs["interval"]
            }

        else:
            # Shouldn't normally happen - exercises come after lesson
            return {
                "srs_data": {},
                "mastery_level": "learning",
                "next_review_days": 1
            }

    def _calculate_mastery_level(
        self,
        repetitions: int,
        best_score: float,
        practice_count: int
    ) -> str:
        """Calculate mastery level based on SRS repetitions and explanation score."""
        if practice_count == 0:
            return "not_started"

        if repetitions >= 5 and best_score >= MASTERY_THRESHOLD:
            return "mastered"
        elif repetitions >= 2 and best_score >= MIN_EXPLANATION_SCORE:
            return "reviewing"
        elif repetitions >= 1 or best_score >= MIN_EXPLANATION_SCORE:
            return "learning"
        else:
            return "new"

    # ==================== HELPER METHODS FOR EXTERNAL USE ====================

    async def get_user_grammar_stats(self, user_id: str) -> dict:
        """Get grammar statistics for a user."""
        progress = await self.db_service.get_grammar_progress(user_id)
        await self._load_rules()

        if not progress:
            return {
                "total_rules": len(self._rules_cache),
                "mastered": 0,
                "reviewing": 0,
                "learning": 0,
                "not_started": len(self._rules_cache),
                "due_for_review": 0,
                "average_score": 0,
                "best_categories": [],
                "weak_categories": []
            }

        stats = {
            "total_rules": len(self._rules_cache),
            "mastered": sum(1 for p in progress if p.get("masteryLevel") == "mastered"),
            "reviewing": sum(1 for p in progress if p.get("masteryLevel") == "reviewing"),
            "learning": sum(1 for p in progress if p.get("masteryLevel") == "learning"),
            "not_started": 0,
            "due_for_review": 0,
            "average_score": 0,
            "best_categories": [],
            "weak_categories": []
        }

        studied_ids = {p.get("ruleId") for p in progress}
        stats["not_started"] = len(self._rules_cache) - len(studied_ids)

        # Calculate due for review
        due_items = await self.db_service.get_grammar_due_for_review(user_id)
        stats["due_for_review"] = len(due_items) if due_items else 0

        # Calculate average score
        scores = [p.get("bestExplanationScore", 0) for p in progress if p.get("bestExplanationScore")]
        stats["average_score"] = round(sum(scores) / len(scores), 1) if scores else 0

        # Analyze categories
        category_scores = {}
        for p in progress:
            rule_id = p.get("ruleId")
            rule = self._rules_cache.get(rule_id)
            if rule:
                category = rule.get("category", "other")
                if category not in category_scores:
                    category_scores[category] = []
                category_scores[category].append(p.get("bestExplanationScore", 0))

        # Find best and weak categories
        category_avgs = {
            cat: sum(scores) / len(scores) if scores else 0
            for cat, scores in category_scores.items()
        }

        if category_avgs:
            sorted_cats = sorted(category_avgs.items(), key=lambda x: x[1], reverse=True)
            stats["best_categories"] = [c[0] for c in sorted_cats[:3] if c[1] >= 70]
            stats["weak_categories"] = [c[0] for c in sorted_cats[-3:] if c[1] < 70]

        return stats

    async def get_rules_to_review(self, user_id: str, limit: int = 10) -> list:
        """Get list of rules due for review."""
        due_items = await self.db_service.get_grammar_due_for_review(user_id)

        if not due_items:
            return []

        await self._load_rules()

        due_items.sort(key=lambda x: x.get("srsData", {}).get("nextReview", ""))

        result = []
        for item in due_items[:limit]:
            rule_id = item.get("ruleId")
            rule_data = self._rules_cache.get(rule_id)
            if rule_data:
                result.append({
                    "rule_id": rule_id,
                    "rule_name": rule_data.get("name"),
                    "category": rule_data.get("category"),
                    "difficulty": rule_data.get("difficulty"),
                    "mastery_level": item.get("masteryLevel"),
                    "last_practiced": item.get("lastPracticed"),
                    "best_explanation_score": item.get("bestExplanationScore", 0)
                })

        return result

    async def get_all_rules(
        self,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> list[dict]:
        """Get all grammar rules with optional user progress."""
        await self._load_rules()

        rules = list(self._rules_cache.values())

        # Filter by category
        if category:
            rules = [r for r in rules if r.get("category") == category]

        # Filter by difficulty
        if difficulty:
            rules = [r for r in rules if r.get("difficulty") == difficulty]

        # Add user progress if user_id provided
        if user_id:
            progress_list = await self.db_service.get_grammar_progress(user_id)
            progress_map = {p.get("ruleId"): p for p in progress_list} if progress_list else {}

            for rule in rules:
                progress = progress_map.get(rule["id"])
                if progress:
                    rule["user_mastery_level"] = progress.get("masteryLevel")
                    rule["user_practice_count"] = progress.get("practiceCount")
                    rule["user_best_score"] = progress.get("bestExplanationScore")
                else:
                    rule["user_mastery_level"] = None
                    rule["user_practice_count"] = None
                    rule["user_best_score"] = None

        return rules

    def get_available_categories(self) -> list[str]:
        """Get list of available grammar categories."""
        return list(self._rules_by_category.keys())


# Singleton instance
grammar_agent = GrammarAgent()
