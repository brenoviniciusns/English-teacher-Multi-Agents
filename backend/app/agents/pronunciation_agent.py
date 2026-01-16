"""
Pronunciation Agent
Manages pronunciation learning with shadowing technique.

Responsibilities:
- Present phonetic sounds with mouth position guidance
- Generate shadowing exercises with TTS audio
- Assess pronunciation via Azure Speech Services
- Track progress and mastery levels using SRS
- Focus on sounds that don't exist in Portuguese
"""
import json
import logging
import random
import base64
from datetime import datetime
from typing import Optional

from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.state import AppState, add_agent_message
from app.config import Settings, get_settings
from app.models.pronunciation import (
    PhoneticSound,
    PronunciationProgress,
    PronunciationSRSData,
    PronunciationExercise,
    PronunciationExerciseResult,
    PronunciationAttempt
)
from app.utils.srs_algorithm import (
    SRSAlgorithm,
    calculate_next_review,
    should_review_low_frequency
)


logger = logging.getLogger(__name__)


# Minimum accuracy score to pass a pronunciation exercise
MIN_PASSING_ACCURACY = 70.0

# Minimum accuracy score to consider a sound mastered
MASTERY_THRESHOLD = 85.0

# Maximum attempts per exercise before moving on
MAX_ATTEMPTS_PER_EXERCISE = 3


