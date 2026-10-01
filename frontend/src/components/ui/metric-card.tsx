import type { ReactNode } from "react";
import { ArrowRightIcon } from "@/components/icons";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { Card } from "./card";

/**
 * KPI tile (dashboard direction): label + 36px icon chip on one line, a display numeral (32/40 semibold),
 * then a footer row with the trend pill at the start and "view details ↗" at the end.
 */
export function MetricCard({
  label,
  value,
  icon,
  trend,
  href,
  hrefLabel,
  className,
}: {
  label: ReactNode;
  value: ReactNode;
  icon?: ReactNode;
  trend?: ReactNode;
  href?: string;
  hrefLabel?: ReactNode;
  className?: string;
}) {
  return (
    <Card variant="panel" className={cn("gap-3 p-4 sm:gap-4 sm:p-5", className)}>
      <div className="flex items-start justify-between gap-3">
        <span className="text-sm text-body">{label}</span>
        {icon ? <IconChip>{icon}</IconChip> : null}
      </div>
      <div className="text-2xl font-semibold tracking-tight text-heading sm:text-3xl">{value}</div>
      {trend || href ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          {trend ?? <span />}
          {href ? (
            <Link href={href} className="inline-flex items-center gap-1 rounded-sm text-xs font-medium text-subtle transition-colors hover:text-primary-700 focus-visible:outline-2 focus-visible:outline-primary-600">
              <span className="max-sm:sr-only">{hrefLabel}</span>
              <ArrowRightIcon className="size-3 -rotate-45 rtl:-scale-x-100 rtl:rotate-45" />
            </Link>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}

/** Round 36px icon holder (gray-50 fill, gray-100 ring) used by KPI tiles and panel headers. */
export function IconChip({ children, tone = "gray", className }: { children: ReactNode; tone?: "gray" | "primary" | "danger" | "warning" | "success"; className?: string }) {
  return (
    <span
      className={cn(
        "flex size-9 shrink-0 items-center justify-center rounded-full border [&_svg]:size-[18px]",
        tone === "gray" && "border-line-subtle bg-surface-subtle text-heading",
        tone === "primary" && "border-primary-100 bg-primary-50 text-primary-700",
        tone === "danger" && "border-danger-100 bg-danger-50 text-danger-600",
        tone === "warning" && "border-warning-100 bg-warning-50 text-warning-800",
        tone === "success" && "border-success-100 bg-success-50 text-success-700",
        className,
      )}
    >
      {children}
    </span>
  );
}
