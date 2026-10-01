import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Source: `.wameed-table`.
 * Wrapper: white, 12px radius, gray-100 border, soft shadow.
 * Toolbar: padding 12/16 — search (max 320px, 40px high), filter button, bulk actions.
 * Head cells: 52px, padding 4/24, gray-50 fill, 14/22 medium heading, 1px gray-200 top border, min-width 140.
 * Body cells: 52px, padding 8/24, 14/22 regular heading; rows separated by 1px gray-200; hover → gray-50.
 * Last column (actions) is sticky at the end side.
 * Below 1150px (`xl`) rows turn into cards: each cell shows its `data-label` at the start and value at the end,
 * the actions cell moves to the top of the card.
 */
export function TableCard({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="table-card"
      className={cn("relative w-full rounded-xl border border-line-subtle bg-white shadow-card xl:overflow-hidden max-xl:border-0 max-xl:bg-transparent max-xl:shadow-none", className)}
      {...props}
    />
  );
}

export function TableToolbar({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      className={cn("flex w-full items-center justify-between gap-4 px-5 py-4 max-xl:flex-col max-xl:items-stretch max-xl:gap-2 max-xl:px-0 max-xl:py-5", className)}
      {...props}
    />
  );
}

/** Title block shown in table toolbars (`.wameed-table-header-title` 16/24 medium + 14/22 muted subtitle). */
export function TableTitle({ title, subtitle }: { title: ReactNode; subtitle?: ReactNode }) {
  return (
    <div className="flex flex-col">
      <h3 className="text-base font-medium text-heading">{title}</h3>
      {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
    </div>
  );
}

export function Table({ className, ...props }: ComponentProps<"table">) {
  return (
    <div className="w-full overflow-x-auto max-xl:overflow-visible">
      <table className={cn("w-full border-collapse text-start max-xl:block", className)} {...props} />
    </div>
  );
}

export function TableHeader({ className, ...props }: ComponentProps<"thead">) {
  return <thead className={cn("max-xl:hidden", className)} {...props} />;
}

export function TableBody({ className, ...props }: ComponentProps<"tbody">) {
  return <tbody className={cn("max-xl:flex max-xl:flex-col max-xl:gap-5", className)} {...props} />;
}

export function TableRow({ className, ...props }: ComponentProps<"tr">) {
  return (
    <tr
      className={cn(
        "group/row border-t border-line transition-colors hover:bg-surface-subtle data-[state=selected]:bg-surface-subtle",
        "max-xl:relative max-xl:block max-xl:rounded-xl max-xl:border max-xl:border-line-subtle max-xl:bg-white max-xl:px-4 max-xl:pt-[73px] max-xl:pb-4 max-xl:shadow-card max-xl:hover:bg-white",
        className,
      )}
      {...props}
    />
  );
}

export function TableHead({ className, ...props }: ComponentProps<"th">) {
  return (
    <th
      className={cn(
        "h-[52px] min-w-[140px] border-t border-line bg-surface-subtle px-6 py-1 text-start text-sm font-medium whitespace-nowrap text-heading",
        "last:sticky last:end-0 last:z-[1] last:w-[180px] last:max-w-[180px]",
        className,
      )}
      {...props}
    />
  );
}

/** Narrow checkbox column (header or cell). */
export function TableCheckboxCell({ header, className, ...props }: ComponentProps<"td"> & { header?: boolean }) {
  const Comp = header ? "th" : "td";
  return (
    <Comp
      className={cn(
        "h-[52px] w-12 min-w-0 px-6 py-2 text-start",
        header && "border-t border-line bg-surface-subtle",
        "max-xl:absolute max-xl:start-4 max-xl:top-4 max-xl:z-[2] max-xl:h-auto max-xl:w-auto max-xl:p-0",
        className,
      )}
      {...(props as ComponentProps<"td">)}
    />
  );
}

type TableCellProps = ComponentProps<"td"> & {
  /** Column name shown next to the value in the mobile card layout. */
  label?: string;
};

export function TableCell({ className, label, ...props }: TableCellProps) {
  return (
    <td
      data-label={label}
      className={cn(
        "h-[52px] px-6 py-2 text-sm text-heading",
        "last:sticky last:end-0 last:z-[1] last:w-[180px] last:max-w-[180px] last:bg-white group-hover/row:last:bg-surface-subtle group-data-[state=selected]/row:last:bg-surface-subtle",
        "max-xl:flex max-xl:h-auto max-xl:min-h-[22px] max-xl:w-full max-xl:items-center max-xl:justify-between max-xl:gap-3 max-xl:px-0 max-xl:pt-2 max-xl:pb-0",
        "max-xl:before:text-sm max-xl:before:text-subtle max-xl:before:content-[attr(data-label)]",
        "max-xl:last:absolute max-xl:last:inset-x-4 max-xl:last:top-3 max-xl:last:w-auto max-xl:last:max-w-none max-xl:last:border-b max-xl:last:border-line max-xl:last:bg-transparent max-xl:last:justify-end max-xl:last:pt-0 max-xl:last:pb-3 max-xl:last:before:hidden",
        className,
      )}
      {...props}
    />
  );
}

/** Row action buttons container (`.actions`, gap 8, 36px icon buttons). */
export function TableActions({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("flex items-center justify-end gap-2", className)} {...props} />;
}

/** Primary cell content: avatar/icon + title (+ optional subtitle). */
export function TableMainCell({ media, title, subtitle }: { media?: ReactNode; title: ReactNode; subtitle?: ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      {media}
      <div className="flex min-w-0 flex-col">
        <span className="truncate text-sm text-heading">{title}</span>
        {subtitle ? <span className="truncate text-xs text-muted">{subtitle}</span> : null}
      </div>
    </div>
  );
}

/** Empty / no-results row spanning all columns. */
export function TableEmpty({ colSpan, children }: { colSpan: number; children: ReactNode }) {
  return (
    <tr className="border-t border-line max-xl:block max-xl:rounded-xl max-xl:border max-xl:border-line-subtle max-xl:bg-white">
      <td colSpan={colSpan} className="max-xl:block">
        {children}
      </td>
    </tr>
  );
}

export function TableFooter({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      className={cn("flex flex-wrap items-center justify-between gap-4 border-t border-line px-5 py-4 max-xl:border-0 max-xl:px-0", className)}
      {...props}
    />
  );
}

/** Bulk-selection pill (`.wameed-table-header-actions`): 36px, pill, gray-300 border, count bubble. */
export function BulkActions({ label, count, className, ...props }: ComponentProps<"button"> & { label: ReactNode; count: number }) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex h-9 items-center gap-1.5 rounded-pill border border-line-strong bg-white ps-3 pe-2 text-sm text-heading transition-colors hover:bg-surface-hover",
        className,
      )}
      {...props}
    >
      {label}
      <span className="ms-1 inline-flex size-[22px] items-center justify-center rounded-full border border-line-strong bg-gray-50 text-2xs font-medium text-subtle">
        {count}
      </span>
    </button>
  );
}
