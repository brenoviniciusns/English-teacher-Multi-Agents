/**
 * Progress Dashboard Component
 * Main dashboard showing overall progress, streaks, and daily goals
 */
import { FC, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { Flame, Target, TrendingUp, Award, Clock, BookOpen } from 'lucide-react';
import { useAppDispatch, useAppSelector, fetchDashboard, fetchStreak } from '../../store';
import type { OverallProgress, PillarProgress } from '../../types';

interface ProgressDashboardProps {
  userId: string;
}

// Color palette for pillars
const PILLAR_COLORS = {
  vocabulary: '#3B82F6', // Blue
  grammar: '#10B981', // Green
  pronunciation: '#F59E0B', // Amber
  speaking: '#8B5CF6' // Purple
};

// Pillar names in Portuguese
const PILLAR_NAMES = {
  vocabulary: 'Vocabulário',
  grammar: 'Gramática',
  pronunciation: 'Pronúncia',
  speaking: 'Conversação'
};

export const ProgressDashboard: FC<ProgressDashboardProps> = ({ userId }) => {
  const dispatch = useAppDispatch();
  const { overallProgress, streakInfo, loading, error } = useAppSelector(
    (state) => state.progress
  );

  useEffect(() => {
    dispatch(fetchDashboard({ userId }));
    dispatch(fetchStreak(userId));
  }, [dispatch, userId]);

  if (loading && !overallProgress) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="loading loading-spinner loading-lg text-primary"></span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-error">
        <span>{error}</span>
      </div>
    );
  }

  if (!overallProgress) {
    return (
      <div className="alert alert-info">
        <span>Nenhum dado de progresso encontrado. Comece uma atividade!</span>
      </div>
    );
  }

  // Prepare data for charts
  const pillarData = [
    {
      name: PILLAR_NAMES.vocabulary,
      score: overallProgress.vocabulary.averageScore,
      color: PILLAR_COLORS.vocabulary
    },
    {
      name: PILLAR_NAMES.grammar,
      score: overallProgress.grammar.averageScore,
      color: PILLAR_COLORS.grammar
    },
    {
      name: PILLAR_NAMES.pronunciation,
      score: overallProgress.pronunciation.averageAccuracy,
      color: PILLAR_COLORS.pronunciation
    },
    {
      name: PILLAR_NAMES.speaking,
      score: overallProgress.speaking.averageScore,
      color: PILLAR_COLORS.speaking
    }
  ];

  const dailyGoalPercentage = Math.min(
    (overallProgress.todayStudyMinutes / overallProgress.dailyGoalMinutes) * 100,
    100
  );

  return (
    <div className="space-y-6">
      {/* Header with Level and Streak */}
      <div className="flex flex-wrap gap-4 justify-between items-start">
        {/* Level Badge */}
        <div className="flex items-center gap-3">
          <div className="badge badge-lg badge-primary">
            {overallProgress.currentLevel === 'beginner' ? 'Iniciante' : 'Intermediário'}
          </div>
          {overallProgress.readyForLevelUp && (
            <div className="badge badge-success badge-outline">
              Pronto para avançar!
            </div>
          )}
        </div>

        {/* Streak Counter */}
        <StreakCard
          currentStreak={overallProgress.currentStreakDays}
          longestStreak={overallProgress.longestStreakDays}
        />
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Overall Score */}
        <StatCard
          icon={<TrendingUp className="w-6 h-6" />}
          title="Score Geral"
          value={`${overallProgress.overallScore.toFixed(0)}%`}
          color="text-primary"
        />

        {/* Daily Goal Progress */}
        <StatCard
          icon={<Target className="w-6 h-6" />}
          title="Meta do Dia"
          value={`${overallProgress.todayStudyMinutes}/${overallProgress.dailyGoalMinutes} min`}
          color="text-success"
          progress={dailyGoalPercentage}
        />

        {/* Today's Activities */}
        <StatCard
          icon={<BookOpen className="w-6 h-6" />}
          title="Atividades Hoje"
          value={overallProgress.todayActivitiesCompleted.toString()}
          color="text-info"
        />

        {/* Total Study Time */}
        <StatCard
          icon={<Clock className="w-6 h-6" />}
          title="Tempo Total"
          value={formatStudyTime(overallProgress.totalStudyTimeMinutes)}
          color="text-secondary"
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pillar Progress Chart */}
        <div className="card bg-base-100 shadow-lg">
          <div className="card-body">
            <h3 className="card-title text-lg">Progresso por Pilar</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={pillarData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" domain={[0, 100]} />
                  <YAxis type="category" dataKey="name" width={100} />
                  <Tooltip
                    formatter={(value: number) => [`${value.toFixed(0)}%`, 'Score']}
                  />
                  <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                    {pillarData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Items Status Pie Chart */}
        <div className="card bg-base-100 shadow-lg">
          <div className="card-body">
            <h3 className="card-title text-lg">Status dos Itens</h3>
            <div className="h-64">
              <ItemsStatusChart progress={overallProgress} />
            </div>
          </div>
        </div>
      </div>

      {/* Weakest Pillar Alert */}
      {overallProgress.weakestPillar && (
        <div className="alert alert-warning">
          <Award className="w-6 h-6" />
          <div>
            <span className="font-semibold">Área de Foco: </span>
            <span>
              {PILLAR_NAMES[overallProgress.weakestPillar as keyof typeof PILLAR_NAMES]}
            </span>
            <span className="text-sm ml-2">
              - Recomendamos dedicar mais tempo a este pilar
            </span>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="card bg-base-100 shadow-lg">
        <div className="card-body">
          <h3 className="card-title text-lg">Ações Rápidas</h3>
          <div className="flex flex-wrap gap-3">
            <button className="btn btn-primary">
              <BookOpen className="w-4 h-4" />
              Praticar Vocabulário
            </button>
            <button className="btn btn-secondary">
              <TrendingUp className="w-4 h-4" />
              Revisar Gramática
            </button>
            <button className="btn btn-accent">
              <Target className="w-4 h-4" />
              Treinar Pronúncia
            </button>
            <button className="btn btn-info">
              <Clock className="w-4 h-4" />
              Iniciar Conversação
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Streak Card Component
interface StreakCardProps {
  currentStreak: number;
  longestStreak: number;
}

const StreakCard: FC<StreakCardProps> = ({ currentStreak, longestStreak }) => {
  const isActive = currentStreak > 0;

  return (
    <div className={`card bg-base-100 shadow ${isActive ? 'border-2 border-orange-500' : ''}`}>
      <div className="card-body py-3 px-4 flex-row items-center gap-3">
        <Flame className={`w-8 h-8 ${isActive ? 'text-orange-500' : 'text-gray-400'}`} />
        <div>
          <div className="text-2xl font-bold">
            {currentStreak}
            <span className="text-sm font-normal ml-1">dias</span>
          </div>
          <div className="text-xs text-base-content/70">
            Recorde: {longestStreak} dias
          </div>
        </div>
      </div>
    </div>
  );
};

// Stat Card Component
interface StatCardProps {
  icon: React.ReactNode;
  title: string;
  value: string;
  color: string;
  progress?: number;
}

const StatCard: FC<StatCardProps> = ({ icon, title, value, color, progress }) => {
  return (
    <div className="card bg-base-100 shadow">
      <div className="card-body py-4">
        <div className="flex items-center gap-3">
          <div className={color}>{icon}</div>
          <div className="flex-1">
            <div className="text-sm text-base-content/70">{title}</div>
            <div className="text-xl font-bold">{value}</div>
          </div>
        </div>
        {progress !== undefined && (
          <progress
            className="progress progress-success w-full mt-2"
            value={progress}
            max="100"
          />
        )}
      </div>
    </div>
  );
};

// Items Status Pie Chart Component
interface ItemsStatusChartProps {
  progress: OverallProgress;
}

const ItemsStatusChart: FC<ItemsStatusChartProps> = ({ progress }) => {
  const totalMastered =
    progress.vocabulary.masteredItems +
    progress.grammar.masteredItems +
    progress.pronunciation.masteredItems;

  const totalLearning =
    progress.vocabulary.learningItems +
    progress.grammar.learningItems +
    progress.pronunciation.learningItems;

  const totalDue =
    progress.vocabulary.itemsDueForReview +
    progress.grammar.itemsDueForReview +
    progress.pronunciation.itemsDueForReview;

  const data = [
    { name: 'Dominados', value: totalMastered, color: '#10B981' },
    { name: 'Aprendendo', value: totalLearning, color: '#3B82F6' },
    { name: 'Para Revisar', value: totalDue, color: '#F59E0B' }
  ].filter((item) => item.value > 0);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-base-content/50">
        Nenhum item ainda
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={80}
          paddingAngle={5}
          dataKey="value"
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
};

// Helper function to format study time
function formatStudyTime(minutes: number): string {
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}

export default ProgressDashboard;