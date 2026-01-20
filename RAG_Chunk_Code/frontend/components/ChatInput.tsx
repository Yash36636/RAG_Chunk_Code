'use client';

import { useState } from "react";
import { ArrowUp, Loader2 } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  placeholder?: string;
  isLoading?: boolean;
  disabled?: boolean;
}

const ChatInput = ({ 
  onSend, 
  placeholder = "Ask a follow-up question...",
  isLoading,
  disabled 
}: ChatInputProps) => {
  const [message, setMessage] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading && !disabled) {
      onSend(message);
      setMessage("");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div className="chat-input-wrapper transition-all duration-300 hover:border-border">
        <div className="flex items-center p-4">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={placeholder}
            disabled={isLoading || disabled}
            className="flex-1 bg-transparent text-foreground placeholder:text-muted-foreground 
                      text-[15px] outline-none disabled:cursor-not-allowed font-sans"
          />
          
          <button
            type="submit"
            disabled={!message.trim() || isLoading || disabled}
            className="ml-3 w-9 h-9 rounded-xl bg-primary/80 hover:bg-primary 
                      disabled:opacity-50 disabled:cursor-not-allowed
                      flex items-center justify-center transition-all duration-200
                      hover:scale-105 active:scale-95"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 text-primary-foreground animate-spin" />
            ) : (
              <ArrowUp className="w-4 h-4 text-primary-foreground" />
            )}
          </button>
        </div>
      </div>
    </form>
  );
};

export default ChatInput;
