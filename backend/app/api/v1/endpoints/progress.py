"""
Progress API Endpoints
REST API for progress tracking and dashboard features.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import logging

from app.agents.progress_agent import progress_agent
from app.agents.scheduler_agent import scheduler_agent
from app.agents.orchestrator import run_orchestrator
from app.agents.state import create_initial_state
from app.schemas.progress import (
    ProgressRequest,
    ScheduleRequest,
    UpdateProgressRequest,
    CompleteScheduledReviewRequest,
    OverallProgressResponse,
    PillarProgressResponse,
    DailyScheduleResponse,
    WeekScheduleResponse,
    WeeklyReportResponse,
    ProgressUpdateResponse,
    NextActivityResponse,
    ScheduledReviewItem,
    DailyGoalProgress,
    DailyBreakdown
)
from app.services.cosmos_db_service import cosmos_db_service


logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== DASHBOARD ENDPOINTS ====================

@router.get("/dashboard/{user_id}", response_model=OverallProgressResponse)
async def get_user_dashboard(
    user_id: str,
    include_weekly_report: bool = Query(
        default=False,
        description="Include weekly report data"
    )
):
    """
    Get complete dashboard data for a user.

    Returns:
    - Overall progress across all pillars
    - Current level and readiness for advancement
    - Streak information
    - Daily goal progress
    - Weakest pillar identification
    """
    try:
        # Run through orchestrator to get progress
        state = await run_orchestrator(
            user_id=user_id,
            request_type="get_progress",
            input_data={"include_weekly": include_weekly_report}
        )

        response = state.get("response", {})

        if response.get("type") == "progress":
            progress_data = response.get("progress", {})

            # Convert pillar progress
            def convert_pillar(data: dict, pillar_name: str) -> PillarProgressResponse:
                return PillarProgressResponse(
                    pillar=pillar_name,
                    total_items=data.get("total_items", 0),
                    mastered_items=data.get("mastered_items", 0),
                    learning_items=data.get("learning_items", 0),
                    average_score=data.get("average_score", 0),
                    average_accuracy=data.get("average_accuracy", 0),
                    study_time_minutes=data.get("study_time_minutes", 0),
                    items_due_for_review=data.get("items_due_for_review", 0),
                    items_low_frequency=data.get("items_low_frequency", 0),
                    last_activity=data.get("last_activity"),
                    streak_days=data.get("streak_days", 0)
                )

            return OverallProgressResponse(
                user_id=user_id,
                current_level=progress_data.get("current_level", "beginner"),
                vocabulary=convert_pillar(progress_data.get("vocabulary", {}), "vocabulary"),
                grammar=convert_pillar(progress_data.get("grammar", {}), "grammar"),
                pronunciation=convert_pillar(progress_data.get("pronunciation", {}), "pronunciation"),
                speaking=convert_pillar(progress_data.get("speaking", {}), "speaking"),
                overall_score=progress_data.get("overall_score", 0),
                total_study_time_minutes=progress_data.get("total_study_time_minutes", 0),
                total_activities_completed=progress_data.get("total_activities_completed", 0),
                current_streak_days=progress_data.get("current_streak_days", 0),
                longest_streak_days=progress_data.get("longest_streak_days", 0),
                last_activity_date=progress_data.get("last_activity_date"),
                initial_assessment_completed=progress_data.get("initial_assessment_completed", False),
                ready_for_level_up=progress_data.get("ready_for_level_up", False),
                weakest_pillar=progress_data.get("weakest_pillar"),
                daily_goal_minutes=progress_data.get("daily_goal_minutes", 30),
                today_study_minutes=progress_data.get("today_study_minutes", 0),
                today_activities_completed=progress_data.get("today_activities_completed", 0),
                message=response.get("message")
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=response.get("message", "Erro ao obter progresso")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter dashboard: {str(e)}"
        )


@router.get("/pillar/{user_id}/{pillar}", response_model=PillarProgressResponse)
async def get_pillar_progress(
    user_id: str,
    pillar: str
):
    """
    Get detailed progress for a specific pillar.

    Pillars: vocabulary, grammar, pronunciation, speaking
    """
    if pillar not in ["vocabulary", "grammar", "pronunciation", "speaking"]:
        raise HTTPException(
            status_code=400,
            detail="Pilar inválido. Use: vocabulary, grammar, pronunciation, speaking"
        )

    try:
        # Get statistics from database
        stats = await cosmos_db_service.get_user_statistics(user_id)
        pillar_stats = stats.get(pillar, {})

        # Get items due for review based on pillar
        items_due = 0
        if pillar == "vocabulary":
            due = await cosmos_db_service.get_vocabulary_due_for_review(user_id)
            items_due = len(due)
        elif pillar == "grammar":
            due = await cosmos_db_service.get_grammar_due_for_review(user_id)
            items_due = len(due)
        elif pillar == "pronunciation":
            due = await cosmos_db_service.get_pronunciation_needs_practice(user_id)
            items_due = len(due)

        return PillarProgressResponse(
            pillar=pillar,
            total_items=pillar_stats.get("total_words", pillar_stats.get("total_rules", pillar_stats.get("total_sounds", 0))),
            mastered_items=pillar_stats.get("mastered", 0),
            learning_items=pillar_stats.get("learning", 0),
            average_score=pillar_stats.get("average_score", pillar_stats.get("average_accuracy", 0)),
            average_accuracy=pillar_stats.get("average_accuracy", pillar_stats.get("average_score", 0)),
            items_due_for_review=items_due
        )

    except Exception as e:
        logger.error(f"Error getting pillar progress: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter progresso do pilar: {str(e)}"
        )


# ==================== SCHEDULE ENDPOINTS ====================

@router.get("/schedule/today/{user_id}", response_model=DailyScheduleResponse)
async def get_today_schedule(user_id: str):
    """
    Get today's study schedule for a user.

    Creates schedule if it doesn't exist, using SRS algorithm to prioritize:
    1. Items due for review (SRS)
    2. Low frequency items
    3. Daily speaking practice
    """
    try:
        # Run through orchestrator
        state = await run_orchestrator(
            user_id=user_id,
            request_type="get_schedule",
            input_data={}
        )

        response = state.get("response", {})

        if response.get("type") == "schedule":
            schedule = response.get("schedule", {})

            # Convert scheduled reviews
            scheduled = [
                ScheduledReviewItem(
                    id=r.get("id", ""),
                    type=r.get("type", ""),
                    pillar=r.get("pillar", ""),
                    item_id=r.get("item_id"),
                    reason=r.get("reason", "srs_due"),
                    priority=r.get("priority", "normal"),
                    estimated_minutes=r.get("estimated_minutes", 0),
                    completed=False
                )
                for r in schedule.get("scheduled_reviews", [])
            ]

            # Convert completed reviews
            completed = [
                ScheduledReviewItem(
                    id=r.get("id", ""),
                    type=r.get("type", ""),
                    pillar=r.get("pillar", ""),
                    item_id=r.get("item_id"),
                    reason=r.get("reason", ""),
                    priority=r.get("priority", "normal"),
                    estimated_minutes=r.get("estimated_minutes", 0),
                    completed=True,
                    completed_at=r.get("completed_at")
                )
                for r in schedule.get("completed_reviews", [])
            ]

            # Calculate goal progress
            goal_data = schedule.get("daily_goal_progress", {})
            goal_minutes = goal_data.get("goalMinutes", 30)
            minutes_studied = goal_data.get("minutesStudied", 0)

            goal_progress = DailyGoalProgress(
                minutes_studied=minutes_studied,
                activities_completed=goal_data.get("activitiesCompleted", 0),
                goal_minutes=goal_minutes,
                total_activities=goal_data.get("totalActivities", len(scheduled)),
                percentage_complete=min((minutes_studied / goal_minutes * 100), 100) if goal_minutes > 0 else 0
            )

            return DailyScheduleResponse(
                date=schedule.get("date", datetime.utcnow().strftime("%Y-%m-%d")),
                user_id=user_id,
                scheduled_reviews=scheduled,
                completed_reviews=completed,
                daily_goal_progress=goal_progress,
                message=response.get("message")
            )
        else:
            # Return empty schedule
            return DailyScheduleResponse(
                date=datetime.utcnow().strftime("%Y-%m-%d"),
                user_id=user_id,
                scheduled_reviews=[],
                completed_reviews=[],
                daily_goal_progress=DailyGoalProgress(),
                message="Nenhuma atividade agendada para hoje"
            )

    except Exception as e:
        logger.error(f"Error getting today's schedule: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter agenda do dia: {str(e)}"
        )


@router.get("/schedule/week/{user_id}", response_model=WeekScheduleResponse)
async def get_week_schedule(user_id: str):
    """
    Get week's schedule for a user.

    Returns schedule for the next 7 days.
    """
    try:
        schedules = await cosmos_db_service.get_week_schedule(user_id)

        daily_schedules = []
        total_minutes = 0
        total_activities = 0

        for schedule in schedules:
            goal_data = schedule.get("daily_goal_progress", {})
            minutes = goal_data.get("minutesStudied", 0)
            activities = goal_data.get("activitiesCompleted", 0)
            total_minutes += minutes
            total_activities += activities

            daily_schedules.append(DailyScheduleResponse(
                date=schedule.get("date"),
                user_id=user_id,
                scheduled_reviews=[
                    ScheduledReviewItem(
                        id=r.get("id", ""),
                        type=r.get("type", ""),
                        pillar=r.get("pillar", ""),
                        item_id=r.get("item_id"),
                        reason=r.get("reason", ""),
                        priority=r.get("priority", "normal"),
                        estimated_minutes=r.get("estimated_minutes", 0)
                    )
                    for r in schedule.get("scheduled_reviews", [])
                ],
                completed_reviews=[
                    ScheduledReviewItem(
                        id=r.get("id", ""),
                        type=r.get("type", ""),
                        pillar=r.get("pillar", ""),
                        item_id=r.get("item_id"),
                        reason=r.get("reason", ""),
                        priority=r.get("priority", "normal"),
                        estimated_minutes=r.get("estimated_minutes", 0),
                        completed=True
                    )
                    for r in schedule.get("completed_reviews", [])
                ],
                daily_goal_progress=DailyGoalProgress(
                    minutes_studied=minutes,
                    activities_completed=activities,
                    goal_minutes=goal_data.get("goalMinutes", 30),
                    total_activities=goal_data.get("totalActivities", 0),
                    percentage_complete=min((minutes / goal_data.get("goalMinutes", 30) * 100), 100)
                    if goal_data.get("goalMinutes", 30) > 0 else 0
                )
            ))

        return WeekScheduleResponse(
            schedules=daily_schedules,
            week_summary={
                "total_minutes": total_minutes,
                "total_activities": total_activities,
                "days_with_activity": len([s for s in schedules if s.get("daily_goal_progress", {}).get("activitiesCompleted", 0) > 0])
            }
        )

    except Exception as e:
        logger.error(f"Error getting week schedule: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter agenda da semana: {str(e)}"
        )


@router.post("/schedule/complete-review/{user_id}", response_model=ProgressUpdateResponse)
async def complete_scheduled_review(
    user_id: str,
    request: CompleteScheduledReviewRequest
):
    """
    Mark a scheduled review as completed.

    Updates daily schedule progress and SRS data.
    """
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        schedule = await cosmos_db_service.get_daily_schedule(user_id, today)

        if not schedule:
            raise HTTPException(
                status_code=404,
                detail="Agenda não encontrada para hoje"
            )

        # Find and move review from scheduled to completed
        scheduled = schedule.get("scheduled_reviews", [])
        completed = schedule.get("completed_reviews", [])
        review_found = None

        for i, review in enumerate(scheduled):
            if review.get("id") == request.review_id:
                review_found = scheduled.pop(i)
                review_found["completed_at"] = datetime.utcnow().isoformat()
                review_found["result"] = request.result
                completed.append(review_found)
                break

        if not review_found:
            raise HTTPException(
                status_code=404,
                detail="Revisão não encontrada na agenda"
            )

        # Update goal progress
        goal_progress = schedule.get("daily_goal_progress", {})
        goal_progress["minutesStudied"] = goal_progress.get("minutesStudied", 0) + review_found.get("estimated_minutes", 0)
        goal_progress["activitiesCompleted"] = goal_progress.get("activitiesCompleted", 0) + 1

        # Save updated schedule
        schedule["scheduled_reviews"] = scheduled
        schedule["completed_reviews"] = completed
        schedule["daily_goal_progress"] = goal_progress

        await cosmos_db_service.create_or_update_schedule(user_id, today, schedule)

        return ProgressUpdateResponse(
            status="success",
            message="Revisão concluída com sucesso",
            today_minutes=goal_progress.get("minutesStudied", 0),
            today_activities=goal_progress.get("activitiesCompleted", 0),
            srs_updated=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing scheduled review: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao completar revisão: {str(e)}"
        )


# ==================== WEEKLY REPORT ENDPOINT ====================

@router.get("/weekly-report/{user_id}", response_model=WeeklyReportResponse)
async def get_weekly_report(
    user_id: str,
    week_start: str = Query(
        default=None,
        description="Start date of week (YYYY-MM-DD). Defaults to 7 days ago."
    )
):
    """
    Get comprehensive weekly progress report.

    Includes:
    - Total study time and daily breakdown
    - Activities completed by pillar
    - Accuracy metrics
    - Achievements and areas to improve
    """
    try:
        # Parse week start date
        if week_start:
            start_date = datetime.strptime(week_start, "%Y-%m-%d")
        else:
            start_date = datetime.utcnow() - timedelta(days=7)

        # Generate weekly report
        report = await progress_agent.generate_weekly_report(user_id, start_date)

        # Convert daily breakdown
        daily_breakdown = [
            DailyBreakdown(
                date=d.get("date", ""),
                minutes=d.get("minutes", 0),
                activities=d.get("activities", 0)
            )
            for d in report.daily_breakdown
        ]

        return WeeklyReportResponse(
            user_id=user_id,
            week_start=report.week_start,
            week_end=report.week_end,
            total_study_minutes=report.total_study_minutes,
            daily_breakdown=daily_breakdown,
            activities_completed=report.activities_completed,
            activities_by_pillar=report.activities_by_pillar,
            words_learned=report.words_learned,
            words_reviewed=report.words_reviewed,
            grammar_rules_practiced=report.grammar_rules_practiced,
            pronunciation_sounds_practiced=report.pronunciation_sounds_practiced,
            speaking_sessions=report.speaking_sessions,
            average_vocabulary_accuracy=report.average_vocabulary_accuracy,
            average_grammar_accuracy=report.average_grammar_accuracy,
            average_pronunciation_accuracy=report.average_pronunciation_accuracy,
            streak_maintained=report.streak_maintained,
            current_streak=report.current_streak,
            achievements=report.achievements,
            areas_to_improve=report.areas_to_improve
        )

    except Exception as e:
        logger.error(f"Error getting weekly report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar relatório semanal: {str(e)}"
        )


# ==================== NEXT ACTIVITY ENDPOINT ====================

@router.get("/next-activity/{user_id}", response_model=NextActivityResponse)
async def get_next_activity(user_id: str):
    """
    Get the next recommended activity for the user.

    Considers:
    - SRS items due for review (highest priority)
    - Pending activities from error integration
    - Low frequency items
    - User learning goals
    """
    try:
        # Run through orchestrator
        state = await run_orchestrator(
            user_id=user_id,
            request_type="get_next_activity",
            input_data={}
        )

        response = state.get("response", {})

        if response.get("type") == "next_activity":
            activity = response.get("activity")

            if activity:
                return NextActivityResponse(
                    has_activity=True,
                    activity_type=activity.get("type"),
                    pillar=activity.get("pillar"),
                    item_id=activity.get("item_id") or activity.get("wordId") or activity.get("ruleId") or activity.get("soundId"),
                    source=response.get("source", "srs"),
                    reason=activity.get("reason")
                )
            else:
                return NextActivityResponse(
                    has_activity=False,
                    source="none",
                    suggestions=response.get("suggestions", []),
                    message=response.get("message", "Nenhuma revisão pendente!")
                )
        else:
            return NextActivityResponse(
                has_activity=False,
                source="none",
                message="Nenhuma atividade disponível"
            )

    except Exception as e:
        logger.error(f"Error getting next activity: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter próxima atividade: {str(e)}"
        )


# ==================== UPDATE PROGRESS ENDPOINT ====================

@router.post("/update/{user_id}", response_model=ProgressUpdateResponse)
async def update_progress(
    user_id: str,
    request: UpdateProgressRequest
):
    """
    Update progress after completing an activity.

    Updates:
    - Pillar-specific metrics
    - SRS data (if applicable)
    - Study time
    - Streak
    """
    try:
        # Get user data
        user_data = await cosmos_db_service.get_user(user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        # Create state for progress update
        state = create_initial_state(user_id, "update_progress", user_data)
        state["activity_output"] = {
            "pillar": request.pillar,
            "item_id": request.item_id,
            "correct": request.correct,
            "accuracy": request.accuracy,
            "time_spent_seconds": request.time_spent_seconds,
            "score": request.accuracy if request.accuracy else (100 if request.correct else 0)
        }

        # Process through progress agent
        result_state = await progress_agent.process(state)

        # Update SRS through scheduler agent
        await scheduler_agent.update_after_activity(
            state,
            {
                "pillar": request.pillar,
                "item_id": request.item_id,
                "correct": request.correct,
                "accuracy": request.accuracy
            }
        )

        progress = result_state.get("progress", {})

        return ProgressUpdateResponse(
            status="success",
            message="Progresso atualizado com sucesso",
            updated_streak=progress.get("current_streak_days", 0),
            today_minutes=progress.get("today_study_minutes", 0),
            today_activities=progress.get("today_activities_completed", 0),
            srs_updated=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating progress: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar progresso: {str(e)}"
        )


# ==================== STREAK ENDPOINT ====================

@router.get("/streak/{user_id}")
async def get_streak(user_id: str):
    """
    Get streak information for a user.
    """
    try:
        user = await cosmos_db_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        # Check if streak is still valid
        last_activity = user.get("last_activity_date")
        current_streak = user.get("current_streak_days", 0)

        if last_activity:
            last_date = datetime.fromisoformat(last_activity).date()
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)

            # If last activity was before yesterday, streak is broken
            if last_date < yesterday:
                current_streak = 0

        return {
            "current_streak": current_streak,
            "longest_streak": user.get("longest_streak_days", 0),
            "last_activity_date": last_activity,
            "streak_active": current_streak > 0
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting streak: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter streak: {str(e)}"
        )