export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 font-semibold tracking-tight ${className}`}>
      <span
        aria-hidden="true"
        className="flex size-6 items-center justify-center rounded-md bg-primary text-xs font-bold text-primary-foreground"
      >
        C
      </span>
      CreatorOS
    </span>
  );
}
