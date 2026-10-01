"use client";

import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";
import { useField } from "./field";

/**
 * Shared "control box" look for inputs, selects, date pickers, phone inputs, textareas.
 * Source: `.el-input__wrapper` — 44px, 12px padding, 8px radius, 1px gray-200 border, white.
 * Focus → primary-300 border. Error → danger-300 border. Disabled/readonly → gray-50 fill.
 */
export const controlVariants = cva(
  [
    "flex w-full items-center gap-2 rounded-md border border-line bg-surface px-3 text-heading transition-[border-color,box-shadow] duration-200 ease-standard",
    "focus-within:border-focus has-[:focus-visible]:border-focus",
    "has-[[aria-invalid=true]]:border-danger-300 data-[invalid=true]:border-danger-300",
    "has-[:disabled]:cursor-not-allowed has-[:disabled]:bg-surface-subtle has-[:disabled]:text-disabled",
    "data-[readonly=true]:bg-surface-subtle data-[readonly=true]:text-disabled",
    "[&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:text-gray-400",
  ],
  {
    variants: {
      size: {
        sm: "h-10",
        /** Header search (38px) */
        md: "h-[38px]",
        default: "h-11",
      },
    },
    defaultVariants: { size: "default" },
  },
);

type InputProps = Omit<ComponentProps<"input">, "size" | "prefix"> &
  VariantProps<typeof controlVariants> & {
    /** Icon/text at the start side (e.g. search icon). */
    prefix?: ReactNode;
    /** Icon/text at the end side (e.g. "Ctrl + K", password toggle). */
    suffix?: ReactNode;
    invalid?: boolean;
    wrapperClassName?: string;
  };

/** Text input. Value text is 12/18 medium heading (source), placeholder gray-300. */
export function Input({ size, prefix, suffix, invalid, className, wrapperClassName, id, readOnly, ...props }: InputProps) {
  const field = useField();
  const isInvalid = invalid ?? field?.invalid ?? false;
  return (
    <div data-slot="input" data-readonly={readOnly || undefined} className={cn(controlVariants({ size }), wrapperClassName)}>
      {prefix ? <span className="flex shrink-0 items-center text-muted">{prefix}</span> : null}
      <input
        id={id ?? field?.id}
        readOnly={readOnly}
        aria-invalid={isInvalid || undefined}
        aria-describedby={field?.describedBy}
        className={cn(
          "h-full w-full min-w-0 bg-transparent text-xs font-medium text-heading outline-none placeholder:font-normal disabled:cursor-not-allowed",
          className,
        )}
        {...props}
      />
      {suffix ? <span className="flex shrink-0 items-center text-xs font-medium text-disabled">{suffix}</span> : null}
    </div>
  );
}

type TextareaProps = ComponentProps<"textarea"> & { invalid?: boolean; maxLength?: number; showCount?: boolean };

/** Multi-line input with optional character counter (`.wameed-texteditor-footer-counter`). */
export function Textarea({ className, invalid, showCount, maxLength, value, id, ...props }: TextareaProps) {
  const field = useField();
  const isInvalid = invalid ?? field?.invalid ?? false;
  const count = typeof value === "string" ? value.length : 0;
  return (
    <div className="flex w-full flex-col gap-2">
      <textarea
        id={id ?? field?.id}
        aria-invalid={isInvalid || undefined}
        aria-describedby={field?.describedBy}
        maxLength={maxLength}
        value={value}
        className={cn(
          "min-h-[88px] w-full resize-y rounded-md border border-line bg-surface p-3 text-xs font-medium text-heading outline-none transition-[border-color] duration-200",
          "focus:border-focus aria-[invalid=true]:border-danger-300 disabled:cursor-not-allowed disabled:bg-surface-subtle disabled:text-disabled",
          className,
        )}
        {...props}
      />
      {showCount && maxLength ? (
        <span className="self-end text-xs text-muted">
          {count}/{maxLength}
        </span>
      ) : null}
    </div>
  );
}
