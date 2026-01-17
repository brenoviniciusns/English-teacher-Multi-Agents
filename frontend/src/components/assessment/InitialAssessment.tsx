/**
 * InitialAssessment Component
 * Handles the 4-step initial assessment flow
 */
import { FC, useState, useEffect } from 'react';
import {
  BookOpen,
  FileText,
  Mic,
  MessageSquare,
  ChevronRight,
  Loader2,
  Check,
  AlertCircle,
  Volume2
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../store';
import {
  startAssessment,
  submitAssessmentAnswers,
  fetchAssessmentResult,
  setAnswers,
  clearError as clearAssessmentError
} from '../../store/assessmentSlice';
import { setAssessmentCompleted, setUserLevel } from '../../store/authSlice';
import type { AssessmentAnswer, VocabularyAssessmentItem, GrammarAssessmentItem } from '../../types';

interface InitialAssessmentProps {
  onComplete: () => void;
}

const STEP_ICONS = {
  vocabulary: BookOpen,
  grammar: FileText,
  pronunciation: Mic,
  speaking: MessageSquare
};

const STEP_LABELS = {
  vocabulary: 'Vocabulário',
  grammar: 'Gramática',
  pronunciation: 'Pronúncia',
  speaking: 'Conversação'
};

export const InitialAssessment: FC<InitialAssessmentProps> = ({ onComplete }) => {
  const dispatch = useAppDispatch();
  const { currentAssessment, assessmentResult, loading, error } = useAppSelector(
    (state) => state.assessment
  );

  const [localAnswers, setLocalAnswers] = useState<Record<number, string>>({});
  const [showResult, setShowResult] = useState(false);

  // Start assessment on mount
  useEffect(() => {
    dispatch(startAssessment('initial'));
  }, [dispatch]);

  // Initialize local answers when step changes
  useEffect(() => {
    if (currentAssessment?.content?.items) {
      setLocalAnswers({});
    }
  }, [currentAssessment?.step]);

  // Show result when assessment is complete
  useEffect(() => {
    if (assessmentResult) {
      setShowResult(true);
      // Update user state
      dispatch(setAssessmentCompleted(true));
      dispatch(setUserLevel(assessmentResult.determinedLevel));
    }
  }, [assessmentResult, dispatch]);

  const handleAnswerChange = (index: number, answer: string) => {
    setLocalAnswers((prev) => ({ ...prev, [index]: answer }));
  };

  const handleSubmitStep = async () => {
    if (!currentAssessment) return;

    // Convert local answers to assessment answers
    const items = currentAssessment.content.items || currentAssessment.content.prompts || [];
    const answers: AssessmentAnswer[] = items.map((item, index) => ({
      id: typeof item === 'object' && 'id' in item ? item.id : `item_${index}`,
      answer: localAnswers[index] || '',
      correct: false // Backend will evaluate
    }));

    dispatch(setAnswers(answers));

    const result = await dispatch(
      submitAssessmentAnswers({
        assessmentId: currentAssessment.assessmentId,
        step: currentAssessment.step,
        stepName: currentAssessment.stepName,
        answers
      })
    );

    if (submitAssessmentAnswers.fulfilled.match(result)) {
      if (result.payload.isComplete) {
        // Fetch final result
        await dispatch(fetchAssessmentResult(currentAssessment.assessmentId));
      }
    }
  };

  const handleClearError = () => {
    dispatch(clearAssessmentError());
  };

  const handleFinish = () => {
    onComplete();
  };

  const canSubmit = () => {
    if (!currentAssessment?.content?.items && !currentAssessment?.content?.prompts) return false;
    const answeredCount = Object.values(localAnswers).filter((a) => a.trim() !== '').length;
    return answeredCount > 0;
  };

  // Loading state
  if (loading && !currentAssessment && !assessmentResult) {
    return (
      <div className="min-h-screen bg-base-200 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-lg">Preparando avaliação...</p>
        </div>
      </div>
    );
  }

  // Result view
  if (showResult && assessmentResult) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary/20 via-base-200 to-secondary/20 flex items-center justify-center p-4">
        <div className="card bg-base-100 shadow-xl w-full max-w-2xl">
          <div className="card-body">
            {/* Header */}
            <div className="text-center mb-6">
              <div className="flex justify-center mb-4">
                <div className="w-20 h-20 bg-success/20 rounded-full flex items-center justify-center">
                  <Check className="w-10 h-10 text-success" />
                </div>
              </div>
              <h1 className="text-2xl font-bold">Avaliação Concluída!</h1>
              <p className="text-base-content/60 mt-1">{assessmentResult.message}</p>
            </div>

            {/* Level Badge */}
            <div className="flex justify-center mb-6">
              <div className={`badge badge-lg ${assessmentResult.determinedLevel === 'intermediate' ? 'badge-secondary' : 'badge-primary'} gap-2 p-4`}>
                <span className="text-lg font-bold capitalize">{assessmentResult.determinedLevel}</span>
              </div>
            </div>

            {/* Scores */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {Object.entries(assessmentResult.scores).map(([pillar, score]) => (
                <div key={pillar} className="stat bg-base-200 rounded-lg p-4">
                  <div className="stat-title text-xs capitalize">{pillar}</div>
                  <div className="stat-value text-2xl">{Math.round(score)}%</div>
                </div>
              ))}
            </div>

            {/* Overall Score */}
            <div className="text-center mb-6">
              <p className="text-sm text-base-content/60">Pontuação Geral</p>
              <p className="text-4xl font-bold text-primary">{Math.round(assessmentResult.overallScore)}%</p>
            </div>

            {/* Recommendations */}
            {assessmentResult.recommendations.length > 0 && (
              <div className="mb-6">
                <h3 className="font-semibold mb-2">Recomendações:</h3>
                <ul className="list-disc list-inside space-y-1 text-sm text-base-content/80">
                  {assessmentResult.recommendations.map((rec, idx) => (
                    <li key={idx}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Continue Button */}
            <button className="btn btn-primary btn-lg w-full" onClick={handleFinish}>
              Começar a Aprender
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Assessment not started
  if (!currentAssessment) {
    return (
      <div className="min-h-screen bg-base-200 flex items-center justify-center">
        <div className="text-center">
          {error ? (
            <div className="alert alert-error max-w-md">
              <AlertCircle className="w-5 h-5" />
              <span>{error}</span>
              <button className="btn btn-ghost btn-sm" onClick={handleClearError}>
                Tentar novamente
              </button>
            </div>
          ) : (
            <>
              <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
              <p className="text-lg">Carregando...</p>
            </>
          )}
        </div>
      </div>
    );
  }

  const StepIcon = STEP_ICONS[currentAssessment.stepName as keyof typeof STEP_ICONS] || BookOpen;
  const stepLabel = STEP_LABELS[currentAssessment.stepName as keyof typeof STEP_LABELS] || 'Avaliação';

  return (
    <div className="min-h-screen bg-base-200 py-8 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold mb-2">Avaliação Inicial</h1>
          <p className="text-base-content/60">
            Vamos avaliar seu nível para criar um plano personalizado
          </p>
        </div>

        {/* Progress */}
        <div className="mb-8">
          <ul className="steps steps-horizontal w-full">
            {['vocabulary', 'grammar', 'pronunciation', 'speaking'].map((stepName, idx) => {
              const Icon = STEP_ICONS[stepName as keyof typeof STEP_ICONS];
              const isActive = currentAssessment.step === idx + 1;
              const isCompleted = currentAssessment.step > idx + 1;
              return (
                <li
                  key={stepName}
                  className={`step ${isCompleted || isActive ? 'step-primary' : ''}`}
                >
                  <span className="flex items-center gap-1">
                    <Icon className="w-4 h-4" />
                    <span className="hidden sm:inline">
                      {STEP_LABELS[stepName as keyof typeof STEP_LABELS]}
                    </span>
                  </span>
                </li>
              );
            })}
          </ul>
        </div>

        {/* Error */}
        {error && (
          <div className="alert alert-error mb-6">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
            <button className="btn btn-ghost btn-sm" onClick={handleClearError}>
              Fechar
            </button>
          </div>
        )}

        {/* Assessment Card */}
        <div className="card bg-base-100 shadow-xl">
          <div className="card-body">
            {/* Step Header */}
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
                <StepIcon className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h2 className="text-xl font-semibold">{stepLabel}</h2>
                <p className="text-sm text-base-content/60">
                  Passo {currentAssessment.step} de {currentAssessment.totalSteps}
                </p>
              </div>
            </div>

            {/* Instructions */}
            <div className="alert alert-info mb-6">
              <AlertCircle className="w-5 h-5" />
              <span>{currentAssessment.content.instructions}</span>
            </div>

            {/* Content */}
            <div className="space-y-4">
              {/* Vocabulary Items */}
              {currentAssessment.stepName === 'vocabulary' &&
                currentAssessment.content.items?.map((item, idx) => {
                  const vocabItem = item as VocabularyAssessmentItem;
                  return (
                    <div key={idx} className="form-control">
                      <label className="label">
                        <span className="label-text font-medium">
                          {idx + 1}. <span className="text-primary">{vocabItem.word}</span>
                        </span>
                        <span className="label-text-alt badge badge-ghost">
                          Dificuldade: {vocabItem.difficulty}
                        </span>
                      </label>
                      <input
                        type="text"
                        placeholder="Digite a tradução em português"
                        className="input input-bordered"
                        value={localAnswers[idx] || ''}
                        onChange={(e) => handleAnswerChange(idx, e.target.value)}
                      />
                    </div>
                  );
                })}

              {/* Grammar Items */}
              {currentAssessment.stepName === 'grammar' &&
                currentAssessment.content.items?.map((item, idx) => {
                  const grammarItem = item as GrammarAssessmentItem;
                  return (
                    <div key={idx} className="card bg-base-200 p-4">
                      <div className="mb-2">
                        <span className="font-semibold">{idx + 1}. {grammarItem.rule}</span>
                      </div>
                      <div className="text-sm text-base-content/70 mb-2">
                        Exemplo: <span className="italic">{grammarItem.example}</span>
                      </div>
                      <div className="mb-3">
                        <span className="text-primary">{grammarItem.question}</span>
                      </div>
                      <input
                        type="text"
                        placeholder="Sua resposta"
                        className="input input-bordered w-full"
                        value={localAnswers[idx] || ''}
                        onChange={(e) => handleAnswerChange(idx, e.target.value)}
                      />
                    </div>
                  );
                })}

              {/* Pronunciation Items */}
              {currentAssessment.stepName === 'pronunciation' &&
                currentAssessment.content.items?.map((item, idx) => {
                  const pronunItem = item as { id: string; phoneme: string; words: string[]; difficulty: string };
                  return (
                    <div key={idx} className="card bg-base-200 p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-lg">{pronunItem.phoneme}</span>
                        <span className="badge badge-outline">{pronunItem.difficulty}</span>
                      </div>
                      <div className="flex flex-wrap gap-2 mb-3">
                        {pronunItem.words.map((word, wIdx) => (
                          <button
                            key={wIdx}
                            className="btn btn-sm btn-ghost gap-1"
                            onClick={() => {
                              // In a real app, play TTS here
                              console.log('Play TTS for:', word);
                            }}
                          >
                            <Volume2 className="w-4 h-4" />
                            {word}
                          </button>
                        ))}
                      </div>
                      <div className="form-control">
                        <label className="label cursor-pointer justify-start gap-2">
                          <input
                            type="checkbox"
                            className="checkbox checkbox-primary"
                            checked={localAnswers[idx] === 'practiced'}
                            onChange={(e) => handleAnswerChange(idx, e.target.checked ? 'practiced' : '')}
                          />
                          <span className="label-text">Pratiquei este som</span>
                        </label>
                      </div>
                    </div>
                  );
                })}

              {/* Speaking Prompts */}
              {currentAssessment.stepName === 'speaking' &&
                currentAssessment.content.prompts?.map((prompt, idx) => (
                  <div key={idx} className="card bg-base-200 p-4">
                    <div className="mb-3">
                      <span className="font-semibold">{idx + 1}. {prompt}</span>
                    </div>
                    <textarea
                      placeholder="Escreva sua resposta em inglês..."
                      className="textarea textarea-bordered w-full"
                      rows={3}
                      value={localAnswers[idx] || ''}
                      onChange={(e) => handleAnswerChange(idx, e.target.value)}
                    />
                  </div>
                ))}
            </div>

            {/* Submit Button */}
            <div className="mt-6">
              <button
                className="btn btn-primary w-full"
                onClick={handleSubmitStep}
                disabled={loading || !canSubmit()}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Processando...
                  </>
                ) : currentAssessment.step === currentAssessment.totalSteps ? (
                  <>
                    Finalizar Avaliação
                    <Check className="w-4 h-4" />
                  </>
                ) : (
                  <>
                    Próximo Passo
                    <ChevronRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InitialAssessment;
