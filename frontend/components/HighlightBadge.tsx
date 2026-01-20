import { Sparkles } from "lucide-react";

interface HighlightBadgeProps {
  text: string;
}

const HighlightBadge = ({ text }: HighlightBadgeProps) => {
  return (
    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20
                    animate-fade-in hover:bg-primary/15 transition-colors duration-300">
      <Sparkles className="w-4 h-4 text-primary animate-pulse-subtle" />
      <span className="text-primary text-sm font-medium font-sans">{text}</span>
    </div>
  );
};

export default HighlightBadge;
