/**
 * Assessment Redux Slice
 * Manages assessment state: current assessment, results, and status
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { assessmentApi } from '../services/api';
import type {
  AssessmentState,
  AssessmentStart,
  AssessmentSubmitResponse,
  AssessmentResult,
  AssessmentStatus,
  AssessmentAnswer
} from '../types';

// Initial state
const initialState: AssessmentState = {
  currentAssessment: null,
  assessmentResult: null,
  assessmentStatus: null,
  currentAnswers: [],
  loading: false,
  error: null
};

// Async thunks
export const startAssessment = createAsyncThunk<
  AssessmentStart,
  string,
  { rejectValue: string }
>(
  'assessment/start',
  async (assessmentType = 'initial', { rejectWithValue }) => {
    try {
      return await assessmentApi.start(assessmentType);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      const message = err.response?.data?.detail || 'Erro ao iniciar avaliação';
      return rejectWithValue(message);
    }
  }
);

export const submitAssessmentAnswers = createAsyncThunk<
  AssessmentSubmitResponse,
  {
    assessmentId: string;
    step: number;
    stepName: string;
    answers: AssessmentAnswer[];
  },
  { rejectValue: string }
>(
  'assessment/submitAnswers',
  async ({ assessmentId, step, stepName, answers }, { rejectWithValue }) => {
    try {
      return await assessmentApi.submitAnswers(assessmentId, step, stepName, answers);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      const message = err.response?.data?.detail || 'Erro ao submeter respostas';
      return rejectWithValue(message);
    }
  }
);

export const fetchAssessmentResult = createAsyncThunk<
  AssessmentResult,
  string,
  { rejectValue: string }
>(
  'assessment/fetchResult',
  async (assessmentId, { rejectWithValue }) => {
    try {
      return await assessmentApi.getResult(assessmentId);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      const message = err.response?.data?.detail || 'Erro ao obter resultado';
      return rejectWithValue(message);
    }
  }
);

export const fetchAssessmentStatus = createAsyncThunk<
  AssessmentStatus,
  void,
  { rejectValue: string }
>(
  'assessment/fetchStatus',
  async (_, { rejectWithValue }) => {
    try {
      return await assessmentApi.getStatus();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      const message = err.response?.data?.detail || 'Erro ao obter status';
      return rejectWithValue(message);
    }
  }
);

export const cancelAssessment = createAsyncThunk<
  void,
  string,
  { rejectValue: string }
>(
  'assessment/cancel',
  async (assessmentId, { rejectWithValue }) => {
    try {
      await assessmentApi.cancel(assessmentId);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      const message = err.response?.data?.detail || 'Erro ao cancelar avaliação';
      return rejectWithValue(message);
    }
  }
);

// Slice
const assessmentSlice = createSlice({
  name: 'assessment',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearAssessment: (state) => {
      state.currentAssessment = null;
      state.assessmentResult = null;
      state.currentAnswers = [];
      state.error = null;
    },
    addAnswer: (state, action: PayloadAction<AssessmentAnswer>) => {
      state.currentAnswers.push(action.payload);
    },
    updateAnswer: (state, action: PayloadAction<{ index: number; answer: AssessmentAnswer }>) => {
      const { index, answer } = action.payload;
      if (index >= 0 && index < state.currentAnswers.length) {
        state.currentAnswers[index] = answer;
      }
    },
    setAnswers: (state, action: PayloadAction<AssessmentAnswer[]>) => {
      state.currentAnswers = action.payload;
    },
    clearAnswers: (state) => {
      state.currentAnswers = [];
    },
    updateCurrentStep: (state, action: PayloadAction<{
      step: number;
      stepName: string;
      content: AssessmentStart['content'];
    }>) => {
      if (state.currentAssessment) {
        state.currentAssessment.step = action.payload.step;
        state.currentAssessment.stepName = action.payload.stepName;
        state.currentAssessment.content = action.payload.content;
      }
    }
  },
  extraReducers: (builder) => {
    // Start Assessment
    builder
      .addCase(startAssessment.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(startAssessment.fulfilled, (state, action) => {
        state.loading = false;
        state.currentAssessment = action.payload;
        state.assessmentResult = null;
        state.currentAnswers = [];
      })
      .addCase(startAssessment.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });

    // Submit Answers
    builder
      .addCase(submitAssessmentAnswers.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(submitAssessmentAnswers.fulfilled, (state, action) => {
        state.loading = false;
        // Clear answers after successful submission
        state.currentAnswers = [];

        // Update assessment state based on response
        if (action.payload.isComplete) {
          // Assessment is complete, clear current assessment
          state.currentAssessment = null;
        } else if (state.currentAssessment && action.payload.nextContent) {
          // Move to next step
          state.currentAssessment.step = action.payload.nextStep || state.currentAssessment.step + 1;
          state.currentAssessment.stepName = action.payload.nextStepName || '';
          state.currentAssessment.content = action.payload.nextContent;
        }
      })
      .addCase(submitAssessmentAnswers.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });

    // Fetch Result
    builder
      .addCase(fetchAssessmentResult.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAssessmentResult.fulfilled, (state, action) => {
        state.loading = false;
        state.assessmentResult = action.payload;
      })
      .addCase(fetchAssessmentResult.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });

    // Fetch Status
    builder
      .addCase(fetchAssessmentStatus.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAssessmentStatus.fulfilled, (state, action) => {
        state.loading = false;
        state.assessmentStatus = action.payload;
      })
      .addCase(fetchAssessmentStatus.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });

    // Cancel Assessment
    builder
      .addCase(cancelAssessment.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(cancelAssessment.fulfilled, (state) => {
        state.loading = false;
        state.currentAssessment = null;
        state.currentAnswers = [];
      })
      .addCase(cancelAssessment.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });
  }
});

// Export actions
export const {
  clearError,
  clearAssessment,
  addAnswer,
  updateAnswer,
  setAnswers,
  clearAnswers,
  updateCurrentStep
} = assessmentSlice.actions;

// Export reducer
export default assessmentSlice.reducer;
