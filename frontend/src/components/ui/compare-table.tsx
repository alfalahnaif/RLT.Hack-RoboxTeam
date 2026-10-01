import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Transposed comparison table (Supplier Radar DS extension): attributes are rows, entities are columns.
 * Same chrome as `TableCard` (white, 20px radius, gray-100 border, card shadow) but it never collapses
 * into cards — it scrolls horizontally with a sticky 200px label column at the start side.
 * Head cells 14/22 medium on gray-50; body cells 14/22, 12/24 padding, gray-200 row lines.
 * `highlight` rows get a warning-50 fill + a text marker so the emphasis is not colour-only.
 */
export function CompareTable({ className, children, ...props }: ComponentProps<"table">) {
  return (
    // `relative` keeps absolutely positioned descendants (sr-only labels) inside the scroll box.
    <div className="relative w-full overflow-x-auto rounded-xl border border-line-subtle bg-white shadow-card">
      <table className={cn("w-full min-w-[640px] border-collapse text-start", className)} {...props}>
        {children}
      </table>
    </div>
  );
}

export function CompareHeadRow({ label, children }: { label?: ReactNode; children: ReactNode }) {
  return (
    <thead>
      <tr>
        <th scope="col" className="sticky start-0 z-[1] w-[200px] min-w-[200px] bg-surface-subtle px-5 py-3 text-start text-xs font-medium text-muted">
          {label}
        </th>
        {children}
      </tr>
    </thead>
  );
}

export function CompareHeadCell({ className, ...props }: ComponentProps<"th">) {
  return <th scope="col" className={cn("min-w-[200px] bg-surface-subtle px-5 py-3 text-start align-top text-sm font-medium text-heading", className)} {...props} />;
}

export function CompareRow({ label, highlight, highlightLabel, children }: { label: ReactNode; highlight?: boolean; highlightLabel?: ReactNode; children: ReactNode }) {
  return (
    <tr className={cn("border-t border-line", highlight && "bg-warning-50")}>
      <th scope="row" className={cn("sticky start-0 z-[1] px-5 py-3 text-start align-top text-sm font-normal text-subtle", highlight ? "bg-warning-50" : "bg-white")}>
        <span className="flex flex-col gap-0.5">
          {label}
          {highlight && highlightLabel ? <span className="text-2xs font-medium text-warning-900">{highlightLabel}</span> : null}
        </span>
      </th>
      {children}
    </tr>
  );
}

export function CompareCell({ className, ...props }: ComponentProps<"td">) {
  return <td className={cn("px-5 py-3 align-top text-sm text-heading", className)} {...props} />;
}

export function CompareSection({ label, colSpan }: { label: ReactNode; colSpan: number }) {
  return (
    <tr className="border-t border-line">
      <th colSpan={colSpan} scope="colgroup" className="bg-surface-subtle px-5 py-2 text-start text-xs font-medium text-muted">
        {label}
      </th>
    </tr>
  );
}
