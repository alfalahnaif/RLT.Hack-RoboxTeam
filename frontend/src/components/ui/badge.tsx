import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/**
 * Source: `.badge` + `.badge-{color}` + `.badge-outline`.
 * Pill, min-width 60, px 12. Default size 26px / 12px text; `sm` 22px / 10px medium.
 * `appearance="soft"` (source "outline") = tinted background + colored text — the most used style.
 */
export const badgeVariants = cva(
  "inline-flex w-fit min-w-[60px] shrink-0 items-center justify-center gap-1 rounded-pill px-3 whitespace-nowrap [&_svg]:size-3 [&_svg]:shrink-0",
  {
    variants: {
      color: {
        primary: "",
        gray: "",
        success: "",
        danger: "",
        info: "",
        warning: "",
        orange: "",
        pink: "",
        purple: "",
      },
      appearance: { soft: "", solid: "" },
      size: {
        sm: "h-[22px] py-1 text-2xs leading-[10px] font-medium",
        default: "h-[26px] py-1 text-xs leading-3",
        md: "h-[30px] py-1.5 text-xs leading-3",
        lg: "h-[34px] py-2 text-xs leading-3",
      },
    },
    compoundVariants: [
      { appearance: "soft", color: "primary", className: "bg-primary-50 text-primary-700" },
      { appearance: "soft", color: "gray", className: "bg-gray-50 text-gray-700" },
      { appearance: "soft", color: "success", className: "bg-success-50 text-success-700" },
      { appearance: "soft", color: "danger", className: "bg-danger-50 text-danger-700" },
      { appearance: "soft", color: "info", className: "bg-info-100 text-info-700" },
      { appearance: "soft", color: "warning", className: "bg-warning-100 text-warning-800" },
      { appearance: "soft", color: "orange", className: "bg-orange-light text-orange" },
      { appearance: "soft", color: "pink", className: "bg-pink-light text-pink" },
      { appearance: "soft", color: "purple", className: "bg-purple-light text-purple" },
      { appearance: "solid", color: "primary", className: "bg-primary-700 text-white" },
      { appearance: "solid", color: "gray", className: "bg-gray-300 text-gray-700" },
      { appearance: "solid", color: "success", className: "bg-success-600 text-white" },
      { appearance: "solid", color: "danger", className: "bg-danger-600 text-white" },
      { appearance: "solid", color: "info", className: "bg-info-600 text-white" },
      { appearance: "solid", color: "warning", className: "bg-warning-500 text-heading" },
      { appearance: "solid", color: "orange", className: "bg-orange text-white" },
      { appearance: "solid", color: "pink", className: "bg-pink text-white" },
      { appearance: "solid", color: "purple", className: "bg-purple text-white" },
    ],
    defaultVariants: { color: "gray", appearance: "soft", size: "default" },
  },
);

export type BadgeProps = Omit<ComponentProps<"span">, "color"> & VariantProps<typeof badgeVariants>;

export function Badge({ className, color, appearance, size, ...props }: BadgeProps) {
  return <span data-slot="badge" className={cn(badgeVariants({ color, appearance, size }), className)} {...props} />;
}

/** Numeric counter bubble (source `.app-navbar-item-counter`): 16px circle, 10px medium, primary. */
export function CountBadge({ className, ...props }: ComponentProps<"span">) {
  return (
    <span
      className={cn(
        "inline-flex size-4 items-center justify-center rounded-full bg-primary-700 text-2xs font-medium text-white",
        className,
      )}
      {...props}
    />
  );
}
