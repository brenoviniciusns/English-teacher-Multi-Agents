"""
Vocabulary API Endpoints
REST API for vocabulary learning features.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from app.agents.vocabulary_agent import vocabulary_agent
from app.agents.orchestrator import run_orchestrator
from app.agents.state import create_initial_state
from app.schemas.vocabulary import (
    VocabularyExerciseRequest,
    VocabularyAnswerRequest,
    VocabularyExerciseResponse,
    VocabularyAnswerResponse,
    VocabularyProgressResponse,
    ReviewListResponse,
    WordDetailResponse,
    WordDetail,
    WordToReview,
    ExerciseContent
)
from app.services.cosmos_db_service import cosmos_db_service


logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== EXERCISE ENDPOINTS ====================

@router.get("/next-activity", response_model=VocabularyExerciseResponse)
async def get_next_vocabulary_activity(
    user_id: str = Query(..., description="User ID"),
    context: str = Query(default="general", description="Context: general, data_engineering, ai, technology")
):
    """
    Get the next vocabulary exercise for the user.

    Uses SRS algorithm to select the best word:
    1. Words due for review (overdue first)
    2. Words with low frequency usage
    3. New words

    Returns a fill-in-the-blank exercise with multiple choice options.
    """
    try:
        # Run through orchestrator
        state = await run_orchestrator(
            user_id=user_id,
            request_type="vocabulary_exercise",
            input_data={"context": context}
        )

        response = state.get("response", {})

        # Convert to response model
        if response.get("status") == "success":
            exercise_data = response.get("exercise", {})
            return VocabularyExerciseResponse(
                type=response.get("type", "vocabulary_exercise"),
                status="success",
                activity_id=response.get("activity_id"),
                word_id=response.get("word_id"),
                word=response.get("word"),
                part_of_speech=response.get("part_of_speech"),
                ipa_pronunciation=response.get("ipa_pronunciation"),
                exercise=ExerciseContent(
                    type=exercise_data.get("type", "fill_in_blank"),
                    sentence=exercise_data.get("sentence", ""),
                    options=exercise_data.get("options", []),
                    context=exercise_data.get("context", "general")
                )
            )
        else:
            return VocabularyExerciseResponse(
                type="vocabulary_exercise",
                status=response.get("status", "error"),
                message=response.get("message", "Erro ao gerar exercício")
            )

    except Exception as e:
        logger.error(f"Error getting vocabulary activity: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter exercício de vocabulário: {str(e)}"
        )


@router.post("/submit-answer", response_model=VocabularyAnswerResponse)
async def submit_vocabulary_answer(
    request: VocabularyAnswerRequest,
    user_id: str = Query(..., description="User ID")
):
    """
    Submit an answer for a vocabulary exercise.

    Processes the answer, updates SRS data, and returns feedback.
    """
    try:
        # Get user data
        user_data = await cosmos_db_service.get_user(user_id)

        # Create state with answer data
        state = create_initial_state(user_id, "vocabulary_exercise", user_data)
        state["activity_input"] = {
            "answer": request.answer,
            "word_id": request.word_id,
            "response_time_ms": request.response_time_ms
        }

        # Get the current activity (if stored)
        # In a real implementation, this would be retrieved from session/cache
        state["current_activity"] = {
            "activity_id": request.activity_id,
            "content": {
                "word_id": request.word_id,
                "exercise": {}  # Would be retrieved from cache
            }
        }

        # Process through vocabulary agent
        result_state = await vocabulary_agent.process(state)

        response = result_state.get("response", {})

        if response.get("status") == "success":
            return VocabularyAnswerResponse(
                type="vocabulary_answer",
                status="success",
                correct=response.get("correct", False),
                user_answer=response.get("user_answer", request.answer),
                correct_answer=response.get("correct_answer", ""),
                explanation=response.get("explanation"),
                example_usage=response.get("example_usage"),
                mastery_level=response.get("mastery_level"),
                next_review_days=response.get("next_review_days"),
                streak=response.get("streak", 0)
            )
        else:
            return VocabularyAnswerResponse(
                type="vocabulary_answer",
                status="error",
                correct=False,
                user_answer=request.answer,
                correct_answer="",
                message=response.get("message", "Erro ao processar resposta")
            )

    except Exception as e:
        logger.error(f"Error submitting vocabulary answer: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao submeter resposta: {str(e)}"
        )


# ==================== PROGRESS ENDPOINTS ====================

@router.get("/progress", response_model=VocabularyProgressResponse)
async def get_vocabulary_progress(
    user_id: str = Query(..., description="User ID")
):
    """
    Get vocabulary learning progress for a user.

    Returns statistics including:
    - Total words learned
    - Mastery levels breakdown
    - Words due for review
    - Average accuracy
    """
    try:
        stats = await vocabulary_agent.get_user_vocabulary_stats(user_id)

        return VocabularyProgressResponse(
            total_words=stats.get("total_words", 0),
            mastered=stats.get("mastered", 0),
            reviewing=stats.get("reviewing", 0),
            learning=stats.get("learning", 0),
            new_words=stats.get("new", 0),
            due_for_review=stats.get("due_for_review", 0),
            average_accuracy=stats.get("average_accuracy", 0.0)
        )

    except Exception as e:
        logger.error(f"Error getting vocabulary progress: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter progresso: {str(e)}"
        )


@router.get("/review-list", response_model=ReviewListResponse)
async def get_review_list(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum words to return")
):
    """
    Get list of words due for review.

    Returns words sorted by priority (most overdue first).
    """
    try:
        words = await vocabulary_agent.get_words_to_review(user_id, limit)

        review_words = [
            WordToReview(
                word_id=w["word_id"],
                word=w["word"],
                definition=w["definition"],
                mastery_level=w["mastery_level"],
                last_practiced=w.get("last_practiced")
            )
            for w in words
        ]

        # Get total due count
        stats = await vocabulary_agent.get_user_vocabulary_stats(user_id)

        return ReviewListResponse(
            words=review_words,
            total_due=stats.get("due_for_review", len(words))
        )

    except Exception as e:
        logger.error(f"Error getting review list: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter lista de revisão: {str(e)}"
        )


# ==================== WORD DETAIL ENDPOINTS ====================

@router.get("/word/{word_id}", response_model=WordDetailResponse)
async def get_word_detail(
    word_id: str,
    user_id: Optional[str] = Query(default=None, description="User ID for progress info")
):
    """
    Get detailed information about a specific word.

    If user_id is provided, includes user's progress on this word.
    """
    try:
        # Load word data
        await vocabulary_agent._load_words()

        # Find word in caches
        word_data = vocabulary_agent._words_cache.get(word_id)
        if not word_data:
            word_data = vocabulary_agent._technical_words_cache.get(word_id)

        if not word_data:
            raise HTTPException(
                status_code=404,
                detail=f"Palavra não encontrada: {word_id}"
            )

        # Create word detail
        word_detail = WordDetail(
            id=word_data["id"],
            word=word_data["word"],
            part_of_speech=word_data["part_of_speech"],
            definition=word_data["definition"],
            example_sentence=word_data["example_sentence"],
            ipa_pronunciation=word_data["ipa_pronunciation"],
            portuguese_translation=word_data.get("portuguese_translation"),
            category=word_data.get("category", "common"),
            difficulty=word_data.get("difficulty", "beginner")
        )

        has_progress = False

        # Get user progress if user_id provided
        if user_id:
            progress = await cosmos_db_service.get_vocabulary_progress(user_id, word_id)
            if progress:
                has_progress = True
                word_detail.mastery_level = progress.get("masteryLevel")
                word_detail.practice_count = progress.get("practiceCount")
                word_detail.correct_count = progress.get("correctCount")
                word_detail.last_practiced = progress.get("lastPracticed")
                word_detail.next_review = progress.get("srsData", {}).get("nextReview")

        return WordDetailResponse(
            word=word_detail,
            has_progress=has_progress
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting word detail: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter detalhes da palavra: {str(e)}"
        )


# ==================== WORD LIST ENDPOINTS ====================

@router.get("/words")
async def list_words(
    category: str = Query(default="common", description="Category: common, technical"),
    difficulty: Optional[str] = Query(default=None, description="Difficulty: beginner, intermediate"),
    subcategory: Optional[str] = Query(default=None, description="Technical subcategory"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum words to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination")
):
    """
    List available vocabulary words with filtering.

    Supports filtering by category, difficulty, and subcategory.
    """
    try:
        await vocabulary_agent._load_words()

        # Select word source
        if category == "technical":
            words = list(vocabulary_agent._technical_words_cache.values())
        else:
            words = list(vocabulary_agent._words_cache.values())

        # Apply filters
        if difficulty:
            words = [w for w in words if w.get("difficulty") == difficulty]

        if subcategory:
            words = [w for w in words if w.get("subcategory") == subcategory]

        # Sort by frequency rank
        words.sort(key=lambda x: x.get("frequency_rank", 9999))

        # Apply pagination
        total = len(words)
        words = words[offset:offset + limit]

        return {
            "words": [
                {
                    "id": w["id"],
                    "word": w["word"],
                    "part_of_speech": w["part_of_speech"],
                    "definition": w["definition"],
                    "difficulty": w.get("difficulty"),
                    "category": w.get("category")
                }
                for w in words
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error listing words: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar palavras: {str(e)}"
        )
