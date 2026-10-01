"use client";

import { Select as SelectPrimitive } from "radix-ui";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";
import { CheckIcon, ChevronDownIcon } from "./_glyphs";
import { useField } from "./field";

/**
 * Source: `.el-select` — trigger identical to inputs (44px, 8px radius) but text is 14/24 regular.
 * Open → border primary-600 + caret rotated. Popper: white, 8px radius, 8px padding, popper shadow.
 * Items: 12px padding, 6px radius, 14/22; hover & selected → gray-50, selected shows a check at the end.
 */
export const Select = SelectPrimitive.Root;
export const SelectGroup = SelectPrimitive.Group;
export const SelectValue = SelectPrimitive.Value;

type TriggerProps = ComponentProps<typeof SelectPrimitive.Trigger> & { size?: "sm" | "default"; invalid?: boolean };

export function SelectTrigger({ className, children, size = "default", invalid, id, ...props }: TriggerProps) {
  const field = useField();
  const isInvalid = invalid ?? field?.invalid ?? false;
  return (
    <SelectPrimitive.Trigger
      id={id ?? field?.id}
      aria-invalid={isInvalid || undefined}
      className={cn(
        "group flex w-full items-center justify-between gap-1.5 rounded-md border border-line bg-surface px-3 text-start text-sm leading-6 text-heading outline-none transition-colors duration-200",
        size === "sm" ? "h-10" : "h-11",
        "focus-visible:border-primary-600 data-[state=open]:border-primary-600 aria-[invalid=true]:border-danger-300",
        "data-[placeholder]:text-placeholder disabled:cursor-not-allowed disabled:bg-surface-subtle disabled:text-disabled",
        "[&>span]:truncate",
        className,
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDownIcon className="size-4 shrink-0 text-gray-400 transition-transform duration-200 group-data-[state=open]:rotate-180" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  );
}

export function SelectContent({ className, children, position = "popper", ...props }: ComponentProps<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        position={position}
        sideOffset={8}
        className={cn(
          "relative z-50 max-h-[min(var(--radix-select-content-available-height),274px)] min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-md bg-surface p-2 shadow-popper",
          "data-[state=open]:animate-popper-in",
          className,
        )}
        {...props}
      >
        <SelectPrimitive.Viewport className="flex flex-col gap-0.5">{children}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  );
}

export function SelectItem({ className, children, ...props }: ComponentProps<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      className={cn(
        "relative flex w-full cursor-pointer items-center gap-2 rounded-sm p-3 pe-10 text-sm text-heading outline-none select-none",
        "data-[highlighted]:bg-surface-subtle data-[state=checked]:bg-surface-subtle data-[disabled]:cursor-not-allowed data-[disabled]:text-disabled",
        className,
      )}
      {...props}
    >
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
      <span className="absolute end-3 flex size-4 items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <CheckIcon className="size-4 text-heading" />
        </SelectPrimitive.ItemIndicator>
      </span>
    </SelectPrimitive.Item>
  );
}

export function SelectLabel({ className, ...props }: ComponentProps<typeof SelectPrimitive.Label>) {
  return <SelectPrimitive.Label className={cn("px-3 py-1.5 text-xs font-medium text-muted", className)} {...props} />;
}

export function SelectSeparator({ className, ...props }: ComponentProps<typeof SelectPrimitive.Separator>) {
  return <SelectPrimitive.Separator className={cn("my-1 h-px bg-line", className)} {...props} />;
}

type Option = { value: string; label: ReactNode; disabled?: boolean };

/** Convenience wrapper: `<SimpleSelect options={[...]} placeholder="مثال: السعودية" />`. */
export function SimpleSelect({
  options,
  placeholder,
  size,
  invalid,
  className,
  ...props
}: ComponentProps<typeof SelectPrimitive.Root> & {
  options: Option[];
  placeholder?: ReactNode;
  size?: "sm" | "default";
  invalid?: boolean;
  className?: string;
}) {
  return (
    <Select {...props}>
      <SelectTrigger size={size} invalid={invalid} className={className}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value} disabled={o.disabled}>
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
