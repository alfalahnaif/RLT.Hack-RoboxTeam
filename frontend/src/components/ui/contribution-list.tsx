import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type ContributionRow = {
  key: string;
  label: ReactNode;
  /** Points out of 100 (already computed by the ranking engine). */
  points: number;
  applicable: boolean;
  /** Emphasise the row (e.g. largest A-vs-B difference). */
  highlight?: boolean;
};

/**
 * Contribution breakdown (Supplier Radar DS extension): one row per ranking feature —
 * label (14/22) · 6px pill bar · "+27" points (14/22 medium). Bars are scaled to the largest row so
 * small differences stay visible. Not-applicable features stay listed with `naLabel` (BR-05, EC-30).
 * An optional total row repeats the Match the points add up to.
 */
export function ContributionList({
  rows,
  naLabel,
  total,
  className,
}: {
  rows: ContributionRow[];
  naLabel: ReactNode;
  total?: { label: ReactNode; value: number };
  className?: string;
}) {
  const max = Math.max(1, ...rows.filter((r) => r.applicable).map((r) => r.points));
  return (
    <div className={cn("flex flex-col gap-2.5", className)}>
      <ul className="flex flex-col gap-2.5">
        {rows.map((r) => (
          <li
            key={r.key}
            className={cn("grid grid-cols-[minmax(0,1fr)_minmax(64px,40%)_44px] items-center gap-3 rounded-sm text-sm", r.highlight && "-mx-2 bg-warning-50 px-2 py-1")}
          >
            <span className={cn("truncate", r.applicable ? "text-body" : "text-muted")}>{r.label}</span>
            {r.applicable ? (
              <span className="h-1.5 w-full overflow-hidden rounded-pill bg-gray-100" aria-hidden>
                <span className="block h-full rounded-pill bg-primary-600" style={{ width: `${(r.points / max) * 100}%` }} />
              </span>
            ) : (
              <span className="text-xs text-muted">{naLabel}</span>
            )}
            <span className={cn("text-end font-medium", r.applicable ? "text-heading" : "text-disabled")} dir="ltr">
              {r.applicable ? `+${r.points}` : "—"}
            </span>
          </li>
        ))}
      </ul>
      {total ? (
        <div className="grid grid-cols-[minmax(0,1fr)_44px] items-center gap-3 border-t border-line pt-2.5 text-sm">
          <span className="font-medium text-heading">{total.label}</span>
          <span className="text-end font-semibold text-heading">{total.value}</span>
        </div>
      ) : null}
    </div>
  );
}
