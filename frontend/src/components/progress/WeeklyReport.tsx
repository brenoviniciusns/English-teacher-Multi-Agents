/**
 * Weekly Report Component
 * Displays comprehensive weekly progress report with charts and achievements
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
  LineChart,
  Line
} from 'recharts';
import { Trophy, TrendingUp, TrendingDown, Clock, Flame, Star, AlertTriangle } from 'lucide-react';
import { useAppDispatch, useAppSelector, fetchWeeklyReport } from '../../store';

interface WeeklyReportProps {
  userId: string;
  weekStart?: string;
}

export const WeeklyReport: FC<WeeklyReportProps> = ({ userId, weekStart }) => {
  const dispatch = useAppDispatch();
  const { weeklyReport, loading, error } = useAppSelector((state) => state.progress);

  useEffect(() => {
    dispatch(fetchWeeklyReport({ userId, weekStart }));
  }, [dispatch, userId, weekStart]);

  if (loading && !weeklyReport) {
    return (
      <div className="card bg-base-100 shadow-lg">
        <div className="card-body">
          <div className="flex items-center justify-center h-48">
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

  if (!weeklyReport) {
    return null;
  }

  // Format daily breakdown for chart
  const dailyChartData = weeklyReport.dailyBreakdown.map((day) => ({
    date: new Date(day.date).toLocaleDateString('pt-BR', { weekday: 'short' }),
    minutos: day.minutes,
    atividades: day.activities
  }));

  // Format pillar data for chart
  const pillarChartData = Object.entries(weeklyReport.activitiesByPillar).map(([pillar, count]) => ({
    pillar: getPillarName(pillar),
    atividades: count
  }));

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="card bg-gradient-to-r from-primary to-secondary text-primary-content shadow-lg">
        <div className="card-body">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="card-title text-2xl">Relatório Semanal</h2>
              <p className="opacity-80">
                {formatDateRange(weeklyReport.weekStart, weeklyReport.weekEnd)}
              </p>
            </div>
            <Trophy className="w-16 h-16 opacity-50" />
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryCard
          icon={<Clock className="w-6 h-6" />}
          label="Tempo Total"
          value={formatTime(weeklyReport.totalStudyMinutes)}
          trend={weeklyReport.totalStudyMinutes > 120 ? 'up' : 'down'}
        />
        <SummaryCard
          icon={<Star className="w-6 h-6" />}
          label="Atividades"
          value={weeklyReport.activitiesCompleted.toString()}
          trend={weeklyReport.activitiesCompleted > 20 ? 'up' : 'neutral'}
        />
        <SummaryCard
          icon={<Flame className="w-6 h-6" />}
          label="Streak"
          value={`${weeklyReport.currentStreak} dias`}
          highlight={weeklyReport.streakMaintained}
        />
        <SummaryCard
          icon={<TrendingUp className="w-6 h-6" />}
          label="Precisão Média"
          value={`${calculateAverageAccuracy(weeklyReport).toFixed(0)}%`}
          trend={calculateAverageAccuracy(weeklyReport) > 80 ? 'up' : 'down'}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Activity Chart */}
        <div className="card bg-base-100 shadow-lg">
          <div className="card-body">
            <h3 className="card-title text-lg">Atividade Diária</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dailyChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="minutos" fill="#3B82F6" name="Minutos" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Pillar Distribution Chart */}
        <div className="card bg-base-100 shadow-lg">
          <div className="card-body">
            <h3 className="card-title text-lg">Atividades por Pilar</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={pillarChartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="pillar" width={100} />
                  <Tooltip />
                  <Bar dataKey="atividades" fill="#10B981" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Progress */}
      <div className="card bg-base-100 shadow-lg">
        <div className="card-body">
          <h3 className="card-title text-lg">Progresso Detalhado</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            <DetailStat
              label="Palavras Aprendidas"
              value={weeklyReport.wordsLearned}
              subtext="novas"
            />
            <DetailStat
              label="Palavras Revisadas"
              value={weeklyReport.wordsReviewed}
              subtext="revisões"
            />
            <DetailStat
              label="Regras de Gramática"
              value={weeklyReport.grammarRulesPracticed}
              subtext="praticadas"
            />
            <DetailStat
              label="Sons Praticados"
              value={weeklyReport.pronunciationSoundsPracticed}
              subtext="fonemas"
            />
          </div>

          {/* Accuracy by Pillar */}
          <div className="mt-6">
            <h4 className="font-semibold mb-3">Precisão por Pilar</h4>
            <div className="space-y-3">
              <AccuracyBar
                label="Vocabulário"
                value={weeklyReport.averageVocabularyAccuracy}
                color="bg-blue-500"
              />
              <AccuracyBar
                label="Gramática"
                value={weeklyReport.averageGrammarAccuracy}
                color="bg-green-500"
              />
              <AccuracyBar
                label="Pronúncia"
                value={weeklyReport.averagePronunciationAccuracy}
                color="bg-amber-500"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Achievements and Areas to Improve */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Achievements */}
        {weeklyReport.achievements.length > 0 && (
          <div className="card bg-success/10 shadow-lg">
            <div className="card-body">
              <h3 className="card-title text-lg text-success">
                <Trophy className="w-5 h-5" />
                Conquistas da Semana
              </h3>
              <ul className="space-y-2 mt-2">
                {weeklyReport.achievements.map((achievement, index) => (
                  <li key={index} className="flex items-center gap-2">
                    <Star className="w-4 h-4 text-success" />
                    <span>{achievement}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Areas to Improve */}
        {weeklyReport.areasToImprove.length > 0 && (
          <div className="card bg-warning/10 shadow-lg">
            <div className="card-body">
              <h3 className="card-title text-lg text-warning">
                <AlertTriangle className="w-5 h-5" />
                Áreas para Melhorar
              </h3>
              <ul className="space-y-2 mt-2">
                {weeklyReport.areasToImprove.map((area, index) => (
                  <li key={index} className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-warning" />
                    <span>{area}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Summary Card Component
interface SummaryCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  trend?: 'up' | 'down' | 'neutral';
  highlight?: boolean;
}

const SummaryCard: FC<SummaryCardProps> = ({ icon, label, value, trend, highlight }) => {
  return (
    <div className={`card ${highlight ? 'bg-success/20' : 'bg-base-100'} shadow`}>
      <div className="card-body py-4">
        <div className="flex items-center gap-2 text-base-content/70">
          {icon}
          <span className="text-sm">{label}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-2xl font-bold">{value}</span>
          {trend === 'up' && <TrendingUp className="w-4 h-4 text-success" />}
          {trend === 'down' && <TrendingDown className="w-4 h-4 text-error" />}
        </div>
      </div>
    </div>
  );
};

// Detail Stat Component
interface DetailStatProps {
  label: string;
  value: number;
  subtext: string;
}

const DetailStat: FC<DetailStatProps> = ({ label, value, subtext }) => {
  return (
    <div className="text-center p-3 bg-base-200/50 rounded-lg">
      <div className="text-sm text-base-content/70">{label}</div>
      <div className="text-3xl font-bold text-primary">{value}</div>
      <div className="text-xs text-base-content/50">{subtext}</div>
    </div>
  );
};

// Accuracy Bar Component
interface AccuracyBarProps {
  label: string;
  value: number;
  color: string;
}

const AccuracyBar: FC<AccuracyBarProps> = ({ label, value, color }) => {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span>{label}</span>
        <span className="font-medium">{value.toFixed(0)}%</span>
      </div>
      <div className="w-full bg-base-300 rounded-full h-2">
        <div
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
    </div>
  );
};

// Helper functions
function formatDateRange(start: string, end: string): string {
  const startDate = new Date(start);
  const endDate = new Date(end);
  return `${startDate.toLocaleDateString('pt-BR', {
    day: 'numeric',
    month: 'short'
  })} - ${endDate.toLocaleDateString('pt-BR', { day: 'numeric', month: 'short' })}`;
}

function formatTime(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}

function getPillarName(pillar: string): string {
  const names: Record<string, string> = {
    vocabulary: 'Vocabulário',
    grammar: 'Gramática',
    pronunciation: 'Pronúncia',
    speaking: 'Conversação'
  };
  return names[pillar] || pillar;
}

function calculateAverageAccuracy(report: {
  averageVocabularyAccuracy: number;
  averageGrammarAccuracy: number;
  averagePronunciationAccuracy: number;
}): number {
  const values = [
    report.averageVocabularyAccuracy,
    report.averageGrammarAccuracy,
    report.averagePronunciationAccuracy
  ].filter((v) => v > 0);
  return values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0;
}

export default WeeklyReport;