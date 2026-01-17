/**
 * Onboarding Page
 * User registration with profile setup
 */
import { FC, useState, FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  UserPlus,
  Mail,
  Lock,
  User,
  Eye,
  EyeOff,
  AlertCircle,
  Loader2,
  ChevronRight,
  ChevronLeft,
  Clock,
  Target,
  Check
} from 'lucide-react';
import { useAppDispatch, useAppSelector, registerUser, clearAuthError } from '../store';
import type { UserProfile } from '../types';

type Step = 'account' | 'profile' | 'goals';

const STUDY_TIME_OPTIONS = [
  { value: 'morning', label: 'Manhã' },
  { value: 'afternoon', label: 'Tarde' },
  { value: 'evening', label: 'Noite' },
  { value: 'flexible', label: 'Flexível' }
];

const DAILY_GOAL_OPTIONS = [
  { value: 15, label: '15 min/dia', description: 'Prática leve' },
  { value: 30, label: '30 min/dia', description: 'Recomendado' },
  { value: 45, label: '45 min/dia', description: 'Intensivo' },
  { value: 60, label: '60 min/dia', description: 'Dedicado' }
];

const LEARNING_GOALS = [
  { value: 'general', label: 'Inglês geral', description: 'Comunicação do dia-a-dia' },
  { value: 'data_engineering', label: 'Engenharia de Dados', description: 'Vocabulário técnico de dados' },
  { value: 'ai', label: 'Inteligência Artificial', description: 'Vocabulário de IA/ML' },
  { value: 'business', label: 'Negócios', description: 'Inglês corporativo' },
  { value: 'conversation', label: 'Conversação', description: 'Fluência na fala' }
];

