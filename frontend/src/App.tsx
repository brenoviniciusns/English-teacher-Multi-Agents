/**
 * App Component
 * Main application component with routing and Redux provider
 */
import { FC, useState } from 'react';
import { Provider } from 'react-redux';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { store } from './store';
import Dashboard from './pages/Dashboard';

// Temporary user ID for development - will be replaced with auth
const DEFAULT_USER_ID = 'dev-user-001';

const App: FC = () => {
  // In a real app, this would come from authentication
  const [userId] = useState(DEFAULT_USER_ID);

  return (
    <Provider store={store}>
      <BrowserRouter>
        <Routes>
          {/* Dashboard Route */}
          <Route path="/" element={<Dashboard userId={userId} />} />
          <Route path="/dashboard" element={<Dashboard userId={userId} />} />

          {/* Placeholder routes for other pages */}
          <Route
            path="/vocabulary"
            element={
              <PlaceholderPage title="Vocabulário" description="Página de exercícios de vocabulário" />
            }
          />
          <Route
            path="/grammar"
            element={
              <PlaceholderPage title="Gramática" description="Página de lições de gramática" />
            }
          />
          <Route
            path="/pronunciation"
            element={
              <PlaceholderPage title="Pronúncia" description="Página de exercícios de pronúncia" />
            }
          />
          <Route
            path="/speaking"
            element={
              <PlaceholderPage title="Conversação" description="Página de prática de conversação" />
            }
          />

          {/* Redirect unknown routes to dashboard */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </Provider>
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
            <a href="/" className="btn btn-primary">
              Voltar ao Dashboard
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;