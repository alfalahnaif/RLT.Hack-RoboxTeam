import { cn } from "@/lib/utils";

/** Circular loading indicator. Inherits `currentColor`; size via `size` prop (px). */
export function Spinner({ size = 16, className }: { size?: number; className?: string }) {
  return (
    <svg
      role="status"
      aria-label="loading"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      className={cn("shrink-0 animate-spin", className)}
    >
      <circle cx="12" cy="12" r="9.5" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21.5 12A9.5 9.5 0 0 0 12 2.5" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}
