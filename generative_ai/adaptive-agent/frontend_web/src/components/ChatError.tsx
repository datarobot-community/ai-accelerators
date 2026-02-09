import { AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ChatErrorEvent } from '@/types/events';

export function ChatError({ error, createdAt }: ChatErrorEvent) {
  // Convert createdAt to Date if it's a string
  const date = typeof createdAt === 'string' ? new Date(createdAt) : createdAt;

  return (
    <div
      className={cn('flex gap-3 p-4 rounded-lg', 'bg-destructive/10 border border-destructive/20')}
    >
      <div className="flex-shrink-0">
        <div
          className={cn(
            'w-8 h-8 rounded-full flex items-center justify-center',
            'bg-destructive/20 text-destructive-background'
          )}
        >
          <AlertCircle className="w-4 h-4" />
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-destructive">Error</span>
          <span className="text-xs text-muted-foreground">{date.toLocaleTimeString()}</span>
        </div>
        <div className="text-sm whitespace-pre-wrap break-words text-destructive">{error}</div>
      </div>
    </div>
  );
}
