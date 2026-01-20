'use client';

import { BookOpen } from 'lucide-react';
import CitationCard from './CitationCard';

interface Citation {
  source_num: number;
  speaker: string;
  video_title: string;
  timestamp: string;
  youtube_url: string;
  video_id: string;
  text_preview: string;
}

interface CitationListProps {
  citations: Citation[];
}

export default function CitationList({ citations }: CitationListProps) {
  if (!citations || citations.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex items-center gap-2">
        <div className="p-1.5 bg-secondary rounded-lg">
          <BookOpen className="w-4 h-4 text-muted-foreground" />
        </div>
        <h3 className="font-medium text-foreground text-sm font-sans">Sources</h3>
        <span className="px-2 py-0.5 bg-secondary rounded-full text-xs text-muted-foreground font-sans">
          {citations.length} citation{citations.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="flex flex-wrap gap-4">
        {citations.map((citation, index) => (
          <div
            key={citation.source_num}
            className="animate-fade-in"
            style={{ animationDelay: `${index * 150}ms` }}
          >
            <CitationCard citation={citation} />
          </div>
        ))}
      </div>
    </div>
  );
}
