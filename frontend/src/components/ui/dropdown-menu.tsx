"use client";

import { DropdownMenu as MenuPrimitive } from "radix-ui";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/**
 * Source: row actions menu (`.menu-sub-dropdown` / `.el-dropdown-menu`).
 * Panel: white, 1px gray-200 border, 8px radius, 8px padding, popper shadow, min-width 175.
 * Item: 8px padding, 8px gap, 8px radius, 14/22 heading, 16px icon gray-500. Hover → gray-50.
 * `tone="danger"` item → danger-600 text & icon (e.g. "حذف العميل").
 */
export const DropdownMenu = MenuPrimitive.Root;
export const DropdownMenuTrigger = MenuPrimitive.Trigger;
export const DropdownMenuGroup = MenuPrimitive.Group;
export const DropdownMenuSub = MenuPrimitive.Sub;
export const DropdownMenuRadioGroup = MenuPrimitive.RadioGroup;

export function DropdownMenuContent({ className, sideOffset = 6, align = "end", ...props }: ComponentProps<typeof MenuPrimitive.Content>) {
  return (
    <MenuPrimitive.Portal>
      <MenuPrimitive.Content
        sideOffset={sideOffset}
        align={align}
        className={cn(
          "z-50 flex min-w-[175px] flex-col gap-0.5 rounded-md border border-line bg-white p-2 shadow-popper outline-none data-[state=open]:animate-popper-in",
          className,
        )}
        {...props}
      />
    </MenuPrimitive.Portal>
  );
}

export function DropdownMenuItem({ className, tone, ...props }: ComponentProps<typeof MenuPrimitive.Item> & { tone?: "default" | "danger" }) {
  return (
    <MenuPrimitive.Item
      className={cn(
        "flex cursor-pointer items-center gap-2 rounded-md p-2 text-sm text-heading outline-none transition-colors select-none",
        "data-[highlighted]:bg-surface-subtle data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50",
        "[&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:text-muted",
        tone === "danger" && "text-danger-600 [&_svg]:text-danger-600",
        className,
      )}
      {...props}
    />
  );
}

export function DropdownMenuLabel({ className, ...props }: ComponentProps<typeof MenuPrimitive.Label>) {
  return <MenuPrimitive.Label className={cn("px-2 py-1.5 text-xs font-medium text-muted", className)} {...props} />;
}

export function DropdownMenuSeparator({ className, ...props }: ComponentProps<typeof MenuPrimitive.Separator>) {
  return <MenuPrimitive.Separator className={cn("my-2 h-px bg-line", className)} {...props} />;
}
