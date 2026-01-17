/**
 * Pillar Progress Component
 * Detailed progress view for a specific learning pillar
 */
import { FC, useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadialBarChart,
  RadialBar,
  Legend
} from 'recharts';
import { BookOpen, CheckCircle, AlertCircle, Clock, TrendingUp, ArrowRight } from 'lucide-react';
import { progressApi } from '../../services/api';
import type { PillarProgress as PillarProgressType } from '../../types';

interface PillarProgressProps {
  userId: string;
  pillar: 'vocabulary' | 'grammar' | 'pronunciation' | 'speaking';
  onStartActivity?: () => void;
}

// Pillar configuration
const PILLAR_CONFIG = {
  vocabulary: {
    name: 'Vocabulário',
    description: 'Aprenda e revise as 2000 palavras mais comuns do inglês americano',
    icon: BookOpen,
    color: '#3B82F6',
    bgColor: 'bg-blue-500',
    textColor: 'text-blue-500'
  },
  grammar: {
    name: 'Gramática',
    description: 'Domine as regras gramaticais com comparação português-inglês',
    icon: CheckCircle,
    color: '#10B981',
    bgColor: 'bg-green-500',
    textColor: 'text-green-500'
  },
  pronunciation: {
    name: 'Pronúncia',
    description: 'Aprenda os sons do inglês que não existem em português',
    icon: AlertCircle,
    color: '#F59E0B',
    bgColor: 'bg-amber-500',
    textColor: 'text-amber-500'
  },
  speaking: {
    name: 'Conversação',
    description: 'Pratique conversação em tempo real com feedback automático',
    icon: Clock,
    color: '#8B5CF6',
    bgColor: 'bg-purple-500',
    textColor: 'text-purple-500'
  }
};

export const PillarProgress: FC<PillarProgressProps> = ({
  userId,
  pillar,
  onStartActivity
}) => {
  const [progress, setProgress] = useState<PillarProgressType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const config = PILLAR_CONFIG[pillar];
  const IconComponent = config.icon;

  useEffect(() => {
    const fetchProgress = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await progressApi.getPillarProgress(userId, pillar);
        setProgress(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro ao carregar progresso');
      } finally {
        setLoading(false);
      }
    };

    fetchProgress();
  }, [userId, pillar]);

  if (loading) {
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

  if (!progress) {
    return null;
  }

  // Calculate mastery percentage
  const masteryPercentage =
    progress.totalItems > 0
      ? Math.round((progress.masteredItems / progress.totalItems) * 100)
      : 0;

  // Radial chart data
  const radialData = [
    {
      name: 'Dominados',
      value: progress.masteredItems,
      fill: '#10B981'
    },
    {
      name: 'Aprendendo',
      value: progress.learningItems,
      fill: '#3B82F6'
    },
    {
      name: 'Para Revisar',
      value: progress.itemsDueForReview,
      fill: '#F59E0B'
    }
  ];

  return (
    <div className="card bg-base-100 shadow-lg">
      <div className="card-body">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className={`p-3 rounded-lg ${config.bgColor} bg-opacity-20`}>
              <IconComponent className={`w-8 h-8 ${config.textColor}`} />
            </div>
            <div>
              <h2 className="card-title text-xl">{config.name}</h2>
              <p className="text-sm text-base-content/70">{config.description}</p>
            </div>
          </div>
          <div className="badge badge-lg" style={{ backgroundColor: config.color, color: 'white' }}>
            {progress.averageScore.toFixed(0)}%
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <StatBox
            label="Total de Itens"
            value={progress.totalItems}
            icon={<BookOpen className="w-4 h-4" />}
          />
          <StatBox
            label="Dominados"
            value={progress.masteredItems}
            icon={<CheckCircle className="w-4 h-4 text-success" />}
            highlight="success"
          />
          <StatBox
            label="Aprendendo"
            value={progress.learningItems}
            icon={<TrendingUp className="w-4 h-4 text-info" />}
            highlight="info"
          />
          <StatBox
            label="Para Revisar"
            value={progress.itemsDueForReview}
            icon={<AlertCircle className="w-4 h-4 text-warning" />}
            highlight={progress.itemsDueForReview > 0 ? 'warning' : undefined}
          />
        </div>

        {/* Progress Bars */}
        <div className="mt-6 space-y-4">
          {/* Mastery Progress */}
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm font-medium">Progresso de Domínio</span>
              <span className="text-sm font-medium">{masteryPercentage}%</span>
            </div>
            <progress
              className="progress progress-success w-full"
              value={masteryPercentage}
              max="100"
            />
          </div>

          {/* Accuracy */}
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm font-medium">Precisão Média</span>
              <span className="text-sm font-medium">{progress.averageAccuracy.toFixed(0)}%</span>
            </div>
            <progress
              className="progress progress-primary w-full"
              value={progress.averageAccuracy}
              max="100"
            />
          </div>
        </div>

        {/* Chart */}
        {progress.totalItems > 0 && (
          <div className="mt-6">
            <h3 className="text-lg font-semibold mb-4">Distribuição de Itens</h3>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart
                  cx="50%"
                  cy="50%"
                  innerRadius="20%"
                  outerRadius="90%"
                  data={radialData}
                  startAngle={180}
                  endAngle={0}
                >
                  <RadialBar
                    minAngle={15}
                    background
                    clockWise
                    dataKey="value"
                    cornerRadius={5}
                  />
                  <Legend
                    iconSize={10}
                    layout="horizontal"
                    verticalAlign="bottom"
                  />
                  <Tooltip />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Action Button */}
        <div className="card-actions justify-end mt-6">
          {progress.itemsDueForReview > 0 && (
            <div className="text-sm text-warning mr-auto">
              {progress.itemsDueForReview} itens aguardando revisão
            </div>
          )}
          <button
            className="btn btn-primary"
            style={{ backgroundColor: config.color, borderColor: config.color }}
            onClick={onStartActivity}
          >
            {progress.itemsDueForReview > 0 ? 'Revisar Agora' : 'Praticar'}
            <ArrowRight className="w-4 h-4 ml-2" />
          </button>
        </div>
      </div>
    </div>
  );
};

// Stat Box Component
interface StatBoxProps {
  label: string;
  value: number;
  icon: React.ReactNode;
  highlight?: 'success' | 'info' | 'warning' | 'error';
}

const StatBox: FC<StatBoxProps> = ({ label, value, icon, highlight }) => {
  const highlightClasses = {
    success: 'border-success bg-success/10',
    info: 'border-info bg-info/10',
    warning: 'border-warning bg-warning/10',
    error: 'border-error bg-error/10'
  };

  return (
    <div
      className={`
        p-3 rounded-lg border
        ${highlight ? highlightClasses[highlight] : 'border-base-300 bg-base-200/50'}
      `}
    >
      <div className="flex items-center gap-2 text-base-content/70">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  );
};

export default PillarProgress;