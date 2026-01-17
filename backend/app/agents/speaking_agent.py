"""
Speaking Agent
Manages real-time conversation sessions with error detection.

Responsibilities:
- Start and manage conversation sessions
- Maintain conversation context
- Generate natural responses via GPT-4
- Generate TTS audio for agent responses
- Transcribe user audio via STT
- Detect grammar and pronunciation errors (without immediate correction)
- Track errors for later activity generation
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
from app.models.speaking import (
    SpeakingSession,
    ConversationExchange,
    DetectedError,
    SessionStatus,
    ErrorType
)


logger = logging.getLogger(__name__)


# Constants
MAX_TURNS_PER_SESSION = 15  # Maximum turns before suggesting to end
MIN_TURNS_FOR_VALID_SESSION = 3  # Minimum turns for a valid session


class SpeakingAgent(BaseAgent[AppState]):
    """
    Speaking Agent - Manages real-time conversation sessions.

    Features:
    - Natural conversation flow with GPT-4
    - TTS audio generation for agent responses
    - STT transcription of user audio
    - Grammar error detection via GPT-4
    - Pronunciation error detection via Azure Speech
    - Error tracking without immediate correction (natural flow)
    """

    def __init__(self, settings: Settings | None = None):
        super().__init__(settings=settings)
        self._topics_cache: dict[str, dict] = {}
        self._topics_by_difficulty: dict[str, list[dict]] = {}

    def _is_topic_for_level(self, topic: dict, user_level: str) -> bool:
        """
        Check if a conversation topic is appropriate for the user's level.

        Level logic:
        - Beginner: Only beginner topics (simple, structured conversation)
        - Intermediate: Both beginner and intermediate topics (complex conversation)

        Args:
            topic: The topic dictionary
            user_level: The user's current level ('beginner' or 'intermediate')

        Returns:
            True if the topic is appropriate for the user's level
        """
        topic_difficulty = topic.get("difficulty", "beginner")

        if user_level == "beginner":
            # Beginners only see beginner topics
            return topic_difficulty == "beginner"
        else:
            # Intermediate users see both beginner and intermediate topics
            return topic_difficulty in ["beginner", "intermediate"]

    @property
    def name(self) -> str:
        return "speaking"

    @property
    def description(self) -> str:
        return "Manages real-time conversation sessions with error detection"

    async def process(self, state: AppState) -> AppState:
        """
        Process speaking request.

        Handles:
        - speaking_session: Start new session or continue conversation
        """
        self.log_start({
            "user_id": state["user"]["user_id"],
            "request_type": state.get("request_type")
        })

        try:
            request_type = state.get("request_type")
            activity_input = state.get("activity_input", {})
            action = activity_input.get("action", "start")

            if request_type == "speaking_session":
                if action == "start":
                    state = await self._start_session(state)
                elif action == "turn":
                    state = await self._process_turn(state)
                elif action == "end":
                    state = await self._end_session(state)
                else:
                    state["response"] = {
                        "error": f"Unknown speaking action: {action}"
                    }
                    state["has_error"] = True

            else:
                state["response"] = {
                    "error": f"Unknown speaking request type: {request_type}"
                }
                state["has_error"] = True

            self.log_complete({"has_error": state.get("has_error", False)})
            return state

        except Exception as e:
            self.log_error(e)
            state["has_error"] = True
            state["error_message"] = f"Speaking agent error: {str(e)}"
            state["response"] = {"error": str(e)}
            return state

    async def _start_session(self, state: AppState) -> AppState:
        """Start a new speaking session."""
        user_id = state["user"]["user_id"]
        user_level = state["user"].get("current_level", "beginner")
        activity_input = state.get("activity_input", {})

        # Select topic
        requested_topic_id = activity_input.get("topic_id")
        requested_difficulty = activity_input.get("difficulty", user_level)

        topic = await self._select_topic(
            user_id=user_id,
            level=user_level,
            topic_id=requested_topic_id,
            difficulty=requested_difficulty
        )

        if not topic:
            state["response"] = {
                "type": "speaking_session_start",
                "status": "error",
                "message": "Não foi possível selecionar um tópico de conversação."
            }
            state["has_error"] = True
            return state

        # Generate session ID
        session_id = f"session_{user_id}_{datetime.utcnow().timestamp()}"

        # Select opening prompt
        opening_prompts = topic.get("opening_prompts", [])
        if not opening_prompts:
            opening_prompts = [f"Hi! Let's talk about {topic['name']}. What do you think about it?"]
        opening_prompt = random.choice(opening_prompts)

        # Generate TTS for opening prompt
        voice = state["user"].get("voice_preference", "american_female")
        opening_audio = None
        try:
            audio_bytes = self.speech_service.text_to_speech(
                text=opening_prompt,
                voice=voice,
                output_format="wav"
            )
            opening_audio = base64.b64encode(audio_bytes).decode("utf-8")
        except Exception as e:
            self.log_error(e, {"context": "TTS generation for opening"})

        # Create session in database
        session_data = {
            "id": session_id,
            "userId": user_id,
            "partitionKey": user_id,
            "status": SessionStatus.ACTIVE.value,
            "topicId": topic["id"],
            "topicName": topic["name"],
            "topicDifficulty": topic.get("difficulty", "beginner"),
            "startedAt": datetime.utcnow().isoformat(),
            "currentTurn": 1,
            "exchanges": [{
                "turn_number": 0,
                "speaker": "agent",
                "text": opening_prompt,
                "timestamp": datetime.utcnow().isoformat()
            }],
            "grammarErrors": [],
            "pronunciationErrors": [],
            "generatedActivityIds": []
        }

        try:
            await self.db_service.create_speaking_session(user_id, session_data)
        except Exception as e:
            self.log_error(e, {"context": "create_speaking_session"})
            state["response"] = {
                "type": "speaking_session_start",
                "status": "error",
                "message": "Erro ao criar sessão de conversação."
            }
            state["has_error"] = True
            return state

        # Update speaking state
        state["speaking"] = {
            "session_id": session_id,
            "topic": topic["name"],
            "exchanges": session_data["exchanges"],
            "current_turn": 1,
            "errors_detected": [],
            "grammar_errors": [],
            "pronunciation_errors": [],
            "is_active": True
        }

        # Generate suggested responses for beginner users only
        # Intermediate users should practice without assistance
        suggested_responses = None
        if user_level == "beginner":
            suggested_responses = await self._generate_suggested_responses(
                topic_name=topic["name"],
                opening_prompt=opening_prompt
            )

        # Prepare level-specific hints
        vocabulary_hints = topic.get("vocabulary_hints", []) if user_level == "beginner" else []
        grammar_focus = topic.get("grammar_focus", [])

        state["response"] = {
            "type": "speaking_session_start",
            "status": "success",
            "session_id": session_id,
            "topic": topic["name"],
            "topic_description": topic.get("description", ""),
            "topic_difficulty": topic.get("difficulty", "beginner"),
            "user_level": user_level,
            "initial_prompt": opening_prompt,
            "initial_prompt_audio": opening_audio,
            "suggested_responses": suggested_responses,
            "vocabulary_hints": vocabulary_hints,
            "grammar_focus": grammar_focus
        }

        state = add_agent_message(
            state,
            self.name,
            f"Started speaking session on topic: {topic['name']}"
        )

        return state

    async def _process_turn(self, state: AppState) -> AppState:
        """Process a conversation turn."""
        user_id = state["user"]["user_id"]
        user_level = state["user"].get("current_level", "beginner")
        activity_input = state.get("activity_input", {})
        speaking_state = state.get("speaking", {})

        session_id = activity_input.get("session_id") or speaking_state.get("session_id")
        user_text = activity_input.get("user_text")
        audio_base64 = activity_input.get("audio_base64")

        if not session_id:
            state["response"] = {
                "type": "speaking_turn",
                "status": "error",
                "message": "Sessão não especificada."
            }
            state["has_error"] = True
            return state

        # Get session from database
        session = await self.db_service.get_speaking_session(user_id, session_id)
        if not session:
            state["response"] = {
                "type": "speaking_turn",
                "status": "error",
                "message": "Sessão não encontrada."
            }
            state["has_error"] = True
            return state

        if session.get("status") != SessionStatus.ACTIVE.value:
            state["response"] = {
                "type": "speaking_turn",
                "status": "session_ended",
                "message": "Esta sessão já foi encerrada."
            }
            return state

        # Transcribe audio if provided
        pronunciation_errors = []
        if audio_base64 and not user_text:
            try:
                audio_bytes = base64.b64decode(audio_base64)
                transcription_result = self.speech_service.speech_to_text(
                    audio_data=audio_bytes,
                    language="en-US"
                )
                user_text = transcription_result.get("text", "")

                # Also assess pronunciation if we have a transcription
                if user_text:
                    assessment = self.speech_service.pronunciation_assessment(
                        audio_data=audio_bytes,
                        reference_text=user_text,
                        granularity="phoneme"
                    )
                    pronunciation_errors = self._extract_pronunciation_errors(
                        assessment,
                        session.get("currentTurn", 0)
                    )
            except Exception as e:
                self.log_error(e, {"context": "STT/pronunciation assessment"})
                state["response"] = {
                    "type": "speaking_turn",
                    "status": "error",
                    "message": "Erro ao processar áudio. Tente novamente."
                }
                state["has_error"] = True
                return state

        if not user_text:
            state["response"] = {
                "type": "speaking_turn",
                "status": "error",
                "message": "Nenhum texto recebido."
            }
            state["has_error"] = True
            return state

        # Detect grammar errors
        grammar_errors = await self._detect_grammar_errors(
            user_text,
            user_level,
            session.get("currentTurn", 0)
        )

        # Get conversation history
        exchanges = session.get("exchanges", [])

        # Generate agent response (natural conversation, no corrections)
        topic_name = session.get("topicName", "general conversation")
        agent_response = await self._generate_response(
            conversation_history=exchanges,
            user_input=user_text,
            topic=topic_name,
            level=user_level
        )

        # Generate TTS for agent response
        voice = state["user"].get("voice_preference", "american_female")
        agent_audio = None
        try:
            audio_bytes = self.speech_service.text_to_speech(
                text=agent_response,
                voice=voice,
                output_format="wav"
            )
            agent_audio = base64.b64encode(audio_bytes).decode("utf-8")
        except Exception as e:
            self.log_error(e, {"context": "TTS generation"})

        # Update session with new exchanges
        current_turn = session.get("currentTurn", 1)
        now = datetime.utcnow().isoformat()

        # User exchange
        user_exchange = {
            "turn_number": current_turn,
            "speaker": "user",
            "text": user_text,
            "timestamp": now,
            "grammar_errors": grammar_errors,
            "pronunciation_errors": pronunciation_errors
        }
        exchanges.append(user_exchange)

        # Agent exchange
        agent_exchange = {
            "turn_number": current_turn,
            "speaker": "agent",
            "text": agent_response,
            "timestamp": now
        }
        exchanges.append(agent_exchange)

        # Update session in database
        all_grammar_errors = session.get("grammarErrors", []) + grammar_errors
        all_pronunciation_errors = session.get("pronunciationErrors", []) + pronunciation_errors

        session_updates = {
            "exchanges": exchanges,
            "currentTurn": current_turn + 1,
            "grammarErrors": all_grammar_errors,
            "pronunciationErrors": all_pronunciation_errors
        }

        try:
            await self.db_service.update_speaking_session(user_id, session_id, session_updates)
        except Exception as e:
            self.log_error(e, {"context": "update_speaking_session"})

        # Check if we should suggest ending
        conversation_continuing = True
        end_suggestion = None
        if current_turn >= MAX_TURNS_PER_SESSION:
            end_suggestion = "Você já fez várias trocas! Que tal encerrar a sessão e revisar seus erros?"
            conversation_continuing = False

        # Update speaking state
        state["speaking"] = {
            "session_id": session_id,
            "topic": topic_name,
            "exchanges": exchanges,
            "current_turn": current_turn + 1,
            "errors_detected": all_grammar_errors + all_pronunciation_errors,
            "grammar_errors": all_grammar_errors,
            "pronunciation_errors": all_pronunciation_errors,
            "is_active": conversation_continuing
        }

        state["response"] = {
            "type": "speaking_turn",
            "status": "success",
            "session_id": session_id,
            "turn_number": current_turn,
            "user_input": user_text,
            "agent_response": agent_response,
            "agent_audio_base64": agent_audio,
            "errors_detected": len(grammar_errors) + len(pronunciation_errors),
            "grammar_errors": grammar_errors,
            "pronunciation_errors": pronunciation_errors,
            "conversation_continuing": conversation_continuing,
            "end_suggestion": end_suggestion
        }

        state = add_agent_message(
            state,
            self.name,
            f"Processed turn {current_turn}: detected {len(grammar_errors)} grammar and {len(pronunciation_errors)} pronunciation errors"
        )

        return state

    async def _end_session(self, state: AppState) -> AppState:
        """End a speaking session and generate summary."""
        user_id = state["user"]["user_id"]
        activity_input = state.get("activity_input", {})
        speaking_state = state.get("speaking", {})

        session_id = activity_input.get("session_id") or speaking_state.get("session_id")

        if not session_id:
            state["response"] = {
                "type": "speaking_session_end",
                "status": "error",
                "message": "Sessão não especificada."
            }
            state["has_error"] = True
            return state

        # Get session
        session = await self.db_service.get_speaking_session(user_id, session_id)
        if not session:
            state["response"] = {
                "type": "speaking_session_end",
                "status": "error",
                "message": "Sessão não encontrada."
            }
            state["has_error"] = True
            return state

        # Calculate duration
        started_at = session.get("startedAt")
        ended_at = datetime.utcnow().isoformat()
        duration_seconds = 0
        if started_at:
            try:
                start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                end_dt = datetime.utcnow()
                duration_seconds = int((end_dt - start_dt).total_seconds())
            except Exception:
                pass

        # Compile errors
        grammar_errors = session.get("grammarErrors", [])
        pronunciation_errors = session.get("pronunciationErrors", [])
        total_turns = session.get("currentTurn", 0)

        # Get unique error types
        unique_grammar_rules = list(set(e.get("rule", "") for e in grammar_errors if e.get("rule")))
        problematic_phonemes = list(set(e.get("phoneme", "") for e in pronunciation_errors if e.get("phoneme")))

        # Generate summary
        summary = {
            "total_turns": total_turns,
            "duration_seconds": duration_seconds,
            "total_errors": len(grammar_errors) + len(pronunciation_errors),
            "grammar_error_count": len(grammar_errors),
            "pronunciation_error_count": len(pronunciation_errors),
            "unique_grammar_rules_violated": unique_grammar_rules,
            "problematic_phonemes": problematic_phonemes
        }

        # Generate overall feedback
        summary["overall_feedback"] = await self._generate_session_feedback(
            total_turns=total_turns,
            grammar_errors=grammar_errors,
            pronunciation_errors=pronunciation_errors
        )

        # Prepare errors for activity generation
        errors_for_activities = []
        for error in grammar_errors:
            errors_for_activities.append({
                "type": "grammar",
                "rule": error.get("rule"),
                "incorrect_text": error.get("incorrect_text"),
                "correction": error.get("correction"),
                "explanation": error.get("explanation")
            })
        for error in pronunciation_errors:
            errors_for_activities.append({
                "type": "pronunciation",
                "phoneme": error.get("phoneme"),
                "word": error.get("word"),
                "accuracy_score": error.get("accuracy_score")
            })

        # Update session in database
        session_final_update = {
            "status": SessionStatus.COMPLETED.value,
            "endedAt": ended_at,
            "durationSeconds": duration_seconds,
            "summary": summary
        }

        try:
            await self.db_service.end_speaking_session(user_id, session_id, summary)
        except Exception as e:
            self.log_error(e, {"context": "end_speaking_session"})

        # Update speaking state
        state["speaking"] = {
            "session_id": session_id,
            "topic": session.get("topicName", ""),
            "exchanges": session.get("exchanges", []),
            "current_turn": total_turns,
            "errors_detected": errors_for_activities,
            "grammar_errors": grammar_errors,
            "pronunciation_errors": pronunciation_errors,
            "is_active": False
        }

        # Store errors for error integration agent
        state["errors"] = {
            "has_errors": len(errors_for_activities) > 0,
            "pending_errors": errors_for_activities,
            "activities_to_generate": errors_for_activities,
            "generated_activity_ids": []
        }

        # Set activity output for progress tracking
        state["activity_output"] = {
            "pillar": "speaking",
            "session_id": session_id,
            "total_turns": total_turns,
            "duration_seconds": duration_seconds,
            "errors": errors_for_activities
        }

        state["response"] = {
            "type": "speaking_session_end",
            "status": "success",
            "session_id": session_id,
            "summary": summary,
            "grammar_errors": grammar_errors,
            "pronunciation_errors": pronunciation_errors,
            "errors_pending_activities": len(errors_for_activities)
        }

        state = add_agent_message(
            state,
            self.name,
            f"Ended session {session_id}: {total_turns} turns, {len(grammar_errors)} grammar errors, {len(pronunciation_errors)} pronunciation errors"
        )

        return state

    async def _select_topic(
        self,
        user_id: str,
        level: str,
        topic_id: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> Optional[dict]:
        """
        Select a conversation topic.

        Level-based filtering:
        - Beginner: Only beginner topics (simple, everyday conversations)
        - Intermediate: Both beginner and intermediate topics (more complex discussions)
        """
        await self._load_topics()

        # If specific topic requested
        if topic_id:
            return self._topics_cache.get(topic_id)

        # Filter by level using the level filtering method
        available = [
            topic for topic in self._topics_cache.values()
            if (level == "all" or self._is_topic_for_level(topic, level))
            and (not difficulty or topic.get("difficulty") == difficulty)
        ]

        if not available:
            # Fallback to all topics if no match found
            available = list(self._topics_cache.values())

        if not available:
            return None

        # For intermediate users, prioritize intermediate topics
        if level == "intermediate":
            # Sort: intermediate topics first, then beginner
            available.sort(key=lambda t: 0 if t.get("difficulty") == "intermediate" else 1)
            # Return a random topic from the top half (intermediate priority)
            intermediate_topics = [t for t in available if t.get("difficulty") == "intermediate"]
            if intermediate_topics and random.random() > 0.3:  # 70% chance of intermediate topic
                return random.choice(intermediate_topics)

        return random.choice(available)

    async def _load_topics(self):
        """Load conversation topics from JSON file."""
        if self._topics_cache:
            return

        try:
            with open("app/data/conversation_topics.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for topic in data.get("topics", []):
                    self._topics_cache[topic["id"]] = topic
                    difficulty = topic.get("difficulty", "beginner")
                    if difficulty not in self._topics_by_difficulty:
                        self._topics_by_difficulty[difficulty] = []
                    self._topics_by_difficulty[difficulty].append(topic)

            self.log_debug(f"Loaded {len(self._topics_cache)} conversation topics")
        except Exception as e:
            self.log_error(e, {"context": "loading conversation_topics"})

    async def _generate_response(
        self,
        conversation_history: list[dict],
        user_input: str,
        topic: str,
        level: str
    ) -> str:
        """Generate a natural conversation response via GPT-4."""
        try:
            response = await self.openai_service.generate_conversation_response(
                conversation_history=conversation_history,
                user_input=user_input,
                topic=topic,
                level=level
            )
            return response
        except Exception as e:
            self.log_error(e, {"context": "generate_conversation_response"})
            # Fallback responses
            fallback_responses = [
                "That's interesting! Can you tell me more about that?",
                "I see. What else would you like to share?",
                "That's a good point. How do you feel about it?",
                "Interesting! And what happened next?"
            ]
            return random.choice(fallback_responses)

    async def _detect_grammar_errors(
        self,
        text: str,
        level: str,
        turn_number: int
    ) -> list[dict]:
        """Detect grammar errors in user's text."""
        try:
            result = await self.openai_service.detect_grammar_errors(text, level)
            errors = result.get("errors", [])

            # Add turn number and timestamp to each error
            for error in errors:
                error["turn_number"] = turn_number
                error["timestamp"] = datetime.utcnow().isoformat()

            return errors
        except Exception as e:
            self.log_error(e, {"context": "detect_grammar_errors"})
            return []

    def _extract_pronunciation_errors(
        self,
        assessment: dict,
        turn_number: int
    ) -> list[dict]:
        """Extract pronunciation errors from assessment result."""
        errors = []

        if not assessment.get("success"):
            return errors

        words_detail = assessment.get("words", [])
        phonemes_detail = assessment.get("phonemes", [])

        # Check word-level accuracy
        for word_info in words_detail:
            accuracy = word_info.get("accuracy_score", 100)
            if accuracy < 70:  # Below threshold
                errors.append({
                    "type": "pronunciation",
                    "word": word_info.get("word", ""),
                    "accuracy_score": accuracy,
                    "turn_number": turn_number,
                    "timestamp": datetime.utcnow().isoformat()
                })

        # Check phoneme-level accuracy
        for phoneme_info in phonemes_detail:
            accuracy = phoneme_info.get("accuracy_score", 100)
            if accuracy < 60:  # More lenient for phonemes
                phoneme = phoneme_info.get("phoneme", "")
                # Avoid duplicate errors for the same phoneme
                if not any(e.get("phoneme") == phoneme for e in errors):
                    errors.append({
                        "type": "pronunciation",
                        "phoneme": phoneme,
                        "accuracy_score": accuracy,
                        "expected": phoneme_info.get("expected", ""),
                        "detected": phoneme_info.get("detected", ""),
                        "turn_number": turn_number,
                        "timestamp": datetime.utcnow().isoformat()
                    })

        return errors

    async def _generate_suggested_responses(
        self,
        topic_name: str,
        opening_prompt: str
    ) -> list[str]:
        """Generate suggested responses for beginner users."""
        # Simple suggested responses based on common patterns
        suggestions = []

        if "wake up" in opening_prompt.lower() or "morning" in opening_prompt.lower():
            suggestions = [
                "I usually wake up at 7 AM.",
                "I wake up early, around 6 o'clock.",
                "I'm not a morning person, so I wake up late."
            ]
        elif "weekend" in opening_prompt.lower():
            suggestions = [
                "I like to relax and watch movies.",
                "I usually spend time with my family.",
                "I enjoy going out with friends."
            ]
        elif "food" in opening_prompt.lower() or "eat" in opening_prompt.lower():
            suggestions = [
                "I really like pizza and pasta.",
                "My favorite food is Brazilian barbecue.",
                "I enjoy trying different cuisines."
            ]
        else:
            # Generic suggestions
            suggestions = [
                "That's an interesting topic. Let me think...",
                "I have some thoughts about that.",
                "Well, I think..."
            ]

        return suggestions[:3]

    async def _generate_session_feedback(
        self,
        total_turns: int,
        grammar_errors: list[dict],
        pronunciation_errors: list[dict]
    ) -> str:
        """Generate overall feedback for the session."""
        total_errors = len(grammar_errors) + len(pronunciation_errors)

        if total_errors == 0:
            return "Excelente sessão! Você não cometeu nenhum erro detectável. Continue praticando para manter esse nível!"

        if total_errors <= 2:
            return "Ótima sessão! Poucos erros detectados. Revise os pontos destacados para melhorar ainda mais."

        if total_errors <= 5:
            return "Boa sessão de prática! Alguns erros foram detectados, mas isso faz parte do aprendizado. Pratique os itens gerados para melhorar."

        return "Sessão produtiva! Vários pontos de melhoria foram identificados. Recomendamos revisar as atividades geradas para cada erro."

    # ==================== PUBLIC HELPER METHODS ====================

    async def get_available_topics(
        self,
        difficulty: Optional[str] = None
    ) -> list[dict]:
        """Get list of available conversation topics."""
        await self._load_topics()

        if difficulty and difficulty in self._topics_by_difficulty:
            return self._topics_by_difficulty[difficulty]

        return list(self._topics_cache.values())

    async def get_active_session(self, user_id: str) -> Optional[dict]:
        """Get user's active speaking session if any."""
        try:
            sessions = await self.db_service.query_items(
                "speaking_sessions",
                """
                SELECT * FROM c
                WHERE c.partitionKey = @user_id
                AND c.status = @status
                ORDER BY c.startedAt DESC
                OFFSET 0 LIMIT 1
                """,
                [
                    {"name": "@user_id", "value": user_id},
                    {"name": "@status", "value": SessionStatus.ACTIVE.value}
                ],
                user_id
            )
            return sessions[0] if sessions else None
        except Exception as e:
            self.log_error(e, {"context": "get_active_session"})
            return None

    async def get_user_speaking_stats(self, user_id: str) -> dict:
        """Get speaking statistics for a user."""
        try:
            # Get all completed sessions
            sessions = await self.db_service.query_items(
                "speaking_sessions",
                """
                SELECT * FROM c
                WHERE c.partitionKey = @user_id
                AND c.status = @status
                """,
                [
                    {"name": "@user_id", "value": user_id},
                    {"name": "@status", "value": SessionStatus.COMPLETED.value}
                ],
                user_id
            )

            if not sessions:
                return {
                    "total_sessions": 0,
                    "total_conversation_time_minutes": 0,
                    "average_turns_per_session": 0,
                    "total_grammar_errors": 0,
                    "total_pronunciation_errors": 0,
                    "most_common_grammar_errors": [],
                    "problematic_phonemes": []
                }

            total_duration = sum(s.get("durationSeconds", 0) for s in sessions)
            total_turns = sum(s.get("currentTurn", 0) for s in sessions)

            # Aggregate errors
            grammar_rules = {}
            phonemes = {}
            for session in sessions:
                for error in session.get("grammarErrors", []):
                    rule = error.get("rule", "unknown")
                    grammar_rules[rule] = grammar_rules.get(rule, 0) + 1
                for error in session.get("pronunciationErrors", []):
                    phoneme = error.get("phoneme", "unknown")
                    phonemes[phoneme] = phonemes.get(phoneme, 0) + 1

            # Sort by frequency
            sorted_rules = sorted(grammar_rules.items(), key=lambda x: x[1], reverse=True)
            sorted_phonemes = sorted(phonemes.items(), key=lambda x: x[1], reverse=True)

            return {
                "total_sessions": len(sessions),
                "total_conversation_time_minutes": total_duration // 60,
                "average_turns_per_session": round(total_turns / len(sessions), 1) if sessions else 0,
                "total_grammar_errors": sum(len(s.get("grammarErrors", [])) for s in sessions),
                "total_pronunciation_errors": sum(len(s.get("pronunciationErrors", [])) for s in sessions),
                "most_common_grammar_errors": [r[0] for r in sorted_rules[:5]],
                "problematic_phonemes": [p[0] for p in sorted_phonemes[:5]]
            }
        except Exception as e:
            self.log_error(e, {"context": "get_user_speaking_stats"})
            return {}


# Singleton instance
speaking_agent = SpeakingAgent()
