import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Read-only details grid (detail pages): label 12/18 muted above value 14/22 heading, 16/24px gaps,
 * 1 → 2 → 3 columns. Empty values render "--".
 */
export function DescriptionList({ items, columns = 3, className }: { items: { label: ReactNode; value?: ReactNode; wide?: boolean }[]; columns?: 2 | 3; className?: string }) {
  return (
    <dl className={cn("grid grid-cols-1 gap-x-6 gap-y-4 md:grid-cols-2", columns === 3 && "xl:grid-cols-3", className)}>
      {items.map((it, i) => (
        <div key={i} className={cn("flex min-w-0 flex-col gap-1", it.wide && "md:col-span-2", it.wide && columns === 3 && "xl:col-span-3")}>
          <dt className="text-xs text-muted">{it.label}</dt>
          <dd className="text-sm break-words text-heading">{it.value === undefined || it.value === null || it.value === "" ? "--" : it.value}</dd>
        </div>
      ))}
    </dl>
  );
}
