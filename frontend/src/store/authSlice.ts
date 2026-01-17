/**
 * Auth Redux Slice
 * Manages authentication state: user, token, and authentication status
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { authApi } from '../services/api';
import type {
  AuthState,
  User,
  UserRegistration,
  UserLogin,
  AuthToken,
  UserProfile
} from '../types';

// Helper to load initial state from localStorage
const loadInitialState = (): AuthState => {
  const token = localStorage.getItem('auth_token');
  const userStr = localStorage.getItem('user');
  let user: User | null = null;

  if (userStr) {
    try {
      user = JSON.parse(userStr);
    } catch {
      localStorage.removeItem('user');
    }
  }

  return {
    user,
    token,
    isAuthenticated: !!token && !!user,
    loading: false,
    error: null
  };
};

// Initial state
const initialState: AuthState = loadInitialState();

// Async thunks
export const registerUser = createAsyncThunk<
  AuthToken,
  UserRegistration,
  { rejectValue: string }
>(
  'auth/register',
  async (data, { rejectWithValue }) => {
    try {
      const result = await authApi.register(data);
      // Store token and user in localStorage
      localStorage.setItem('auth_token', result.accessToken);
      localStorage.setItem('user', JSON.stringify(result.user));
      return result;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      const message = err.response?.data?.detail || 'Erro ao registrar usuário';
      return rejectWithValue(message);
    }
  }
);

export const loginUser = createAsyncThunk<
  AuthToken,
  UserLogin,
  { rejectValue: string }
>(
  'auth/login',
  async (credentials, { rejectWithValue }) => {
    try {
      const result = await authApi.login(credentials);
      // Store token and user in localStorage
      localStorage.setItem('auth_token', result.accessToken);
      localStorage.setItem('user', JSON.stringify(result.user));
      return result;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      const message = err.response?.data?.detail || 'Email ou senha incorretos';
      return rejectWithValue(message);
    }
  }
);

export const fetchCurrentUser = createAsyncThunk<
  User,
  void,
  { rejectValue: string }
>(
  'auth/fetchCurrentUser',
  async (_, { rejectWithValue }) => {
    try {
      const user = await authApi.getCurrentUser();
      // Update user in localStorage
      localStorage.setItem('user', JSON.stringify(user));
      return user;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      const message = err.response?.data?.detail || 'Erro ao carregar usuário';
      return rejectWithValue(message);
    }
  }
);

export const updateUserProfile = createAsyncThunk<
  User,
  Partial<UserProfile>,
  { rejectValue: string }
>(
  'auth/updateProfile',
  async (profile, { rejectWithValue }) => {
    try {
      const user = await authApi.updateProfile(profile);
      // Update user in localStorage
      localStorage.setItem('user', JSON.stringify(user));
      return user;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      const message = err.response?.data?.detail || 'Erro ao atualizar perfil';
      return rejectWithValue(message);
    }
  }
);

// Slice
const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    logout: (state) => {
      authApi.logout();
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      state.error = null;
    },
    setUser: (state, action: PayloadAction<User>) => {
      state.user = action.payload;
      localStorage.setItem('user', JSON.stringify(action.payload));
    },
    updateUserScores: (state, action: PayloadAction<{
      vocabularyScore?: number;
      grammarScore?: number;
      pronunciationScore?: number;
      speakingScore?: number;
    }>) => {
      if (state.user) {
        state.user = { ...state.user, ...action.payload };
        localStorage.setItem('user', JSON.stringify(state.user));
      }
    },
    setAssessmentCompleted: (state, action: PayloadAction<boolean>) => {
      if (state.user) {
        state.user.initialAssessmentCompleted = action.payload;
        localStorage.setItem('user', JSON.stringify(state.user));
      }
    },
    setUserLevel: (state, action: PayloadAction<'beginner' | 'intermediate'>) => {
      if (state.user) {
        state.user.currentLevel = action.payload;
        localStorage.setItem('user', JSON.stringify(state.user));
      }
    }
  },
  extraReducers: (builder) => {
    // Register
    builder
      .addCase(registerUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(registerUser.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload.user;
        state.token = action.payload.accessToken;
        state.isAuthenticated = true;
      })
      .addCase(registerUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });

    // Login
    builder
      .addCase(loginUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload.user;
        state.token = action.payload.accessToken;
        state.isAuthenticated = true;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });

    // Fetch Current User
    builder
      .addCase(fetchCurrentUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCurrentUser.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload;
      })
      .addCase(fetchCurrentUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
        // If fetching user fails, clear auth state
        state.user = null;
        state.token = null;
        state.isAuthenticated = false;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
      });

    // Update Profile
    builder
      .addCase(updateUserProfile.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateUserProfile.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload;
      })
      .addCase(updateUserProfile.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Erro desconhecido';
      });
  }
});

// Export actions
export const {
  clearError,
  logout,
  setUser,
  updateUserScores,
  setAssessmentCompleted,
  setUserLevel
} = authSlice.actions;

// Export reducer
export default authSlice.reducer;
