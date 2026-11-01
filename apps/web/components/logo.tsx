export function LogoMark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path
        d="M18.4 7.3a7 7 0 1 0 0 9.4"
        stroke="currentColor"
        strokeWidth="2.6"
        strokeLinecap="round"
      />
      <circle cx="18.4" cy="7.3" r="2" fill="currentColor" />
    </svg>
  );
}

export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 font-semibold tracking-tight ${className}`}>
      <span
        aria-hidden="true"
        className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground"
      >
        <LogoMark className="size-3.5" />
      </span>
      CreatorOS
    </span>
  );
}
