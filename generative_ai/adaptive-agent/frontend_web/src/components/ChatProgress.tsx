import { useEffect, useRef } from 'react';
import { CheckCircle2, Loader2, Circle, XCircle, X } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { ProgressState } from '@/types/progress';

const removeAfter = 2000;

export function ChatProgress({
  progress,
  deleteProgress,
}: {
  progress: ProgressState;
  deleteProgress: (progressId: string) => void;
}) {
  const progressTimeoutsRef = useRef<Record<string, any>>({});
  useEffect(() => {
    Object.entries(progress).forEach(([id, p]) => {
      const allDone = p.every(({ done }) => !!done);
      if (allDone && !progressTimeoutsRef.current[id]) {
        progressTimeoutsRef.current[id] = setTimeout(() => {
          console.debug('Remove progress data', id);
          deleteProgress(id);
        }, removeAfter);
      }
    });
  }, [progress]);

  const handleClose = (id: string) => {
    deleteProgress(id);
    // Clear timeout if exists
    if (progressTimeoutsRef.current[id]) {
      clearTimeout(progressTimeoutsRef.current[id]);
      delete progressTimeoutsRef.current[id];
    }
  };

  if (Object.keys(progress).length === 0) {
    return null;
  }

  return (
    <div className="space-y-3 mb-4">
      {Object.entries(progress).map(([id, p]) => {
        const allDone = p.every(({ done }) => !!done);
        const hasError = p.some(({ error }) => !!error);
        const completedCount = p.filter(({ done }) => !!done).length;
        const errorCount = p.filter(({ error }) => !!error).length;
        const totalCount = p.length;

        return (
          <Card
            key={id}
            className={cn(
              'transition-all duration-300 py-0',
              allDone && !hasError && 'opacity-80 border-green-500/30',
              hasError && 'opacity-80 border-red-500/30'
            )}
          >
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  {hasError ? (
                    <XCircle className="h-4 w-4 text-red-500" />
                  ) : allDone ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  ) : (
                    <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                  )}
                  <span className="text-sm font-medium">
                    {hasError ? 'Failed' : allDone ? 'Completed' : 'Processing'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge
                    variant={hasError ? 'destructive' : allDone ? 'secondary' : 'default'}
                    className="text-xs"
                  >
                    {hasError
                      ? `${errorCount} error${errorCount > 1 ? 's' : ''}`
                      : `${completedCount}/${totalCount}`}
                  </Badge>
                  {hasError && (
                    <button
                      onClick={() => handleClose(id)}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                      aria-label="Close"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                {p.map(step => (
                  <div key={step.name}>
                    <div
                      className={cn(
                        'flex items-center gap-2 text-sm transition-all duration-200',
                        step.done ? 'text-muted-foreground' : 'text-foreground',
                        step.error && 'text-red-500'
                      )}
                    >
                      {step.error ? (
                        <XCircle className="h-3.5 w-3.5 text-red-500 flex-shrink-0" />
                      ) : step.done ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-green-500 flex-shrink-0" />
                      ) : (
                        <Circle className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                      )}
                      <span className={cn(step.done && !step.error && 'line-through')}>
                        {step.name}
                      </span>
                    </div>
                    {step.error && (
                      <div className="ml-5.5 mt-1 text-xs text-red-500/80">{step.error}</div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
