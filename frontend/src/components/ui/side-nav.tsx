import type { ComponentProps, ElementType, ReactNode } from "react";
import { cn } from "@/lib/utils";
import { CheckIcon } from "./_glyphs";

/**
 * Secondary navigation card (source `.tabs-nav`) — used by Settings and Help-center.
 * Card: 260–300px wide, 16px padding, 8px gap, 12px radius, gray-100 border, soft shadow.
 * Section title 14/22 gray-700 (8px bottom margin). Links: 8px padding, 6px radius, gray-200 border,
 * 14/22 heading, 16px gray-500 icon. Active → gray-50 fill + check glyph at the end.
 * On < 1150px the card turns into a horizontal scroller.
 */
export function SideNav({ className, ...props }: ComponentProps<"nav">) {
  return (
    <nav
      className={cn(
        "flex w-full shrink-0 flex-row gap-2 overflow-x-auto rounded-xl border border-line-subtle bg-white p-4 shadow-card xl:w-auto xl:min-w-[260px] xl:max-w-[300px] xl:flex-col",
        className,
      )}
      {...props}
    />
  );
}

export function SideNavSection({ title, className, children, ...props }: ComponentProps<"div"> & { title?: ReactNode }) {
  return (
    <div className={cn("flex w-full flex-col", className)} {...props}>
      {title ? <h3 className="mb-2 hidden text-sm text-subtle xl:block">{title}</h3> : null}
      <ul className="flex w-full flex-row gap-2 xl:flex-col">{children}</ul>
    </div>
  );
}

type SideNavItemProps = ComponentProps<"a"> & {
  icon?: ReactNode;
  active?: boolean;
  /** Render as another link component, e.g. `as={Link}` from `@/i18n/navigation`. */
  as?: ElementType;
};

export function SideNavItem({ icon, active, as: Comp = "a", className, children, ...props }: SideNavItemProps) {
  return (
    <li className="w-full min-w-[120px] xl:min-w-0">
      <Comp
        aria-current={active ? "page" : undefined}
        className={cn(
          "relative flex w-full items-center gap-2 rounded-sm border border-line bg-white p-2 pe-8 text-sm text-heading transition-colors hover:bg-surface-subtle",
          "[&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:text-muted",
          active && "bg-surface-subtle",
          className,
        )}
        {...props}
      >
        {icon}
        <span className="truncate">{children}</span>
        {active ? <CheckIcon className="absolute end-2 text-heading!" /> : null}
      </Comp>
    </li>
  );
}
