import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/**
 * White, 1px gray-100 border, 20px radius, `0 6px 12px rgba(0,0,0,.03)` (Avocat direction — was 12px/16px in SafarFlow).
 * Header padding 20/20/8, body 20. `compact` = 16px paddings (stat cards).
 * `internal` = nested card (8px radius, gray-200 border, no shadow, 12px padding).
 */
export const cardVariants = cva("flex min-w-0 flex-col border bg-surface", {
  variants: {
    variant: {
      /** Avocat direction (2026-09): every page card is a 20px-radius panel with 20px paddings. */
      default: "rounded-xl border-line-subtle shadow-card",
      soft: "rounded-xl border-line-subtle shadow-soft",
      outlined: "rounded-xl border-line",
      internal: "rounded-md border-line p-3",
      ghost: "rounded-lg border-transparent bg-transparent",
      /** Dashboard panel — 20px radius, 20px paddings (see ds-dashboard skill). */
      panel: "rounded-xl border-line-subtle shadow-card",
    },
  },
  defaultVariants: { variant: "default" },
});

type CardProps = ComponentProps<"div"> & VariantProps<typeof cardVariants> & { compact?: boolean };

export function Card({ className, variant, compact, ...props }: CardProps) {
  return (
    <div
      data-slot="card"
      data-compact={compact || undefined}
      data-variant={variant ?? "default"}
      className={cn(cardVariants({ variant }), "group/card", className)}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        "flex items-center justify-between gap-3 px-5 pt-5 pb-2 group-data-[compact]/card:px-4 group-data-[compact]/card:pt-4",
        className,
      )}
      {...props}
    />
  );
}

/** Card heading — 16/24 medium (`.card-label`). Use `as` to change the tag. */
export function CardTitle({ className, ...props }: ComponentProps<"h3">) {
  return <h3 data-slot="card-title" className={cn("text-base font-medium text-heading", className)} {...props} />;
}

/** Small card heading used by stat cards — 14/22 regular (`.card-subtitle`). */
export function CardSubtitle({ className, ...props }: ComponentProps<"p">) {
  return <p data-slot="card-subtitle" className={cn("text-sm text-heading", className)} {...props} />;
}

export function CardDescription({ className, ...props }: ComponentProps<"p">) {
  return <p data-slot="card-description" className={cn("text-sm text-muted", className)} {...props} />;
}

export function CardBody({ className, ...props }: ComponentProps<"div">) {
  return <div data-slot="card-body" className={cn("p-5 group-data-[compact]/card:p-4", className)} {...props} />;
}

/** Footer with actions aligned to the end (`.card-footer-actions`, gap 12). */
export function CardFooter({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn("flex items-center justify-end gap-3 px-5 pb-5 group-data-[compact]/card:px-4 group-data-[compact]/card:pb-4", className)}
      {...props}
    />
  );
}
