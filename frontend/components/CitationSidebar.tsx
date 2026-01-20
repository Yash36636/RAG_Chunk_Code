'use client';

import { ExternalLink, Play } from 'lucide-react';
import { SourceItem } from '@/data/mockData';

interface CitationSidebarProps {
  sources: SourceItem[];
  activeSourceId?: string | null;
}

function SourceCard({ 
  source, 
  index, 
  isActive 
}: { 
  source: SourceItem; 
  index: number;
  isActive: boolean;
}) {
  const sourceId = `src-${index + 1}`;
  
  return (
    <a
      href={source.link}
      target="_blank"
      rel="noopener noreferrer"
      id={sourceId}
      className={`block group animate-slide-up ${isActive ? 'source-pulse' : ''}`}
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <div className={`w-full rounded-lg border bg-card transition-all duration-300 shadow-sm overflow-hidden
        ${isActive 
          ? 'border-primary ring-2 ring-primary/30' 
          : 'border-border/50 hover:border-primary/30 hover:bg-card/80'
        }`}
      >
        {/* Thumbnail - tall aspect ratio */}
        <div className="relative w-full h-[140px] overflow-hidden">
          <img
            src={source.thumbnail}
            alt={source.video_title}
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <Play className="w-10 h-10 text-white" />
          </div>
          {/* Source number badge */}
          <div className={`absolute top-2 left-2 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
            ${isActive 
              ? 'bg-primary text-primary-foreground' 
              : 'bg-black/70 text-white'
            }`}
          >
            {index + 1}
          </div>
          {/* Score badge */}
          <div className="absolute top-2 right-2 px-2 py-0.5 bg-black/70 rounded text-[10px] text-white font-medium">
            {Math.round(source.score * 100)}%
          </div>
        </div>

        {/* Content - stacked vertically */}
        <div className="p-3 space-y-2">
          {/* Speaker */}
          <p className="text-xs font-semibold text-primary">
            {source.speaker}
          </p>
          
          {/* Video Title */}
          <p className="text-sm text-foreground line-clamp-2 leading-snug">
            {source.video_title}
          </p>
          
          {/* Timestamp link */}
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <Play className="w-3 h-3" />
              <span className="font-mono">{source.timestamp}</span>
            </span>
            <ExternalLink className="w-3 h-3 text-muted-foreground group-hover:text-primary transition-colors" />
          </div>
        </div>
      </div>
    </a>
  );
}

export default function CitationSidebar({ sources, activeSourceId }: CitationSidebarProps) {
  if (sources.length === 0) return null;

  return (
    <div className="citation-sidebar space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-muted-foreground">
          Sources ({sources.length})
        </h3>
      </div>
      
      {/* Source cards - stacked */}
      <div className="space-y-3">
        {sources.map((source, index) => (
          <SourceCard 
            key={`${source.link}-${index}`} 
            source={source} 
            index={index}
            isActive={activeSourceId === `src-${index + 1}`}
          />
        ))}
      </div>
      
      {/* Footer note */}
      <p className="text-[10px] text-muted-foreground/60 text-center pt-2">
        Click to watch at timestamp
      </p>
    </div>
  );
}
