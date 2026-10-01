"use client";

import { RadioGroup as RadioPrimitive } from "radix-ui";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Source: `.el-radio` — 16px circle, gray-200 border. Checked → primary-50 fill, primary-700 border
 * with a 6px primary-700 dot. Label 12/18 subtle, 8px gap. Groups lay out inline with 16px gap.
 */
export function RadioGroup({ className, ...props }: ComponentProps<typeof RadioPrimitive.Root>) {
  return <RadioPrimitive.Root className={cn("flex flex-wrap items-center gap-4", className)} {...props} />;
}

export function Radio({ className, ...props }: ComponentProps<typeof RadioPrimitive.Item>) {
  return (
    <RadioPrimitive.Item
      className={cn(
        "inline-flex size-4 shrink-0 items-center justify-center rounded-full border border-line bg-white outline-none transition-colors",
        "focus-visible:ring-4 focus-visible:ring-primary-600/15 data-[state=checked]:border-primary-700 data-[state=checked]:bg-primary-50",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    >
      <RadioPrimitive.Indicator className="size-1.5 rounded-full bg-primary-700" />
    </RadioPrimitive.Item>
  );
}

export function RadioItem({ label, className, ...props }: ComponentProps<typeof RadioPrimitive.Item> & { label: ReactNode }) {
  return (
    <label className={cn("inline-flex cursor-pointer items-center gap-2 text-xs text-subtle has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-50", className)}>
      <Radio {...props} />
      {label}
    </label>
  );
}

/**
 * Button-like radio options (source `.radio-group-buttons`): each option min-width 100, padding 12/16,
 * 8px radius, gray-200 border, 12/18 medium gray-700. Active → primary-600 border, primary-50 fill,
 * primary-700 semibold text. Default layout: 3 per row, gap 12.
 */
export function RadioCards({ className, ...props }: ComponentProps<typeof RadioPrimitive.Root>) {
  return <RadioPrimitive.Root className={cn("grid grid-cols-3 gap-3", className)} {...props} />;
}

export function RadioCard({ icon, className, children, ...props }: ComponentProps<typeof RadioPrimitive.Item> & { icon?: ReactNode }) {
  return (
    <RadioPrimitive.Item
      className={cn(
        "flex min-h-11 min-w-[100px] items-center justify-center gap-2 rounded-md border border-line bg-white px-4 py-3 text-xs font-medium text-subtle outline-none transition-colors",
        "data-[state=checked]:border-primary-600 data-[state=checked]:bg-primary-50 data-[state=checked]:font-semibold data-[state=checked]:text-primary-700",
        "focus-visible:ring-4 focus-visible:ring-primary-600/15 disabled:cursor-not-allowed disabled:opacity-50 [&_svg]:size-4",
        className,
      )}
      {...props}
    >
      {icon}
      {children}
    </RadioPrimitive.Item>
  );
}
