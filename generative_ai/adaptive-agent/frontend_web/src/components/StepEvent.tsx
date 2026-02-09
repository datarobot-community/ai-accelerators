import { Loader2, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ChatStepEvent as StepEventType } from '@/types/events';
import { useMemo } from 'react';

export function StepEvent({ id, name, createdAt, isRunning, threadId }: StepEventType) {
  const Icon = useMemo(() => {
    return isRunning ? Loader2 : CheckCircle2;
  }, [isRunning]);

  // Convert createdAt to Date if it's a string
  const date = typeof createdAt === 'string' ? new Date(createdAt) : createdAt;

  return (
    <div
      className={cn('flex gap-3 p-4 rounded-lg bg-card')}
      data-step-id={id}
      data-thread-id={threadId}
    >
      <div className="flex-shrink-0">
        <div
          className={cn(
            'w-8 h-8 rounded-full flex items-center justify-center',
            isRunning ? 'bg-blue-500/10 text-blue-500' : 'bg-green-500/10 text-green-500'
          )}
        >
          <Icon className={cn('w-4 h-4', isRunning && 'animate-spin')} />
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium">{name}</span>
          <span className="text-xs text-muted-foreground">{date.toLocaleTimeString()}</span>
        </div>
        <div className="text-xs text-muted-foreground">
          {isRunning ? 'In progress...' : 'Completed'}
        </div>
      </div>
    </div>
  );
}
