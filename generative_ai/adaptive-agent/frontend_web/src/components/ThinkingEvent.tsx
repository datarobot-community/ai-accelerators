import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export function ThinkingEvent() {
  return (
    <div className={cn('flex gap-3 p-4 rounded-lg bg-card')}>
      <div className="flex-shrink-0">
        <div
          className={cn(
            'w-8 h-8 rounded-full flex items-center justify-center',
            'bg-blue-500/10 text-blue-500'
          )}
        >
          <Loader2 className={cn('w-4 h-4 animate-spin')} />
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 h-full">
          <span
            className="text-sm font-medium flex items-center h-full"
            data-testid="thinking-loading"
          >
            Thinking
          </span>
        </div>
      </div>
    </div>
  );
}
