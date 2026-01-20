interface SuggestionChipProps {
  text: string;
  onClick: (text: string) => void;
  disabled?: boolean;
}

const SuggestionChip = ({ text, onClick, disabled }: SuggestionChipProps) => {
  return (
    <button
      onClick={() => onClick(text)}
      disabled={disabled}
      className="px-4 py-2.5 rounded-xl 
                border border-border/50 bg-card/50 
                text-foreground/80 text-sm font-sans
                hover:border-primary/40 hover:bg-card hover:text-foreground
                hover:shadow-md hover:-translate-y-0.5
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-all duration-200 ease-out"
    >
      {text}
    </button>
  );
};

export default SuggestionChip;
