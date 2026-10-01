"use client";

import { Checkbox as CheckboxPrimitive } from "radix-ui";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";
import { MinusIcon } from "./_glyphs";

/**
 * Source: `.form-check-input[type=checkbox]` — 20px (lg, tables) / 16px (sm), 1px gray-200 border.
 * Checked & indeterminate: primary-50 fill, primary-700 border and glyph. Disabled: 50% opacity.
 */
type CheckboxProps = ComponentProps<typeof CheckboxPrimitive.Root> & { size?: "sm" | "default" };

export function Checkbox({ className, size = "default", ...props }: CheckboxProps) {
  return (
    <CheckboxPrimitive.Root
      data-slot="checkbox"
      className={cn(
        "peer inline-flex shrink-0 items-center justify-center border border-line bg-white text-primary-700 outline-none transition-colors",
        size === "sm" ? "size-4 rounded-xs" : "size-5 rounded-sm",
        "focus-visible:ring-4 focus-visible:ring-primary-600/15",
        "data-[state=checked]:border-primary-700 data-[state=checked]:bg-primary-50 data-[state=indeterminate]:border-primary-700 data-[state=indeterminate]:bg-primary-50",
        "disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-danger-300",
        className,
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator className="flex items-center justify-center">
        {props.checked === "indeterminate" ? (
          <MinusIcon className="size-3" />
        ) : (
          <svg viewBox="0 0 13 11" fill="none" className="size-3" aria-hidden>
            <path d="M1.5 5.8 4.8 9.2 11.5 1.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
}

/** Checkbox + inline label (label 12/18 subtle, gap 8). */
export function CheckboxLabel({ label, className, id, ...props }: CheckboxProps & { label: ReactNode }) {
  return (
    <label className={cn("inline-flex cursor-pointer items-center gap-2 text-xs text-subtle has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-50", className)}>
      <Checkbox id={id} {...props} />
      {label}
    </label>
  );
}

/**
 * Selectable card (source `.wameed-checkbox .el-checkbox`): min-height 46, padding 12, gap 12,
 * 12px radius, gray-200 border. Checked → primary-50/20 fill, primary-300 border, primary-700 label.
 */
export function CheckboxCard({
  label,
  description,
  icon,
  className,
  ...props
}: CheckboxProps & { label: ReactNode; description?: ReactNode; icon?: ReactNode }) {
  return (
    <label
      className={cn(
        "group/cc flex min-h-[46px] w-full cursor-pointer items-center gap-3 rounded-lg border border-line bg-white p-3 transition-colors",
        "has-[[data-state=checked]]:border-primary-300 has-[[data-state=checked]]:bg-primary-50/20",
        "has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-50",
        className,
      )}
    >
      <Checkbox size="sm" {...props} />
      {icon ? <span className="text-muted [&_svg]:size-5">{icon}</span> : null}
      <span className="flex flex-col gap-0.5">
        <span className="text-sm text-heading group-has-[[data-state=checked]]/cc:text-primary-700">{label}</span>
        {description ? <span className="text-xs text-subtle">{description}</span> : null}
      </span>
    </label>
  );
}
