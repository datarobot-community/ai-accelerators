import { useState, useEffect } from 'react';
import { Brain, Zap, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface AdaptiveState {
  thinkMode: boolean;
  currentModel: string;
  turnCount: number;
  lastReflection?: {
    needsThinking: boolean;
    reason: string;
    confidence: number;
  } | null;
}

interface AdaptiveIndicatorProps {
  className?: string;
}

export function AdaptiveIndicator({ className }: AdaptiveIndicatorProps) {
  const [state, setState] = useState<AdaptiveState>({
    thinkMode: false,
    currentModel: 'gpt-4o-mini',
    turnCount: 0,
    lastReflection: null,
  });
  const [isExpanded, setIsExpanded] = useState(false);

  // Poll for adaptive state (in production, use WebSocket or SSE)
  useEffect(() => {
    const fetchState = async () => {
      try {
        const res = await fetch('/api/v1/adaptive-state');
        if (res.ok) {
          const data = await res.json();
          setState(data);
        }
      } catch {
        // Endpoint may not exist yet - use default state
      }
    };
    
    // Fetch immediately on mount
    fetchState();
    
    const interval = setInterval(fetchState, 2000);
    return () => clearInterval(interval);
  }, []);
  
  // Reset backend state on component mount (new conversation started)
  useEffect(() => {
    // Reset to defaults when indicator mounts (usually when new chat starts)
    fetch('/api/v1/adaptive-state', {
      method: 'DELETE',
    }).catch(() => {});
  }, []); // Only on mount

  const modelName = state.currentModel.includes('gpt-4o-mini') ? 'GPT-4o-mini' : 
                    state.currentModel.includes('gpt-4o') ? 'GPT-4o' : 
                    state.currentModel.split('/').pop() || 'Unknown';

  return (
    <div className={cn('adaptive-indicator relative', className)}>
      {/* Main indicator badge */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-300 border',
          state.thinkMode
            ? 'bg-purple-500/20 text-purple-300 border-purple-500/50 hover:bg-purple-500/30'
            : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50 hover:bg-emerald-500/30'
        )}
      >
        {state.thinkMode ? (
          <>
            <Brain className="w-3.5 h-3.5 animate-pulse" />
            <span>Thinking Mode</span>
          </>
        ) : (
          <>
            <Zap className="w-3.5 h-3.5" />
            <span>Fast Mode</span>
          </>
        )}
        <span className="opacity-60">|</span>
        <span className="opacity-80">{modelName}</span>
      </button>

      {/* Expanded details panel */}
      {isExpanded && (
        <div className="absolute top-full right-0 mt-2 w-72 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl p-3 z-50">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-zinc-400">Current Model</span>
              <span className="text-xs font-mono text-zinc-200">{modelName}</span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-xs text-zinc-400">Mode</span>
              <span className={cn(
                'text-xs font-medium',
                state.thinkMode ? 'text-purple-400' : 'text-emerald-400'
              )}>
                {state.thinkMode ? 'Deep Thinking' : 'Fast Response'}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs text-zinc-400">Conversation Turns</span>
              <span className="text-xs text-zinc-200">{state.turnCount}</span>
            </div>

            {state.lastReflection && (
              <div className="pt-2 border-t border-zinc-700">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <RefreshCw className="w-3 h-3 text-zinc-400" />
                  <span className="text-xs text-zinc-400">Last Reflection</span>
                </div>
                <p className="text-xs text-zinc-300 leading-relaxed">
                  {state.lastReflection.reason}
                </p>
                <div className="flex items-center gap-2 mt-2">
                  <div className="flex-1 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-full',
                        state.lastReflection.confidence >= 0.7 ? 'bg-emerald-500' :
                        state.lastReflection.confidence >= 0.4 ? 'bg-amber-500' : 'bg-red-500'
                      )}
                      style={{ width: `${state.lastReflection.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-zinc-400">
                    {(state.lastReflection.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Simple inline indicator for showing model switches in the chat
export function ModelSwitchEvent({ 
  fromModel, 
  toModel, 
  reason 
}: { 
  fromModel: string; 
  toModel: string; 
  reason?: string;
}) {
  const toName = toModel.includes('gpt-4o-mini') ? 'GPT-4o-mini' : 
                 toModel.includes('gpt-4o') ? 'GPT-4o' : toModel;
  const isUpgrade = toModel.includes('gpt-4o') && !toModel.includes('mini');

  return (
    <div className="flex items-center justify-center my-3">
      <div className={cn(
        'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs border',
        isUpgrade 
          ? 'bg-purple-500/10 border-purple-500/30 text-purple-300'
          : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
      )}>
        {isUpgrade ? (
          <Brain className="w-3.5 h-3.5" />
        ) : (
          <Zap className="w-3.5 h-3.5" />
        )}
        <span>
          Switched to <strong>{toName}</strong>
          {reason && <span className="opacity-70"> — {reason}</span>}
        </span>
      </div>
    </div>
  );
}
