'use client';

import { useState, useEffect } from 'react';
import { Copy, ThumbsUp, ThumbsDown, RotateCcw } from 'lucide-react';
import { AnswerContent } from '@/data/mockData';
import AccentIcon from './AccentIcon';

interface AnswerPanelProps {
  answer: AnswerContent;
  confidence: 'low' | 'medium' | 'high';
  latencyMs: number;
  onCopy: () => void;
  onRegenerate: () => void;
  onSourceClick?: (sourceId: string) => void;
}

// Parse **bold** text and [SOURCE X] citations (Wikipedia-style superscript)
function FormattedText({ 
  text, 
  onSourceClick 
}: { 
  text: string; 
  onSourceClick?: (sourceId: string) => void;
}) {
  // Split by bold markers and source citations
  const parts = text.split(/(\*\*[^*]+\*\*|\[SOURCE \d+\])/g);
  
  return (
    <>
      {parts.map((part, index) => {
        // Bold text
        if (part.startsWith('**') && part.endsWith('**')) {
          return (
            <strong key={index} className="font-semibold text-foreground">
              {part.slice(2, -2)}
            </strong>
          );
        }
        
        // Citation reference [SOURCE X] → Wikipedia-style superscript [1]
        const sourceMatch = part.match(/\[SOURCE (\d+)\]/);
        if (sourceMatch) {
          const sourceNum = sourceMatch[1];
          return (
            <sup
              key={index}
              onClick={() => onSourceClick?.(`src-${sourceNum}`)}
              className="citation-ref cursor-pointer"
              title={`View Source ${sourceNum}`}
            >
              [{sourceNum}]
            </sup>
          );
        }
        
        return <span key={index}>{part}</span>;
      })}
    </>
  );
}

// Typewriter effect hook
function useTypewriter(text: string, speed: number = 5) {
  const [displayedText, setDisplayedText] = useState('');
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    setDisplayedText('');
    setIsComplete(false);
    
    let currentIndex = 0;
    const interval = setInterval(() => {
      if (currentIndex < text.length) {
        const charsToAdd = Math.min(4, text.length - currentIndex);
        setDisplayedText(text.slice(0, currentIndex + charsToAdd));
        currentIndex += charsToAdd;
      } else {
        setIsComplete(true);
        clearInterval(interval);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed]);

  return { displayedText, isComplete };
}

export default function AnswerPanel({ 
  answer, 
  confidence, 
  latencyMs, 
  onCopy, 
  onRegenerate,
  onSourceClick
}: AnswerPanelProps) {
  const { displayedText, isComplete } = useTypewriter(answer.direct_answer, 4);
  const [showFull, setShowFull] = useState(false);

  // Show full content after typewriter completes
  useEffect(() => {
    if (isComplete) {
      const timer = setTimeout(() => setShowFull(true), 100);
      return () => clearTimeout(timer);
    }
  }, [isComplete]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Direct Answer - with typewriter */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-primary flex items-center gap-2">
          <AccentIcon className="w-4 h-4" />
          Direct Answer
        </h3>
        <p className="text-foreground/90 text-[15px] leading-relaxed font-sans">
          <FormattedText text={displayedText} onSourceClick={onSourceClick} />
          {!isComplete && (
            <span className="inline-block w-0.5 h-4 bg-primary ml-1 animate-pulse" />
          )}
        </p>
      </div>

      {/* Key Ideas - fade in after typewriter */}
      {showFull && answer.key_ideas.length > 0 && (
        <div className="space-y-3 animate-fade-in">
          <h3 className="text-sm font-medium text-[#E29E60]">Key Ideas</h3>
          <ul className="space-y-2">
            {answer.key_ideas.map((idea, index) => (
              <li 
                key={index}
                className="flex items-start gap-2 text-foreground/80 text-sm animate-slide-up"
                style={{ animationDelay: `${index * 80}ms` }}
              >
                <span className="text-primary mt-1">•</span>
                <span><FormattedText text={idea} onSourceClick={onSourceClick} /></span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Common Pitfall */}
      {showFull && answer.common_pitfall && (
        <div className="space-y-2 animate-fade-in" style={{ animationDelay: '200ms' }}>
          <h3 className="text-sm font-medium text-amber-500">Common Pitfall</h3>
          <p className="text-foreground/70 text-sm">
            <FormattedText text={answer.common_pitfall} onSourceClick={onSourceClick} />
          </p>
        </div>
      )}

      {/* Summary */}
      {showFull && answer.summary && (
        <div className="pt-3 border-t border-border/30 animate-fade-in" style={{ animationDelay: '300ms' }}>
          <p className="text-muted-foreground text-sm italic">
            <FormattedText text={answer.summary} onSourceClick={onSourceClick} />
          </p>
        </div>
      )}

      {/* Actions */}
      {showFull && (
        <div className="flex items-center justify-between pt-4 animate-fade-in" style={{ animationDelay: '400ms' }}>
          <div className="flex items-center gap-2">
            <button 
              onClick={onCopy}
              className="p-2 text-muted-foreground hover:text-foreground transition-colors group relative"
            >
              <Copy className="w-4 h-4" />
              <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs text-foreground bg-card border border-border rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                Copy answer
              </span>
            </button>
            
            <button className="p-2 text-muted-foreground hover:text-emerald-500 transition-colors group relative">
              <ThumbsUp className="w-4 h-4" />
              <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs text-foreground bg-card border border-border rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                Helpful
              </span>
            </button>
            
            <button className="p-2 text-muted-foreground hover:text-red-400 transition-colors group relative">
              <ThumbsDown className="w-4 h-4" />
              <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs text-foreground bg-card border border-border rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                Not helpful
              </span>
            </button>
          </div>
          
          <span className="text-xs text-muted-foreground">
            {latencyMs}ms
          </span>
        </div>
      )}
    </div>
  );
}
