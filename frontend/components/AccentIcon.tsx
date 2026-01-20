import { Sparkles } from "lucide-react";

interface AccentIconProps {
  className?: string;
}

const AccentIcon = ({ className = "" }: AccentIconProps) => {
  return (
    <div className={`accent-icon inline-flex ${className}`}>
      <Sparkles className="w-6 h-6" />
    </div>
  );
};

export default AccentIcon;
