/**
 * App Component
 * Main application component with routing and Redux provider
 */
import { FC } from 'react';
import { Provider } from 'react-redux';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { store, useAppSelector } from './store';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Onboarding from './pages/Onboarding';
import Assessment from './pages/Assessment';

// Protected Route Component
interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, user } = useAppSelector((state) => state.auth);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Redirect to assessment if not completed
  if (user && !user.initialAssessmentCompleted) {
    return <Navigate to="/assessment" replace />;
  }

  return <>{children}</>;
};

// Auth Route Component (redirect if already authenticated)
interface AuthRouteProps {
  children: React.ReactNode;
}

const AuthRoute: FC<AuthRouteProps> = ({ children }) => {
  const { isAuthenticated, user } = useAppSelector((state) => state.auth);

  if (isAuthenticated) {
    // Redirect to assessment if not completed, otherwise to dashboard
    if (user && !user.initialAssessmentCompleted) {
      return <Navigate to="/assessment" replace />;
    }
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

// Main App with Routes
const AppRoutes: FC = () => {
  const { user } = useAppSelector((state) => state.auth);
  const userId = user?.id || 'guest';

  return (
    <Routes>
      {/* Auth Routes */}
      <Route
        path="/login"
        element={
          <AuthRoute>
            <Login />
          </AuthRoute>
        }
      />
      <Route
        path="/register"
        element={
          <AuthRoute>
            <Onboarding />
          </AuthRoute>
        }
      />

      {/* Assessment Route */}
      <Route path="/assessment" element={<Assessment />} />

      {/* Protected Routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Dashboard userId={userId} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard userId={userId} />
          </ProtectedRoute>
        }
      />

      {/* Pillar Routes */}
      <Route
        path="/vocabulary"
        element={
          <ProtectedRoute>
            <PlaceholderPage title="Vocabulário" description="Página de exercícios de vocabulário" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/grammar"
        element={
          <ProtectedRoute>
            <PlaceholderPage title="Gramática" description="Página de lições de gramática" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pronunciation"
        element={
          <ProtectedRoute>
            <PlaceholderPage title="Pronúncia" description="Página de exercícios de pronúncia" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/speaking"
        element={
          <ProtectedRoute>
            <PlaceholderPage title="Conversação" description="Página de prática de conversação" />
          </ProtectedRoute>
        }
      />

      {/* Redirect unknown routes to login (or dashboard if authenticated) */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
};

// Placeholder Page Component
interface PlaceholderPageProps {
  title: string;
  description: string;
}

const PlaceholderPage: FC<PlaceholderPageProps> = ({ title, description }) => {
  return (
    <div className="min-h-screen bg-base-200 flex items-center justify-center">
      <div className="card bg-base-100 shadow-xl">
        <div className="card-body text-center">
          <h2 className="card-title text-2xl justify-center">{title}</h2>
          <p className="text-base-content/70">{description}</p>
          <div className="card-actions justify-center mt-4">
            <a href="/dashboard" className="btn btn-primary">
              Voltar ao Dashboard
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

// Main App Component
const App: FC = () => {
  return (
    <Provider store={store}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </Provider>
  );
};

export default App;
