/**
 * Progress Redux Slice
 * Manages progress-related state: overall progress, weekly reports, and streaks
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { progressApi } from '../services/api';
import type {
  ProgressState,
  OverallProgress,
  WeeklyReport,
  StreakInfo,
  ProgressUpdate,
  ProgressUpdateResponse
} from '../types';

// Initial state
const initialState: ProgressState = {
  overallProgress: null,
  weeklyReport: null,
  streakInfo: null,
  loading: false,
  error: null
};

// Async thunks
export const fetchDashboard = createAsyncThunk<
  OverallProgress,
  { userId: string; includeWeeklyReport?: boolean },
  { rejectValue: string }
>(
  'progress/fetchDashboard',
  async ({ userId, includeWeeklyReport = false }, { rejectWithValue }) => {
    try {
      return await progressApi.getDashboard(userId, includeWeeklyReport);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Erro ao carregar dashboard';
      return rejectWithValue(message);
    }
  }
);

export const fetchWeeklyReport = createAsyncThunk<
  WeeklyReport,
  { userId: string; weekStart?: string },
  { rejectValue: string }
>(
  'progress/fetchWeeklyReport',
  async ({ userId, weekStart }, { rejectWithValue }) => {
    try {
      return await progressApi.getWeeklyReport(userId, weekStart);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Erro ao carregar relatório semanal';
      return rejectWithValue(message);
    }
  }
);

export const fetchStreak = createAsyncThunk<
  StreakInfo,
  string,
  { rejectValue: string }
>(
  'progress/fetchStreak',
  async (userId, { rejectWithValue }) => {
    try {
      return await progressApi.getStreak(userId);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Erro ao carregar streak';
      return rejectWithValue(message);
    }
  }
);

export const updateProgress = createAsyncThunk<
  ProgressUpdateResponse,
  { userId: string; update: ProgressUpdate },
  { rejectValue: string }
>(
  'progress/updateProgress',
  async ({ userId, update }, { rejectWithValue }) => {
    try {
      return await progressApi.updateProgress(userId, update);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Erro ao atualizar progresso';
      return rejectWithValue(message);
    }
  }
);

// Slice
const progressSlice = createSlice({
  name: 'progress',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setOverallProgress: (state, action: PayloadAction<OverallProgress>) => {
      state.overallProgress = action.payload;
    },
    incrementTodayMinutes: (state, action: PayloadAction<number>) => {
      if (state.overallProgress) {
        state.overallProgress.todayStudyMinutes += action.payload;
      }
    },
    incrementTodayActivities: (state) => {
      if (state.overallProgress) {
        state.overallProgress.todayActivitiesCompleted += 1;
      }
    },
    updateStreak: (state, action: PayloadAction<number>) => {
      if (state.overallProgress) {
        state.overallProgress.currentStreakDays = action.payload;
      }
      if (state.streakInfo) {
        state.streakInfo.currentStreak = action.payload;
      }
    }
  },
  extraReducers: (builder) => {
    // Fetch Dashboard
    builder
      .addCase(fetchDashboard.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDashboard.fulfilled, (state, action) => {
        state.loading = false;
        state.overallProgress = action.payload;
      })
      .addCase(fetchDashboard.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });

    // Fetch Weekly Report
    builder
      .addCase(fetchWeeklyReport.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchWeeklyReport.fulfilled, (state, action) => {
        state.loading = false;
        state.weeklyReport = action.payload;
      })
      .addCase(fetchWeeklyReport.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });

    // Fetch Streak
    builder
      .addCase(fetchStreak.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchStreak.fulfilled, (state, action) => {
        state.loading = false;
        state.streakInfo = action.payload;
      })
      .addCase(fetchStreak.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });

    // Update Progress
    builder
      .addCase(updateProgress.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateProgress.fulfilled, (state, action) => {
        state.loading = false;
        // Update local state with response data
        if (state.overallProgress) {
          state.overallProgress.todayStudyMinutes = action.payload.todayMinutes;
          state.overallProgress.todayActivitiesCompleted = action.payload.todayActivities;
          state.overallProgress.currentStreakDays = action.payload.updatedStreak;
        }
        if (state.streakInfo) {
          state.streakInfo.currentStreak = action.payload.updatedStreak;
        }
      })
      .addCase(updateProgress.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });
  }
});

// Export actions
export const {
  clearError,
  setOverallProgress,
  incrementTodayMinutes,
  incrementTodayActivities,
  updateStreak
} = progressSlice.actions;

// Export reducer
export default progressSlice.reducer;