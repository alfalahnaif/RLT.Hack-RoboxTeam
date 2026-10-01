"use client";

import { Popover as PopoverPrimitive } from "radix-ui";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/**
 * Header menus (notifications, profile) — source `.notification-menu` / `.profile-menu`.
 * White, 1px gray-100 border, 12px radius. Notifications: 440px, overlay shadow.
 * Profile: 256px, 12px padding, soft shadow.
 */
export const Popover = PopoverPrimitive.Root;
export const PopoverTrigger = PopoverPrimitive.Trigger;
export const PopoverClose = PopoverPrimitive.Close;
export const PopoverAnchor = PopoverPrimitive.Anchor;

export function PopoverContent({ className, sideOffset = 8, align = "end", ...props }: ComponentProps<typeof PopoverPrimitive.Content>) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content
        sideOffset={sideOffset}
        align={align}
        className={cn(
          "z-50 rounded-lg border border-line-subtle bg-white shadow-overlay outline-none data-[state=open]:animate-popper-in",
          className,
        )}
        {...props}
      />
    </PopoverPrimitive.Portal>
  );
}
