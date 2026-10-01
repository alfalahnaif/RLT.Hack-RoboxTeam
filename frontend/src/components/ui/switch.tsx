"use client";

import { Switch as SwitchPrimitive } from "radix-ui";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Source: `.form-switch.form-check-solid` — 36×20 pill. Off: gray-200 track. On: primary-700 track.
 * White 14px knob. Disabled: 40% opacity. Optional label 14/22 medium heading with 8px gap.
 * Like the source, the track is NOT mirrored in RTL: off = knob on the left, on = knob on the right.
 */
export function Switch({ className, ...props }: ComponentProps<typeof SwitchPrimitive.Root>) {
  return (
    <SwitchPrimitive.Root
      dir="ltr"
      data-slot="switch"
      className={cn(
        "peer inline-flex h-5 w-9 shrink-0 items-center rounded-pill bg-gray-200 p-[3px] outline-none transition-colors duration-150",
        "data-[state=checked]:bg-primary-700 focus-visible:ring-4 focus-visible:ring-primary-600/20 disabled:cursor-not-allowed disabled:opacity-40",
        className,
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb
        className={cn(
          "block size-3.5 rounded-full bg-white shadow-[0_1px_2px_rgb(10_13_18/0.12)] transition-transform duration-150",
          "data-[state=checked]:translate-x-4",
        )}
      />
    </SwitchPrimitive.Root>
  );
}

export function SwitchLabel({ label, className, ...props }: ComponentProps<typeof SwitchPrimitive.Root> & { label: ReactNode }) {
  return (
    <label className={cn("inline-flex cursor-pointer items-center gap-2 text-sm font-medium text-heading", className)}>
      <Switch {...props} />
      {label}
    </label>
  );
}
