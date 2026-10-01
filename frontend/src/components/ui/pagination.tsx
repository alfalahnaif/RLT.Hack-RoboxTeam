"use client";

import type { ReactNode } from "react";
import { ChevronRightIcon } from "@/components/icons";
import { cn } from "@/lib/utils";
import { SimpleSelect } from "./select";

/**
 * Source: `.page-item .page-link` — 36×36, 8px radius, 1px gray-100 border, white, 14px medium gray-700,
 * 13px gap. Active → primary-700 text, primary-50 fill, primary-600/40 border. Disabled → gray-400.
 */
function pageRange(page: number, total: number): (number | "…")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const out: (number | "…")[] = [1];
  const start = Math.max(2, page - 1);
  const end = Math.min(total - 1, page + 1);
  if (start > 2) out.push("…");
  for (let i = start; i <= end; i++) out.push(i);
  if (end < total - 1) out.push("…");
  out.push(total);
  return out;
}

const itemCls =
  "inline-flex size-9 items-center justify-center rounded-md border border-line-subtle bg-white text-sm font-medium text-subtle outline-none transition-colors hover:text-primary-700 focus-visible:ring-4 focus-visible:ring-primary-600/15 disabled:pointer-events-none disabled:text-disabled";

export function Pagination({
  page,
  pageCount,
  onPageChange,
  className,
}: {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  className?: string;
}) {
  return (
    <nav aria-label="pagination" className={cn("flex items-center gap-[13px]", className)}>
      <button type="button" className={itemCls} disabled={page <= 1} onClick={() => onPageChange(page - 1)} aria-label="previous">
        <ChevronRightIcon className="size-5 text-gray-700 ltr:rotate-180" />
      </button>
      {pageRange(page, pageCount).map((p, i) =>
        p === "…" ? (
          <span key={`e${i}`} className="inline-flex size-9 items-center justify-center text-sm text-disabled">
            …
          </span>
        ) : (
          <button
            key={p}
            type="button"
            aria-current={p === page ? "page" : undefined}
            onClick={() => onPageChange(p)}
            className={cn(itemCls, p === page && "border-primary-600/40 bg-primary-50 text-primary-700")}
          >
            {p}
          </button>
        ),
      )}
      <button type="button" className={itemCls} disabled={page >= pageCount} onClick={() => onPageChange(page + 1)} aria-label="next">
        <ChevronRightIcon className="size-5 text-gray-700 rtl:rotate-180" />
      </button>
    </nav>
  );
}

/** "عدد الصفوف في الصفحة:" + select (14/22 medium gray-700 label, 12px gap, 100px select). */
export function PageSize({
  label,
  value,
  onValueChange,
  options = ["12", "25", "50", "all"],
  allLabel,
}: {
  label: ReactNode;
  value: string;
  onValueChange: (v: string) => void;
  options?: string[];
  allLabel?: ReactNode;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm font-medium text-subtle">{label}</span>
      <SimpleSelect
        value={value}
        onValueChange={onValueChange}
        className="w-[100px]"
        options={options.map((o) => ({ value: o, label: o === "all" ? (allLabel ?? o) : o }))}
      />
    </div>
  );
}
