"use client";

import { Popover as PopoverPrimitive } from "radix-ui";
import { useMemo, useState, type ReactNode } from "react";
import { SearchIcon } from "@/components/icons";
import { cn } from "@/lib/utils";
import { CheckIcon, ChevronDownIcon } from "./_glyphs";
import { useField } from "./field";

type Option = { value: string; label: string; disabled?: boolean };

type ComboboxProps = {
  options: Option[];
  value?: string;
  onValueChange?: (value: string) => void;
  placeholder?: ReactNode;
  searchPlaceholder?: string;
  emptyText?: ReactNode;
  disabled?: boolean;
  invalid?: boolean;
  className?: string;
};

/**
 * Filterable select (source `.el-select.is-filterable`, e.g. country / timezone pickers).
 * Same trigger & popper styling as `Select`, with a search input at the top of the popper.
 */
export function Combobox({
  options,
  value,
  onValueChange,
  placeholder,
  searchPlaceholder = "…",
  emptyText = "—",
  disabled,
  invalid,
  className,
}: ComboboxProps) {
  const field = useField();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const selected = options.find((o) => o.value === value);
  const filtered = useMemo(
    () => options.filter((o) => o.label.toLowerCase().includes(query.trim().toLowerCase())),
    [options, query],
  );
  const isInvalid = invalid ?? field?.invalid ?? false;

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={(o) => (setOpen(o), o || setQuery(""))}>
      <PopoverPrimitive.Trigger
        id={field?.id}
        disabled={disabled}
        aria-invalid={isInvalid || undefined}
        className={cn(
          "group flex h-11 w-full items-center justify-between gap-1.5 rounded-md border border-line bg-surface px-3 text-start text-sm leading-6 outline-none transition-colors",
          "data-[state=open]:border-primary-600 aria-[invalid=true]:border-danger-300 disabled:cursor-not-allowed disabled:bg-surface-subtle",
          selected ? "text-heading" : "text-placeholder",
          className,
        )}
      >
        <span className="truncate">{selected ? selected.label : placeholder}</span>
        <ChevronDownIcon className="size-4 shrink-0 text-gray-400 transition-transform group-data-[state=open]:rotate-180" />
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          sideOffset={8}
          align="start"
          className="z-50 w-[var(--radix-popover-trigger-width)] rounded-md bg-surface p-2 shadow-popper data-[state=open]:animate-popper-in"
        >
          <div className="mb-1 flex h-10 items-center gap-2 rounded-md border border-line px-3 focus-within:border-focus">
            <SearchIcon className="size-4 text-gray-400" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={searchPlaceholder}
              className="h-full w-full bg-transparent text-xs font-medium text-heading outline-none"
            />
          </div>
          <div role="listbox" className="flex max-h-[228px] flex-col gap-0.5 overflow-y-auto">
            {filtered.length === 0 ? (
              <p className="p-3 text-center text-sm text-muted">{emptyText}</p>
            ) : (
              filtered.map((o) => {
                const isSel = o.value === value;
                return (
                  <button
                    key={o.value}
                    type="button"
                    role="option"
                    aria-selected={isSel}
                    disabled={o.disabled}
                    onClick={() => {
                      onValueChange?.(o.value);
                      setOpen(false);
                    }}
                    className={cn(
                      "relative flex w-full items-center rounded-sm p-3 pe-10 text-start text-sm text-heading outline-none hover:bg-surface-subtle focus-visible:bg-surface-subtle disabled:text-disabled",
                      isSel && "bg-surface-subtle",
                    )}
                  >
                    {o.label}
                    {isSel ? <CheckIcon className="absolute end-3 size-4" /> : null}
                  </button>
                );
              })
            )}
          </div>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
