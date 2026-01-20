'use client';

import { ShieldAlert, Heart } from 'lucide-react';

interface SafetyMessageProps {
  message: string;
}

export default function SafetyMessage({ message }: SafetyMessageProps) {
  // Parse message for **bold** text
  const formatMessage = (text: string) => {
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={index} className="font-semibold">{part.slice(2, -2)}</strong>;
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="animate-fade-in">
      <div className="flex items-start gap-4 p-5 rounded-2xl bg-card border border-border/50">
        <div className="flex-shrink-0 p-2 bg-amber-500/10 rounded-xl">
          <Heart className="w-5 h-5 text-amber-500" />
        </div>
        
        <div className="flex-1 space-y-3">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground font-sans">Support Message</span>
          </div>
          
          <p className="text-foreground/90 text-[15px] leading-relaxed font-sans whitespace-pre-wrap">
            {formatMessage(message)}
          </p>
        </div>
      </div>
    </div>
  );
}
