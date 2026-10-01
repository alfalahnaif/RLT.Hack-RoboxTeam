import type { ComponentProps, ReactNode } from "react";
import { MessageAlertIcon } from "@/components/icons";
import { cn } from "@/lib/utils";

type EmptyStateProps = Omit<ComponentProps<"div">, "title"> & {
  icon?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  /** Buttons row (gap 16). */
  actions?: ReactNode;
  /** `small` = horizontal, 16px padding (inline empty blocks). */
  size?: "default" | "small";
};

/**
 * Source: `.empty-state` — centered column, padding 64/16, gap 24.
 * Icon: 56px gray-100 circle with a 10px gray-50 ring, 24px gray-500 glyph.
 * Title 16/24 medium, description 16/24 regular muted.
 */
export function EmptyState({ icon, title, description, actions, size = "default", className, ...props }: EmptyStateProps) {
  const small = size === "small";
  return (
    <div
      data-slot="empty-state"
      className={cn(
        "flex gap-6 self-stretch",
        small ? "flex-row items-center justify-start p-4 text-start" : "flex-col items-center justify-center px-4 py-16 text-center",
        className,
      )}
      {...props}
    >
      <EmptyStateIcon>{icon ?? <MessageAlertIcon />}</EmptyStateIcon>
      <div className={cn("flex flex-col justify-center gap-1", small ? "items-start" : "items-center")}>
        <h3 className="text-base font-medium text-heading">{title}</h3>
        {description ? <p className="text-base text-muted">{description}</p> : null}
      </div>
      {actions ? <div className="flex items-center justify-center gap-4">{actions}</div> : null}
    </div>
  );
}

export function EmptyStateIcon({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "flex size-14 shrink-0 items-center justify-center rounded-full border-[10px] border-gray-50 bg-gray-100 text-gray-500 [&_svg]:size-6",
        className,
      )}
      {...props}
    />
  );
}
