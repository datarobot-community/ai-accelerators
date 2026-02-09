import { useState, useCallback, useMemo } from 'react';
import { Copy, Check, ChevronDown, ChevronRight } from 'lucide-react';
import { Button } from './button';
import { cn } from '@/lib/utils';

const COLLAPSE_THRESHOLD = 10;
const COLLAPSED_LINES = 5;

interface CodeBlockProps {
  code: string;
  className?: string;
}

export function CodeBlock({ code, className }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const lines = useMemo(() => code.split('\n'), [code]);
  const lineCount = lines.length;
  const isCollapsible = lineCount > COLLAPSE_THRESHOLD;

  const [isExpanded, setIsExpanded] = useState(!isCollapsible);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1000);
  }, [code]);

  const displayedCode = useMemo(() => {
    if (isExpanded || !isCollapsible) {
      return code;
    }
    return lines.slice(0, COLLAPSED_LINES).join('\n');
  }, [code, lines, isExpanded, isCollapsible]);

  return (
    <div className="relative group">
      <div className="absolute top-1 right-1 flex items-center gap-1">
        {isCollapsible && (
          <Button
            variant="ghost"
            size="icon-sm"
            className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
            onClick={() => setIsExpanded(!isExpanded)}
            aria-label={isExpanded ? 'Collapse code' : 'Expand code'}
          >
            {isExpanded ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
          </Button>
        )}
        <Button
          variant="ghost"
          size="icon-sm"
          className={cn(
            'h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer',
            copied && 'opacity-100'
          )}
          onClick={handleCopy}
          aria-label={copied ? 'Copied' : 'Copy to clipboard'}
        >
          {copied ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
        </Button>
      </div>
      <pre
        className={cn(
          'px-3 py-2 text-xs overflow-x-auto bg-transparent border-0 m-0 rounded-none',
          className
        )}
      >
        {displayedCode}
      </pre>
      {isCollapsible && !isExpanded && (
        <button
          onClick={() => setIsExpanded(true)}
          className="w-full text-xs text-muted-foreground hover:text-foreground py-1 px-3 text-left border-t border-border/50 bg-muted/30 hover:bg-muted/50 transition-colors cursor-pointer"
        >
          ... {lineCount - COLLAPSED_LINES} more lines (click to expand)
        </button>
      )}
    </div>
  );
}
