'use client';

import { Copy, ThumbsUp, ThumbsDown, RotateCcw } from 'lucide-react';

interface FeedbackBarProps {
  confidence: 'high' | 'medium' | 'low';
  latencySeconds: number;
  onCopy?: () => void;
  onRegenerate?: () => void;
}

export default function FeedbackBar({ confidence, latencySeconds, onCopy, onRegenerate }: FeedbackBarProps) {
  const confidenceLabel = confidence === 'high' ? 'High confidence' : 
                          confidence === 'medium' ? 'Medium confidence' : 'Low confidence';

  return (
    <div className="flex items-center justify-end gap-1 pt-4">
      {/* Action buttons with hover tooltips */}
      <div className="relative group">
        <button 
          onClick={onCopy}
          className="p-1.5 text-muted-foreground hover:text-foreground transition-colors"
        >
          <Copy className="w-4 h-4" />
        </button>
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs text-foreground bg-card border border-border rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
          Copy response
        </span>
      </div>
      
      <div className="relative group">
        <button 
          className="p-1.5 text-muted-foreground hover:text-foreground transition-colors"
        >
          <ThumbsUp className="w-4 h-4" />
        </button>
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs text-foreground bg-card border border-border rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
          {confidenceLabel} • {latencySeconds.toFixed(2)}s
        </span>
      </div>
      
      <div className="relative group">
        <button 
          className="p-1.5 text-muted-foreground hover:text-foreground transition-colors"
        >
          <ThumbsDown className="w-4 h-4" />
        </button>
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs text-foreground bg-card border border-border rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
          Give negative feedback
        </span>
      </div>
      
      <div className="relative group">
        <button 
          onClick={onRegenerate}
          className="p-1.5 text-muted-foreground hover:text-foreground transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs text-foreground bg-card border border-border rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
          Regenerate
        </span>
      </div>
    </div>
  );
}
