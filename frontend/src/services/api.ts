/**
 * API Service
 * Centralized API client for communicating with the backend
 */
import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  OverallProgress,
  PillarProgress,
  DailySchedule,
  WeekSchedule,
  WeeklyReport,
  NextActivity,
  ProgressUpdate,
  ProgressUpdateResponse,
  StreakInfo
} from '../types';

// API base URL from environment
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_V1_PREFIX = '/api/v1';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}${API_V1_PREFIX}`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor for auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Helper to convert snake_case to camelCase
function toCamelCase(obj: Record<string, unknown>): Record<string, unknown> {
  if (Array.isArray(obj)) {
    return obj.map((item) =>
      typeof item === 'object' && item !== null ? toCamelCase(item as Record<string, unknown>) : item
    ) as unknown as Record<string, unknown>;
  }

  if (obj !== null && typeof obj === 'object') {
    return Object.keys(obj).reduce((result, key) => {
      const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
      const value = obj[key];
      result[camelKey] = typeof value === 'object' && value !== null
        ? toCamelCase(value as Record<string, unknown>)
        : value;
      return result;
    }, {} as Record<string, unknown>);
  }

  return obj;
}

// ==================== PROGRESS API ====================

export const progressApi = {
  /**
   * Get complete dashboard data for a user
   */
  getDashboard: async (userId: string, includeWeeklyReport = false): Promise<OverallProgress> => {
    const response = await apiClient.get(`/progress/dashboard/${userId}`, {
      params: { include_weekly_report: includeWeeklyReport }
    });
    return toCamelCase(response.data) as unknown as OverallProgress;
  },

  /**
   * Get detailed progress for a specific pillar
   */
  getPillarProgress: async (userId: string, pillar: string): Promise<PillarProgress> => {
    const response = await apiClient.get(`/progress/pillar/${userId}/${pillar}`);
    return toCamelCase(response.data) as unknown as PillarProgress;
  },

  /**
   * Get weekly progress report
   */
  getWeeklyReport: async (userId: string, weekStart?: string): Promise<WeeklyReport> => {
    const params = weekStart ? { week_start: weekStart } : {};
    const response = await apiClient.get(`/progress/weekly-report/${userId}`, { params });
    return toCamelCase(response.data) as unknown as WeeklyReport;
  },

  /**
   * Update progress after completing an activity
   */
  updateProgress: async (userId: string, update: ProgressUpdate): Promise<ProgressUpdateResponse> => {
    const response = await apiClient.post(`/progress/update/${userId}`, {
      pillar: update.pillar,
      item_id: update.itemId,
      correct: update.correct,
      accuracy: update.accuracy,
      time_spent_seconds: update.timeSpentSeconds
    });
    return toCamelCase(response.data) as unknown as ProgressUpdateResponse;
  },

  /**
   * Get streak information
   */
  getStreak: async (userId: string): Promise<StreakInfo> => {
    const response = await apiClient.get(`/progress/streak/${userId}`);
    return toCamelCase(response.data) as unknown as StreakInfo;
  }
};

// ==================== SCHEDULE API ====================

export const scheduleApi = {
  /**
   * Get today's study schedule
   */
  getTodaySchedule: async (userId: string): Promise<DailySchedule> => {
    const response = await apiClient.get(`/progress/schedule/today/${userId}`);
    return toCamelCase(response.data) as unknown as DailySchedule;
  },

  /**
   * Get week's schedule
   */
  getWeekSchedule: async (userId: string): Promise<WeekSchedule> => {
    const response = await apiClient.get(`/progress/schedule/week/${userId}`);
    return toCamelCase(response.data) as unknown as WeekSchedule;
  },

  /**
   * Mark a scheduled review as completed
   */
  completeReview: async (userId: string, reviewId: string, result: Record<string, unknown>): Promise<ProgressUpdateResponse> => {
    const response = await apiClient.post(`/progress/schedule/complete-review/${userId}`, {
      review_id: reviewId,
      result
    });
    return toCamelCase(response.data) as unknown as ProgressUpdateResponse;
  },

  /**
   * Get next recommended activity
   */
  getNextActivity: async (userId: string): Promise<NextActivity> => {
    const response = await apiClient.get(`/progress/next-activity/${userId}`);
    return toCamelCase(response.data) as unknown as NextActivity;
  }
};

// ==================== VOCABULARY API ====================

export const vocabularyApi = {
  /**
   * Get next vocabulary exercise
   */
  getNextActivity: async (userId: string, context = 'general') => {
    const response = await apiClient.get('/vocabulary/next-activity', {
      params: { user_id: userId, context }
    });
    return toCamelCase(response.data);
  },

  /**
   * Submit vocabulary answer
   */
  submitAnswer: async (userId: string, data: {
    activityId: string;
    wordId: string;
    answer: string;
    responseTimeMs: number;
  }) => {
    const response = await apiClient.post('/vocabulary/submit-answer', {
      activity_id: data.activityId,
      word_id: data.wordId,
      answer: data.answer,
      response_time_ms: data.responseTimeMs
    }, { params: { user_id: userId } });
    return toCamelCase(response.data);
  },

  /**
   * Get vocabulary progress
   */
  getProgress: async (userId: string) => {
    const response = await apiClient.get('/vocabulary/progress', {
      params: { user_id: userId }
    });
    return toCamelCase(response.data);
  },

  /**
   * Get words due for review
   */
  getReviewList: async (userId: string, limit = 10) => {
    const response = await apiClient.get('/vocabulary/review-list', {
      params: { user_id: userId, limit }
    });
    return toCamelCase(response.data);
  }
};

// ==================== GRAMMAR API ====================

export const grammarApi = {
  /**
   * Get next grammar lesson
   */
  getNextLesson: async (userId: string) => {
    const response = await apiClient.get('/grammar/next-lesson', {
      params: { user_id: userId }
    });
    return toCamelCase(response.data);
  },

  /**
   * Submit grammar explanation
   */
  submitExplanation: async (userId: string, data: {
    ruleId: string;
    explanation: string;
  }) => {
    const response = await apiClient.post('/grammar/submit-explanation', {
      rule_id: data.ruleId,
      explanation: data.explanation
    }, { params: { user_id: userId } });
    return toCamelCase(response.data);
  },

  /**
   * Get grammar progress
   */
  getProgress: async (userId: string) => {
    const response = await apiClient.get('/grammar/progress', {
      params: { user_id: userId }
    });
    return toCamelCase(response.data);
  }
};

// ==================== PRONUNCIATION API ====================

export const pronunciationApi = {
  /**
   * Get next pronunciation exercise
   */
  getNextExercise: async (userId: string) => {
    const response = await apiClient.get('/pronunciation/next-exercise', {
      params: { user_id: userId }
    });
    return toCamelCase(response.data);
  },

  /**
   * Submit pronunciation audio for evaluation
   */
  submitAudio: async (userId: string, data: {
    exerciseId: string;
    soundId: string;
    audioBlob: Blob;
  }) => {
    const formData = new FormData();
    formData.append('exercise_id', data.exerciseId);
    formData.append('sound_id', data.soundId);
    formData.append('audio', data.audioBlob, 'recording.wav');

    const response = await apiClient.post('/pronunciation/submit-audio', formData, {
      params: { user_id: userId },
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return toCamelCase(response.data);
  },

  /**
   * Get pronunciation progress
   */
  getProgress: async (userId: string) => {
    const response = await apiClient.get('/pronunciation/progress', {
      params: { user_id: userId }
    });
    return toCamelCase(response.data);
  }
};

// ==================== SPEAKING API ====================

export const speakingApi = {
  /**
   * Start a new speaking session
   */
  startSession: async (userId: string, topic?: string) => {
    const response = await apiClient.post('/speaking/start-session', {
      topic
    }, { params: { user_id: userId } });
    return toCamelCase(response.data);
  },

  /**
   * End a speaking session
   */
  endSession: async (userId: string, sessionId: string) => {
    const response = await apiClient.post(`/speaking/end-session/${sessionId}`, null, {
      params: { user_id: userId }
    });
    return toCamelCase(response.data);
  },

  /**
   * Get speaking session history
   */
  getHistory: async (userId: string, limit = 20) => {
    const response = await apiClient.get('/speaking/history', {
      params: { user_id: userId, limit }
    });
    return toCamelCase(response.data);
  },

  /**
   * Get speaking progress
   */
  getProgress: async (userId: string) => {
    const response = await apiClient.get('/speaking/progress', {
      params: { user_id: userId }
    });
    return toCamelCase(response.data);
  }
};

// Export default API object
export default {
  progress: progressApi,
  schedule: scheduleApi,
  vocabulary: vocabularyApi,
  grammar: grammarApi,
  pronunciation: pronunciationApi,
  speaking: speakingApi
};