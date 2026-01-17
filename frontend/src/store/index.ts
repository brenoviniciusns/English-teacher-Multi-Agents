/**
 * Redux Store Configuration
 * Main store setup combining all slices
 */
import { configureStore } from '@reduxjs/toolkit';
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';

import progressReducer from './progressSlice';
import scheduleReducer from './scheduleSlice';

// Create the store
export const store = configureStore({
  reducer: {
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
  devTools: process.env.NODE_ENV !== 'production'
});

// Infer types from the store
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Typed hooks for use throughout the app
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

// Export all actions from slices
export * from './progressSlice';
export * from './scheduleSlice';

export default store;