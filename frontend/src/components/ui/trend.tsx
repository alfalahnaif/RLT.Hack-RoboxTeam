import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Change indicator pill (dashboard direction): tinted pill with a round arrow chip + signed %
 * and an optional muted comparison label ("مقارنة بالشهر الماضي").
 * `inverse` flips the semantics for metrics where going up is bad (overdue, refunds).
 */
export function Trend({ value, label, inverse, className }: { value: number; label?: ReactNode; inverse?: boolean; className?: string }) {
  const dir = value > 0 ? "up" : value < 0 ? "down" : "flat";
  const good = dir === "flat" ? undefined : (dir === "up") !== !!inverse;
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-pill bg-surface-subtle py-0.5 ps-0.5 pe-2.5 text-xs", className)}>
      <span
        aria-hidden
        className={cn(
          "flex size-5 items-center justify-center rounded-full text-2xs text-white",
          good === undefined ? "bg-gray-400" : good ? "bg-success-600" : "bg-danger-600",
        )}
      >
        {dir === "flat" ? "–" : dir === "up" ? "↗" : "↘"}
      </span>
      <span className={cn("font-medium", good === undefined ? "text-subtle" : good ? "text-success-700" : "text-danger-600")} dir="ltr">
        {value > 0 ? "+" : ""}
        {Number.isInteger(value) ? value : value.toFixed(1)}%
      </span>
      {label ? <span className="text-muted">{label}</span> : null}
    </span>
  );
}

/** Percentage change helper — returns 0 when there is no baseline. */
export const pctChange = (current: number, previous: number) => (previous ? Math.round(((current - previous) / previous) * 1000) / 10 : current ? 100 : 0);
