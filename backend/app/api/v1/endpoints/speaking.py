"""
Speaking API Endpoints
Endpoints for conversation/speaking practice sessions.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, WebSocket, WebSocketDisconnect

from app.agents.orchestrator import run_orchestrator
from app.agents.speaking_agent import speaking_agent
from app.agents.error_integration_agent import error_integration_agent
from app.core.websocket_manager import websocket_manager
from app.schemas.speaking import (
    StartSessionRequest,
    StartSessionResponse,
    ConversationTurnRequest,
    ConversationTurnResponse,
    AudioTurnRequest,
    EndSessionRequest,
    EndSessionResponse,
    SpeakingProgressResponse,
    TopicsListResponse,
    TopicInfo,
    ActiveSessionResponse
)


logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== SESSION MANAGEMENT ====================

@router.post("/start-session", response_model=StartSessionResponse)
async def start_session(
    request: StartSessionRequest,
    user_id: str = Query(..., description="User ID")
):
    """
    Start a new speaking/conversation session.

    Selects a topic (or uses the provided one) and initiates a conversation.
    Returns the agent's opening prompt with TTS audio.
    """
    try:
        state = await run_orchestrator(
            user_id=user_id,
            request_type="speaking_session",
            input_data={
                "action": "start",
                "topic_id": request.topic,
                "difficulty": request.difficulty
            }
        )

        response = state.get("response", {})

        if state.get("has_error"):
            return StartSessionResponse(
                status="error",
                message=state.get("error_message", "Erro ao iniciar sessão")
            )

        return StartSessionResponse(
            status=response.get("status", "success"),
            session_id=response.get("session_id"),
            topic=response.get("topic"),
            topic_description=response.get("topic_description"),
            initial_prompt=response.get("initial_prompt"),
            initial_prompt_audio=response.get("initial_prompt_audio"),
            suggested_responses=response.get("suggested_responses"),
            message=response.get("message")
        )

    except Exception as e:
        logger.error(f"Error starting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/turn", response_model=ConversationTurnResponse)
async def process_turn(
    request: ConversationTurnRequest,
    user_id: str = Query(..., description="User ID")
):
    """
    Process a conversation turn with text input.

    Sends user's text to the speaking agent for response generation
    and error detection.
    """
    try:
        state = await run_orchestrator(
            user_id=user_id,
            request_type="speaking_session",
            input_data={
                "action": "turn",
                "session_id": request.session_id,
                "user_text": request.user_text
            }
        )

        response = state.get("response", {})

        if state.get("has_error"):
            return ConversationTurnResponse(
                status="error",
                session_id=request.session_id,
                turn_number=0,
                user_input=request.user_text,
                message=state.get("error_message", "Erro ao processar turno")
            )

        return ConversationTurnResponse(
            status=response.get("status", "success"),
            session_id=response.get("session_id", request.session_id),
            turn_number=response.get("turn_number", 0),
            user_input=response.get("user_input", request.user_text),
            agent_response=response.get("agent_response"),
            agent_audio_base64=response.get("agent_audio_base64"),
            errors_detected=response.get("errors_detected"),
            grammar_errors=response.get("grammar_errors"),
            pronunciation_errors=response.get("pronunciation_errors"),
            conversation_continuing=response.get("conversation_continuing", True),
            message=response.get("end_suggestion") or response.get("message")
        )

    except Exception as e:
        logger.error(f"Error processing turn: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/turn-audio", response_model=ConversationTurnResponse)
async def process_audio_turn(
    request: AudioTurnRequest,
    user_id: str = Query(..., description="User ID")
):
    """
    Process a conversation turn with audio input.

    Audio is transcribed via STT, then processed like a text turn.
    Also includes pronunciation assessment.
    """
    try:
        state = await run_orchestrator(
            user_id=user_id,
            request_type="speaking_session",
            input_data={
                "action": "turn",
                "session_id": request.session_id,
                "audio_base64": request.audio_base64
            }
        )

        response = state.get("response", {})

        if state.get("has_error"):
            return ConversationTurnResponse(
                status="error",
                session_id=request.session_id,
                turn_number=0,
                user_input="[audio]",
                message=state.get("error_message", "Erro ao processar áudio")
            )

        return ConversationTurnResponse(
            status=response.get("status", "success"),
            session_id=response.get("session_id", request.session_id),
            turn_number=response.get("turn_number", 0),
            user_input=response.get("user_input", "[transcription]"),
            agent_response=response.get("agent_response"),
            agent_audio_base64=response.get("agent_audio_base64"),
            errors_detected=response.get("errors_detected"),
            grammar_errors=response.get("grammar_errors"),
            pronunciation_errors=response.get("pronunciation_errors"),
            conversation_continuing=response.get("conversation_continuing", True),
            message=response.get("end_suggestion") or response.get("message")
        )

    except Exception as e:
        logger.error(f"Error processing audio turn: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/end-session", response_model=EndSessionResponse)
async def end_session(
    request: EndSessionRequest,
    user_id: str = Query(..., description="User ID")
):
    """
    End a speaking session.

    Generates session summary and creates corrective activities
    for detected errors.
    """
    try:
        state = await run_orchestrator(
            user_id=user_id,
            request_type="speaking_session",
            input_data={
                "action": "end",
                "session_id": request.session_id
            }
        )

        response = state.get("response", {})

        if state.get("has_error"):
            return EndSessionResponse(
                status="error",
                session_id=request.session_id,
                message=state.get("error_message", "Erro ao encerrar sessão")
            )

        return EndSessionResponse(
            status=response.get("status", "success"),
            session_id=response.get("session_id", request.session_id),
            summary=response.get("summary"),
            grammar_errors=response.get("grammar_errors"),
            pronunciation_errors=response.get("pronunciation_errors"),
            generated_activities=response.get("generated_activities"),
            message=response.get("message")
        )

    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SESSION INFO ====================

@router.get("/active-session", response_model=ActiveSessionResponse)
async def get_active_session(
    user_id: str = Query(..., description="User ID")
):
    """
    Check if user has an active speaking session.
    """
    try:
        active_session = await speaking_agent.get_active_session(user_id)

        if active_session:
            return ActiveSessionResponse(
                has_active_session=True,
                session_id=active_session.get("id"),
                topic=active_session.get("topicName"),
                turn_count=active_session.get("currentTurn", 0),
                started_at=active_session.get("startedAt")
            )
        else:
            return ActiveSessionResponse(
                has_active_session=False
            )

    except Exception as e:
        logger.error(f"Error getting active session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== TOPICS ====================

@router.get("/topics", response_model=TopicsListResponse)
async def get_topics(
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (beginner/intermediate)")
):
    """
    Get list of available conversation topics.
    """
    try:
        topics = await speaking_agent.get_available_topics(difficulty)

        topic_list = [
            TopicInfo(
                id=t["id"],
                name=t["name"],
                description=t.get("description", ""),
                difficulty=t.get("difficulty", "beginner"),
                sample_questions=t.get("sample_questions", [])[:3]
            )
            for t in topics
        ]

        return TopicsListResponse(
            topics=topic_list,
            total=len(topic_list)
        )

    except Exception as e:
        logger.error(f"Error getting topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PROGRESS & STATS ====================

@router.get("/progress", response_model=SpeakingProgressResponse)
async def get_speaking_progress(
    user_id: str = Query(..., description="User ID")
):
    """
    Get speaking progress and statistics for a user.
    """
    try:
        stats = await speaking_agent.get_user_speaking_stats(user_id)

        return SpeakingProgressResponse(
            total_sessions=stats.get("total_sessions", 0),
            total_conversation_time_minutes=stats.get("total_conversation_time_minutes", 0),
            average_session_turns=stats.get("average_turns_per_session", 0),
            common_grammar_errors=stats.get("most_common_grammar_errors", []),
            problematic_phonemes=stats.get("problematic_phonemes", []),
            sessions_this_week=stats.get("sessions_this_week", 0)
        )

    except Exception as e:
        logger.error(f"Error getting speaking progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_session_history(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum sessions to return"),
    status: Optional[str] = Query(None, description="Filter by status (active/completed)")
):
    """
    Get speaking session history for a user.
    """
    try:
        from app.services.cosmos_db_service import cosmos_db_service

        sessions = await cosmos_db_service.get_speaking_sessions_history(
            user_id=user_id,
            limit=limit,
            status=status
        )

        return {
            "sessions": [
                {
                    "session_id": s.get("id"),
                    "topic": s.get("topicName"),
                    "status": s.get("status"),
                    "turn_count": s.get("currentTurn", 0),
                    "duration_seconds": s.get("durationSeconds", 0),
                    "grammar_errors": len(s.get("grammarErrors", [])),
                    "pronunciation_errors": len(s.get("pronunciationErrors", [])),
                    "started_at": s.get("startedAt"),
                    "ended_at": s.get("endedAt")
                }
                for s in sessions
            ],
            "total": len(sessions)
        }

    except Exception as e:
        logger.error(f"Error getting session history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session_details(
    session_id: str,
    user_id: str = Query(..., description="User ID")
):
    """
    Get detailed information about a specific session.
    """
    try:
        from app.services.cosmos_db_service import cosmos_db_service

        session = await cosmos_db_service.get_speaking_session(user_id, session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")

        # Get generated activities for this session
        activities = await error_integration_agent.get_activities_from_session(
            user_id, session_id
        )

        return {
            "session_id": session.get("id"),
            "topic": session.get("topicName"),
            "status": session.get("status"),
            "exchanges": session.get("exchanges", []),
            "turn_count": session.get("currentTurn", 0),
            "duration_seconds": session.get("durationSeconds", 0),
            "grammar_errors": session.get("grammarErrors", []),
            "pronunciation_errors": session.get("pronunciationErrors", []),
            "summary": session.get("summary"),
            "generated_activities": activities,
            "started_at": session.get("startedAt"),
            "ended_at": session.get("endedAt")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CORRECTIVE ACTIVITIES ====================

@router.get("/corrective-activities")
async def get_corrective_activities(
    user_id: str = Query(..., description="User ID"),
    pillar: Optional[str] = Query(None, description="Filter by pillar (grammar/pronunciation)"),
    limit: int = Query(default=10, ge=1, le=50)
):
    """
    Get pending corrective activities generated from speaking sessions.
    """
    try:
        activities = await error_integration_agent.get_pending_corrective_activities(
            user_id=user_id,
            pillar=pillar,
            limit=limit
        )

        return {
            "activities": activities,
            "total": len(activities)
        }

    except Exception as e:
        logger.error(f"Error getting corrective activities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/error-statistics")
async def get_error_statistics(
    user_id: str = Query(..., description="User ID")
):
    """
    Get statistics about user's errors and corrective activities.
    """
    try:
        stats = await error_integration_agent.get_error_statistics(user_id)
        return stats

    except Exception as e:
        logger.error(f"Error getting error statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WEBSOCKET ENDPOINT ====================

@router.websocket("/ws/{user_id}")
async def speaking_websocket(
    websocket: WebSocket,
    user_id: str
):
    """
    WebSocket endpoint for real-time conversation.

    Supports:
    - start_session: Start a new conversation
    - audio_turn: Send audio for a turn
    - text_turn: Send text for a turn
    - end_session: End the session
    - get_status: Get current session status
    """
    session_id = f"ws_{user_id}_{websocket.client.port}"

    connected = await websocket_manager.connect(
        websocket=websocket,
        user_id=user_id,
        session_id=session_id,
        namespace="speaking"
    )

    if not connected:
        return

    try:
        while True:
            # Receive message (text or binary)
            data = await websocket.receive()

            if "text" in data:
                import json
                message = json.loads(data["text"])
            elif "bytes" in data:
                # Binary data - assume it's audio with metadata in first bytes
                # For simplicity, we expect JSON messages for now
                continue
            else:
                continue

            # Process message through handler
            response = await websocket_manager.handle_message(
                user_id=user_id,
                namespace="speaking",
                message=message
            )

            # Send response
            if response:
                await websocket_manager.send_message(
                    user_id=user_id,
                    namespace="speaking",
                    message=response
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket_manager.disconnect(user_id, "speaking")
