/**
 * Assessment Page
 * Page wrapper for the initial assessment flow
 */
import { FC, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppSelector } from '../store';
import { InitialAssessment } from '../components/assessment';

export const Assessment: FC = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAppSelector((state) => state.auth);

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  // Redirect if assessment already completed
  useEffect(() => {
    if (user?.initialAssessmentCompleted) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  const handleComplete = () => {
    navigate('/dashboard');
  };

  if (!isAuthenticated || user?.initialAssessmentCompleted) {
    return null;
  }

  return <InitialAssessment onComplete={handleComplete} />;
};

export default Assessment;
