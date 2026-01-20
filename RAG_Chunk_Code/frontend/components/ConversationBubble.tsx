'use client';

import { useState, useEffect } from 'react';
import { Copy, ThumbsUp, ThumbsDown } from 'lucide-react';
import AccentIcon from './AccentIcon';

interface ConversationBubbleProps {
  message: string;
}

// Typewriter hook for conversation mode
function useTypewriter(text: string, speed: number = 8) {
  const [displayedText, setDisplayedText] = useState('');
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    setDisplayedText('');
    setIsComplete(false);
    
    let currentIndex = 0;
    const interval = setInterval(() => {
      if (currentIndex < text.length) {
        const charsToAdd = Math.min(3, text.length - currentIndex);
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

// Parse **bold** text
function FormattedText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={index} className="font-semibold text-foreground">{part.slice(2, -2)}</strong>;
        }
        return <span key={index}>{part}</span>;
      })}
    </>
  );
}

export default function ConversationBubble({ message }: ConversationBubbleProps) {
  const { displayedText, isComplete } = useTypewriter(message, 6);

  const handleCopy = () => {
    navigator.clipboard.writeText(message);
  };

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Conversation message - friendly, no structure */}
      <div className="text-foreground/85 text-[15px] leading-relaxed font-sans whitespace-pre-wrap">
        <FormattedText text={displayedText} />
        {!isComplete && (
          <span className="inline-block w-0.5 h-4 bg-primary ml-1 animate-pulse" />
        )}
      </div>

      {/* Simple actions - only show when typing complete */}
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
            <button className="p-1.5 text-muted-foreground hover:text-foreground transition-colors">
              <ThumbsUp className="w-4 h-4" />
            </button>
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs text-foreground bg-card border border-border rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
              Helpful
            </span>
          </div>
          
          <div className="relative group">
            <button className="p-1.5 text-muted-foreground hover:text-foreground transition-colors">
              <ThumbsDown className="w-4 h-4" />
            </button>
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs text-foreground bg-card border border-border rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
              Not helpful
            </span>
          </div>
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
