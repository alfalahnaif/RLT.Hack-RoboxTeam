"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Tooltip } from "./tooltip";

export type StackedSegment = { key: string; label: ReactNode; value: number; tone: "primary" | "info" | "success" | "warning" | "danger" | "gray" | "purple" };

const FILL: Record<StackedSegment["tone"], string> = {
  primary: "bg-primary-600",
  info: "bg-info-500",
  success: "bg-success-500",
  warning: "bg-warning-500",
  danger: "bg-danger-500",
  gray: "bg-gray-300",
  purple: "bg-purple",
};

/**
 * Part-to-whole bar (ds-dashboard): one 12px rounded track split into segments with 2px surface gaps,
 * each segment has a tooltip; the legend below repeats label · value · share so colour is never the only cue.
 * `legend="inline"` puts the legend on one wrapping row (compact panels).
 */
export function StackedBar({ segments, legend = "list", size = "md", className }: { segments: StackedSegment[]; legend?: "list" | "inline" | "none"; size?: "sm" | "md"; className?: string }) {
  const total = segments.reduce((s, x) => s + x.value, 0);
  const pct = (v: number) => (total ? Math.round((v / total) * 100) : 0);
  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <div className={cn("flex w-full gap-[2px] overflow-hidden rounded-pill bg-gray-100", size === "sm" ? "h-2" : "h-3")} role="img" aria-label={segments.map((s) => `${typeof s.label === "string" ? s.label : s.key}: ${s.value}`).join(", ")}>
        {total
          ? segments
              .filter((s) => s.value > 0)
              .map((s) => (
                <Tooltip key={s.key} content={`${typeof s.label === "string" ? s.label : ""} ${s.value} (${pct(s.value)}%)`}>
                  <span className={cn("h-full transition-[width] duration-300 first:rounded-s-pill last:rounded-e-pill", FILL[s.tone])} style={{ width: `${(s.value / total) * 100}%` }} />
                </Tooltip>
              ))
          : null}
      </div>
      {legend === "list" ? (
        <ul className="flex flex-col gap-2">
          {segments.map((s) => (
            <li key={s.key} className="flex items-center gap-2 text-sm">
              <span aria-hidden className={cn("size-2 shrink-0 rounded-full", FILL[s.tone])} />
              <span className="flex-1 text-body">{s.label}</span>
              <span className="font-medium text-heading">{s.value}</span>
              <span className="w-10 text-end text-xs text-muted" dir="ltr">
                {pct(s.value)}%
              </span>
            </li>
          ))}
        </ul>
      ) : legend === "inline" ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
          {segments.map((s) => (
            <span key={s.key} className="flex items-center gap-1.5 text-muted">
              <span aria-hidden className={cn("size-2 rounded-full", FILL[s.tone])} />
              {s.label} <span className="font-medium text-heading">{s.value}</span>
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
