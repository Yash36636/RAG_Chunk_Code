'use client';

import { useState, useEffect } from 'react';
import { Copy, ThumbsUp, ThumbsDown, RotateCcw } from 'lucide-react';
import AccentIcon from './AccentIcon';

interface Answer {
  directAnswer: string;
  keyIdeas: string[];
  commonPitfall: string;
  summary: string;
}

interface AnswerCardProps {
  answer: Answer;
  query: string;
  confidence: 'high' | 'medium' | 'low';
  latencySeconds: number;
}

// Typewriter hook - shows text being typed character by character
function useTypewriter(text: string, speed: number = 6, startDelay: number = 0) {
  const [displayedText, setDisplayedText] = useState('');
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    setDisplayedText('');
    setIsComplete(false);
    
    const timeout = setTimeout(() => {
      let currentIndex = 0;
      const interval = setInterval(() => {
        if (currentIndex < text.length) {
          // Type multiple characters at once for faster effect
          const charsToAdd = Math.min(4, text.length - currentIndex);
          setDisplayedText(text.slice(0, currentIndex + charsToAdd));
          currentIndex += charsToAdd;
        } else {
          setIsComplete(true);
          clearInterval(interval);
        }
      }, speed);

      return () => clearInterval(interval);
    }, startDelay);

    return () => clearTimeout(timeout);
  }, [text, speed, startDelay]);

  return { displayedText, isComplete };
}

// Parse **bold** text and render with proper formatting
function FormattedText({ text }: { text: string }) {
  // Split by **text** pattern and render bold parts
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  
  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          // Remove ** and render as bold
          const boldText = part.slice(2, -2);
          return <strong key={index} className="font-semibold text-foreground">{boldText}</strong>;
        }
        return <span key={index}>{part}</span>;
      })}
    </>
  );
}

export default function AnswerCard({ answer, query, confidence, latencySeconds }: AnswerCardProps) {
  // Use the direct answer from the backend
  const fullText = answer.directAnswer;
  
  const { displayedText, isComplete } = useTypewriter(fullText, 6);

  const handleCopy = () => {
    navigator.clipboard.writeText(fullText);
  };

  const confidenceLabel = confidence === 'high' ? 'High confidence' : 
                          confidence === 'medium' ? 'Medium confidence' : 'Low confidence';

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Typing Answer - consistent font */}
      <div className="text-foreground/85 text-[15px] leading-relaxed font-normal whitespace-pre-wrap">
        <FormattedText text={displayedText} />
        {!isComplete && (
          <span className="inline-block w-0.5 h-4 bg-primary ml-1 animate-pulse" />
        )}
      </div>

      {/* Action buttons - only show when typing is complete */}
      {isComplete && (
        <div className="flex items-center gap-2 pt-2 animate-fade-in">
          <button 
            onClick={handleCopy}
            className="p-1.5 text-muted-foreground hover:text-foreground transition-colors group relative"
          >
            <Copy className="w-4 h-4" />
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs text-foreground bg-card border border-border rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
              Copy
            </span>
          </button>
          
          <div className="relative group">
            <button 
              className="p-1.5 text-muted-foreground hover:text-foreground transition-colors"
            >
              <ThumbsUp className="w-4 h-4" />
            </button>
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs text-foreground bg-card border border-border rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
              {confidenceLabel}
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
          
          <button 
            className="p-1.5 text-muted-foreground hover:text-foreground transition-colors group relative"
          >
            <RotateCcw className="w-4 h-4" />
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs text-foreground bg-card border border-border rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
              Regenerate
            </span>
          </button>
        </div>
      )}

      {/* Accent icon */}
      {isComplete && (
        <div className="pt-2 animate-fade-in">
          <AccentIcon className="animate-pulse-subtle" />
        </div>
      )}
    </div>
  );
}
