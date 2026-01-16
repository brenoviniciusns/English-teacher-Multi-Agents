"""
Vocabulary Agent
Manages vocabulary learning with Spaced Repetition System (SRS).

Responsibilities:
- Select words for practice based on SRS and frequency
- Generate contextual exercises via Azure OpenAI
- Process user answers and update progress
- Track mastery levels and usage patterns
"""
import json
import logging
import random
from datetime import datetime
from typing import Optional

from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.state import AppState, add_agent_message
from app.config import Settings, get_settings
from app.models.vocabulary import (
    VocabularyWord,
    VocabularyProgress,
    VocabularyExercise,
    VocabularyExerciseResult,
    MasteryLevel,
    SRSData
)
from app.utils.srs_algorithm import (
    SRSAlgorithm,
    SRSData as SRSDataUtil,
    calculate_next_review,
    should_review_low_frequency
)


logger = logging.getLogger(__name__)


class VocabularyAgent(BaseAgent[AppState]):
    """
    Vocabulary Agent - Manages vocabulary learning with SRS.

    Features:
    - Selects words based on SRS due dates and usage frequency
    - Generates contextualized exercises via GPT-4
    - Tracks progress and updates mastery levels
    - Supports different contexts (general, data_engineering, ai)
    """

    def __init__(self, settings: Settings | None = None):
        super().__init__(settings=settings)
        self.srs = SRSAlgorithm()
        self._words_cache: dict = {}
        self._technical_words_cache: dict = {}

    @property
    def name(self) -> str:
        return "vocabulary"

    @property
    def description(self) -> str:
        return "Manages vocabulary learning with SRS and contextual exercises"

    async def process(self, state: AppState) -> AppState:
        """
        Process vocabulary request.

        Handles:
        - vocabulary_exercise: Generate and serve an exercise
        - submit_answer: Process user's answer
        """
        self.log_start({
            "user_id": state["user"]["user_id"],
            "request_type": state.get("request_type")
        })

        try:
            request_type = state.get("request_type")
            activity_input = state.get("activity_input", {})

            if request_type == "vocabulary_exercise":
                # Check if submitting an answer or requesting new exercise
                if activity_input.get("answer"):
                    state = await self._process_answer(state)
                else:
                    state = await self._generate_exercise(state)
            else:
                # Unknown request type
                state["response"] = {
                    "error": f"Unknown vocabulary request type: {request_type}"
                }
                state["has_error"] = True

            self.log_complete({"has_error": state.get("has_error", False)})
            return state

        except Exception as e:
            self.log_error(e)
            state["has_error"] = True
            state["error_message"] = f"Vocabulary agent error: {str(e)}"
            state["response"] = {"error": str(e)}
            return state

    async def _generate_exercise(self, state: AppState) -> AppState:
        """Generate a vocabulary exercise for the user."""
        user_id = state["user"]["user_id"]
        user_level = state["user"].get("current_level", "beginner")
        learning_goals = state["user"].get("learning_goals", ["general"])

        # Determine context based on learning goals
        context = self._determine_context(learning_goals)

        # Select word for exercise
        word_data = await self._select_word(user_id, user_level, context)

        if not word_data:
            state["response"] = {
                "type": "vocabulary_exercise",
                "status": "no_words",
                "message": "Parabéns! Você completou todas as palavras disponíveis."
            }
            return state

        # Generate exercise via GPT-4
        exercise = await self._create_exercise(word_data, user_level, context)

        if not exercise:
            state["response"] = {
                "type": "vocabulary_exercise",
                "status": "error",
                "message": "Erro ao gerar exercício. Tente novamente."
            }
            state["has_error"] = True
            return state

        # Store current activity in state
        state["current_activity"] = {
            "activity_id": f"vocab_{user_id}_{datetime.utcnow().timestamp()}",
            "activity_type": "vocabulary_exercise",
            "pillar": "vocabulary",
            "content": {
                "word_id": word_data["id"],
                "word": word_data["word"],
                "exercise": exercise
            },
            "started_at": datetime.utcnow().isoformat(),
            "status": "in_progress"
        }

        # Prepare response
        state["response"] = {
            "type": "vocabulary_exercise",
            "status": "success",
            "activity_id": state["current_activity"]["activity_id"],
            "word_id": word_data["id"],
            "word": word_data["word"],
            "part_of_speech": word_data.get("part_of_speech"),
            "ipa_pronunciation": word_data.get("ipa_pronunciation"),
            "exercise": {
                "type": "fill_in_blank",
                "sentence": exercise.get("sentence"),
                "options": exercise.get("options", []),
                "context": context
            }
        }

        state = add_agent_message(
            state,
            self.name,
            f"Generated vocabulary exercise for word: {word_data['word']}"
        )

        return state

    async def _process_answer(self, state: AppState) -> AppState:
        """Process user's answer to vocabulary exercise."""
        user_id = state["user"]["user_id"]
        activity_input = state.get("activity_input", {})
        current_activity = state.get("current_activity", {})

        # Extract answer data
        user_answer = activity_input.get("answer")
        response_time_ms = activity_input.get("response_time_ms", 5000)
        word_id = activity_input.get("word_id") or current_activity.get("content", {}).get("word_id")

        if not word_id:
            state["response"] = {
                "type": "vocabulary_answer",
                "status": "error",
                "message": "ID da palavra não encontrado."
            }
            state["has_error"] = True
            return state

        # Get exercise data
        exercise_data = current_activity.get("content", {}).get("exercise", {})
        correct_answer = exercise_data.get("correct_answer")
        correct_index = exercise_data.get("correct_index")

        # Check if answer is correct
        is_correct = self._check_answer(user_answer, correct_answer, correct_index)

        # Calculate quality response for SRS
        quality = self.srs.quality_from_response_time(
            is_correct=is_correct,
            response_time_ms=response_time_ms
        )

        # Update progress
        progress_update = await self._update_progress(
            user_id=user_id,
            word_id=word_id,
            word=current_activity.get("content", {}).get("word", ""),
            is_correct=is_correct,
            quality=quality,
            response_time_ms=response_time_ms
        )

        # Mark activity as completed
        state["current_activity"]["status"] = "completed"
        state["current_activity"]["result"] = {
            "correct": is_correct,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "quality": quality
        }

        # Store activity output for progress agent
        state["activity_output"] = {
            "pillar": "vocabulary",
            "word_id": word_id,
            "correct": is_correct,
            "quality": quality,
            "response_time_ms": response_time_ms,
            "srs_update": progress_update.get("srs_data", {})
        }

        # Prepare response
        state["response"] = {
            "type": "vocabulary_answer",
            "status": "success",
            "correct": is_correct,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "explanation": exercise_data.get("explanation", ""),
            "example_usage": exercise_data.get("example_usage", ""),
            "mastery_level": progress_update.get("mastery_level"),
            "next_review_days": progress_update.get("next_review_days"),
            "streak": progress_update.get("streak", 0)
        }

        state = add_agent_message(
            state,
            self.name,
            f"Processed answer for word: {word_id}, correct: {is_correct}"
        )

        return state

    async def _select_word(
        self,
        user_id: str,
        level: str,
        context: str
    ) -> Optional[dict]:
        """
        Select a word for the exercise based on SRS and usage.

        Priority:
        1. Words due for SRS review (overdue first)
        2. Words with low frequency usage (not used in 7 days)
        3. New words (not yet learned)
        """
        # Get user's vocabulary progress
        try:
            # 1. Check SRS due items
            due_items = await self.db_service.get_vocabulary_due_for_review(user_id)
            if due_items:
                self.log_debug(f"Found {len(due_items)} SRS due items")
                # Sort by most overdue first
                due_items.sort(key=lambda x: x.get("srsData", {}).get("nextReview", ""))
                # Get the word data for the first due item
                word_id = due_items[0].get("wordId")
                return await self._get_word_by_id(word_id, context)

            # 2. Check low frequency items
            low_freq_items = await self.db_service.get_vocabulary_low_frequency(user_id)
            if low_freq_items:
                self.log_debug(f"Found {len(low_freq_items)} low frequency items")
                # Pick random from low frequency
                item = random.choice(low_freq_items)
                word_id = item.get("wordId")
                return await self._get_word_by_id(word_id, context)

            # 3. Get new word
            self.log_debug("Selecting new word for user")
            return await self._get_new_word(user_id, level, context)

        except Exception as e:
            self.log_error(e, {"context": "word_selection"})
            # Fallback: return random word from cache
            return await self._get_random_word(level, context)

    async def _get_word_by_id(self, word_id: str, context: str) -> Optional[dict]:
        """Get word data by ID from cache or data files."""
        # Load words if not cached
        await self._load_words()

        # Check common words
        if word_id in self._words_cache:
            return self._words_cache[word_id]

        # Check technical words
        if word_id in self._technical_words_cache:
            return self._technical_words_cache[word_id]

        return None

    async def _get_new_word(
        self,
        user_id: str,
        level: str,
        context: str
    ) -> Optional[dict]:
        """Get a new word that the user hasn't learned yet."""
        await self._load_words()

        # Get user's existing progress
        existing_progress = await self.db_service.get_vocabulary_progress(user_id)
        learned_word_ids = {p.get("wordId") for p in existing_progress} if existing_progress else set()

        # Determine which words to consider
        if context in ["data_engineering", "ai", "technology"]:
            # Prefer technical words
            available_words = [
                w for w_id, w in self._technical_words_cache.items()
                if w_id not in learned_word_ids
                and w.get("subcategory") in [context, "programming", "cloud"]
            ]
            # If no technical words available, fall back to common
            if not available_words:
                available_words = [
                    w for w_id, w in self._words_cache.items()
                    if w_id not in learned_word_ids
                    and w.get("difficulty") == level
                ]
        else:
            # Use common words filtered by level
            available_words = [
                w for w_id, w in self._words_cache.items()
                if w_id not in learned_word_ids
                and w.get("difficulty") == level
            ]

        if not available_words:
            # All words learned at this level, try any level
            available_words = [
                w for w_id, w in self._words_cache.items()
                if w_id not in learned_word_ids
            ]

        if not available_words:
            return None

        # Select word with lower frequency rank (more common = lower rank)
        available_words.sort(key=lambda x: x.get("frequency_rank", 9999))
        return available_words[0]

    async def _get_random_word(self, level: str, context: str) -> Optional[dict]:
        """Get a random word as fallback."""
        await self._load_words()

        if context in ["data_engineering", "ai", "technology"]:
            words = list(self._technical_words_cache.values())
        else:
            words = [w for w in self._words_cache.values() if w.get("difficulty") == level]

        return random.choice(words) if words else None

    async def _load_words(self):
        """Load vocabulary words from JSON files."""
        if not self._words_cache:
            try:
                with open("app/data/common_words_2000.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for word in data.get("words", []):
                        self._words_cache[word["id"]] = word
                self.log_debug(f"Loaded {len(self._words_cache)} common words")
            except Exception as e:
                self.log_error(e, {"context": "loading common_words"})

        if not self._technical_words_cache:
            try:
                with open("app/data/technical_vocabulary.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for word in data.get("words", []):
                        self._technical_words_cache[word["id"]] = word
                self.log_debug(f"Loaded {len(self._technical_words_cache)} technical words")
            except Exception as e:
                self.log_error(e, {"context": "loading technical_vocabulary"})

    async def _create_exercise(
        self,
        word_data: dict,
        level: str,
        context: str
    ) -> Optional[dict]:
        """Create vocabulary exercise using Azure OpenAI."""
        try:
            exercise = await self.openai_service.generate_vocabulary_exercise(
                word=word_data["word"],
                word_definition=word_data["definition"],
                level=level,
                context=context
            )
            return exercise
        except Exception as e:
            self.log_error(e, {"context": "exercise_generation", "word": word_data["word"]})
            # Fallback: create simple exercise from word data
            return self._create_fallback_exercise(word_data)

    def _create_fallback_exercise(self, word_data: dict) -> dict:
        """Create a simple exercise when GPT-4 fails."""
        word = word_data["word"]
        sentence = word_data.get("example_sentence", f"Please use the word ___ in a sentence.")
        sentence = sentence.replace(word, "___")

        # Create distractors (simple approach)
        distractors = ["something", "anything", "nothing"]
        options = [word] + distractors[:3]
        random.shuffle(options)

        return {
            "sentence": sentence,
            "options": options,
            "correct_answer": word,
            "correct_index": options.index(word),
            "explanation": word_data.get("definition", ""),
            "example_usage": word_data.get("example_sentence", "")
        }

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

        # Check by text match
        return user_answer.lower().strip() == correct_answer.lower().strip()

    async def _update_progress(
        self,
        user_id: str,
        word_id: str,
        word: str,
        is_correct: bool,
        quality: int,
        response_time_ms: int
    ) -> dict:
        """Update vocabulary progress for a word."""
        # Get existing progress
        existing = await self.db_service.get_vocabulary_progress(user_id, word_id)

        if existing:
            # Update existing progress
            srs_data = existing.get("srsData", {
                "easeFactor": 2.5,
                "interval": 1,
                "repetitions": 0,
                "nextReview": datetime.utcnow().isoformat()
            })

            # Calculate new SRS values
            new_srs = calculate_next_review(srs_data, quality)

            # Update counts
            practice_count = existing.get("practiceCount", 0) + 1
            correct_count = existing.get("correctCount", 0) + (1 if is_correct else 0)

            # Determine mastery level
            mastery_level = self._calculate_mastery_level(
                repetitions=new_srs["repetitions"],
                correct_count=correct_count,
                practice_count=practice_count
            )

            # Update progress
            progress_data = {
                "id": f"vocab_{user_id}_{word_id}",
                "userId": user_id,
                "wordId": word_id,
                "word": word,
                "masteryLevel": mastery_level,
                "practiceCount": practice_count,
                "correctCount": correct_count,
                "lastPracticed": datetime.utcnow().isoformat(),
                "srsData": new_srs,
                "averageResponseTimeMs": int(
                    (existing.get("averageResponseTimeMs", response_time_ms) + response_time_ms) / 2
                )
            }

            await self.db_service.update_vocabulary_progress(user_id, word_id, progress_data)

            return {
                "srs_data": new_srs,
                "mastery_level": mastery_level,
                "next_review_days": new_srs["interval"],
                "streak": new_srs["repetitions"]
            }

        else:
            # Create new progress
            srs_data = calculate_next_review(
                {"easeFactor": 2.5, "interval": 1, "repetitions": 0, "nextReview": datetime.utcnow().isoformat()},
                quality
            )

            mastery_level = "new" if not is_correct else "learning"

            progress_data = {
                "id": f"vocab_{user_id}_{word_id}",
                "userId": user_id,
                "wordId": word_id,
                "word": word,
                "masteryLevel": mastery_level,
                "practiceCount": 1,
                "correctCount": 1 if is_correct else 0,
                "lastPracticed": datetime.utcnow().isoformat(),
                "srsData": srs_data,
                "averageResponseTimeMs": response_time_ms
            }

            await self.db_service.update_vocabulary_progress(user_id, word_id, progress_data)

            return {
                "srs_data": srs_data,
                "mastery_level": mastery_level,
                "next_review_days": srs_data["interval"],
                "streak": srs_data["repetitions"]
            }

    def _calculate_mastery_level(
        self,
        repetitions: int,
        correct_count: int,
        practice_count: int
    ) -> str:
        """Calculate mastery level based on SRS repetitions and accuracy."""
        if practice_count == 0:
            return "new"

        accuracy = correct_count / practice_count

        if repetitions >= 5 and accuracy >= 0.85:
            return "mastered"
        elif repetitions >= 2 and accuracy >= 0.7:
            return "reviewing"
        elif repetitions >= 1:
            return "learning"
        else:
            return "new"

    def _determine_context(self, learning_goals: list) -> str:
        """Determine context for exercise generation."""
        if "data_engineering" in learning_goals:
            return "data_engineering"
        elif "ai" in learning_goals or "artificial_intelligence" in learning_goals:
            return "ai"
        elif "technology" in learning_goals or "programming" in learning_goals:
            return "technology"
        else:
            return "general"

    # ==================== HELPER METHODS FOR EXTERNAL USE ====================

    async def get_user_vocabulary_stats(self, user_id: str) -> dict:
        """Get vocabulary statistics for a user."""
        progress = await self.db_service.get_vocabulary_progress(user_id)

        if not progress:
            return {
                "total_words": 0,
                "mastered": 0,
                "reviewing": 0,
                "learning": 0,
                "new": 0,
                "due_for_review": 0,
                "average_accuracy": 0
            }

        stats = {
            "total_words": len(progress),
            "mastered": sum(1 for p in progress if p.get("masteryLevel") == "mastered"),
            "reviewing": sum(1 for p in progress if p.get("masteryLevel") == "reviewing"),
            "learning": sum(1 for p in progress if p.get("masteryLevel") == "learning"),
            "new": sum(1 for p in progress if p.get("masteryLevel") == "new"),
            "due_for_review": 0,
            "average_accuracy": 0
        }

        # Calculate due for review
        due_items = await self.db_service.get_vocabulary_due_for_review(user_id)
        stats["due_for_review"] = len(due_items) if due_items else 0

        # Calculate average accuracy
        total_practice = sum(p.get("practiceCount", 0) for p in progress)
        total_correct = sum(p.get("correctCount", 0) for p in progress)
        stats["average_accuracy"] = round(total_correct / total_practice * 100, 1) if total_practice > 0 else 0

        return stats

    async def get_words_to_review(self, user_id: str, limit: int = 10) -> list:
        """Get list of words due for review."""
        due_items = await self.db_service.get_vocabulary_due_for_review(user_id)

        if not due_items:
            return []

        # Sort by priority (most overdue first)
        due_items.sort(key=lambda x: x.get("srsData", {}).get("nextReview", ""))

        # Get word details
        result = []
        for item in due_items[:limit]:
            word_data = await self._get_word_by_id(item.get("wordId"), "general")
            if word_data:
                result.append({
                    "word_id": item.get("wordId"),
                    "word": word_data.get("word"),
                    "definition": word_data.get("definition"),
                    "mastery_level": item.get("masteryLevel"),
                    "last_practiced": item.get("lastPracticed")
                })

        return result


# Singleton instance
vocabulary_agent = VocabularyAgent()
