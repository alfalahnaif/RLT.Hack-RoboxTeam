import type { ComponentProps, ReactNode } from "react";
import { ArrowRightIcon } from "@/components/icons";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

/**
 * Page header (Avocat direction, 2026-09): title 26/36 semibold tight + muted 14/22 line, actions at the
 * end side (12px gap, wrap on mobile). Optional round back button (36px, same ring as IconChip).
 */
export function PageHeader({
  title,
  description,
  actions,
  backHref,
  className,
  ...props
}: Omit<ComponentProps<"div">, "title"> & { title: ReactNode; description?: ReactNode; actions?: ReactNode; backHref?: string }) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-4 pt-5 pb-5", className)} {...props}>
      <div className="flex min-w-0 items-start gap-3">
        {backHref ? (
          <Link
            href={backHref}
            aria-label="back"
            className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full border border-line-subtle bg-white text-heading shadow-card transition-colors hover:bg-surface-subtle focus-visible:outline-2 focus-visible:outline-primary-600"
          >
            <ArrowRightIcon className="size-3.5 ltr:rotate-180" />
          </Link>
        ) : null}
        <div className="flex min-w-0 flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight text-heading">{title}</h1>
          {description ? <p className="text-sm text-muted">{description}</p> : null}
        </div>
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
    </div>
  );
}
