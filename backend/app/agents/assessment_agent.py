"""
Assessment Agent
Handles initial and continuous assessments to determine user level and progress.

Initial Assessment:
- 20 vocabulary words
- 5 grammar rules
- 5 pronunciation sounds
- Brief conversation sample

Continuous Assessment:
- Triggered every 5 sessions
- Analyzes performance trends
- Recommends level changes
"""
import logging
from datetime import datetime
from typing import Any

from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.state import AppState, add_agent_message
from app.config import Settings
from app.models.progress import AssessmentResult


logger = logging.getLogger(__name__)


class AssessmentAgent(BaseAgent[AppState]):
    """
    Assessment Agent for evaluating user proficiency.

    Responsibilities:
    - Conduct initial assessments for new users
    - Perform continuous assessments to track progress
    - Determine appropriate learning level
    - Generate personalized recommendations
    """

    @property
    def name(self) -> str:
        return "assessment"

    @property
    def description(self) -> str:
        return "Evaluates user proficiency through initial and continuous assessments"

    async def process(self, state: AppState) -> AppState:
        """Process assessment request"""
        self.log_start({"user_id": state["user"]["user_id"]})

        try:
            request_type = state.get("request_type", "")

            if request_type == "assessment_initial":
                return await self._process_initial_assessment(state)
            elif request_type == "assessment_continuous":
                return await self._process_continuous_assessment(state)
            else:
                # Check if assessment is needed
                if self._should_run_assessment(state):
                    return await self._process_continuous_assessment(state)

                # No assessment needed
                state = add_agent_message(
                    state,
                    self.name,
                    "No assessment needed at this time"
                )
                return state

        except Exception as e:
            self.log_error(e)
            state["has_error"] = True
            state["error_message"] = f"Assessment error: {str(e)}"
            return state

    async def _process_initial_assessment(self, state: AppState) -> AppState:
        """
        Process initial assessment for new users.

        Steps:
        1. Generate assessment questions for each pillar
        2. Return questions to user
        3. Process user answers
        4. Calculate scores and determine level
        """
        self.log_debug("Starting initial assessment")
        user_id = state["user"]["user_id"]

        # Check current step
        current_step = state["assessment"].get("current_step", 0)

        if current_step == 0:
            # Step 0: Generate assessment questions
            assessment_content = await self._generate_initial_assessment_content()

            state["assessment"]["is_initial"] = True
            state["assessment"]["total_steps"] = 4  # vocab, grammar, pronunciation, speaking
            state["assessment"]["current_step"] = 1

            state["response"] = {
                "type": "assessment_initial",
                "step": 1,
                "step_name": "vocabulary",
                "total_steps": 4,
                "content": assessment_content["vocabulary"],
                "instructions": "Answer the following vocabulary questions"
            }

            state = add_agent_message(
                state,
                self.name,
                "Generated initial assessment - starting with vocabulary"
            )

        else:
            # Process answers from previous step and move to next
            await self._process_assessment_step(state)

        return state

    async def _process_continuous_assessment(self, state: AppState) -> AppState:
        """
        Process continuous assessment to track progress.

        Analyzes recent performance across all pillars and recommends
        level changes if appropriate.
        """
        self.log_debug("Starting continuous assessment")
        user_id = state["user"]["user_id"]

        # Get user statistics
        stats = await self.db_service.get_user_statistics(user_id)

        # Calculate scores from recent performance
        scores = self._calculate_scores_from_stats(stats)

        # Determine if level change is warranted
        current_level = state["user"].get("current_level", "beginner")
        new_level, should_change = self._determine_level_change(
            current_level, scores, stats
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(scores, current_level)

        # Find weakest pillar
        weakest_pillar = min(scores, key=scores.get)

        # Create assessment result
        result = AssessmentResult(
            user_id=user_id,
            assessment_type="continuous",
            vocabulary_score=scores["vocabulary"],
            grammar_score=scores["grammar"],
            pronunciation_score=scores["pronunciation"],
            speaking_score=scores["speaking"],
            overall_score=sum(scores.values()) / 4,
            determined_level=new_level,
            previous_level=current_level,
            level_changed=should_change,
            weakest_pillar=weakest_pillar,
            recommendations=recommendations
        )

        # Update state
        state["assessment"]["final_scores"] = scores
        state["assessment"]["determined_level"] = new_level
        state["assessment"]["recommendations"] = recommendations
        state["assessment"]["is_continuous"] = True

        # Update user scores in state
        state["pillar_scores"] = scores

        if should_change:
            state["user"]["current_level"] = new_level
            # Update user in database
            await self.db_service.update_user(user_id, {
                "current_level": new_level,
                "vocabulary_score": int(scores["vocabulary"]),
                "grammar_score": int(scores["grammar"]),
                "pronunciation_score": int(scores["pronunciation"]),
                "speaking_score": int(scores["speaking"]),
                "last_assessment_date": datetime.utcnow().isoformat(),
                "sessions_since_last_assessment": 0
            })

        # Calculate progress towards next level
        level_progress = self._calculate_level_progress(scores, stats, current_level)

        state["response"] = {
            "type": "assessment_continuous",
            "result": result.model_dump(),
            "level_changed": should_change,
            "level_progress": level_progress,
            "message": self._generate_assessment_message(result)
        }

        state = add_agent_message(
            state,
            self.name,
            f"Continuous assessment complete. Level: {new_level}",
            {"scores": scores, "level_changed": should_change}
        )

        self.log_complete({"level": new_level, "changed": should_change})
        return state

    async def _generate_initial_assessment_content(self) -> dict:
        """Generate content for initial assessment"""
        # Vocabulary: 20 words ranging from basic to intermediate
        vocabulary_words = [
            {"word": "hello", "difficulty": 1},
            {"word": "goodbye", "difficulty": 1},
            {"word": "please", "difficulty": 1},
            {"word": "thank you", "difficulty": 1},
            {"word": "computer", "difficulty": 1},
            {"word": "beautiful", "difficulty": 2},
            {"word": "important", "difficulty": 2},
            {"word": "understand", "difficulty": 2},
            {"word": "experience", "difficulty": 2},
            {"word": "knowledge", "difficulty": 2},
            {"word": "algorithm", "difficulty": 3},
            {"word": "database", "difficulty": 3},
            {"word": "efficient", "difficulty": 3},
            {"word": "sophisticated", "difficulty": 3},
            {"word": "consequently", "difficulty": 3},
            {"word": "infrastructure", "difficulty": 4},
            {"word": "implementation", "difficulty": 4},
            {"word": "comprehensive", "difficulty": 4},
            {"word": "methodology", "difficulty": 4},
            {"word": "paradigm", "difficulty": 4}
        ]

        # Grammar: 5 rules from basic to intermediate
        grammar_rules = [
            {
                "id": "present_simple",
                "rule": "Present Simple",
                "example": "She works every day.",
                "question": "What is the correct form: 'He ___ to work every day.' (go)"
            },
            {
                "id": "past_simple",
                "rule": "Past Simple",
                "example": "I went to the store yesterday.",
                "question": "What is the correct form: 'They ___ a movie last night.' (watch)"
            },
            {
                "id": "present_perfect",
                "rule": "Present Perfect",
                "example": "I have worked here for 5 years.",
                "question": "Complete: 'She ___ never ___ to Paris.' (be)"
            },
            {
                "id": "conditionals",
                "rule": "First Conditional",
                "example": "If it rains, I will stay home.",
                "question": "Complete: 'If you ___ hard, you will pass.' (study)"
            },
            {
                "id": "passive_voice",
                "rule": "Passive Voice",
                "example": "The book was written by the author.",
                "question": "Change to passive: 'The chef cooked the meal.'"
            }
        ]

        # Pronunciation: 5 sounds problematic for Portuguese speakers
        pronunciation_sounds = [
            {
                "id": "th_voiceless",
                "phoneme": "/θ/",
                "words": ["think", "three", "through"],
                "difficulty": "high"
            },
            {
                "id": "th_voiced",
                "phoneme": "/ð/",
                "words": ["the", "this", "that"],
                "difficulty": "high"
            },
            {
                "id": "short_i",
                "phoneme": "/ɪ/",
                "words": ["sit", "bit", "ship"],
                "difficulty": "medium"
            },
            {
                "id": "r_sound",
                "phoneme": "/ɹ/",
                "words": ["red", "right", "around"],
                "difficulty": "medium"
            },
            {
                "id": "ng_sound",
                "phoneme": "/ŋ/",
                "words": ["sing", "thing", "running"],
                "difficulty": "medium"
            }
        ]

        # Speaking: Simple conversation prompts
        speaking_prompts = [
            "Tell me about yourself",
            "What did you do yesterday?",
            "Describe your job or studies"
        ]

        return {
            "vocabulary": {
                "type": "vocabulary",
                "items": vocabulary_words,
                "instructions": "For each word, provide the Portuguese translation"
            },
            "grammar": {
                "type": "grammar",
                "items": grammar_rules,
                "instructions": "Answer each grammar question"
            },
            "pronunciation": {
                "type": "pronunciation",
                "items": pronunciation_sounds,
                "instructions": "Read each word aloud for pronunciation assessment"
            },
            "speaking": {
                "type": "speaking",
                "prompts": speaking_prompts,
                "instructions": "Respond to each prompt in 1-2 sentences"
            }
        }

    async def _process_assessment_step(self, state: AppState) -> None:
        """Process the current assessment step and move to next"""
        current_step = state["assessment"]["current_step"]
        activity_input = state.get("activity_input", {})

        step_names = ["", "vocabulary", "grammar", "pronunciation", "speaking"]
        current_step_name = step_names[current_step] if current_step < len(step_names) else ""

        # Store results for current step
        results_key = f"{current_step_name}_results"
        if results_key in state["assessment"]:
            state["assessment"][results_key] = activity_input.get("results", [])

        # Move to next step or complete
        if current_step < 4:
            state["assessment"]["current_step"] = current_step + 1
            next_step_name = step_names[current_step + 1]

            # Generate content for next step
            assessment_content = await self._generate_initial_assessment_content()

            state["response"] = {
                "type": "assessment_initial",
                "step": current_step + 1,
                "step_name": next_step_name,
                "total_steps": 4,
                "content": assessment_content.get(next_step_name, {}),
                "instructions": f"Complete the {next_step_name} assessment"
            }
        else:
            # Assessment complete - calculate final results
            await self._complete_initial_assessment(state)

    async def _complete_initial_assessment(self, state: AppState) -> None:
        """Complete initial assessment and determine level"""
        user_id = state["user"]["user_id"]

        # Calculate scores from results
        vocab_results = state["assessment"].get("vocabulary_results", [])
        grammar_results = state["assessment"].get("grammar_results", [])
        pronun_results = state["assessment"].get("pronunciation_results", [])
        speaking_results = state["assessment"].get("speaking_results", [])

        scores = {
            "vocabulary": self._calculate_score(vocab_results),
            "grammar": self._calculate_score(grammar_results),
            "pronunciation": self._calculate_score(pronun_results),
            "speaking": self._calculate_score(speaking_results)
        }

        overall_score = sum(scores.values()) / 4

        # Determine level
        level = "intermediate" if overall_score >= self.settings.INTERMEDIATE_UPGRADE_THRESHOLD else "beginner"

        # Find weakest pillar
        weakest_pillar = min(scores, key=scores.get)

        # Generate recommendations
        recommendations = self._generate_recommendations(scores, level)

        # Create assessment result
        result = AssessmentResult(
            user_id=user_id,
            assessment_type="initial",
            vocabulary_score=scores["vocabulary"],
            grammar_score=scores["grammar"],
            pronunciation_score=scores["pronunciation"],
            speaking_score=scores["speaking"],
            overall_score=overall_score,
            determined_level=level,
            weakest_pillar=weakest_pillar,
            recommendations=recommendations
        )

        # Update user in database
        await self.db_service.update_user(user_id, {
            "current_level": level,
            "initial_assessment_completed": True,
            "vocabulary_score": int(scores["vocabulary"]),
            "grammar_score": int(scores["grammar"]),
            "pronunciation_score": int(scores["pronunciation"]),
            "speaking_score": int(scores["speaking"]),
            "last_assessment_date": datetime.utcnow().isoformat(),
            "sessions_since_last_assessment": 0
        })

        # Update state
        state["assessment"]["final_scores"] = scores
        state["assessment"]["determined_level"] = level
        state["assessment"]["recommendations"] = recommendations
        state["user"]["current_level"] = level
        state["user"]["initial_assessment_completed"] = True
        state["pillar_scores"] = scores

        state["response"] = {
            "type": "assessment_complete",
            "result": result.model_dump(),
            "message": self._generate_assessment_message(result)
        }

        state = add_agent_message(
            state,
            self.name,
            f"Initial assessment complete. Level: {level}",
            {"scores": scores}
        )

    def _should_run_assessment(self, state: AppState) -> bool:
        """Check if continuous assessment should run"""
        if not state["user"].get("initial_assessment_completed", False):
            return False

        sessions = state["user"].get("sessions_since_last_assessment", 0)
        return sessions >= self.settings.CONTINUOUS_ASSESSMENT_FREQUENCY

    def _calculate_score(self, results: list[dict]) -> float:
        """Calculate score from assessment results"""
        if not results:
            return 0.0

        correct = sum(1 for r in results if r.get("correct", False))
        return (correct / len(results)) * 100

    def _calculate_scores_from_stats(self, stats: dict) -> dict:
        """Calculate pillar scores from user statistics"""
        scores = {
            "vocabulary": 0.0,
            "grammar": 0.0,
            "pronunciation": 0.0,
            "speaking": 0.0
        }

        # Vocabulary score based on mastery
        vocab_stats = stats.get("vocabulary", {})
        total_words = vocab_stats.get("total_words", 0)
        mastered = vocab_stats.get("mastered", 0)
        if total_words > 0:
            scores["vocabulary"] = (mastered / total_words) * 100

        # Grammar score
        grammar_stats = stats.get("grammar", {})
        scores["grammar"] = grammar_stats.get("average_score", 0)

        # Pronunciation score
        pronun_stats = stats.get("pronunciation", {})
        scores["pronunciation"] = pronun_stats.get("average_accuracy", 0)

        # Speaking score (based on sessions)
        speaking_stats = stats.get("speaking", {})
        sessions = speaking_stats.get("sessions_last_30_days", 0)
        # More sessions = higher score (up to 100)
        scores["speaking"] = min(sessions * 10, 100)

        return scores

    def _determine_level_change(
        self,
        current_level: str,
        scores: dict,
        stats: dict = None
    ) -> tuple[str, bool]:
        """
        Determine if user should change level.

        Upgrade criteria (beginner -> intermediate):
        - Overall score >= 85% (INTERMEDIATE_UPGRADE_THRESHOLD)
        - All pillars >= 75%
        - At least 50 vocabulary words mastered
        - At least 10 grammar rules practiced with good scores
        - At least 5 pronunciation sounds mastered
        - At least 3 speaking sessions completed

        Downgrade criteria (intermediate -> beginner):
        - Overall score < 65% for extended period

        Returns:
            Tuple of (new_level, should_change)
        """
        overall = sum(scores.values()) / 4
        threshold = self.settings.INTERMEDIATE_UPGRADE_THRESHOLD
        min_pillar_score = threshold - 10  # 75%

        if current_level == "beginner":
            # Check if ready for intermediate
            if overall >= threshold and all(s >= min_pillar_score for s in scores.values()):
                # Additional mastery requirements if stats available
                if stats:
                    vocab_stats = stats.get("vocabulary", {})
                    grammar_stats = stats.get("grammar", {})
                    pronun_stats = stats.get("pronunciation", {})
                    speaking_stats = stats.get("speaking", {})

                    # Minimum mastery requirements for level upgrade
                    vocab_mastered = vocab_stats.get("mastered", 0) >= 50
                    grammar_practiced = grammar_stats.get("rules_practiced", 0) >= 10
                    pronun_mastered = pronun_stats.get("mastered", 0) >= 5
                    speaking_sessions = speaking_stats.get("total_sessions", 0) >= 3

                    if all([vocab_mastered, grammar_practiced, pronun_mastered, speaking_sessions]):
                        return "intermediate", True
                    else:
                        # Not enough content mastered yet
                        return current_level, False
                else:
                    # Without stats, use score-based upgrade
                    return "intermediate", True
        else:
            # Intermediate - check if should downgrade (rare)
            if overall < threshold - 20:  # Below 65%
                return "beginner", True

        return current_level, False

    def _calculate_level_progress(
        self,
        scores: dict,
        stats: dict,
        current_level: str
    ) -> dict:
        """
        Calculate user's progress towards the next level.

        Returns detailed progress breakdown for each requirement.
        """
        if current_level != "beginner":
            # Already at highest level
            return {
                "current_level": current_level,
                "next_level": None,
                "overall_progress": 100,
                "message": "Você está no nível mais alto! Continue praticando para manter sua fluência."
            }

        threshold = self.settings.INTERMEDIATE_UPGRADE_THRESHOLD
        min_pillar_score = threshold - 10

        # Calculate progress for each criterion
        vocab_stats = stats.get("vocabulary", {}) if stats else {}
        grammar_stats = stats.get("grammar", {}) if stats else {}
        pronun_stats = stats.get("pronunciation", {}) if stats else {}
        speaking_stats = stats.get("speaking", {}) if stats else {}

        progress = {
            "current_level": current_level,
            "next_level": "intermediate",
            "requirements": {
                "overall_score": {
                    "label": "Pontuação Geral",
                    "current": sum(scores.values()) / 4,
                    "target": threshold,
                    "met": sum(scores.values()) / 4 >= threshold
                },
                "vocabulary_score": {
                    "label": "Pontuação de Vocabulário",
                    "current": scores.get("vocabulary", 0),
                    "target": min_pillar_score,
                    "met": scores.get("vocabulary", 0) >= min_pillar_score
                },
                "grammar_score": {
                    "label": "Pontuação de Gramática",
                    "current": scores.get("grammar", 0),
                    "target": min_pillar_score,
                    "met": scores.get("grammar", 0) >= min_pillar_score
                },
                "pronunciation_score": {
                    "label": "Pontuação de Pronúncia",
                    "current": scores.get("pronunciation", 0),
                    "target": min_pillar_score,
                    "met": scores.get("pronunciation", 0) >= min_pillar_score
                },
                "speaking_score": {
                    "label": "Pontuação de Conversação",
                    "current": scores.get("speaking", 0),
                    "target": min_pillar_score,
                    "met": scores.get("speaking", 0) >= min_pillar_score
                },
                "vocabulary_mastered": {
                    "label": "Palavras Dominadas",
                    "current": vocab_stats.get("mastered", 0),
                    "target": 50,
                    "met": vocab_stats.get("mastered", 0) >= 50
                },
                "grammar_practiced": {
                    "label": "Regras de Gramática Praticadas",
                    "current": grammar_stats.get("rules_practiced", 0),
                    "target": 10,
                    "met": grammar_stats.get("rules_practiced", 0) >= 10
                },
                "pronunciation_mastered": {
                    "label": "Sons Dominados",
                    "current": pronun_stats.get("mastered", 0),
                    "target": 5,
                    "met": pronun_stats.get("mastered", 0) >= 5
                },
                "speaking_sessions": {
                    "label": "Sessões de Conversação",
                    "current": speaking_stats.get("total_sessions", 0),
                    "target": 3,
                    "met": speaking_stats.get("total_sessions", 0) >= 3
                }
            }
        }

        # Calculate overall progress percentage
        requirements_met = sum(1 for req in progress["requirements"].values() if req["met"])
        total_requirements = len(progress["requirements"])
        progress["overall_progress"] = int((requirements_met / total_requirements) * 100)
        progress["requirements_met"] = requirements_met
        progress["total_requirements"] = total_requirements

        # Generate progress message
        if progress["overall_progress"] >= 100:
            progress["message"] = "Parabéns! Você está pronto para avançar para o nível Intermediário!"
        elif progress["overall_progress"] >= 75:
            progress["message"] = "Você está quase lá! Continue praticando para alcançar o nível Intermediário."
        elif progress["overall_progress"] >= 50:
            progress["message"] = "Bom progresso! Metade dos requisitos já foram cumpridos."
        else:
            progress["message"] = "Continue praticando! Cada sessão te aproxima do próximo nível."

        return progress

    def _generate_recommendations(
        self,
        scores: dict,
        level: str
    ) -> list[str]:
        """Generate personalized recommendations based on scores"""
        recommendations = []

        # Find weak areas
        for pillar, score in scores.items():
            if score < 60:
                recommendations.append(
                    f"Focus more on {pillar} - your score is {score:.0f}%"
                )
            elif score < 80:
                recommendations.append(
                    f"Keep practicing {pillar} - almost there!"
                )

        # Level-specific recommendations
        if level == "beginner":
            recommendations.append(
                "Continue with basic vocabulary and grammar foundations"
            )
            recommendations.append(
                "Practice pronunciation of common sounds daily"
            )
        else:
            recommendations.append(
                "Try more advanced vocabulary in technical contexts"
            )
            recommendations.append(
                "Practice connected speech and natural conversation"
            )

        return recommendations[:5]  # Limit to 5 recommendations

    def _generate_assessment_message(self, result: AssessmentResult) -> str:
        """Generate a user-friendly assessment message"""
        level = result.determined_level.capitalize()
        overall = result.overall_score

        if result.level_changed:
            return (
                f"Congratulations! Based on your performance, you've been "
                f"moved to {level} level. Your overall score is {overall:.0f}%. "
                f"Focus on: {result.weakest_pillar}"
            )

        return (
            f"Assessment complete! Your current level is {level} "
            f"with an overall score of {overall:.0f}%. "
            f"Focus area: {result.weakest_pillar}"
        )


# Singleton instance
assessment_agent = AssessmentAgent()
