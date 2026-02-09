import { ProcessingStep } from './ProcessingStep';
import { type ProcessingStep as ProcessingStepType } from '../../types/compliance';

interface ProcessingViewProps {
  steps: ProcessingStepType[];
}

export function ProcessingView({ steps }: ProcessingViewProps) {
  // Determine if a step should be active
  const isStepActive = (step: ProcessingStepType, index: number) => {
    // For regulation steps: active if not complete
    if (step.regulationIndex !== undefined) {
      return !step.isComplete;
    }
    // For non-regulation steps: active if it's the last step
    // (and there are no incomplete regulation steps after it)
    if (index === steps.length - 1) {
      return true;
    }
    // Check if there are any incomplete regulation steps after this non-regulation step
    const hasIncompleteRegulationStepsAfter = steps
      .slice(index + 1)
      .some(s => s.regulationIndex !== undefined && !s.isComplete);
    // If there are incomplete regulation steps after, this non-regulation step is done
    return !hasIncompleteRegulationStepsAfter;
  };

  return (
    <div className="flex flex-col items-center justify-center flex-1 px-8 py-8 -mt-16">
      <h1 className="text-3xl font-extrabold text-gray-900 mb-6">Generating compliance report...</h1>
      <div className="flex flex-col gap-1 max-h-96 overflow-y-auto w-full max-w-2xl pr-2">
        {steps.map((step, index) => (
          <ProcessingStep
            key={step.id}
            message={step.message}
            isActive={isStepActive(step, index)}
          />
        ))}
      </div>
    </div>
  );
}
