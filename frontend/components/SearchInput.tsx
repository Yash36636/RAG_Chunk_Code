'use client';

import { useState } from "react";
import { Search, Send, Loader2 } from "lucide-react";

interface SearchInputProps {
  onSubmit: (query: string) => void;
  placeholder?: string;
  isLoading?: boolean;
  disabled?: boolean;
}

const SearchInput = ({ 
  onSubmit, 
  placeholder = "Ask anything about product management...",
  isLoading,
  disabled 
}: SearchInputProps) => {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading && !disabled) {
      onSubmit(query);
      setQuery("");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <div className="relative flex items-center rounded-2xl border border-border/60 bg-card/80 backdrop-blur-sm overflow-hidden
                      focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/20 
                      transition-all duration-300 hover:border-border">
        <Search className="w-5 h-5 text-muted-foreground ml-5" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          disabled={isLoading || disabled}
          className="flex-1 bg-transparent text-foreground placeholder:text-muted-foreground text-[15px]
                    py-4 px-4 outline-none disabled:cursor-not-allowed font-sans"
        />
        <button
          type="submit"
          disabled={!query.trim() || isLoading || disabled}
          className="mr-3 w-10 h-10 rounded-xl bg-secondary hover:bg-secondary/80 
                    disabled:opacity-50 disabled:cursor-not-allowed
                    flex items-center justify-center transition-all duration-200
                    hover:scale-105 active:scale-95"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 text-foreground animate-spin" />
          ) : (
            <Send className="w-4 h-4 text-foreground" />
          )}
        </button>
      </div>
    </form>
  );
};

export default SearchInput;
