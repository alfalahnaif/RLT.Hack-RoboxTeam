import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";
import { Spinner } from "./spinner";

/**
 * Source: `.wameed-button` — pill shaped, 38px min height, 14/22 label, 16px icons, 8px gap,
 * `transition: all .3s ease-in-out`, generic disabled = opacity .4.
 */
export const buttonVariants = cva(
  [
    "inline-flex shrink-0 items-center justify-center gap-2 rounded-pill border border-transparent",
    "text-sm font-normal whitespace-nowrap transition-all duration-300 ease-in-out outline-none select-none",
    "focus-visible:ring-4 focus-visible:ring-primary-600/20",
    "disabled:cursor-not-allowed disabled:opacity-40 aria-disabled:pointer-events-none aria-disabled:opacity-40",
    "[&_svg]:size-4 [&_svg]:shrink-0",
  ],
  {
    variants: {
      variant: {
        /** Main call-to-action. Disabled keeps full opacity with a 40% primary-600 fill. */
        primary: "bg-primary-700 text-white hover:bg-primary-800 disabled:bg-primary-600/40 disabled:opacity-100",
        /** Primary outline — fills on hover. */
        outline:
          "border-primary-700 bg-white text-primary-700 hover:border-primary-800 hover:bg-primary-800 hover:text-white disabled:border-transparent disabled:bg-primary-600/40 disabled:text-white disabled:opacity-100",
        /** Neutral / cancel ("تراجع") button. */
        secondary:
          "border-line-strong bg-white text-heading hover:bg-surface-hover [&_svg]:text-subtle disabled:border-line disabled:bg-surface-hover disabled:text-disabled disabled:opacity-100",
        danger: "bg-danger-600 text-white hover:bg-danger-700 disabled:bg-danger-300 disabled:opacity-100",
        "danger-outline":
          "border-danger-600 bg-white text-danger-600 hover:bg-danger-600 hover:text-white disabled:border-danger-300 disabled:bg-danger-300 disabled:text-white disabled:opacity-100",
        /** Upgrade / premium CTA ("ترقية الباقة"). */
        warning: "bg-warning-600 text-heading hover:bg-warning-700",
        "warning-outline": "border-warning-600 bg-white text-warning-600",
        success: "bg-success-600 text-white hover:bg-success-700",
        "success-outline": "border-success-600 bg-white text-success-600",
        info: "bg-info-700 text-white hover:bg-info-800",
        "info-outline": "border-info-700 bg-white text-info-700",
        purple: "bg-purple text-white",
        "purple-outline": "border-purple bg-white text-purple",
        light: "bg-gray-300 text-heading",
        /** Text-only action (e.g. "تحديد الكل كمقروءة"). */
        link: "min-w-0 px-0 font-medium text-muted hover:text-heading",
        /** Borderless icon action used inside table rows / card headers. */
        ghost: "min-w-0 text-subtle hover:bg-surface-subtle [&_svg]:size-5",
      },
      size: {
        sm: "min-h-9 min-w-[100px] px-3.5 py-1.5",
        default: "min-h-[38px] min-w-[100px] px-3.5 py-1.5",
        md: "min-h-10 min-w-[100px] px-3.5 py-1.5",
        lg: "min-h-11 min-w-[100px] px-3.5 py-1.5",
        /** Square icon-only button (36×36, 20px icon). */
        icon: "size-9 min-w-9 p-0 [&_svg]:size-5",
      },
      block: { true: "w-full" },
    },
    compoundVariants: [{ variant: "link", className: "min-w-0 px-0" }],
    defaultVariants: { variant: "primary", size: "default" },
  },
);

export type ButtonProps = ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
    loading?: boolean;
    /** Semibold (500) label — `.font-weight-semibold`. */
    strong?: boolean;
  };

export function Button({
  className,
  variant,
  size,
  block,
  asChild,
  loading,
  strong,
  disabled,
  children,
  ...props
}: ButtonProps) {
  const Comp = asChild ? Slot.Root : "button";
  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, block }), strong && "font-medium", className)}
      disabled={asChild ? undefined : disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {asChild ? (
        children
      ) : (
        <>
          {loading ? <Spinner /> : null}
          {children}
        </>
      )}
    </Comp>
  );
}