class PronunciationAgent(BaseAgent[AppState]):
    """
    Pronunciation Agent - Manages pronunciation learning with shadowing.

    Features:
    - Presents phonetic sounds with mouth position diagrams
    - Generates shadowing exercises with TTS audio
    - Assesses pronunciation accuracy via Azure Speech
    - Tracks progress using SRS algorithm
    - Focuses on sounds problematic for Portuguese speakers
    """

    def __init__(self, settings: Settings | None = None):
        super().__init__(settings=settings)
        self.srs = SRSAlgorithm()
        self._sounds_cache: dict[str, dict] = {}
        self._sounds_by_difficulty: dict[str, list[dict]] = {}

    @property
    def name(self) -> str:
        return "pronunciation"

    @property
    def description(self) -> str:
        return "Manages pronunciation learning with shadowing and Azure Speech assessment"

    async def process(self, state: AppState) -> AppState:
        """
        Process pronunciation request.

        Handles:
        - pronunciation_exercise: Generate shadowing exercise
        - shadowing: Process audio submission and assess pronunciation
        """
        self.log_start({
            "user_id": state["user"]["user_id"],
            "request_type": state.get("request_type")
        })

        try:
            request_type = state.get("request_type")
            activity_input = state.get("activity_input", {})

            if request_type == "pronunciation_exercise":
                # Check if submitting audio or requesting new exercise
                if activity_input.get("audio_base64"):
                    state = await self._process_audio_submission(state)
                else:
                    state = await self._generate_exercise(state)

            elif request_type == "shadowing":
                # Direct audio submission for shadowing
                state = await self._process_audio_submission(state)

            else:
                state["response"] = {
                    "error": f"Unknown pronunciation request type: {request_type}"
                }
                state["has_error"] = True

            self.log_complete({"has_error": state.get("has_error", False)})
            return state

        except Exception as e:
            self.log_error(e)
            state["has_error"] = True
            state["error_message"] = f"Pronunciation agent error: {str(e)}"
            state["response"] = {"error": str(e)}
            return state

    async def _generate_exercise(self, state: AppState) -> AppState:
        """Generate a pronunciation/shadowing exercise for the user."""
        user_id = state["user"]["user_id"]
        user_level = state["user"].get("current_level", "beginner")
        activity_input = state.get("activity_input", {})

        # Check if specific sound requested
        requested_sound_id = activity_input.get("sound_id")
        requested_difficulty = activity_input.get("difficulty")
        exercise_type = activity_input.get("exercise_type", "shadowing")

        # Select sound for exercise
        sound_data = await self._select_sound(
            user_id=user_id,
            level=user_level,
            sound_id=requested_sound_id,
            difficulty=requested_difficulty
        )

        if not sound_data:
            state["response"] = {
                "type": "pronunciation_exercise",
                "status": "no_sounds",
                "message": "Parabéns! Você praticou todos os sons disponíveis para seu nível."
            }
            return state

        # Get user's progress for this sound
        user_progress = await self._get_user_progress(user_id, sound_data["id"])

        # Select target word for practice
        example_words = sound_data.get("example_words", [])
        if not example_words:
            example_words = ["example"]

        # Prioritize words not yet mastered or select random
        target_word = self._select_target_word(example_words, user_progress)

        # Generate reference audio using TTS
        voice = state["user"].get("voice_preference", "american_female")
        try:
            audio_bytes = self.speech_service.text_to_speech(
                text=target_word,
                voice=voice,
                output_format="wav"
            )
            reference_audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        except Exception as e:
            self.log_error(e, {"context": "TTS generation"})
            reference_audio_base64 = None

        # Build exercise content
        exercise_content = {
            "exercise_type": exercise_type,
            "sound": {
                "id": sound_data["id"],
                "phoneme": sound_data["phoneme"],
                "ipa": sound_data.get("ipa", sound_data["phoneme"]),
                "name": sound_data["name"],
                "exists_in_portuguese": sound_data.get("exists_in_portuguese", False),
                "difficulty": sound_data.get("difficulty", "medium"),
                "mouth_position": sound_data.get("mouth_position", {}),
                "example_words": example_words[:5],
                "minimal_pairs": sound_data.get("minimal_pairs", [])[:3],
                "common_mistake": sound_data.get("common_mistake", ""),
                "portuguese_similar": sound_data.get("portuguese_similar"),
                "tip": sound_data.get("tip", "")
            },
            "target_word": target_word,
            "target_sentence": self._create_context_sentence(target_word, sound_data),
            "reference_audio_base64": reference_audio_base64,
            "instructions": self._get_exercise_instructions(exercise_type, sound_data)
        }

        # Store current activity in state
        activity_id = f"pronun_{user_id}_{datetime.utcnow().timestamp()}"
        state["current_activity"] = {
            "activity_id": activity_id,
            "activity_type": "pronunciation_exercise",
            "pillar": "pronunciation",
            "content": {
                "sound_id": sound_data["id"],
                "phoneme": sound_data["phoneme"],
                "target_word": target_word,
                "attempt_count": 0,
                "best_accuracy": 0
            },
            "started_at": datetime.utcnow().isoformat(),
            "status": "in_progress"
        }

        # Calculate attempts remaining
        attempts_remaining = MAX_ATTEMPTS_PER_EXERCISE
        if user_progress:
            # Check if there's an ongoing exercise for this sound
            last_attempt = user_progress.get("lastAttemptCount", 0)
            if last_attempt > 0 and last_attempt < MAX_ATTEMPTS_PER_EXERCISE:
                attempts_remaining = MAX_ATTEMPTS_PER_EXERCISE - last_attempt

        # Prepare response
        state["response"] = {
            "type": "pronunciation_exercise",
            "status": "success",
            "activity_id": activity_id,
            "exercise": exercise_content,
            "user_progress": {
                "practice_count": user_progress.get("practiceCount", 0) if user_progress else 0,
                "average_accuracy": user_progress.get("averageAccuracy", 0) if user_progress else 0,
                "best_accuracy": user_progress.get("bestAccuracy", 0) if user_progress else 0,
                "mastered": user_progress.get("mastered", False) if user_progress else False,
                "last_practiced": user_progress.get("lastPracticed") if user_progress else None
            },
            "attempts_remaining": attempts_remaining
        }

        state = add_agent_message(
            state,
            self.name,
            f"Generated pronunciation exercise for sound: {sound_data['phoneme']} ({sound_data['name']})"
        )

        return state

    async def _process_audio_submission(self, state: AppState) -> AppState:
        """Process audio submission and assess pronunciation."""
        user_id = state["user"]["user_id"]
        activity_input = state.get("activity_input", {})
        current_activity = state.get("current_activity", {})

        # Extract data
        audio_base64 = activity_input.get("audio_base64")
        sound_id = activity_input.get("sound_id") or current_activity.get("content", {}).get("sound_id")
        target_word = activity_input.get("word") or current_activity.get("content", {}).get("target_word")
        reference_text = activity_input.get("reference_text") or target_word
        attempt_number = activity_input.get("attempt_number", 1)

        if not audio_base64:
            state["response"] = {
                "type": "shadowing_result",
                "status": "error",
                "message": "Áudio não fornecido. Por favor, grave sua pronúncia."
            }
            state["has_error"] = True
            return state

        if not sound_id or not reference_text:
            state["response"] = {
                "type": "shadowing_result",
                "status": "error",
                "message": "Informações do exercício incompletas."
            }
            state["has_error"] = True
            return state

        # Decode audio
        try:
            audio_bytes = base64.b64decode(audio_base64)
        except Exception as e:
            self.log_error(e, {"context": "audio decode"})
            state["response"] = {
                "type": "shadowing_result",
                "status": "error",
                "message": "Erro ao processar áudio. Formato inválido."
            }
            state["has_error"] = True
            return state

        # Assess pronunciation using Azure Speech
        try:
            assessment_result = self.speech_service.pronunciation_assessment(
                audio_data=audio_bytes,
                reference_text=reference_text,
                language="en-US",
                granularity="phoneme"
            )
        except Exception as e:
            self.log_error(e, {"context": "pronunciation assessment"})
            state["response"] = {
                "type": "shadowing_result",
                "status": "error",
                "message": "Erro ao avaliar pronúncia. Tente novamente."
            }
            state["has_error"] = True
            return state

        if not assessment_result.get("success"):
            state["response"] = {
                "type": "shadowing_result",
                "status": "error",
                "message": assessment_result.get("error", "Não foi possível reconhecer a fala."),
                "suggestion": assessment_result.get("suggestion", "Fale mais claramente e próximo ao microfone.")
            }
            state["has_error"] = True
            return state

        # Extract scores
        scores = assessment_result.get("scores", {})
        accuracy_score = scores.get("accuracy", 0)
        fluency_score = scores.get("fluency", 0)
        completeness_score = scores.get("completeness", 0)
        pronunciation_score = scores.get("pronunciation", 0)

        recognized_text = assessment_result.get("recognized_text", "")
        words_detail = assessment_result.get("words", [])
        phonemes_detail = assessment_result.get("phonemes", [])
        feedback = assessment_result.get("feedback", {})

        # Determine if passed
        passed = accuracy_score >= MIN_PASSING_ACCURACY

        # Update attempt tracking in current activity
        current_attempt_count = current_activity.get("content", {}).get("attempt_count", 0) + 1
        current_best_accuracy = current_activity.get("content", {}).get("best_accuracy", 0)
        best_accuracy = max(current_best_accuracy, accuracy_score)

        if current_activity:
            state["current_activity"]["content"]["attempt_count"] = current_attempt_count
            state["current_activity"]["content"]["best_accuracy"] = best_accuracy

        # Calculate attempts remaining
        attempts_remaining = MAX_ATTEMPTS_PER_EXERCISE - current_attempt_count

        # Determine if exercise is complete (passed or no more attempts)
        exercise_complete = passed or attempts_remaining <= 0

        # Calculate SRS quality based on accuracy
        quality = self._accuracy_to_quality(accuracy_score)

        # Update progress if exercise is complete
        mastery_updated = False
        new_mastery_level = None
        next_review_days = None

        if exercise_complete:
            progress_update = await self._update_progress(
                user_id=user_id,
                sound_id=sound_id,
                word=target_word,
                recognized_text=recognized_text,
                accuracy_score=best_accuracy,
                quality=quality,
                attempt_count=current_attempt_count
            )

            if current_activity:
                state["current_activity"]["status"] = "completed"
                state["current_activity"]["result"] = {
                    "passed": passed,
                    "accuracy": best_accuracy,
                    "quality": quality
                }

            # Store activity output for progress agent
            state["activity_output"] = {
                "pillar": "pronunciation",
                "sound_id": sound_id,
                "word": target_word,
                "correct": passed,
                "quality": quality,
                "accuracy": best_accuracy,
                "srs_update": progress_update.get("srs_data", {})
            }

            mastery_updated = progress_update.get("mastery_changed", False)
            new_mastery_level = progress_update.get("mastery_level")
            next_review_days = progress_update.get("next_review_days")

        # Get sound data for additional context
        sound_data = await self._get_sound_by_id(sound_id)

        # Build detailed response
        state["response"] = {
            "type": "shadowing_result",
            "status": "success",
            "sound_id": sound_id,
            "word": target_word,
            "recognized_text": recognized_text,
            "reference_text": reference_text,
            "scores": {
                "accuracy": accuracy_score,
                "fluency": fluency_score,
                "completeness": completeness_score,
                "pronunciation": pronunciation_score
            },
            "words_detail": words_detail,
            "phonemes_detail": phonemes_detail,
            "feedback": feedback,
            "passed": passed,
            "attempt_number": current_attempt_count,
            "attempts_remaining": max(0, attempts_remaining),
            "mastery_updated": mastery_updated,
            "new_mastery_level": new_mastery_level,
            "next_review_days": next_review_days
        }

        # Add specific feedback for problematic phonemes if assessment detected issues
        if sound_data and not passed:
            problem_phonemes = [
                p for p in phonemes_detail
                if p.get("accuracy_score", 100) < 70
            ]
            if problem_phonemes:
                state["response"]["phoneme_guidance"] = {
                    "target_phoneme": sound_data.get("phoneme"),
                    "tip": sound_data.get("tip"),
                    "common_mistake": sound_data.get("common_mistake"),
                    "mouth_position": sound_data.get("mouth_position", {})
                }

        state = add_agent_message(
            state,
            self.name,
            f"Assessed pronunciation for '{target_word}': accuracy={accuracy_score:.1f}%, passed={passed}"
        )

        return state

    async def _select_sound(
        self,
        user_id: str,
        level: str,
        sound_id: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> Optional[dict]:
        """
        Select a phonetic sound for the exercise.

        Priority:
        1. Specific sound if requested
        2. Sounds due for SRS review
        3. Sounds with low accuracy (needs practice)
        4. Sounds with low frequency usage
        5. New sounds not yet studied
        """
        await self._load_sounds()

        # If specific sound requested
        if sound_id:
            return self._sounds_cache.get(sound_id)

        try:
            # 1. Check SRS due items
            due_items = await self.db_service.get_pronunciation_due_for_review(user_id)
            if due_items:
                self.log_debug(f"Found {len(due_items)} pronunciation sounds due for review")
                due_items.sort(key=lambda x: x.get("srsData", {}).get("nextReview", ""))
                due_sound_id = due_items[0].get("soundId")
                if due_sound_id and due_sound_id in self._sounds_cache:
                    return self._sounds_cache[due_sound_id]

            # 2. Check items needing practice (low accuracy)
            needs_practice = await self.db_service.get_pronunciation_needs_practice(
                user_id,
                threshold=MIN_PASSING_ACCURACY
            )
            if needs_practice:
                self.log_debug(f"Found {len(needs_practice)} sounds needing practice")
                # Sort by accuracy (lowest first)
                needs_practice.sort(key=lambda x: x.get("averageAccuracy", 0))
                sound_id = needs_practice[0].get("soundId")
                if sound_id and sound_id in self._sounds_cache:
                    return self._sounds_cache[sound_id]

            # 3. Check low frequency items
            low_freq_items = await self.db_service.get_pronunciation_low_frequency(user_id)
            if low_freq_items:
                self.log_debug(f"Found {len(low_freq_items)} low frequency pronunciation sounds")
                item = random.choice(low_freq_items)
                sound_id = item.get("soundId")
                if sound_id and sound_id in self._sounds_cache:
                    return self._sounds_cache[sound_id]

            # 4. Get new sound
            self.log_debug("Selecting new pronunciation sound for user")
            return await self._get_new_sound(user_id, level, difficulty)

        except Exception as e:
            self.log_error(e, {"context": "sound_selection"})
            # Fallback: return random sound
            return await self._get_random_sound(level, difficulty)

    async def _get_sound_by_id(self, sound_id: str) -> Optional[dict]:
        """Get phonetic sound data by ID."""
        await self._load_sounds()
        return self._sounds_cache.get(sound_id)

    async def _get_new_sound(
        self,
        user_id: str,
        level: str,
        difficulty: Optional[str] = None
    ) -> Optional[dict]:
        """Get a new sound that the user hasn't studied yet."""
        await self._load_sounds()

        # Get user's existing progress
        existing_progress = await self.db_service.get_pronunciation_progress(user_id)
        studied_sound_ids = {p.get("soundId") for p in existing_progress} if existing_progress else set()

        # Filter sounds by level and optionally difficulty
        available_sounds = []
        for sound_id, sound in self._sounds_cache.items():
            if sound_id in studied_sound_ids:
                continue

            # Map level to difficulty
            sound_difficulty = sound.get("difficulty", "medium")
            if level == "beginner" and sound_difficulty == "high":
                continue  # Skip hard sounds for beginners
            if difficulty and sound_difficulty != difficulty:
                continue

            available_sounds.append(sound)

        if not available_sounds:
            # Try without level filter
            available_sounds = [
                s for s_id, s in self._sounds_cache.items()
                if s_id not in studied_sound_ids
                and (not difficulty or s.get("difficulty") == difficulty)
            ]

        if not available_sounds:
            return None

        # Prioritize sounds that don't exist in Portuguese (harder but important)
        # Start with easier sounds for beginners
        available_sounds.sort(
            key=lambda x: (
                x.get("exists_in_portuguese", True),  # Non-Portuguese sounds first
                {"low": 0, "medium": 1, "high": 2}.get(x.get("difficulty", "medium"), 1)
            )
        )

        # For beginners, start with easier sounds
        if level == "beginner":
            available_sounds.sort(
                key=lambda x: (
                    {"low": 0, "medium": 1, "high": 2}.get(x.get("difficulty", "medium"), 1),
                    not x.get("exists_in_portuguese", True)
                )
            )

        return available_sounds[0]

    async def _get_random_sound(
        self,
        level: str,
        difficulty: Optional[str] = None
    ) -> Optional[dict]:
        """Get a random sound as fallback."""
        await self._load_sounds()

        sounds = list(self._sounds_cache.values())

        if difficulty:
            sounds = [s for s in sounds if s.get("difficulty") == difficulty]
        elif level == "beginner":
            # Filter out high difficulty for beginners
            sounds = [s for s in sounds if s.get("difficulty") != "high"]

        return random.choice(sounds) if sounds else None

    async def _load_sounds(self):
        """Load phonetic sounds from JSON file."""
        if self._sounds_cache:
            return

        try:
            with open("app/data/phonetic_sounds.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for sound in data.get("sounds", []):
                    self._sounds_cache[sound["id"]] = sound
                    # Index by difficulty
                    difficulty = sound.get("difficulty", "medium")
                    if difficulty not in self._sounds_by_difficulty:
                        self._sounds_by_difficulty[difficulty] = []
                    self._sounds_by_difficulty[difficulty].append(sound)

            self.log_debug(f"Loaded {len(self._sounds_cache)} phonetic sounds")
        except Exception as e:
            self.log_error(e, {"context": "loading phonetic_sounds"})

    async def _get_user_progress(self, user_id: str, sound_id: str) -> Optional[dict]:
        """Get user's progress for a specific sound."""
        try:
            return await self.db_service.get_pronunciation_progress(user_id, sound_id)
        except Exception as e:
            self.log_error(e, {"context": "get_user_progress"})
            return None

    def _select_target_word(
        self,
        example_words: list[str],
        user_progress: Optional[dict]
    ) -> str:
        """Select a target word for practice, prioritizing less practiced words."""
        if not example_words:
            return "example"

        if not user_progress:
            # New user - start with first word
            return example_words[0]

        # Get practiced words history
        practice_history = user_progress.get("practiceHistory", [])
        practiced_words = {h.get("word") for h in practice_history}

        # Find unpracticed words
        unpracticed = [w for w in example_words if w not in practiced_words]
        if unpracticed:
            return unpracticed[0]

        # All words practiced - return random or least practiced
        return random.choice(example_words)

    def _create_context_sentence(self, word: str, sound_data: dict) -> Optional[str]:
        """Create a simple context sentence for the target word."""
        # Simple sentence templates
        templates = [
            f"Please say '{word}' clearly.",
            f"Practice saying: {word}",
            f"The word is: {word}"
        ]
        return random.choice(templates)

    def _get_exercise_instructions(self, exercise_type: str, sound_data: dict) -> str:
        """Get instructions for the exercise in Portuguese."""
        phoneme = sound_data.get("phoneme", "")
        tip = sound_data.get("tip", "")

        if exercise_type == "shadowing":
            return (
                f"Ouça o áudio e repita a palavra, focando no som /{phoneme}/. "
                f"Dica: {tip}"
            )
        elif exercise_type == "minimal_pair":
            return (
                f"Pratique distinguindo o som /{phoneme}/ de sons semelhantes. "
                f"Preste atenção na diferença entre as palavras."
            )
        else:
            return f"Pratique o som /{phoneme}/. {tip}"

    def _accuracy_to_quality(self, accuracy: float) -> int:
        """Convert accuracy score to SRS quality (0-5)."""
        if accuracy >= 95:
            return 5  # Perfect
        elif accuracy >= 85:
            return 4  # Good
        elif accuracy >= 70:
            return 3  # OK
        elif accuracy >= 50:
            return 2  # Poor
        elif accuracy >= 30:
            return 1  # Bad
        else:
            return 0  # Blackout

    async def _update_progress(
        self,
        user_id: str,
        sound_id: str,
        word: str,
        recognized_text: str,
        accuracy_score: float,
        quality: int,
        attempt_count: int
    ) -> dict:
        """Update pronunciation progress after assessment."""
        # Get sound data
        sound_data = await self._get_sound_by_id(sound_id)
        phoneme = sound_data.get("phoneme", "") if sound_data else ""

        existing = await self.db_service.get_pronunciation_progress(user_id, sound_id)
        now = datetime.utcnow().isoformat()

        if existing:
            # Update existing progress
            srs_data = existing.get("srsData", {
                "easeFactor": 2.5,
                "interval": 1,
                "repetitions": 0,
                "nextReview": now
            })

            new_srs = calculate_next_review(srs_data, quality)

            practice_count = existing.get("practiceCount", 0) + 1
            best_accuracy = max(existing.get("bestAccuracy", 0), accuracy_score)

            # Calculate new average accuracy
            recent_accuracies = existing.get("recentAccuracies", [])
            recent_accuracies.append(accuracy_score)
            recent_accuracies = recent_accuracies[-10:]  # Keep last 10
            average_accuracy = sum(recent_accuracies) / len(recent_accuracies)

            # Add to practice history
            practice_history = existing.get("practiceHistory", [])
            practice_history.append({
                "timestamp": now,
                "word": word,
                "referenceText": word,
                "recognizedText": recognized_text,
                "accuracyScore": accuracy_score,
                "feedback": ""
            })
            practice_history = practice_history[-20:]  # Keep last 20

            # Determine mastery
            old_mastered = existing.get("mastered", False)
            new_mastered = average_accuracy >= MASTERY_THRESHOLD and practice_count >= 3
            mastery_changed = old_mastered != new_mastered

            mastery_level = self._calculate_mastery_level(
                average_accuracy=average_accuracy,
                practice_count=practice_count,
                repetitions=new_srs["repetitions"]
            )

            progress_data = {
                "id": f"pronun_{user_id}_{sound_id}",
                "userId": user_id,
                "soundId": sound_id,
                "phoneme": phoneme,
                "partitionKey": user_id,
                "practiceCount": practice_count,
                "lastPracticed": now,
                "averageAccuracy": round(average_accuracy, 2),
                "bestAccuracy": round(best_accuracy, 2),
                "recentAccuracies": recent_accuracies,
                "practiceHistory": practice_history,
                "srsData": new_srs,
                "mastered": new_mastered,
                "needsMouthPositionReview": accuracy_score < MIN_PASSING_ACCURACY,
                "updatedAt": now
            }

            await self.db_service.update_pronunciation_progress(user_id, sound_id, progress_data)

            return {
                "srs_data": new_srs,
                "mastery_level": mastery_level,
                "mastery_changed": mastery_changed,
                "next_review_days": new_srs["interval"]
            }

        else:
            # Create new progress
            srs_data = calculate_next_review(
                {"easeFactor": 2.5, "interval": 1, "repetitions": 0, "nextReview": now},
                quality
            )

            mastered = accuracy_score >= MASTERY_THRESHOLD
            mastery_level = "mastered" if mastered else ("practicing" if accuracy_score >= MIN_PASSING_ACCURACY else "needs_work")

            progress_data = {
                "id": f"pronun_{user_id}_{sound_id}",
                "userId": user_id,
                "soundId": sound_id,
                "phoneme": phoneme,
                "partitionKey": user_id,
                "practiceCount": 1,
                "lastPracticed": now,
                "averageAccuracy": round(accuracy_score, 2),
                "bestAccuracy": round(accuracy_score, 2),
                "recentAccuracies": [accuracy_score],
                "practiceHistory": [{
                    "timestamp": now,
                    "word": word,
                    "referenceText": word,
                    "recognizedText": recognized_text,
                    "accuracyScore": accuracy_score,
                    "feedback": ""
                }],
                "srsData": srs_data,
                "mastered": mastered,
                "needsMouthPositionReview": accuracy_score < MIN_PASSING_ACCURACY,
                "createdAt": now,
                "updatedAt": now
            }

            await self.db_service.update_pronunciation_progress(user_id, sound_id, progress_data)

            return {
                "srs_data": srs_data,
                "mastery_level": mastery_level,
                "mastery_changed": False,
                "next_review_days": srs_data["interval"]
            }

    def _calculate_mastery_level(
        self,
        average_accuracy: float,
        practice_count: int,
        repetitions: int
    ) -> str:
        """Calculate mastery level based on accuracy and practice count."""
        if practice_count == 0:
            return "not_started"

        if average_accuracy >= MASTERY_THRESHOLD and repetitions >= 3:
            return "mastered"
        elif average_accuracy >= MIN_PASSING_ACCURACY:
            return "practicing"
        else:
            return "needs_work"

    # ==================== HELPER METHODS FOR EXTERNAL USE ====================

    async def get_user_pronunciation_stats(self, user_id: str) -> dict:
        """Get pronunciation statistics for a user."""
        progress = await self.db_service.get_pronunciation_progress(user_id)
        await self._load_sounds()

        if not progress:
            return {
                "total_sounds": len(self._sounds_cache),
                "mastered": 0,
                "practicing": 0,
                "needs_work": 0,
                "not_started": len(self._sounds_cache),
                "due_for_review": 0,
                "average_accuracy": 0,
                "total_practice_count": 0,
                "hardest_sounds": [],
                "best_sounds": []
            }

        stats = {
            "total_sounds": len(self._sounds_cache),
            "mastered": sum(1 for p in progress if p.get("mastered", False)),
            "practicing": sum(
                1 for p in progress
                if not p.get("mastered") and p.get("averageAccuracy", 0) >= MIN_PASSING_ACCURACY
            ),
            "needs_work": sum(
                1 for p in progress
                if p.get("averageAccuracy", 0) < MIN_PASSING_ACCURACY
            ),
            "not_started": 0,
            "due_for_review": 0,
            "average_accuracy": 0,
            "total_practice_count": 0,
            "hardest_sounds": [],
            "best_sounds": []
        }

        studied_ids = {p.get("soundId") for p in progress}
        stats["not_started"] = len(self._sounds_cache) - len(studied_ids)

        # Calculate due for review
        due_items = await self.db_service.get_pronunciation_due_for_review(user_id)
        stats["due_for_review"] = len(due_items) if due_items else 0

        # Calculate averages
        accuracies = [p.get("averageAccuracy", 0) for p in progress if p.get("averageAccuracy")]
        stats["average_accuracy"] = round(sum(accuracies) / len(accuracies), 1) if accuracies else 0

        practice_counts = [p.get("practiceCount", 0) for p in progress]
        stats["total_practice_count"] = sum(practice_counts)

        # Find hardest and best sounds
        progress_with_data = [p for p in progress if p.get("averageAccuracy") is not None]
        progress_with_data.sort(key=lambda x: x.get("averageAccuracy", 0))

        # Hardest sounds (lowest accuracy)
        for p in progress_with_data[:3]:
            sound_id = p.get("soundId")
            sound = self._sounds_cache.get(sound_id)
            if sound:
                stats["hardest_sounds"].append(sound.get("phoneme", sound_id))

        # Best sounds (highest accuracy)
        for p in progress_with_data[-3:]:
            sound_id = p.get("soundId")
            sound = self._sounds_cache.get(sound_id)
            if sound:
                stats["best_sounds"].append(sound.get("phoneme", sound_id))

        return stats

    async def get_sounds_to_review(self, user_id: str, limit: int = 10) -> list:
        """Get list of sounds due for review."""
        await self._load_sounds()

        # Combine different review sources
        review_list = []

        # 1. SRS due items
        due_items = await self.db_service.get_pronunciation_due_for_review(user_id)
        if due_items:
            for item in due_items:
                sound_id = item.get("soundId")
                sound = self._sounds_cache.get(sound_id)
                if sound:
                    review_list.append({
                        "sound_id": sound_id,
                        "phoneme": sound.get("phoneme"),
                        "name": sound.get("name"),
                        "difficulty": sound.get("difficulty"),
                        "average_accuracy": item.get("averageAccuracy", 0),
                        "practice_count": item.get("practiceCount", 0),
                        "last_practiced": item.get("lastPracticed"),
                        "review_reason": "srs_due"
                    })

        # 2. Low accuracy items
        needs_practice = await self.db_service.get_pronunciation_needs_practice(
            user_id, threshold=MIN_PASSING_ACCURACY
        )
        if needs_practice:
            for item in needs_practice:
                sound_id = item.get("soundId")
                # Avoid duplicates
                if any(r.get("sound_id") == sound_id for r in review_list):
                    continue
                sound = self._sounds_cache.get(sound_id)
                if sound:
                    review_list.append({
                        "sound_id": sound_id,
                        "phoneme": sound.get("phoneme"),
                        "name": sound.get("name"),
                        "difficulty": sound.get("difficulty"),
                        "average_accuracy": item.get("averageAccuracy", 0),
                        "practice_count": item.get("practiceCount", 0),
                        "last_practiced": item.get("lastPracticed"),
                        "review_reason": "low_accuracy"
                    })

        # 3. Low frequency items
        low_freq = await self.db_service.get_pronunciation_low_frequency(user_id)
        if low_freq:
            for item in low_freq:
                sound_id = item.get("soundId")
                if any(r.get("sound_id") == sound_id for r in review_list):
                    continue
                sound = self._sounds_cache.get(sound_id)
                if sound:
                    review_list.append({
                        "sound_id": sound_id,
                        "phoneme": sound.get("phoneme"),
                        "name": sound.get("name"),
                        "difficulty": sound.get("difficulty"),
                        "average_accuracy": item.get("averageAccuracy", 0),
                        "practice_count": item.get("practiceCount", 0),
                        "last_practiced": item.get("lastPracticed"),
                        "review_reason": "low_frequency"
                    })

        return review_list[:limit]

    async def get_all_sounds(
        self,
        user_id: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> list[dict]:
        """Get all phonetic sounds with optional user progress."""
        await self._load_sounds()

        sounds = list(self._sounds_cache.values())

        # Filter by difficulty
        if difficulty:
            sounds = [s for s in sounds if s.get("difficulty") == difficulty]

        # Add user progress if user_id provided
        if user_id:
            progress_list = await self.db_service.get_pronunciation_progress(user_id)
            progress_map = {p.get("soundId"): p for p in progress_list} if progress_list else {}

            for sound in sounds:
                progress = progress_map.get(sound["id"])
                if progress:
                    sound["user_accuracy"] = progress.get("averageAccuracy")
                    sound["user_practice_count"] = progress.get("practiceCount")
                    sound["user_mastered"] = progress.get("mastered", False)
                else:
                    sound["user_accuracy"] = None
                    sound["user_practice_count"] = None
                    sound["user_mastered"] = None

        return sounds

    def get_available_difficulties(self) -> list[str]:
        """Get list of available difficulty levels."""
        return list(self._sounds_by_difficulty.keys())

    async def get_phoneme_guidance(self, phoneme: str) -> dict:
        """Get guidance for a specific phoneme."""
        # Use the speech service's phoneme guidance
        guidance = self.speech_service.get_phoneme_guidance(phoneme)

        # Also search in our sounds cache for more details
        await self._load_sounds()
        for sound in self._sounds_cache.values():
            if sound.get("phoneme") == phoneme or sound.get("ipa") == phoneme:
                return {
                    "phoneme": phoneme,
                    "name": sound.get("name", guidance.get("name", "")),
                    "ipa": sound.get("ipa", phoneme),
                    "mouth_position": sound.get("mouth_position", guidance.get("mouth_position", {})),
                    "example_words": sound.get("example_words", guidance.get("example_words", [])),
                    "common_mistake": sound.get("common_mistake", guidance.get("common_mistake", "")),
                    "tip": sound.get("tip", guidance.get("tip", "")),
                    "portuguese_similar": sound.get("portuguese_similar"),
                    "video_url": sound.get("video_url"),
                    "diagram_url": sound.get("diagram_url")
                }

        return guidance


# Singleton instance
pronunciation_agent = PronunciationAgent()
