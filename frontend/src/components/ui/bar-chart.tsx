"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Tooltip } from "./tooltip";

export type BarDatum = { key: string; label: ReactNode; value: number; tooltip?: ReactNode };

const niceMax = (v: number) => {
  if (v <= 0) return 4;
  const pow = 10 ** Math.floor(Math.log10(v));
  const step = [1, 2, 2.5, 5, 10].find((s) => s * pow * 4 >= v)!;
  return step * pow * 4;
};

/**
 * Single-series column chart (dashboard direction):
 * - dashed recessive grid with 5 value ticks on the start axis;
 * - inactive bars are hatched gray, the `highlight` bar is solid primary with a 4px cap and a value label;
 * - every bar has a hover/focus tooltip; the whole chart gets an aria summary.
 */
export function BarChart({ data, highlight, format = (v) => String(v), height = 220, className }: { data: BarDatum[]; highlight?: string; format?: (v: number) => string; height?: number; className?: string }) {
  const max = niceMax(Math.max(...data.map((d) => d.value), 0));
  const ticks = [4, 3, 2, 1, 0].map((i) => (max / 4) * i);
  return (
    <div className={cn("flex gap-3", className)} role="img" aria-label={data.map((d) => `${typeof d.label === "string" ? d.label : d.key}: ${format(d.value)}`).join(", ")}>
      <div className="flex shrink-0 flex-col justify-between pb-6 text-2xs text-muted" style={{ height }} aria-hidden>
        {ticks.map((t) => (
          <span key={t} className="-translate-y-1/2 leading-none first:translate-y-0 last:translate-y-0" dir="ltr">
            {format(t)}
          </span>
        ))}
      </div>
      <div className="relative min-w-0 flex-1" style={{ height }}>
        <div className="pointer-events-none absolute inset-x-0 top-0 bottom-6 flex flex-col justify-between" aria-hidden>
          {ticks.map((t) => (
            <span key={t} className="border-t border-dashed border-line" />
          ))}
        </div>
        <div className="absolute inset-x-0 top-0 bottom-0 flex items-end gap-1.5 sm:gap-3">
          {data.map((d) => {
            const on = d.key === highlight;
            const h = max ? (d.value / max) * 100 : 0;
            return (
              <Tooltip key={d.key} content={d.tooltip ?? format(d.value)}>
                <button type="button" className="group flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1.5 rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-primary-600/30">
                  <div className="relative flex w-full max-w-12 flex-1 flex-col justify-end pb-0">
                    {on ? (
                      <span className="absolute inset-x-0 text-center text-2xs font-semibold text-primary-700" style={{ bottom: `calc(${h}% + 6px)` }} dir="ltr">
                        {format(d.value)}
                      </span>
                    ) : null}
                    <div
                      className={cn(
                        "w-full rounded-t-xs transition-[height,background-color] duration-300",
                        on ? "border-t-4 border-primary-700 bg-linear-to-b from-primary-500 to-primary-100" : "bg-hatch border-t-2 border-gray-200 group-hover:border-gray-300",
                      )}
                      style={{ height: `${h}%`, minHeight: d.value ? 6 : 0 }}
                    />
                  </div>
                  <span className={cn("h-4.5 truncate text-2xs", on ? "font-medium text-heading" : "text-muted")}>{d.label}</span>
                </button>
              </Tooltip>
            );
          })}
        </div>
      </div>
    </div>
  );
}
