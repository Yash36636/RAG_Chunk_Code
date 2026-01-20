'use client';

import { Shield, AlertTriangle, CheckCircle } from 'lucide-react';

interface ConfidenceBadgeProps {
  confidence: 'low' | 'medium' | 'high';
  showLabel?: boolean;
}

export default function ConfidenceBadge({ confidence, showLabel = true }: ConfidenceBadgeProps) {
  const config = {
    high: {
      icon: CheckCircle,
      color: 'text-emerald-500',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20',
      label: 'High confidence'
    },
    medium: {
      icon: Shield,
      color: 'text-amber-500',
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20',
      label: 'Medium confidence'
    },
    low: {
      icon: AlertTriangle,
      color: 'text-red-400',
      bg: 'bg-red-500/10',
      border: 'border-red-500/20',
      label: 'Low confidence'
    }
  };

  const { icon: Icon, color, bg, border, label } = config[confidence];

  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full ${bg} border ${border}`}>
      <Icon className={`w-3.5 h-3.5 ${color}`} />
      {showLabel && (
        <span className={`text-xs font-medium ${color}`}>{label}</span>
      )}
    </div>
  );
}
