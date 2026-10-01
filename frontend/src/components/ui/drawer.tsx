"use client";

import { Dialog as DialogPrimitive } from "radix-ui";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";
import { CloseIcon } from "./_glyphs";

/**
 * Source: `.wameed-drawer` (el-drawer restyled as a floating panel).
 * Inset 16px from the viewport edges, 300px wide (filters) — `size="lg"` 480px for forms/details.
 * White, gray-100 border, 12px radius, overlay shadow, same backdrop as dialogs.
 * Header: padding 16/16/0, title 16/24 medium + 20px close. Body scrolls. Footer: padding 0/16/16,
 * gap 12, white, pinned to the bottom, packed at the end. JSX order: [secondary, primary].
 * `side="end"` (default) = left in RTL / right in LTR — matches the source filter drawer.
 */
export const Drawer = DialogPrimitive.Root;
export const DrawerTrigger = DialogPrimitive.Trigger;
export const DrawerClose = DialogPrimitive.Close;

type DrawerContentProps = ComponentProps<typeof DialogPrimitive.Content> & {
  side?: "start" | "end";
  size?: "default" | "lg";
};

export function DrawerContent({ className, children, side = "end", size = "default", ...props }: DrawerContentProps) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-overlay data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out" />
      <DialogPrimitive.Content
        className={cn(
          "fixed inset-y-4 z-50 flex w-[calc(100%-32px)] flex-col gap-5 overflow-hidden rounded-lg border border-line-subtle bg-white shadow-overlay outline-none",
          size === "lg" ? "max-w-[480px]" : "max-w-[300px]",
          side === "end" ? "end-4 data-[state=open]:animate-drawer-in-end" : "start-4 data-[state=open]:animate-drawer-in-start",
          className,
        )}
        {...props}
      >
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function DrawerHeader({ className, children, ...props }: ComponentProps<"div">) {
  return (
    <div className={cn("flex items-center gap-4 px-4 pt-4", className)} {...props}>
      <div className="flex min-w-0 flex-1 flex-col gap-1">{children}</div>
      <DialogPrimitive.Close className="flex size-5 shrink-0 items-center justify-center rounded-sm text-gray-500 outline-none hover:text-heading focus-visible:ring-4 focus-visible:ring-primary-600/15">
        <CloseIcon className="size-5" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </div>
  );
}

export function DrawerTitle({ className, ...props }: ComponentProps<typeof DialogPrimitive.Title>) {
  return <DialogPrimitive.Title className={cn("text-base font-medium text-heading", className)} {...props} />;
}

export function DrawerDescription({ className, ...props }: ComponentProps<typeof DialogPrimitive.Description>) {
  return <DialogPrimitive.Description className={cn("text-sm text-muted", className)} {...props} />;
}

export function DrawerBody({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("flex min-h-0 flex-1 flex-col overflow-y-auto", className)} {...props} />;
}

/** Group of fields inside a drawer body (`.wameed-drawer-filter-sections-item`). */
export function DrawerSection({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("flex flex-col gap-4 px-4 pb-4", className)} {...props} />;
}

export function DrawerFooter({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("mt-auto flex items-center justify-end gap-3 bg-white px-4 pb-4 [&>*]:min-w-[100px]", className)} {...props} />;
}
