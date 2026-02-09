import { MdCheckCircle } from 'react-icons/md';
import { AiOutlineLoading3Quarters } from 'react-icons/ai';

interface ProcessingStepProps {
  message: string;
  isActive?: boolean;
}

export function ProcessingStep({ message, isActive = false }: ProcessingStepProps) {
  return (
    <div className={`flex items-center gap-3 py-2 animate-fade-in ${isActive ? 'animate-pulse-glow' : ''}`}>
      {isActive ? (
        <AiOutlineLoading3Quarters className="w-4 h-4 text-primary animate-spin flex-shrink-0" />
      ) : (
        <MdCheckCircle className="w-4 h-4 text-green-600 flex-shrink-0" />
      )}
      <span className="text-sm text-gray-700">{message}</span>
    </div>
  );
}
