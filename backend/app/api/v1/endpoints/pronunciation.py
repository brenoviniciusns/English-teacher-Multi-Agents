"""
Pronunciation API Endpoints
REST endpoints for pronunciation learning functionality.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.agents.pronunciation_agent import pronunciation_agent
from app.agents.state import create_initial_state
from app.schemas.pronunciation import (
    PronunciationExerciseRequest,
    PronunciationExerciseResponse,
    ShadowingSubmitRequest,
    ShadowingResultResponse,
    PronunciationProgressResponse,
    SoundsToReviewResponse,
    SoundToReview,
    PhoneticSoundsListResponse,
    PhoneticSoundSummary,
    PhonemeGuidanceResponse,
    MouthPositionInfo
)


router = APIRouter()


# Store active activities in memory (in production, use Redis or similar)
_active_activities: dict[str, dict] = {}


@router.get(
    "/next-exercise",
    response_model=PronunciationExerciseResponse,
    summary="Get next pronunciation exercise",
    description="Get the next pronunciation/shadowing exercise based on SRS and user progress."
)
async def get_next_exercise(
    user_id: str = Query(..., description="User ID"),
    sound_id: Optional[str] = Query(None, description="Specific sound ID to practice"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (low, medium, high)"),
    exercise_type: str = Query("shadowing", description="Exercise type: shadowing, minimal_pair, word_practice")
) -> PronunciationExerciseResponse:
    """
    Get the next pronunciation exercise for a user.

    Priority:
    1. Specific sound if requested
    2. Sounds due for SRS review
    3. Sounds with low accuracy (needs practice)
    4. Sounds with low frequency usage
    5. New sounds not yet studied
    """
    try:
        # Create state for the request
        state = create_initial_state(user_id, "pronunciation_exercise")
        state["activity_input"] = {
            "sound_id": sound_id,
            "difficulty": difficulty,
            "exercise_type": exercise_type
        }

        # Process through pronunciation agent
        result_state = await pronunciation_agent.process(state)

        # Check for errors
        if result_state.get("has_error"):
            raise HTTPException(
                status_code=500,
                detail=result_state.get("error_message", "Erro ao gerar exercício")
            )

        response = result_state.get("response", {})

        # Store activity for audio submission
        if response.get("status") == "success":
            activity_id = response.get("activity_id")
            if activity_id:
                _active_activities[activity_id] = result_state.get("current_activity", {})

        return PronunciationExerciseResponse(**response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/submit-audio",
    response_model=ShadowingResultResponse,
    summary="Submit audio for pronunciation assessment",
    description="Submit recorded audio for pronunciation assessment."
)
async def submit_audio(
    user_id: str = Query(..., description="User ID"),
    request: ShadowingSubmitRequest = ...
) -> ShadowingResultResponse:
    """
    Submit audio recording for pronunciation assessment.

    The audio is assessed using Azure Speech Services for:
    - Accuracy: How close to native pronunciation
    - Fluency: Smoothness of speech
    - Completeness: Coverage of expected sounds
    - Overall pronunciation score
    """
    try:
        # Create state for the request
        state = create_initial_state(user_id, "shadowing")
        state["activity_input"] = {
            "sound_id": request.sound_id,
            "word": request.word,
            "reference_text": request.reference_text,
            "audio_base64": request.audio_base64,
            "attempt_number": request.attempt_number
        }

        # Get any existing activity context
        for activity_id, activity in _active_activities.items():
            if activity.get("content", {}).get("sound_id") == request.sound_id:
                state["current_activity"] = activity
                break

        # Process through pronunciation agent
        result_state = await pronunciation_agent.process(state)

        if result_state.get("has_error"):
            raise HTTPException(
                status_code=500,
                detail=result_state.get("error_message", "Erro ao avaliar pronúncia")
            )

        response = result_state.get("response", {})
        return ShadowingResultResponse(**response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/progress",
    response_model=PronunciationProgressResponse,
    summary="Get pronunciation progress",
    description="Get user's pronunciation learning progress and statistics."
)
async def get_progress(
    user_id: str = Query(..., description="User ID")
) -> PronunciationProgressResponse:
    """
    Get pronunciation learning statistics for a user.

    Includes:
    - Mastery counts (mastered, practicing, needs work)
    - Sounds due for review
    - Average accuracy
    - Hardest and best sounds
    """
    try:
        stats = await pronunciation_agent.get_user_pronunciation_stats(user_id)
        return PronunciationProgressResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/review-list",
    response_model=SoundsToReviewResponse,
    summary="Get sounds to review",
    description="Get list of phonetic sounds due for review."
)
async def get_review_list(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(10, ge=1, le=50, description="Maximum sounds to return")
) -> SoundsToReviewResponse:
    """
    Get phonetic sounds that need review.

    Includes sounds due for:
    - SRS scheduled review
    - Low accuracy (below passing threshold)
    - Low practice frequency
    """
    try:
        sounds = await pronunciation_agent.get_sounds_to_review(user_id, limit)

        # Count by reason
        srs_due = sum(1 for s in sounds if s.get("review_reason") == "srs_due")
        low_accuracy = sum(1 for s in sounds if s.get("review_reason") == "low_accuracy")
        low_frequency = sum(1 for s in sounds if s.get("review_reason") == "low_frequency")

        return SoundsToReviewResponse(
            sounds=[SoundToReview(**s) for s in sounds],
            total_due=len(sounds),
            srs_due=srs_due,
            low_accuracy_due=low_accuracy,
            low_frequency_due=low_frequency
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/sounds",
    response_model=PhoneticSoundsListResponse,
    summary="List phonetic sounds",
    description="Get all available phonetic sounds with optional filtering."
)
async def list_sounds(
    user_id: Optional[str] = Query(None, description="User ID for progress info"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (low, medium, high)")
) -> PhoneticSoundsListResponse:
    """
    Get all available phonetic sounds.

    Optionally includes user progress if user_id provided.
    """
    try:
        sounds = await pronunciation_agent.get_all_sounds(
            user_id=user_id,
            difficulty=difficulty
        )

        difficulties = pronunciation_agent.get_available_difficulties()

        return PhoneticSoundsListResponse(
            sounds=[
                PhoneticSoundSummary(
                    id=s["id"],
                    phoneme=s["phoneme"],
                    name=s["name"],
                    difficulty=s.get("difficulty", "medium"),
                    exists_in_portuguese=s.get("exists_in_portuguese", False),
                    example_words=s.get("example_words", [])[:3],
                    user_accuracy=s.get("user_accuracy"),
                    practice_count=s.get("user_practice_count"),
                    mastered=s.get("user_mastered")
                )
                for s in sounds
            ],
            total=len(sounds),
            difficulties=difficulties
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/sound/{sound_id}",
    response_model=PronunciationExerciseResponse,
    summary="Get specific sound",
    description="Get a specific phonetic sound by ID with exercise."
)
async def get_sound(
    sound_id: str,
    user_id: str = Query(..., description="User ID")
) -> PronunciationExerciseResponse:
    """
    Get a specific phonetic sound with full details and exercise.
    """
    try:
        # Create state for the request with specific sound
        state = create_initial_state(user_id, "pronunciation_exercise")
        state["activity_input"] = {
            "sound_id": sound_id,
            "exercise_type": "shadowing"
        }

        # Process through pronunciation agent
        result_state = await pronunciation_agent.process(state)

        if result_state.get("has_error"):
            raise HTTPException(
                status_code=500,
                detail=result_state.get("error_message", "Erro ao carregar som")
            )

        response = result_state.get("response", {})

        if response.get("status") == "no_sounds":
            raise HTTPException(
                status_code=404,
                detail=f"Som '{sound_id}' não encontrado"
            )

        # Store activity
        if response.get("status") == "success":
            activity_id = response.get("activity_id")
            if activity_id:
                _active_activities[activity_id] = result_state.get("current_activity", {})

        return PronunciationExerciseResponse(**response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/phoneme-guidance/{phoneme}",
    response_model=PhonemeGuidanceResponse,
    summary="Get phoneme guidance",
    description="Get detailed guidance for pronouncing a specific phoneme."
)
async def get_phoneme_guidance(
    phoneme: str
) -> PhonemeGuidanceResponse:
    """
    Get detailed guidance for a specific phoneme.

    Includes:
    - Mouth position diagrams
    - Common mistakes by Portuguese speakers
    - Tips for correct pronunciation
    - Example words
    """
    try:
        guidance = await pronunciation_agent.get_phoneme_guidance(phoneme)

        if not guidance or guidance.get("name") == "Unknown phoneme":
            raise HTTPException(
                status_code=404,
                detail=f"Fonema '{phoneme}' não encontrado"
            )

        # Convert mouth_position to proper schema
        mouth_position = guidance.get("mouth_position", {})
        if isinstance(mouth_position, dict):
            mouth_position_info = MouthPositionInfo(
                tongue=mouth_position.get("tongue", ""),
                lips=mouth_position.get("lips", ""),
                teeth=mouth_position.get("teeth"),
                jaw=mouth_position.get("jaw"),
                airflow=mouth_position.get("airflow"),
                voicing=mouth_position.get("voicing")
            )
        else:
            mouth_position_info = MouthPositionInfo(tongue="", lips="")

        return PhonemeGuidanceResponse(
            phoneme=guidance.get("phoneme", phoneme),
            name=guidance.get("name", ""),
            ipa=guidance.get("ipa", phoneme),
            mouth_position=mouth_position_info,
            example_words=guidance.get("example_words", []),
            common_mistake=guidance.get("common_mistake", ""),
            tip=guidance.get("tip", ""),
            portuguese_similar=guidance.get("portuguese_similar"),
            video_url=guidance.get("video_url"),
            diagram_url=guidance.get("diagram_url")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/difficulties",
    summary="List difficulty levels",
    description="Get all available difficulty levels for phonetic sounds."
)
async def list_difficulties() -> dict:
    """
    Get all available difficulty levels with counts.
    """
    try:
        await pronunciation_agent._load_sounds()
        difficulties = pronunciation_agent.get_available_difficulties()

        # Get count per difficulty
        difficulty_counts = {
            diff: len(sounds)
            for diff, sounds in pronunciation_agent._sounds_by_difficulty.items()
        }

        return {
            "difficulties": difficulties,
            "counts": difficulty_counts,
            "total_sounds": sum(difficulty_counts.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/problematic-sounds",
    summary="Get sounds problematic for Portuguese speakers",
    description="Get phonetic sounds that don't exist in Portuguese."
)
async def get_problematic_sounds(
    user_id: Optional[str] = Query(None, description="User ID for progress info")
) -> dict:
    """
    Get sounds that are typically difficult for Portuguese speakers.

    These are sounds that don't exist in Portuguese and require
    special attention and practice.
    """
    try:
        sounds = await pronunciation_agent.get_all_sounds(user_id=user_id)

        # Filter to sounds that don't exist in Portuguese
        problematic = [
            {
                "id": s["id"],
                "phoneme": s["phoneme"],
                "name": s["name"],
                "difficulty": s.get("difficulty", "medium"),
                "common_mistake": s.get("common_mistake", ""),
                "tip": s.get("tip", ""),
                "example_words": s.get("example_words", [])[:3],
                "user_accuracy": s.get("user_accuracy"),
                "user_mastered": s.get("user_mastered")
            }
            for s in sounds
            if not s.get("exists_in_portuguese", True)
        ]

        # Sort by difficulty (high first for awareness)
        difficulty_order = {"high": 0, "medium": 1, "low": 2}
        problematic.sort(key=lambda x: difficulty_order.get(x["difficulty"], 1))

        return {
            "sounds": problematic,
            "total": len(problematic),
            "message": "Estes sons não existem em português e requerem atenção especial."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
