import { useState } from 'react';
import { ChevronDown, ChevronUp, Eye, AlertCircle, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ReflectionData {
  needsThinking: boolean;
  reason: string;
  confidence: number;
  timestamp?: string;
}

export interface ReflectionPanelProps {
  reflection: ReflectionData | null;
  turnCount: number;
  className?: string;
}

export function ReflectionPanel({ reflection, turnCount, className }: ReflectionPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!reflection) {
    return (
      <div className={cn('bg-gray-50 border border-gray-200 rounded-lg p-3', className)}>
        <div className="flex items-center gap-2 text-gray-500 text-sm">
          <Eye className="w-4 h-4" />
          <span>Reflection will activate after 2 conversation turns</span>
          <span className="ml-auto text-xs">Turn {turnCount}/2</span>
        </div>
      </div>
    );
  }

  const confidenceColor = reflection.confidence >= 0.7 
    ? 'text-green-600' 
    : reflection.confidence >= 0.4 
      ? 'text-amber-600' 
      : 'text-red-600';

  return (
    <div className={cn('bg-white border border-gray-200 rounded-lg shadow-sm', className)}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Eye className="w-4 h-4 text-blue-600" />
          <span className="font-medium text-sm">Reflection Analysis</span>
          {reflection.needsThinking ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full">
              <AlertCircle className="w-3 h-3" />
              Correction Detected
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
              <CheckCircle className="w-3 h-3" />
              Conversation Smooth
            </span>
          )}
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {isExpanded && (
        <div className="px-3 pb-3 border-t border-gray-100">
          <div className="mt-3 space-y-2">
            <div className="flex items-start gap-2">
              <span className="text-xs text-gray-500 w-20 flex-shrink-0">Reasoning:</span>
              <p className="text-sm text-gray-700">{reflection.reason}</p>
            </div>
            
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 w-20 flex-shrink-0">Confidence:</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all',
                      reflection.confidence >= 0.7 ? 'bg-green-500' :
                      reflection.confidence >= 0.4 ? 'bg-amber-500' : 'bg-red-500'
                    )}
                    style={{ width: `${reflection.confidence * 100}%` }}
                  />
                </div>
                <span className={cn('text-xs font-medium', confidenceColor)}>
                  {(reflection.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 w-20 flex-shrink-0">Decision:</span>
              <span className={cn(
                'text-sm font-medium',
                reflection.needsThinking ? 'text-purple-700' : 'text-green-700'
              )}>
                {reflection.needsThinking ? 'Enable deep thinking' : 'Keep fast mode'}
              </span>
            </div>

            {reflection.timestamp && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500 w-20 flex-shrink-0">Time:</span>
                <span className="text-xs text-gray-400">{reflection.timestamp}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export interface ReflectionHistoryProps {
  reflections: ReflectionData[];
  className?: string;
}

export function ReflectionHistory({ reflections, className }: ReflectionHistoryProps) {
  if (reflections.length === 0) return null;

  return (
    <div className={cn('space-y-2', className)}>
      <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider">
        Reflection History
      </h4>
      <div className="space-y-1 max-h-48 overflow-y-auto">
        {reflections.map((reflection, index) => (
          <div
            key={index}
            className={cn(
              'flex items-center gap-2 px-2 py-1 rounded text-xs',
              reflection.needsThinking ? 'bg-purple-50' : 'bg-gray-50'
            )}
          >
            <span className="text-gray-400">#{index + 1}</span>
            <span className={reflection.needsThinking ? 'text-purple-600' : 'text-gray-600'}>
              {reflection.needsThinking ? 'Think' : 'Fast'}
            </span>
            <span className="text-gray-400 truncate flex-1">{reflection.reason}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
