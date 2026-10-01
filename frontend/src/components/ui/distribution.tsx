import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type DistributionItem = { key: string; label: ReactNode; value: number; tone: "primary" | "success" | "warning" | "danger" | "info" | "gray" | "purple" };

const TICK: Record<DistributionItem["tone"], string> = {
  primary: "bg-primary-600",
  success: "bg-success-500",
  warning: "bg-warning-500",
  danger: "bg-danger-500",
  info: "bg-info-500",
  gray: "bg-gray-300",
  purple: "bg-purple",
};
const DOT = TICK;

/**
 * Share-of-total strip (dashboard direction): legend row of labelled percentages, then a single strip
 * of thin rounded ticks where each group gets ticks proportional to its share (2px gaps).
 * Identity is never colour-only — every group is labelled with its name and share.
 */
export function Distribution({ items, ticks = 48, className }: { items: DistributionItem[]; ticks?: number; className?: string }) {
  const total = items.reduce((s, i) => s + i.value, 0);
  const shown = items.filter((i) => i.value > 0);
  // Largest-remainder allocation so tick counts always sum to `ticks`.
  const raw = shown.map((i) => (total ? (i.value / total) * ticks : 0));
  const counts = raw.map(Math.floor);
  let left = ticks - counts.reduce((s, c) => s + c, 0);
  raw
    .map((r, i) => [r - Math.floor(r), i] as const)
    .sort((a, b) => b[0] - a[0])
    .forEach(([, i]) => left-- > 0 && counts[i]++);

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-[repeat(auto-fit,minmax(88px,1fr))]">
        {items.map((i) => (
          <div key={i.key} className="flex flex-col gap-0.5">
            <span className="flex items-center gap-1.5 text-xs text-muted">
              <span aria-hidden className={cn("size-2 rounded-xs", DOT[i.tone])} />
              {i.label}
            </span>
            <span className="text-xl font-semibold text-heading" dir="ltr">
              {total ? Math.round((i.value / total) * 100) : 0}%
            </span>
          </div>
        ))}
      </div>
      <div className="flex h-9 items-stretch gap-[2px]" aria-hidden>
        {shown.flatMap((i, gi) => Array.from({ length: counts[gi] }, (_, k) => <span key={`${i.key}-${k}`} className={cn("flex-1 rounded-pill", TICK[i.tone])} />))}
        {!total ? Array.from({ length: ticks }, (_, k) => <span key={k} className="flex-1 rounded-pill bg-gray-100" />) : null}
      </div>
    </div>
  );
}
