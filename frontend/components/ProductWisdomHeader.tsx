'use client';

import Image from 'next/image';

const ProductWisdomHeader = () => {
  return (
    <header className="flex items-center justify-center py-4">
      {/* Rectangular branded container */}
      <div className="flex items-center gap-3 px-5 py-3 rounded-2xl bg-card/60 border border-border/40 backdrop-blur-sm shadow-lg">
        {/* Logo - Book with Flame */}
        <div className="w-11 h-11 rounded-xl overflow-hidden flex-shrink-0 shadow-md">
          <Image
            src="/logo.png"
            alt="Lenny's Podcast Second Brain"
            width={44}
            height={44}
            className="w-full h-full object-cover"
            priority
          />
        </div>
        
        {/* Text content */}
        <div className="flex flex-col items-start leading-tight">
          <span className="text-lg font-semibold text-foreground tracking-tight">
            Lenny's Podcast
          </span>
          <span className="text-[10px] text-primary/80 font-semibold tracking-widest uppercase">
            Second Brain
          </span>
        </div>
      </div>
    </header>
  );
};

export default ProductWisdomHeader;