export const Onboarding: FC = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { loading, error } = useAppSelector((state) => state.auth);

  // Current step
  const [step, setStep] = useState<Step>('account');

  // Account data
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Profile data
  const [preferredStudyTime, setPreferredStudyTime] = useState('evening');
  const [dailyGoalMinutes, setDailyGoalMinutes] = useState(30);
  const [learningGoals, setLearningGoals] = useState<string[]>(['general']);

  // Validation
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleGoalToggle = (goal: string) => {
    setLearningGoals((prev) => {
      if (prev.includes(goal)) {
        return prev.filter((g) => g !== goal);
      }
      return [...prev, goal];
    });
  };

  const validateStep = (): boolean => {
    setValidationError(null);

    if (step === 'account') {
      if (!name || name.length < 2) {
        setValidationError('Nome deve ter pelo menos 2 caracteres');
        return false;
      }
      if (!email) {
        setValidationError('Email é obrigatório');
        return false;
      }
      if (password.length < 8) {
        setValidationError('Senha deve ter pelo menos 8 caracteres');
        return false;
      }
      if (password !== confirmPassword) {
        setValidationError('Senhas não conferem');
        return false;
      }
    }

    if (step === 'goals' && learningGoals.length === 0) {
      setValidationError('Selecione pelo menos um objetivo');
      return false;
    }

    return true;
  };

  const handleNextStep = () => {
    if (!validateStep()) return;

    if (step === 'account') setStep('profile');
    else if (step === 'profile') setStep('goals');
  };

  const handlePrevStep = () => {
    if (step === 'profile') setStep('account');
    else if (step === 'goals') setStep('profile');
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validateStep()) return;

    const profile: Partial<UserProfile> = {
      learningGoals,
      nativeLanguage: 'pt-BR',
      preferredStudyTime,
      dailyGoalMinutes,
      notificationsEnabled: true,
      voicePreference: 'american_female'
    };

    const result = await dispatch(
      registerUser({
        name,
        email,
        password,
        profile
      })
    );

    if (registerUser.fulfilled.match(result)) {
      // Navigate to initial assessment
      navigate('/assessment');
    }
  };

  const handleClearError = () => {
    dispatch(clearAuthError());
    setValidationError(null);
  };

  const currentError = error || validationError;

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/20 via-base-200 to-secondary/20 flex items-center justify-center p-4">
      <div className="card bg-base-100 shadow-xl w-full max-w-lg">
        <div className="card-body">
          {/* Header */}
          <div className="text-center mb-6">
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
                <UserPlus className="w-8 h-8 text-primary" />
              </div>
            </div>
            <h1 className="text-2xl font-bold">Crie sua conta</h1>
            <p className="text-base-content/60 mt-1">
              {step === 'account' && 'Informe seus dados de acesso'}
              {step === 'profile' && 'Configure sua rotina de estudos'}
              {step === 'goals' && 'Defina seus objetivos de aprendizado'}
            </p>
          </div>

          {/* Step Indicator */}
          <ul className="steps steps-horizontal w-full mb-6">
            <li className={`step ${step === 'account' || step === 'profile' || step === 'goals' ? 'step-primary' : ''}`}>
              Conta
            </li>
            <li className={`step ${step === 'profile' || step === 'goals' ? 'step-primary' : ''}`}>
              Perfil
            </li>
            <li className={`step ${step === 'goals' ? 'step-primary' : ''}`}>
              Objetivos
            </li>
          </ul>

          {/* Error Alert */}
          {currentError && (
            <div className="alert alert-error mb-4">
              <AlertCircle className="w-5 h-5" />
              <span>{currentError}</span>
              <button className="btn btn-ghost btn-sm" onClick={handleClearError}>
                Fechar
              </button>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Step 1: Account */}
            {step === 'account' && (
              <>
                <div className="form-control">
                  <label className="label">
                    <span className="label-text">Nome</span>
                  </label>
                  <label className="input input-bordered flex items-center gap-2">
                    <User className="w-4 h-4 opacity-70" />
                    <input
                      type="text"
                      placeholder="Seu nome"
                      className="grow"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      minLength={2}
                    />
                  </label>
                </div>

                <div className="form-control">
                  <label className="label">
                    <span className="label-text">Email</span>
                  </label>
                  <label className="input input-bordered flex items-center gap-2">
                    <Mail className="w-4 h-4 opacity-70" />
                    <input
                      type="email"
                      placeholder="seu@email.com"
                      className="grow"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </label>
                </div>

                <div className="form-control">
                  <label className="label">
                    <span className="label-text">Senha</span>
                  </label>
                  <label className="input input-bordered flex items-center gap-2">
                    <Lock className="w-4 h-4 opacity-70" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Mínimo 8 caracteres"
                      className="grow"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={8}
                    />
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm btn-circle"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </label>
                </div>

                <div className="form-control">
                  <label className="label">
                    <span className="label-text">Confirmar Senha</span>
                  </label>
                  <label className="input input-bordered flex items-center gap-2">
                    <Lock className="w-4 h-4 opacity-70" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Repita a senha"
                      className="grow"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                    />
                  </label>
                </div>
              </>
            )}

            {/* Step 2: Profile */}
            {step === 'profile' && (
              <>
                <div className="form-control">
                  <label className="label">
                    <span className="label-text flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      Melhor horário para estudar
                    </span>
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {STUDY_TIME_OPTIONS.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        className={`btn ${preferredStudyTime === option.value ? 'btn-primary' : 'btn-outline'}`}
                        onClick={() => setPreferredStudyTime(option.value)}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="form-control">
                  <label className="label">
                    <span className="label-text flex items-center gap-2">
                      <Target className="w-4 h-4" />
                      Meta diária de estudo
                    </span>
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {DAILY_GOAL_OPTIONS.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        className={`btn flex-col h-auto py-3 ${dailyGoalMinutes === option.value ? 'btn-primary' : 'btn-outline'}`}
                        onClick={() => setDailyGoalMinutes(option.value)}
                      >
                        <span className="font-bold">{option.label}</span>
                        <span className="text-xs opacity-70">{option.description}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* Step 3: Goals */}
            {step === 'goals' && (
              <div className="form-control">
                <label className="label">
                  <span className="label-text">Quais são seus objetivos?</span>
                  <span className="label-text-alt">Selecione um ou mais</span>
                </label>
                <div className="space-y-2">
                  {LEARNING_GOALS.map((goal) => (
                    <button
                      key={goal.value}
                      type="button"
                      className={`w-full flex items-center justify-between p-3 rounded-lg border-2 transition-colors ${
                        learningGoals.includes(goal.value)
                          ? 'border-primary bg-primary/10'
                          : 'border-base-300 hover:border-primary/50'
                      }`}
                      onClick={() => handleGoalToggle(goal.value)}
                    >
                      <div className="text-left">
                        <div className="font-medium">{goal.label}</div>
                        <div className="text-sm opacity-60">{goal.description}</div>
                      </div>
                      {learningGoals.includes(goal.value) && (
                        <Check className="w-5 h-5 text-primary" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Navigation Buttons */}
            <div className="flex gap-2 pt-4">
              {step !== 'account' && (
                <button type="button" className="btn btn-outline flex-1" onClick={handlePrevStep}>
                  <ChevronLeft className="w-4 h-4" />
                  Voltar
                </button>
              )}

              {step !== 'goals' ? (
                <button type="button" className="btn btn-primary flex-1" onClick={handleNextStep}>
                  Próximo
                  <ChevronRight className="w-4 h-4" />
                </button>
              ) : (
                <button type="submit" className="btn btn-primary flex-1" disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Criando conta...
                    </>
                  ) : (
                    <>
                      Criar conta
                      <ChevronRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              )}
            </div>
          </form>

          {/* Divider */}
          <div className="divider text-xs text-base-content/50">ou</div>

          {/* Login Link */}
          <div className="text-center">
            <p className="text-base-content/60">
              Já tem uma conta?{' '}
              <Link to="/login" className="link link-primary font-medium">
                Fazer login
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Onboarding;
