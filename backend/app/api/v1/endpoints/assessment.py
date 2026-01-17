"""
Assessment API Endpoints
REST API for initial and continuous assessments.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime
import logging
import uuid

from app.agents.assessment_agent import assessment_agent
from app.agents.state import create_initial_state
from app.core.dependencies import get_current_user
from app.services.cosmos_db_service import cosmos_db_service
from app.schemas.assessment import (
    StartAssessmentRequest,
    StartAssessmentResponse,
    SubmitAssessmentAnswerRequest,
    SubmitAssessmentAnswerResponse,
    AssessmentResultResponse,
    AssessmentStatusResponse,
    AssessmentStepContent,
    PillarScores
)


logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for active assessments (in production, use Redis or similar)
_active_assessments: dict[str, dict] = {}


# ==================== ASSESSMENT ENDPOINTS ====================

@router.post("/start", response_model=StartAssessmentResponse)
async def start_assessment(
    request: StartAssessmentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Start a new assessment session.

    For new users, this starts the initial assessment (4 steps).
    For existing users, this can start a continuous assessment.
    """
    try:
        user_id = current_user["id"]

        # Check if initial assessment is needed
        if not current_user.get("initial_assessment_completed", False):
            assessment_type = "initial"
        else:
            assessment_type = request.assessment_type

        # Generate assessment ID
        assessment_id = f"assessment_{user_id}_{uuid.uuid4().hex[:8]}"

        # Create initial state
        state = create_initial_state(user_id, f"assessment_{assessment_type}", current_user)
        state["assessment"]["assessment_id"] = assessment_id
        state["assessment"]["is_initial"] = assessment_type == "initial"

        # Process through assessment agent to get first step
        result_state = await assessment_agent.process(state)

        response = result_state.get("response", {})

        # Store assessment state in memory
        _active_assessments[assessment_id] = {
            "user_id": user_id,
            "type": assessment_type,
            "state": result_state,
            "started_at": datetime.utcnow().isoformat(),
            "step_scores": {}
        }

        # Build response
        step_content = response.get("content", {})

        return StartAssessmentResponse(
            assessment_id=assessment_id,
            assessment_type=assessment_type,
            step=response.get("step", 1),
            step_name=response.get("step_name", "vocabulary"),
            total_steps=response.get("total_steps", 4),
            content=AssessmentStepContent(
                type=step_content.get("type", "vocabulary"),
                items=step_content.get("items"),
                prompts=step_content.get("prompts"),
                instructions=step_content.get("instructions", "")
            ),
            instructions=response.get("instructions", "")
        )

    except Exception as e:
        logger.error(f"Error starting assessment: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao iniciar avaliação: {str(e)}"
        )


