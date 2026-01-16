"""
Grammar API Endpoints
REST endpoints for grammar learning functionality.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.agents.grammar_agent import grammar_agent
from app.agents.state import create_initial_state
from app.schemas.grammar import (
    GrammarLessonRequest,
    GrammarLessonResponse,
    GrammarExplanationRequest,
    GrammarExplanationResponse,
    GrammarExerciseRequest,
    GrammarExercisesResponse,
    GrammarExerciseAnswerRequest,
    GrammarExerciseAnswerResponse,
    GrammarProgressResponse,
    ReviewListResponse,
    RuleToReview,
    GrammarRulesListResponse,
    GrammarRuleSummary
)


router = APIRouter()


# Store active activities in memory (in production, use Redis or similar)
_active_activities: dict[str, dict] = {}


@router.get(
    "/next-lesson",
    response_model=GrammarLessonResponse,
    summary="Get next grammar lesson",
    description="Get the next grammar rule to study based on SRS and user progress."
)
async def get_next_lesson(
    user_id: str = Query(..., description="User ID"),
    rule_id: Optional[str] = Query(None, description="Specific rule ID to study"),
    category: Optional[str] = Query(None, description="Filter by category")
) -> GrammarLessonResponse:
    """
    Get the next grammar lesson for a user.

    Priority:
    1. Specific rule if requested
    2. Rules due for SRS review
    3. Rules with low frequency
    4. New rules not yet studied
    """
    try:
        # Create state for the request
        state = create_initial_state(user_id, "grammar_lesson")
        state["activity_input"] = {
            "rule_id": rule_id,
            "category": category
        }

        # Process through grammar agent
        result_state = await grammar_agent.process(state)

        # Check for errors
        if result_state.get("has_error"):
            raise HTTPException(
                status_code=500,
                detail=result_state.get("error_message", "Erro ao processar lição")
            )

        response = result_state.get("response", {})

        # Store activity for answer submission
        if response.get("status") == "success":
            activity_id = response.get("activity_id")
            if activity_id:
                _active_activities[activity_id] = result_state.get("current_activity", {})

        return GrammarLessonResponse(**response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/submit-explanation",
    response_model=GrammarExplanationResponse,
    summary="Submit grammar rule explanation",
    description="Submit user's explanation of a grammar rule for evaluation."
)
async def submit_explanation(
    user_id: str = Query(..., description="User ID"),
    request: GrammarExplanationRequest = ...
) -> GrammarExplanationResponse:
    """
    Submit and evaluate user's explanation of a grammar rule.

    The explanation is evaluated by GPT-4 for:
    - Accuracy: How correct is the explanation
    - Completeness: Coverage of key points
    - Understanding: True comprehension level
    """
    try:
        # Create state for the request
        state = create_initial_state(user_id, "grammar_lesson")
        state["activity_input"] = {
            "rule_id": request.rule_id,
            "explanation": request.explanation
        }

        # Get any existing activity context
        for activity_id, activity in _active_activities.items():
            if activity.get("content", {}).get("rule_id") == request.rule_id:
                state["current_activity"] = activity
                break

        # Process through grammar agent
        result_state = await grammar_agent.process(state)

        if result_state.get("has_error"):
            raise HTTPException(
                status_code=500,
                detail=result_state.get("error_message", "Erro ao avaliar explicação")
            )

        response = result_state.get("response", {})
        return GrammarExplanationResponse(**response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/exercises",
    response_model=GrammarExercisesResponse,
    summary="Get grammar exercises",
    description="Get practice exercises for a specific grammar rule."
)
async def get_exercises(
    user_id: str = Query(..., description="User ID"),
    rule_id: str = Query(..., description="Rule ID to practice"),
    count: int = Query(5, ge=1, le=10, description="Number of exercises")
) -> GrammarExercisesResponse:
    """
    Generate practice exercises for a grammar rule.

    Exercises are generated via GPT-4 and include:
    - Fill-in-the-blank
    - Error correction
    - Sentence completion
    """
    try:
        state = create_initial_state(user_id, "grammar_exercise")
        state["activity_input"] = {
            "rule_id": rule_id,
            "count": count
        }

        result_state = await grammar_agent.process(state)

        if result_state.get("has_error"):
            raise HTTPException(
                status_code=500,
                detail=result_state.get("error_message", "Erro ao gerar exercícios")
            )

        response = result_state.get("response", {})

        # Store activity for answer tracking
        if response.get("status") == "success":
            activity_id = response.get("activity_id")
            if activity_id:
                _active_activities[activity_id] = result_state.get("current_activity", {})

        return GrammarExercisesResponse(**response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/submit-exercise",
    response_model=GrammarExerciseAnswerResponse,
    summary="Submit exercise answer",
    description="Submit an answer for a grammar exercise."
)
async def submit_exercise_answer(
    user_id: str = Query(..., description="User ID"),
    request: GrammarExerciseAnswerRequest = ...
) -> GrammarExerciseAnswerResponse:
    """
    Submit an answer for a grammar exercise.

    Returns whether the answer was correct and updates progress.
    """
    try:
        # Get the activity context
        activity = _active_activities.get(request.activity_id)
        if not activity:
            raise HTTPException(
                status_code=404,
                detail="Atividade não encontrada. Por favor, solicite novos exercícios."
            )

        state = create_initial_state(user_id, "grammar_exercise")
        state["current_activity"] = activity
        state["activity_input"] = {
            "rule_id": request.rule_id,
            "answer": request.answer,
            "exercise_index": request.exercise_index,
            "response_time_ms": request.response_time_ms
        }

        result_state = await grammar_agent.process(state)

        if result_state.get("has_error"):
            raise HTTPException(
                status_code=500,
                detail=result_state.get("error_message", "Erro ao processar resposta")
            )

        # Update stored activity
        if result_state.get("current_activity"):
            _active_activities[request.activity_id] = result_state["current_activity"]

        response = result_state.get("response", {})
        return GrammarExerciseAnswerResponse(**response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/progress",
    response_model=GrammarProgressResponse,
    summary="Get grammar progress",
    description="Get user's grammar learning progress and statistics."
)
async def get_progress(
    user_id: str = Query(..., description="User ID")
) -> GrammarProgressResponse:
    """
    Get grammar learning statistics for a user.

    Includes:
    - Mastery levels count
    - Rules due for review
    - Average explanation score
    - Best and weak categories
    """
    try:
        stats = await grammar_agent.get_user_grammar_stats(user_id)
        return GrammarProgressResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/review-list",
    response_model=ReviewListResponse,
    summary="Get rules to review",
    description="Get list of grammar rules due for review."
)
async def get_review_list(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(10, ge=1, le=50, description="Maximum rules to return")
) -> ReviewListResponse:
    """
    Get grammar rules that are due for SRS review.
    """
    try:
        rules = await grammar_agent.get_rules_to_review(user_id, limit)

        return ReviewListResponse(
            rules=[RuleToReview(**r) for r in rules],
            total_due=len(rules)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/rules",
    response_model=GrammarRulesListResponse,
    summary="List grammar rules",
    description="Get all available grammar rules with optional filtering."
)
async def list_rules(
    user_id: Optional[str] = Query(None, description="User ID for progress info"),
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty")
) -> GrammarRulesListResponse:
    """
    Get all available grammar rules.

    Optionally includes user progress if user_id provided.
    """
    try:
        rules = await grammar_agent.get_all_rules(
            user_id=user_id,
            category=category,
            difficulty=difficulty
        )

        categories = grammar_agent.get_available_categories()

        return GrammarRulesListResponse(
            rules=[
                GrammarRuleSummary(
                    id=r["id"],
                    name=r["name"],
                    category=r.get("category", "other"),
                    difficulty=r.get("difficulty", "beginner"),
                    exists_in_portuguese=r.get("exists_in_portuguese", True),
                    mastery_level=r.get("user_mastery_level"),
                    practice_count=r.get("user_practice_count"),
                    best_explanation_score=r.get("user_best_score")
                )
                for r in rules
            ],
            total=len(rules),
            categories=categories
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/rule/{rule_id}",
    response_model=GrammarLessonResponse,
    summary="Get specific rule",
    description="Get a specific grammar rule by ID."
)
async def get_rule(
    rule_id: str,
    user_id: Optional[str] = Query(None, description="User ID for progress info")
) -> GrammarLessonResponse:
    """
    Get a specific grammar rule with full details.
    """
    try:
        # Load the rule
        await grammar_agent._load_rules()
        rule_data = grammar_agent._rules_cache.get(rule_id)

        if not rule_data:
            raise HTTPException(
                status_code=404,
                detail=f"Regra '{rule_id}' não encontrada"
            )

        # Get user progress if provided
        user_progress = None
        if user_id:
            progress = await grammar_agent._get_user_progress(user_id, rule_id)
            if progress:
                user_progress = {
                    "practice_count": progress.get("practiceCount", 0),
                    "best_explanation_score": progress.get("bestExplanationScore", 0),
                    "mastery_level": progress.get("masteryLevel", "not_started"),
                    "last_practiced": progress.get("lastPracticed")
                }

        comparison = {
            "exists_in_portuguese": rule_data.get("exists_in_portuguese", True),
            "portuguese_equivalent": rule_data.get("portuguese_equivalent"),
            "similarities": rule_data.get("similarities", []),
            "differences": rule_data.get("differences", [])
        }

        return GrammarLessonResponse(
            type="grammar_lesson",
            status="success",
            rule={
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
            user_progress=user_progress
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/categories",
    summary="List grammar categories",
    description="Get all available grammar rule categories."
)
async def list_categories() -> dict:
    """
    Get all available grammar categories.
    """
    try:
        await grammar_agent._load_rules()
        categories = grammar_agent.get_available_categories()

        # Get count per category
        category_counts = {
            cat: len(rules)
            for cat, rules in grammar_agent._rules_by_category.items()
        }

        return {
            "categories": categories,
            "counts": category_counts,
            "total_categories": len(categories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
