'use client';

import { Copy, ThumbsUp, ThumbsDown, RotateCcw } from "lucide-react";
import AccentIcon from "./AccentIcon";

interface ChatMessageProps {
  content: string;
  isUser: boolean;
  showActions?: boolean;
}

const ChatMessage = ({ content, isUser, showActions = true }: ChatMessageProps) => {
  const handleCopy = () => {
    navigator.clipboard.writeText(content);
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-6 animate-fade-in">
        <div className="message-user">
          <p className="text-foreground text-[15px] leading-relaxed">{content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col mb-8 animate-fade-in">
      <div className="message-ai">
        <div className="text-foreground/90 text-[15px] leading-relaxed whitespace-pre-wrap">
          {content}
        </div>
        
        {showActions && (
          <div className="flex items-center gap-3 mt-4">
            <button 
              onClick={handleCopy}
              className="p-1.5 text-muted-foreground hover:text-foreground transition-colors"
              title="Copy"
            >
              <Copy className="w-4 h-4" />
            </button>
            <button className="p-1.5 text-muted-foreground hover:text-foreground transition-colors" title="Good">
              <ThumbsUp className="w-4 h-4" />
            </button>
            <button className="p-1.5 text-muted-foreground hover:text-foreground transition-colors" title="Bad">
              <ThumbsDown className="w-4 h-4" />
            </button>
            <button className="p-1.5 text-muted-foreground hover:text-foreground transition-colors" title="Regenerate">
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
      
      <div className="mt-4">
        <AccentIcon />
      </div>
    </div>
  );
};

export default ChatMessage;
