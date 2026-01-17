/**
 * Review Schedule Component
 * Displays today's scheduled reviews and daily goal progress
 */
import { FC, useEffect } from 'react';
import { Calendar, Clock, CheckCircle2, Circle, Play, Target, Flame } from 'lucide-react';
import { useAppDispatch, useAppSelector, fetchTodaySchedule, completeReview } from '../../store';
import type { ScheduledReviewItem, DailyGoalProgress } from '../../types';

interface ReviewScheduleProps {
  userId: string;
  onStartReview?: (review: ScheduledReviewItem) => void;
}

// Pillar colors and icons
const PILLAR_CONFIG = {
  vocabulary: { color: 'bg-blue-500', name: 'Vocabulário' },
  grammar: { color: 'bg-green-500', name: 'Gramática' },
  pronunciation: { color: 'bg-amber-500', name: 'Pronúncia' },
  speaking: { color: 'bg-purple-500', name: 'Conversação' }
};

// Reason labels
const REASON_LABELS: Record<string, string> = {
  srs_due: 'Revisão SRS',
  low_frequency: 'Pouco usado',
  low_accuracy: 'Precisa praticar',
  daily_practice: 'Prática diária'
};

export const ReviewSchedule: FC<ReviewScheduleProps> = ({ userId, onStartReview }) => {
  const dispatch = useAppDispatch();
  const { todaySchedule, loading, error } = useAppSelector((state) => state.schedule);

  useEffect(() => {
    dispatch(fetchTodaySchedule(userId));
  }, [dispatch, userId]);

  if (loading && !todaySchedule) {
    return (
      <div className="card bg-base-100 shadow-lg">
        <div className="card-body">
          <div className="flex items-center justify-center h-32">
            <span className="loading loading-spinner loading-lg text-primary"></span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card bg-base-100 shadow-lg">
        <div className="card-body">
          <div className="alert alert-error">
            <span>{error}</span>
          </div>
        </div>
      </div>
    );
  }

  if (!todaySchedule) {
    return (
      <div className="card bg-base-100 shadow-lg">
        <div className="card-body">
          <div className="text-center text-base-content/70">
            Nenhuma atividade agendada para hoje
          </div>
        </div>
      </div>
    );
  }

  const { scheduledReviews, completedReviews, dailyGoalProgress, date } = todaySchedule;

  // Format date
  const formattedDate = new Date(date).toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long'
  });

  return (
    <div className="space-y-6">
      {/* Daily Goal Card */}
      <DailyGoalCard progress={dailyGoalProgress} />

      {/* Schedule Card */}
      <div className="card bg-base-100 shadow-lg">
        <div className="card-body">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Calendar className="w-6 h-6 text-primary" />
              <div>
                <h2 className="card-title text-lg">Agenda do Dia</h2>
                <p className="text-sm text-base-content/70 capitalize">{formattedDate}</p>
              </div>
            </div>
            <div className="badge badge-primary badge-lg">
              {completedReviews.length}/{scheduledReviews.length + completedReviews.length}
            </div>
          </div>

          {/* Scheduled Reviews */}
          {scheduledReviews.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-base-content/70 mb-3">
                Pendentes ({scheduledReviews.length})
              </h3>
              <div className="space-y-3">
                {scheduledReviews.map((review) => (
                  <ReviewItem
                    key={review.id}
                    review={review}
                    onStart={() => onStartReview?.(review)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Completed Reviews */}
          {completedReviews.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-base-content/70 mb-3">
                Concluídos ({completedReviews.length})
              </h3>
              <div className="space-y-3 opacity-60">
                {completedReviews.map((review) => (
                  <ReviewItem
                    key={review.id}
                    review={review}
                    completed
                  />
                ))}
              </div>
            </div>
          )}

          {/* Empty State */}
          {scheduledReviews.length === 0 && completedReviews.length === 0 && (
            <div className="text-center py-8 text-base-content/50">
              <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Nenhuma revisão agendada para hoje</p>
              <p className="text-sm">Continue praticando para manter seu progresso!</p>
            </div>
          )}

          {/* All Complete Message */}
          {scheduledReviews.length === 0 && completedReviews.length > 0 && (
            <div className="alert alert-success mt-4">
              <CheckCircle2 className="w-6 h-6" />
              <span>Parabéns! Você completou todas as revisões de hoje!</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Daily Goal Card Component
interface DailyGoalCardProps {
  progress: DailyGoalProgress;
}

const DailyGoalCard: FC<DailyGoalCardProps> = ({ progress }) => {
  const percentage = Math.min(progress.percentageComplete, 100);
  const isComplete = percentage >= 100;

  return (
    <div className={`card shadow-lg ${isComplete ? 'bg-success/20' : 'bg-base-100'}`}>
      <div className="card-body">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isComplete ? 'bg-success' : 'bg-primary'} bg-opacity-20`}>
              <Target className={`w-6 h-6 ${isComplete ? 'text-success' : 'text-primary'}`} />
            </div>
            <div>
              <h3 className="font-semibold">Meta Diária</h3>
              <p className="text-sm text-base-content/70">
                {progress.minutesStudied} de {progress.goalMinutes} minutos
              </p>
            </div>
          </div>
          <div className={`text-3xl font-bold ${isComplete ? 'text-success' : 'text-primary'}`}>
            {percentage.toFixed(0)}%
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-4">
          <progress
            className={`progress w-full ${isComplete ? 'progress-success' : 'progress-primary'}`}
            value={percentage}
            max="100"
          />
        </div>

        {/* Stats */}
        <div className="flex justify-between mt-3 text-sm">
          <div className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            <span>{progress.minutesStudied} minutos estudados</span>
          </div>
          <div className="flex items-center gap-1">
            <CheckCircle2 className="w-4 h-4" />
            <span>{progress.activitiesCompleted} atividades</span>
          </div>
        </div>

        {isComplete && (
          <div className="flex items-center justify-center mt-4 text-success">
            <Flame className="w-5 h-5 mr-2" />
            <span className="font-semibold">Meta alcançada! Continue assim!</span>
          </div>
        )}
      </div>
    </div>
  );
};

// Review Item Component
interface ReviewItemProps {
  review: ScheduledReviewItem;
  completed?: boolean;
  onStart?: () => void;
}

const ReviewItem: FC<ReviewItemProps> = ({ review, completed = false, onStart }) => {
  const pillarConfig = PILLAR_CONFIG[review.pillar as keyof typeof PILLAR_CONFIG] || {
    color: 'bg-gray-500',
    name: review.pillar
  };

  return (
    <div
      className={`
        flex items-center justify-between p-3 rounded-lg border
        ${completed ? 'border-base-300 bg-base-200/30' : 'border-base-300 bg-base-100 hover:bg-base-200'}
        transition-colors
      `}
    >
      <div className="flex items-center gap-3">
        {/* Status Icon */}
        {completed ? (
          <CheckCircle2 className="w-5 h-5 text-success" />
        ) : (
          <Circle className="w-5 h-5 text-base-content/30" />
        )}

        {/* Pillar Badge */}
        <div className={`px-2 py-1 rounded text-xs text-white ${pillarConfig.color}`}>
          {pillarConfig.name}
        </div>

        {/* Review Info */}
        <div>
          <div className="font-medium text-sm">
            {review.type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
          </div>
          <div className="text-xs text-base-content/60">
            {REASON_LABELS[review.reason] || review.reason}
            {' • '}
            {review.estimatedMinutes} min
          </div>
        </div>
      </div>

      {/* Action Button */}
      {!completed && onStart && (
        <button
          className="btn btn-sm btn-primary btn-circle"
          onClick={onStart}
          title="Iniciar revisão"
        >
          <Play className="w-4 h-4" />
        </button>
      )}

      {/* Completed Time */}
      {completed && review.completedAt && (
        <div className="text-xs text-base-content/50">
          {new Date(review.completedAt).toLocaleTimeString('pt-BR', {
            hour: '2-digit',
            minute: '2-digit'
          })}
        </div>
      )}

      {/* Priority Badge */}
      {!completed && review.priority === 'high' && (
        <div className="badge badge-error badge-sm">Urgente</div>
      )}
    </div>
  );
};

export default ReviewSchedule;