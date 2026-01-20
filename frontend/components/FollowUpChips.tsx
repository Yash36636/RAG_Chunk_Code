'use client';

import { Send } from 'lucide-react';

interface FollowUpChipsProps {
  suggestions: string[];
  onSelect: (suggestion: string) => void;
  disabled?: boolean;
}

export default function FollowUpChips({ suggestions, onSelect, disabled }: FollowUpChipsProps) {
  return (
    <div className="space-y-3 animate-slide-up">
      <span className="text-sm text-muted-foreground font-sans">Follow up with:</span>
      
      <div className="flex flex-wrap gap-2">
        {suggestions.map((suggestion, index) => (
          <button
            key={suggestion}
            onClick={() => onSelect(suggestion)}
            disabled={disabled}
            className="group flex items-center gap-2 px-4 py-2.5 
                      bg-card/60 hover:bg-card
                      border border-border/40 hover:border-border
                      rounded-xl
                      text-sm text-foreground/80 hover:text-foreground
                      disabled:opacity-50 disabled:cursor-not-allowed
                      transition-all duration-200 ease-out
                      hover:shadow-md
                      font-sans"
            style={{ animationDelay: `${index * 100}ms` }}
          >
            <span>{suggestion}</span>
            <Send className="w-3.5 h-3.5 opacity-0 group-hover:opacity-60 transition-opacity -ml-1" />
          </button>
        ))}
      </div>
    </div>
  );
}
