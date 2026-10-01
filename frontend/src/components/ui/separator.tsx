import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

/** 1px gray-200 divider (`.separator`, margin 12px 0). Pass `label` for the centered "أو" style. */
export function Separator({
  orientation = "horizontal",
  label,
  className,
  ...props
}: ComponentProps<"div"> & { orientation?: "horizontal" | "vertical"; label?: ReactNode }) {
  if (label) {
    return (
      <div role="separator" className={cn("flex items-center gap-3 text-sm text-muted", className)} {...props}>
        <span className="h-px flex-1 bg-line" />
        {label}
        <span className="h-px flex-1 bg-line" />
      </div>
    );
  }
  return (
    <div
      role="separator"
      aria-orientation={orientation}
      className={cn(orientation === "horizontal" ? "h-px w-full bg-line" : "h-full w-px bg-line-subtle", className)}
      {...props}
    />
  );
}

/** Keyboard hint chip (header search "Ctrl + K"). */
export function Kbd({ className, ...props }: ComponentProps<"kbd">) {
  return (
    <kbd
      className={cn("inline-flex h-6 items-center rounded-sm bg-gray-100 px-1.5 font-sans text-xs font-medium text-disabled", className)}
      {...props}
    />
  );
}

