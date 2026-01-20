'use client';

import { AlertTriangle } from 'lucide-react';

interface LowConfidenceWarningProps {
  visible: boolean;
}

export default function LowConfidenceWarning({ visible }: LowConfidenceWarningProps) {
  if (!visible) return null;

  return (
    <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 animate-fade-in">
      <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
      <div className="space-y-1">
        <p className="text-amber-200 text-sm font-medium">
          Weakly grounded answer
        </p>
        <p className="text-amber-200/70 text-xs">
          Sources are limited. This answer has been reframed toward product thinking.
        </p>
      </div>
    </div>
  );
}
