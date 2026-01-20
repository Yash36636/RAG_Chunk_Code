const HeroTitle = () => {
  return (
    <h1 className="text-4xl md:text-5xl lg:text-6xl font-serif text-center leading-tight">
      <span className="text-foreground">Ask </span>
      <span className="relative inline-block">
        <span className="relative z-10 text-background font-semibold px-3">anything</span>
        <span 
          className="absolute inset-0 bg-gradient-to-r from-amber-400 to-amber-500 rounded-lg transform -rotate-1"
          style={{ boxShadow: '0 4px 20px hsla(45, 95%, 55%, 0.3)' }}
        />
      </span>
      <span className="text-foreground"> about</span>
      <br />
      <span className="text-primary">product management</span>
    </h1>
  );
};

export default HeroTitle;