@router.post("/submit", response_model=SubmitAssessmentAnswerResponse)
async def submit_assessment_answers(
    request: SubmitAssessmentAnswerRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit answers for the current assessment step and move to next.
    """
    try:
        user_id = current_user["id"]

        # Verify assessment exists and belongs to user
        assessment = _active_assessments.get(request.assessment_id)
        if not assessment or assessment["user_id"] != user_id:
            raise HTTPException(
                status_code=404,
                detail="Avaliação não encontrada"
            )

        # Get current state
        state = assessment["state"]

        # Calculate score for this step
        step_score = _calculate_step_score(request.step_name, request.answers)
        assessment["step_scores"][request.step_name] = step_score

        # Update state with answers
        state["assessment"][f"{request.step_name}_results"] = request.answers
        state["assessment"]["current_step"] = request.step
        state["activity_input"] = {"results": request.answers}

        # Process through assessment agent
        result_state = await assessment_agent.process(state)
        response = result_state.get("response", {})

        # Update stored state
        assessment["state"] = result_state

        # Check if assessment is complete
        is_complete = response.get("type") == "assessment_complete"

        if is_complete:
            # Assessment complete - process final results
            return await _finalize_assessment(request.assessment_id, current_user, result_state)

        # Get next step content
        next_content = response.get("content", {})

        return SubmitAssessmentAnswerResponse(
            assessment_id=request.assessment_id,
            step_completed=request.step,
            step_name=request.step_name,
            step_score=step_score,
            next_step=response.get("step"),
            next_step_name=response.get("step_name"),
            next_content=AssessmentStepContent(
                type=next_content.get("type", ""),
                items=next_content.get("items"),
                prompts=next_content.get("prompts"),
                instructions=next_content.get("instructions", "")
            ) if next_content else None,
            is_complete=False
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting assessment answers: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao submeter respostas: {str(e)}"
        )


@router.get("/result/{assessment_id}", response_model=AssessmentResultResponse)
async def get_assessment_result(
    assessment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the result of a completed assessment.
    """
    try:
        user_id = current_user["id"]

        # Check if assessment exists
        assessment = _active_assessments.get(assessment_id)
        if not assessment or assessment["user_id"] != user_id:
            raise HTTPException(
                status_code=404,
                detail="Avaliação não encontrada"
            )

        state = assessment["state"]
        assessment_data = state.get("assessment", {})

        # Check if assessment is complete
        if not assessment_data.get("final_scores"):
            raise HTTPException(
                status_code=400,
                detail="Avaliação ainda não foi completada"
            )

        scores = assessment_data.get("final_scores", {})
        recommendations = assessment_data.get("recommendations", [])

        return AssessmentResultResponse(
            assessment_id=assessment_id,
            assessment_type="initial" if assessment_data.get("is_initial") else "continuous",
            scores=PillarScores(
                vocabulary=scores.get("vocabulary", 0),
                grammar=scores.get("grammar", 0),
                pronunciation=scores.get("pronunciation", 0),
                speaking=scores.get("speaking", 0)
            ),
            overall_score=sum(scores.values()) / 4 if scores else 0,
            determined_level=assessment_data.get("determined_level", "beginner"),
            previous_level=state["user"].get("current_level"),
            level_changed=assessment_data.get("level_changed", False),
            weakest_pillar=min(scores, key=scores.get) if scores else "vocabulary",
            recommendations=recommendations,
            message=state.get("response", {}).get("message", "Avaliação concluída!")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting assessment result: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter resultado: {str(e)}"
        )


@router.get("/status", response_model=AssessmentStatusResponse)
async def get_assessment_status(
    current_user: dict = Depends(get_current_user)
):
    """
    Get the current assessment status for the user.

    Returns information about any active assessment and
    whether initial assessment has been completed.
    """
    try:
        user_id = current_user["id"]

        # Find any active assessment for this user
        active_assessment = None
        active_id = None

        for aid, assessment in _active_assessments.items():
            if assessment["user_id"] == user_id:
                state = assessment["state"]
                # Check if not completed
                if not state.get("assessment", {}).get("final_scores"):
                    active_assessment = assessment
                    active_id = aid
                    break

        if active_assessment:
            state = active_assessment["state"]
            assessment_data = state.get("assessment", {})

            return AssessmentStatusResponse(
                has_active_assessment=True,
                assessment_id=active_id,
                assessment_type="initial" if assessment_data.get("is_initial") else "continuous",
                current_step=assessment_data.get("current_step", 1),
                total_steps=assessment_data.get("total_steps", 4),
                step_scores=active_assessment.get("step_scores", {}),
                initial_assessment_completed=current_user.get("initial_assessment_completed", False),
                last_assessment_date=current_user.get("last_assessment_date"),
                sessions_since_last_assessment=current_user.get("sessions_since_last_assessment", 0)
            )

        return AssessmentStatusResponse(
            has_active_assessment=False,
            initial_assessment_completed=current_user.get("initial_assessment_completed", False),
            last_assessment_date=current_user.get("last_assessment_date"),
            sessions_since_last_assessment=current_user.get("sessions_since_last_assessment", 0)
        )

    except Exception as e:
        logger.error(f"Error getting assessment status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter status: {str(e)}"
        )


@router.delete("/{assessment_id}")
async def cancel_assessment(
    assessment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel an active assessment.
    """
    try:
        user_id = current_user["id"]

        # Verify assessment exists and belongs to user
        assessment = _active_assessments.get(assessment_id)
        if not assessment or assessment["user_id"] != user_id:
            raise HTTPException(
                status_code=404,
                detail="Avaliação não encontrada"
            )

        # Remove from active assessments
        del _active_assessments[assessment_id]

        return {"message": "Avaliação cancelada com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling assessment: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao cancelar avaliação: {str(e)}"
        )


# ==================== HELPER FUNCTIONS ====================

def _calculate_step_score(step_name: str, answers: list[dict]) -> float:
    """Calculate score for an assessment step."""
    if not answers:
        return 0.0

    correct = sum(1 for a in answers if a.get("correct", False))
    return (correct / len(answers)) * 100


async def _finalize_assessment(
    assessment_id: str,
    user: dict,
    state: dict
) -> SubmitAssessmentAnswerResponse:
    """Finalize assessment and return final response."""
    assessment = _active_assessments.get(assessment_id)

    # Get final scores
    assessment_data = state.get("assessment", {})
    scores = assessment_data.get("final_scores", {})

    # Calculate final step score
    step_scores = assessment.get("step_scores", {})
    if "speaking" not in step_scores and scores.get("speaking"):
        step_scores["speaking"] = scores["speaking"]

    last_step_name = list(step_scores.keys())[-1] if step_scores else "speaking"
    last_step_score = step_scores.get(last_step_name, 0)

    return SubmitAssessmentAnswerResponse(
        assessment_id=assessment_id,
        step_completed=4,
        step_name=last_step_name,
        step_score=last_step_score,
        next_step=None,
        next_step_name=None,
        next_content=None,
        is_complete=True
    )
