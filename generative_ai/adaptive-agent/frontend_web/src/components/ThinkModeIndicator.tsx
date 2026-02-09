import { Brain, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ThinkModeIndicatorProps {
  active: boolean;
  className?: string;
}

export function ThinkModeIndicator({ active, className }: ThinkModeIndicatorProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-300',
        active
          ? 'bg-purple-100 text-purple-700 border border-purple-300'
          : 'bg-gray-100 text-gray-600 border border-gray-200',
        className
      )}
    >
      {active ? (
        <>
          <Brain className="w-4 h-4 animate-pulse" />
          <span>Deep Thinking: ON</span>
        </>
      ) : (
        <>
          <Zap className="w-4 h-4" />
          <span>Fast Mode: ON</span>
        </>
      )}
    </div>
  );
}

export interface ThinkModeToggleEventProps {
  previousMode: boolean;
  newMode: boolean;
  reason?: string;
}

export function ThinkModeToggleEvent({ previousMode, newMode, reason }: ThinkModeToggleEventProps) {
  const modeChanged = previousMode !== newMode;
  
  if (!modeChanged) return null;
  
  return (
    <div className="flex items-center justify-center my-2">
      <div className="inline-flex items-center gap-2 px-4 py-2 bg-amber-50 border border-amber-200 rounded-lg text-sm">
        <span className="text-amber-600">
          {newMode ? (
            <>
              <Brain className="w-4 h-4 inline mr-1" />
              Switching to Deep Thinking mode
            </>
          ) : (
            <>
              <Zap className="w-4 h-4 inline mr-1" />
              Switching to Fast mode
            </>
          )}
        </span>
        {reason && (
          <span className="text-amber-500 text-xs">({reason})</span>
        )}
      </div>
    </div>
  );
}
