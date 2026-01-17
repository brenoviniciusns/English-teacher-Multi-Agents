/**
 * Level Progress Card Component
 * Shows user's current level and detailed progress towards the next level
 */
import { FC } from 'react';
import { Trophy, Star, BookOpen, MessageSquare, Volume2, CheckCircle, Circle, ArrowUp } from 'lucide-react';

export interface LevelRequirement {
  label: string;
  current: number;
  target: number;
  met: boolean;
}

export interface LevelProgress {
  current_level: string;
  next_level: string | null;
  overall_progress: number;
  requirements_met?: number;
  total_requirements?: number;
  message: string;
  requirements?: Record<string, LevelRequirement>;
}

interface LevelProgressCardProps {
  levelProgress: LevelProgress;
  onRequestAssessment?: () => void;
}

// Level display names
const LEVEL_NAMES: Record<string, string> = {
  beginner: 'Iniciante',
  intermediate: 'Intermediário',
  advanced: 'Avançado'
};

// Level colors
const LEVEL_COLORS: Record<string, string> = {
  beginner: 'badge-primary',
  intermediate: 'badge-secondary',
  advanced: 'badge-accent'
};

// Requirement icons
const getRequirementIcon = (key: string) => {
  if (key.includes('vocabulary')) return <BookOpen className="w-4 h-4" />;
  if (key.includes('grammar')) return <Star className="w-4 h-4" />;
  if (key.includes('pronunciation')) return <Volume2 className="w-4 h-4" />;
  if (key.includes('speaking')) return <MessageSquare className="w-4 h-4" />;
  return <Trophy className="w-4 h-4" />;
};

export const LevelProgressCard: FC<LevelProgressCardProps> = ({
  levelProgress,
  onRequestAssessment
}) => {
  const {
    current_level,
    next_level,
    overall_progress,
    requirements_met,
    total_requirements,
    message,
    requirements
  } = levelProgress;

  const currentLevelName = LEVEL_NAMES[current_level] || current_level;
  const nextLevelName = next_level ? LEVEL_NAMES[next_level] : null;
  const levelColorClass = LEVEL_COLORS[current_level] || 'badge-primary';

  // If at max level
  if (!next_level) {
    return (
      <div className="card bg-gradient-to-r from-primary to-secondary text-primary-content shadow-xl">
        <div className="card-body">
          <div className="flex items-center gap-3">
            <Trophy className="w-10 h-10" />
            <div>
              <h3 className="card-title">Nível Máximo Alcançado!</h3>
              <div className={`badge ${levelColorClass} badge-lg`}>
                {currentLevelName}
              </div>
            </div>
          </div>
          <p className="mt-4">{message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card bg-base-100 shadow-lg">
      <div className="card-body">
        {/* Header with Current Level */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="avatar placeholder">
              <div className="bg-primary text-primary-content rounded-full w-12">
                <Trophy className="w-6 h-6" />
              </div>
            </div>
            <div>
              <h3 className="card-title text-lg">Seu Nível</h3>
              <div className={`badge ${levelColorClass} badge-lg`}>
                {currentLevelName}
              </div>
            </div>
          </div>

          {overall_progress >= 100 && onRequestAssessment && (
            <button
              className="btn btn-success btn-sm gap-2"
              onClick={onRequestAssessment}
            >
              <ArrowUp className="w-4 h-4" />
              Avançar Nível
            </button>
          )}
        </div>

        {/* Progress to Next Level */}
        <div className="mt-4">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-base-content/70">Progresso para {nextLevelName}</span>
            <span className="font-semibold">{overall_progress}%</span>
          </div>
          <progress
            className={`progress w-full ${overall_progress >= 100 ? 'progress-success' : 'progress-primary'}`}
            value={overall_progress}
            max="100"
          />
          {requirements_met !== undefined && total_requirements !== undefined && (
            <div className="text-xs text-base-content/60 mt-1">
              {requirements_met} de {total_requirements} requisitos cumpridos
            </div>
          )}
        </div>

        {/* Progress Message */}
        <div className={`alert ${overall_progress >= 100 ? 'alert-success' : 'alert-info'} mt-4`}>
          <span>{message}</span>
        </div>

        {/* Requirements List */}
        {requirements && Object.keys(requirements).length > 0 && (
          <div className="mt-4">
            <h4 className="font-semibold mb-3">Requisitos para Avançar</h4>
            <div className="space-y-2">
              {Object.entries(requirements).map(([key, req]) => (
                <RequirementItem key={key} id={key} requirement={req} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Individual Requirement Item
interface RequirementItemProps {
  id: string;
  requirement: LevelRequirement;
}

const RequirementItem: FC<RequirementItemProps> = ({ id, requirement }) => {
  const { label, current, target, met } = requirement;
  const progress = Math.min((current / target) * 100, 100);
  const isPercentage = target === 75 || target === 85; // Score thresholds

  return (
    <div className="flex items-center gap-3 p-2 rounded-lg bg-base-200">
      {/* Status Icon */}
      {met ? (
        <CheckCircle className="w-5 h-5 text-success flex-shrink-0" />
      ) : (
        <Circle className="w-5 h-5 text-base-content/30 flex-shrink-0" />
      )}

      {/* Requirement Icon */}
      <div className={`${met ? 'text-success' : 'text-base-content/50'}`}>
        {getRequirementIcon(id)}
      </div>

      {/* Details */}
      <div className="flex-1 min-w-0">
        <div className="flex justify-between items-center">
          <span className={`text-sm ${met ? 'text-success font-medium' : ''}`}>
            {label}
          </span>
          <span className={`text-xs ${met ? 'text-success' : 'text-base-content/70'}`}>
            {isPercentage
              ? `${current.toFixed(0)}% / ${target}%`
              : `${current} / ${target}`
            }
          </span>
        </div>
        <progress
          className={`progress progress-xs w-full mt-1 ${met ? 'progress-success' : 'progress-primary'}`}
          value={progress}
          max="100"
        />
      </div>
    </div>
  );
};

export default LevelProgressCard;
