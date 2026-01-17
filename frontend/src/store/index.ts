/**
 * Redux Store Configuration
 * Main store setup combining all slices
 */
import { configureStore } from '@reduxjs/toolkit';
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';

import authReducer from './authSlice';
import assessmentReducer from './assessmentSlice';
import progressReducer from './progressSlice';
import scheduleReducer from './scheduleSlice';

// Create the store
export const store = configureStore({
  reducer: {
    auth: authReducer,
    assessment: assessmentReducer,
    progress: progressReducer,
    schedule: scheduleReducer
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE']
      }
    }),
  devTools: import.meta.env.DEV
});

// Infer types from the store
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Typed hooks for use throughout the app
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

// Export all actions from slices
// Auth actions
export {
  clearError as clearAuthError,
  logout,
  setUser,
  updateUserScores,
  setAssessmentCompleted,
  setUserLevel,
  registerUser,
  loginUser,
  fetchCurrentUser,
  updateUserProfile
} from './authSlice';

// Assessment actions
export {
  clearError as clearAssessmentError,
  clearAssessment,
  addAnswer,
  updateAnswer,
  setAnswers,
  clearAnswers,
  updateCurrentStep,
  startAssessment,
  submitAssessmentAnswers,
  fetchAssessmentResult,
  fetchAssessmentStatus,
  cancelAssessment
} from './assessmentSlice';

// Progress actions
export {
  clearError as clearProgressError,
  setOverallProgress,
  incrementTodayMinutes,
  incrementTodayActivities,
  updateStreak,
  fetchDashboard,
  fetchWeeklyReport,
  fetchStreak,
  updateProgress
} from './progressSlice';

// Schedule actions
export {
  clearError as clearScheduleError,
  setTodaySchedule,
  setNextActivity,
  markReviewCompleted,
  updateGoalProgress,
  clearNextActivity,
  fetchTodaySchedule,
  fetchWeekSchedule,
  fetchNextActivity,
  completeReview
} from './scheduleSlice';

export default store;