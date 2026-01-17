/**
 * Dashboard Page
 * Main dashboard page integrating all progress components
 */
import { FC, useState } from 'react';
import { LayoutDashboard, Calendar, BarChart3, BookOpen } from 'lucide-react';
import { ProgressDashboard, ReviewSchedule, WeeklyReport, PillarProgress } from '../components/progress';

interface DashboardProps {
  userId: string;
}

type TabType = 'overview' | 'schedule' | 'report' | 'pillars';

const TABS = [
  { id: 'overview' as TabType, label: 'Visão Geral', icon: LayoutDashboard },
  { id: 'schedule' as TabType, label: 'Agenda', icon: Calendar },
  { id: 'report' as TabType, label: 'Relatório', icon: BarChart3 },
  { id: 'pillars' as TabType, label: 'Pilares', icon: BookOpen }
];

export const Dashboard: FC<DashboardProps> = ({ userId }) => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [selectedPillar, setSelectedPillar] = useState<'vocabulary' | 'grammar' | 'pronunciation' | 'speaking'>('vocabulary');

  const handleStartActivity = () => {
    // Navigate to activity page based on pillar
    console.log('Start activity for pillar:', selectedPillar);
  };

  const handleStartReview = (review: { pillar: string }) => {
    // Navigate to review activity
    console.log('Start review:', review);
  };

  return (
    <div className="min-h-screen bg-base-200">
      {/* Header */}
      <header className="bg-base-100 shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-primary">English Learning App</h1>
            <div className="flex items-center gap-4">
              <div className="badge badge-primary badge-lg">User: {userId}</div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="bg-base-100 border-b border-base-300">
        <div className="container mx-auto px-4">
          <div className="tabs tabs-boxed bg-transparent gap-2 py-2">
            {TABS.map((tab) => {
              const IconComponent = tab.icon;
              return (
                <button
                  key={tab.id}
                  className={`tab tab-lg gap-2 ${activeTab === tab.id ? 'tab-active' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  <IconComponent className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main Dashboard */}
            <div className="lg:col-span-2">
              <ProgressDashboard userId={userId} />
            </div>

            {/* Schedule Sidebar */}
            <div className="lg:col-span-1">
              <ReviewSchedule userId={userId} onStartReview={handleStartReview} />
            </div>
          </div>
        )}

        {/* Schedule Tab */}
        {activeTab === 'schedule' && (
          <ReviewSchedule userId={userId} onStartReview={handleStartReview} />
        )}

        {/* Report Tab */}
        {activeTab === 'report' && <WeeklyReport userId={userId} />}

        {/* Pillars Tab */}
        {activeTab === 'pillars' && (
          <div className="space-y-6">
            {/* Pillar Selector */}
            <div className="flex flex-wrap gap-2">
              {(['vocabulary', 'grammar', 'pronunciation', 'speaking'] as const).map((pillar) => (
                <button
                  key={pillar}
                  className={`btn ${selectedPillar === pillar ? 'btn-primary' : 'btn-outline'}`}
                  onClick={() => setSelectedPillar(pillar)}
                >
                  {pillar === 'vocabulary' && 'Vocabulário'}
                  {pillar === 'grammar' && 'Gramática'}
                  {pillar === 'pronunciation' && 'Pronúncia'}
                  {pillar === 'speaking' && 'Conversação'}
                </button>
              ))}
            </div>

            {/* Selected Pillar Progress */}
            <PillarProgress
              userId={userId}
              pillar={selectedPillar}
              onStartActivity={handleStartActivity}
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-base-100 border-t border-base-300 mt-auto">
        <div className="container mx-auto px-4 py-4">
          <p className="text-center text-sm text-base-content/60">
            English Learning Multi-Agent App - Powered by Azure AI
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Dashboard;