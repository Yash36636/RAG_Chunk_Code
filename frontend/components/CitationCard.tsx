'use client';

import { Clock } from 'lucide-react';
import Image from 'next/image';

interface CitationCardProps {
  citation: {
    source_num: number;
    speaker: string;
    video_title: string;
    timestamp: string;
    youtube_url: string;
    video_id: string;
    text_preview: string;
  };
}

export default function CitationCard({ citation }: CitationCardProps) {
  const thumbnailUrl = `https://img.youtube.com/vi/${citation.video_id}/mqdefault.jpg`;

  return (
    <a
      href={citation.youtube_url}
      target="_blank"
      rel="noopener noreferrer"
      className="card card-hover flex gap-3 p-3 group cursor-pointer min-w-[280px] max-w-[320px]
                 transform transition-all duration-300 hover:scale-[1.02] hover:-translate-y-1"
    >
      {/* Source badge */}
      <div className="relative flex-shrink-0">
        <div className="absolute -top-1 -left-1 z-10 px-2 py-0.5 bg-primary text-primary-foreground text-[10px] font-medium rounded">
          Source {citation.source_num}
        </div>
        {/* YouTube Thumbnail */}
        <div className="relative w-16 h-16 rounded-lg overflow-hidden bg-muted">
          <Image
            src={thumbnailUrl}
            alt={citation.video_title}
            fill
            className="object-cover transition-transform duration-300 group-hover:scale-110"
            sizes="64px"
          />
        </div>
      </div>

      {/* Citation Details - consistent font */}
      <div className="flex-1 min-w-0">
        <h4 className="font-medium text-sm text-foreground group-hover:text-primary transition-colors line-clamp-1 font-sans">
          {citation.video_title}
        </h4>
        
        <div className="flex items-center gap-2 mt-0.5 text-xs text-muted-foreground font-sans">
          <span className="flex items-center gap-1">
            ★ {citation.speaker}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {citation.timestamp}
          </span>
        </div>

        <p className="mt-1 text-xs text-muted-foreground line-clamp-2 font-sans">
          "{citation.text_preview}"
        </p>
      </div>
    </a>
  );
}
