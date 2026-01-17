/**
 * TypeScript type definitions for the English Learning App
 */

// ==================== USER TYPES ====================

export interface User {
  id: string;
  email: string;
  name: string;
  currentLevel: 'beginner' | 'intermediate';
  nativeLanguage: string;
  learningGoals: string[];
  dailyGoalMinutes: number;
  createdAt: string;
  lastActivityDate?: string;
}

// ==================== PROGRESS TYPES ====================

export interface PillarProgress {
  pillar: 'vocabulary' | 'grammar' | 'pronunciation' | 'speaking';
  totalItems: number;
  masteredItems: number;
  learningItems: number;
  averageScore: number;
  averageAccuracy: number;
  studyTimeMinutes: number;
  itemsDueForReview: number;
  itemsLowFrequency: number;
  lastActivity?: string;
  streakDays: number;
}

export interface OverallProgress {
  userId: string;
  currentLevel: 'beginner' | 'intermediate';
  vocabulary: PillarProgress;
  grammar: PillarProgress;
  pronunciation: PillarProgress;
  speaking: PillarProgress;
  overallScore: number;
  totalStudyTimeMinutes: number;
  totalActivitiesCompleted: number;
  currentStreakDays: number;
  longestStreakDays: number;
  lastActivityDate?: string;
  initialAssessmentCompleted: boolean;
  readyForLevelUp: boolean;
  weakestPillar?: string;
  dailyGoalMinutes: number;
  todayStudyMinutes: number;
  todayActivitiesCompleted: number;
  message?: string;
}

// ==================== SCHEDULE TYPES ====================

export interface ScheduledReviewItem {
  id: string;
  type: string;
  pillar: 'vocabulary' | 'grammar' | 'pronunciation' | 'speaking';
  itemId?: string;
  reason: 'srs_due' | 'low_frequency' | 'low_accuracy' | 'daily_practice';
  priority: 'high' | 'normal' | 'low';
  estimatedMinutes: number;
  completed: boolean;
  completedAt?: string;
}

export interface DailyGoalProgress {
  minutesStudied: number;
  activitiesCompleted: number;
  goalMinutes: number;
  totalActivities: number;
  percentageComplete: number;
}

export interface DailySchedule {
  date: string;
  userId: string;
  scheduledReviews: ScheduledReviewItem[];
  completedReviews: ScheduledReviewItem[];
  dailyGoalProgress: DailyGoalProgress;
  message?: string;
}

export interface WeekSchedule {
  schedules: DailySchedule[];
  weekSummary: {
    totalMinutes: number;
    totalActivities: number;
    daysWithActivity: number;
  };
}

// ==================== WEEKLY REPORT TYPES ====================

export interface DailyBreakdown {
  date: string;
  minutes: number;
  activities: number;
}

export interface WeeklyReport {
  userId: string;
  weekStart: string;
  weekEnd: string;
  totalStudyMinutes: number;
  dailyBreakdown: DailyBreakdown[];
  activitiesCompleted: number;
  activitiesByPillar: Record<string, number>;
  wordsLearned: number;
  wordsReviewed: number;
  grammarRulesPracticed: number;
  pronunciationSoundsPracticed: number;
  speakingSessions: number;
  averageVocabularyAccuracy: number;
  averageGrammarAccuracy: number;
  averagePronunciationAccuracy: number;
  streakMaintained: boolean;
  currentStreak: number;
  achievements: string[];
  areasToImprove: string[];
}

// ==================== ACTIVITY TYPES ====================

export interface NextActivity {
  hasActivity: boolean;
  activityType?: string;
  pillar?: 'vocabulary' | 'grammar' | 'pronunciation' | 'speaking';
  itemId?: string;
  source: 'srs' | 'pending' | 'low_frequency' | 'none';
  reason?: string;
  suggestions: ActivitySuggestion[];
  message?: string;
}

export interface ActivitySuggestion {
  type: string;
  pillar: string;
  category?: string;
  reason: string;
}

export interface ProgressUpdate {
  pillar: string;
  itemId: string;
  correct: boolean;
  accuracy?: number;
  timeSpentSeconds: number;
}

export interface ProgressUpdateResponse {
  status: string;
  message: string;
  updatedStreak: number;
  todayMinutes: number;
  todayActivities: number;
  srsUpdated: boolean;
  nextReviewDays?: number;
}

// ==================== STREAK TYPES ====================

export interface StreakInfo {
  currentStreak: number;
  longestStreak: number;
  lastActivityDate?: string;
  streakActive: boolean;
}

// ==================== API RESPONSE TYPES ====================

export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

export interface ApiError {
  status: number;
  message: string;
  detail?: string;
}

// ==================== REDUX STATE TYPES ====================

export interface ProgressState {
  overallProgress: OverallProgress | null;
  weeklyReport: WeeklyReport | null;
  streakInfo: StreakInfo | null;
  loading: boolean;
  error: string | null;
}

export interface ScheduleState {
  todaySchedule: DailySchedule | null;
  weekSchedule: WeekSchedule | null;
  nextActivity: NextActivity | null;
  loading: boolean;
  error: string | null;
}

export interface AppState {
  progress: ProgressState;
  schedule: ScheduleState;
}