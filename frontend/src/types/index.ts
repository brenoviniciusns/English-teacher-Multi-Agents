/**
 * TypeScript type definitions for the English Learning App
 */

// ==================== USER TYPES ====================

export interface UserProfile {
  learningGoals: string[];
  nativeLanguage: string;
  preferredStudyTime: string;
  dailyGoalMinutes: number;
  notificationsEnabled: boolean;
  voicePreference: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  currentLevel: 'beginner' | 'intermediate';
  profile: UserProfile;
  totalStudyTimeMinutes: number;
  currentStreakDays: number;
  vocabularyScore: number;
  grammarScore: number;
  pronunciationScore: number;
  speakingScore: number;
  initialAssessmentCompleted: boolean;
  nativeLanguage?: string;
  learningGoals?: string[];
  dailyGoalMinutes?: number;
  createdAt?: string;
  lastActivityDate?: string;
}

export interface UserRegistration {
  email: string;
  password: string;
  name: string;
  profile?: Partial<UserProfile>;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface AuthToken {
  accessToken: string;
  tokenType: string;
  user: User;
}

// ==================== ASSESSMENT TYPES ====================

export interface VocabularyAssessmentItem {
  word: string;
  difficulty: number;
}

export interface GrammarAssessmentItem {
  id: string;
  rule: string;
  example: string;
  question: string;
}

export interface PronunciationAssessmentItem {
  id: string;
  phoneme: string;
  words: string[];
  difficulty: string;
}

export interface AssessmentStepContent {
  type: string;
  items?: VocabularyAssessmentItem[] | GrammarAssessmentItem[] | PronunciationAssessmentItem[];
  prompts?: string[];
  instructions: string;
}

export interface AssessmentStart {
  assessmentId: string;
  assessmentType: 'initial' | 'continuous';
  step: number;
  stepName: string;
  totalSteps: number;
  content: AssessmentStepContent;
  instructions: string;
}

export interface AssessmentAnswer {
  id?: string;
  answer: string;
  correct?: boolean;
}

export interface AssessmentSubmitResponse {
  assessmentId: string;
  stepCompleted: number;
  stepName: string;
  stepScore: number;
  nextStep?: number;
  nextStepName?: string;
  nextContent?: AssessmentStepContent;
  isComplete: boolean;
}

export interface PillarScores {
  vocabulary: number;
  grammar: number;
  pronunciation: number;
  speaking: number;
}

export interface AssessmentResult {
  assessmentId: string;
  assessmentType: 'initial' | 'continuous';
  scores: PillarScores;
  overallScore: number;
  determinedLevel: 'beginner' | 'intermediate';
  previousLevel?: string;
  levelChanged: boolean;
  weakestPillar: string;
  recommendations: string[];
  message: string;
  completedAt?: string;
}

export interface AssessmentStatus {
  hasActiveAssessment: boolean;
  assessmentId?: string;
  assessmentType?: 'initial' | 'continuous';
  currentStep?: number;
  totalSteps?: number;
  stepScores?: Record<string, number>;
  initialAssessmentCompleted: boolean;
  lastAssessmentDate?: string;
  sessionsSinceLastAssessment?: number;
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

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

export interface AssessmentState {
  currentAssessment: AssessmentStart | null;
  assessmentResult: AssessmentResult | null;
  assessmentStatus: AssessmentStatus | null;
  currentAnswers: AssessmentAnswer[];
  loading: boolean;
  error: string | null;
}

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
  auth: AuthState;
  assessment: AssessmentState;
  progress: ProgressState;
  schedule: ScheduleState;
}