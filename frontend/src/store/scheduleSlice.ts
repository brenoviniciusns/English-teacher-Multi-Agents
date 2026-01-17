/**
 * Schedule Redux Slice
 * Manages schedule-related state: daily schedules, week schedules, and next activities
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { scheduleApi } from '../services/api';
import type {
  ScheduleState,
  DailySchedule,
  WeekSchedule,
  NextActivity,
  ProgressUpdateResponse,
  ScheduledReviewItem
} from '../types';

// Initial state
const initialState: ScheduleState = {
  todaySchedule: null,
  weekSchedule: null,
  nextActivity: null,
  loading: false,
  error: null
};

// Async thunks
export const fetchTodaySchedule = createAsyncThunk<
  DailySchedule,
  string,
  { rejectValue: string }
>(
  'schedule/fetchTodaySchedule',
  async (userId, { rejectWithValue }) => {
    try {
      return await scheduleApi.getTodaySchedule(userId);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Erro ao carregar agenda do dia';
      return rejectWithValue(message);
    }
  }
);

export const fetchWeekSchedule = createAsyncThunk<
  WeekSchedule,
  string,
  { rejectValue: string }
>(
  'schedule/fetchWeekSchedule',
  async (userId, { rejectWithValue }) => {
    try {
      return await scheduleApi.getWeekSchedule(userId);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Erro ao carregar agenda da semana';
      return rejectWithValue(message);
    }
  }
);

export const fetchNextActivity = createAsyncThunk<
  NextActivity,
  string,
  { rejectValue: string }
>(
  'schedule/fetchNextActivity',
  async (userId, { rejectWithValue }) => {
    try {
      return await scheduleApi.getNextActivity(userId);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Erro ao carregar próxima atividade';
      return rejectWithValue(message);
    }
  }
);

export const completeReview = createAsyncThunk<
  ProgressUpdateResponse,
  { userId: string; reviewId: string; result: Record<string, unknown> },
  { rejectValue: string }
>(
  'schedule/completeReview',
  async ({ userId, reviewId, result }, { rejectWithValue }) => {
    try {
      return await scheduleApi.completeReview(userId, reviewId, result);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Erro ao completar revisão';
      return rejectWithValue(message);
    }
  }
);

// Slice
const scheduleSlice = createSlice({
  name: 'schedule',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setTodaySchedule: (state, action: PayloadAction<DailySchedule>) => {
      state.todaySchedule = action.payload;
    },
    markReviewCompleted: (state, action: PayloadAction<string>) => {
      if (state.todaySchedule) {
        const reviewId = action.payload;
        const reviewIndex = state.todaySchedule.scheduledReviews.findIndex(
          (r) => r.id === reviewId
        );
        if (reviewIndex !== -1) {
          const review = state.todaySchedule.scheduledReviews[reviewIndex];
          review.completed = true;
          review.completedAt = new Date().toISOString();

          // Move from scheduled to completed
          state.todaySchedule.scheduledReviews.splice(reviewIndex, 1);
          state.todaySchedule.completedReviews.push(review);

          // Update goal progress
          state.todaySchedule.dailyGoalProgress.activitiesCompleted += 1;
          state.todaySchedule.dailyGoalProgress.minutesStudied += review.estimatedMinutes;
          state.todaySchedule.dailyGoalProgress.percentageComplete = Math.min(
            (state.todaySchedule.dailyGoalProgress.minutesStudied /
             state.todaySchedule.dailyGoalProgress.goalMinutes) * 100,
            100
          );
        }
      }
    },
    updateGoalProgress: (state, action: PayloadAction<{ minutes: number; activities: number }>) => {
      if (state.todaySchedule) {
        state.todaySchedule.dailyGoalProgress.minutesStudied += action.payload.minutes;
        state.todaySchedule.dailyGoalProgress.activitiesCompleted += action.payload.activities;
        state.todaySchedule.dailyGoalProgress.percentageComplete = Math.min(
          (state.todaySchedule.dailyGoalProgress.minutesStudied /
           state.todaySchedule.dailyGoalProgress.goalMinutes) * 100,
          100
        );
      }
    },
    setNextActivity: (state, action: PayloadAction<NextActivity>) => {
      state.nextActivity = action.payload;
    },
    clearNextActivity: (state) => {
      state.nextActivity = null;
    }
  },
  extraReducers: (builder) => {
    // Fetch Today Schedule
    builder
      .addCase(fetchTodaySchedule.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchTodaySchedule.fulfilled, (state, action) => {
        state.loading = false;
        state.todaySchedule = action.payload;
      })
      .addCase(fetchTodaySchedule.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });

    // Fetch Week Schedule
    builder
      .addCase(fetchWeekSchedule.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchWeekSchedule.fulfilled, (state, action) => {
        state.loading = false;
        state.weekSchedule = action.payload;
      })
      .addCase(fetchWeekSchedule.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });

    // Fetch Next Activity
    builder
      .addCase(fetchNextActivity.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchNextActivity.fulfilled, (state, action) => {
        state.loading = false;
        state.nextActivity = action.payload;
      })
      .addCase(fetchNextActivity.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });

    // Complete Review
    builder
      .addCase(completeReview.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(completeReview.fulfilled, (state, action) => {
        state.loading = false;
        // Update today schedule with response data
        if (state.todaySchedule) {
          state.todaySchedule.dailyGoalProgress.minutesStudied = action.payload.todayMinutes;
          state.todaySchedule.dailyGoalProgress.activitiesCompleted = action.payload.todayActivities;
          state.todaySchedule.dailyGoalProgress.percentageComplete = Math.min(
            (action.payload.todayMinutes / state.todaySchedule.dailyGoalProgress.goalMinutes) * 100,
            100
          );
        }
      })
      .addCase(completeReview.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });
  }
});

// Export actions
export const {
  clearError,
  setTodaySchedule,
  markReviewCompleted,
  updateGoalProgress,
  setNextActivity,
  clearNextActivity
} = scheduleSlice.actions;

// Export reducer
export default scheduleSlice.reducer;