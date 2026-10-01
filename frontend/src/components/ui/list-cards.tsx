import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Setting row card (source `.setting-card`): 1px gray-200 border, 12px radius, 16px padding, 12px gap.
 * 24px icon, title 14/22 medium heading, subtitle 12/18 gray-700, actions at the end.
 */
export function SettingCard({
  icon,
  title,
  description,
  actions,
  className,
  ...props
}: Omit<ComponentProps<"div">, "title"> & { icon?: ReactNode; title: ReactNode; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className={cn("flex items-center gap-3 rounded-lg border border-line p-4 max-md:flex-wrap", className)} {...props}>
      {icon ? <div className="flex size-6 shrink-0 items-center justify-center text-gray-500 [&_svg]:size-6">{icon}</div> : null}
      <div className="flex min-w-0 flex-1 flex-col">
        <h3 className="text-sm font-medium text-heading">{title}</h3>
        {description ? <p className="text-xs text-subtle">{description}</p> : null}
      </div>
      {actions ? <div className="ms-auto flex shrink-0 items-center gap-3">{actions}</div> : null}
    </div>
  );
}

/**
 * Selectable option card (source `.step5-card` / `.current-package-card`): 12px radius, 16px padding.
 * Default: white + gray-200 border. `active`: primary-50/20 fill + primary-300 border.
 */
export function OptionCard({ active, className, ...props }: ComponentProps<"div"> & { active?: boolean }) {
  return (
    <div
      data-active={active || undefined}
      className={cn(
        "flex flex-col gap-4 rounded-lg border p-4 transition-colors",
        active ? "border-primary-300 bg-primary-50/20" : "border-line bg-white",
        className,
      )}
      {...props}
    />
  );
}

/**
 * Notification / activity row (source `.notification-menu-body-notice`): 8/16 padding, 16px gap.
 * 40px gray-100 icon tile (8px radius) with a 6px primary dot when unread; title 14/22 medium;
 * meta 12/18 gray-700; date 10/14 muted at the end. Unread rows: primary-50/20 fill + primary-100 border.
 */
export function NotificationItem({
  icon,
  title,
  meta,
  date,
  unread,
  className,
  ...props
}: Omit<ComponentProps<"div">, "title"> & { icon: ReactNode; title: ReactNode; meta?: ReactNode; date?: ReactNode; unread?: boolean }) {
  return (
    <div
      className={cn(
        "flex items-end gap-4 border-b px-4 py-2 last:border-b-0",
        unread ? "border-primary-100 bg-primary-50/20" : "border-line bg-white",
        className,
      )}
      {...props}
    >
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <div className="relative flex size-10 shrink-0 items-center justify-center rounded-md bg-gray-100 text-gray-500 [&_svg]:size-4">
          {icon}
          {unread ? <span className="absolute -bottom-0.5 -end-0.5 size-1.5 rounded-full bg-primary-700 ring-2 ring-white" /> : null}
        </div>
        <div className="min-w-0">
          <p className="mb-1.5 text-sm font-medium text-heading">{title}</p>
          {meta ? <div className="flex items-center gap-1 text-xs text-subtle">{meta}</div> : null}
        </div>
      </div>
      {date ? <span className="shrink-0 text-2xs text-muted">{date}</span> : null}
    </div>
  );
}
