"use client";

import { Popover as PopoverPrimitive } from "radix-ui";
import { useMemo, useState, type ReactNode } from "react";
import { SearchIcon } from "@/components/icons";
import { cn } from "@/lib/utils";
import { Checkbox } from "./checkbox";
import { ChevronDownIcon, CloseIcon } from "./_glyphs";
import { useField } from "./field";

export type MultiOption = { value: string; label: string; description?: ReactNode; avatar?: ReactNode };

/**
 * Searchable multi-select (participants, assistant lawyers, agents).
 * Trigger: standard control box that grows with selected chips (soft gray, pill, 24px, removable).
 * Popper: search field + checkbox rows (label 14/22 + optional 12/18 description).
 */
export function MultiSelect({
  options,
  value,
  onChange,
  placeholder,
  searchPlaceholder = "…",
  emptyText = "—",
  className,
}: {
  options: MultiOption[];
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: ReactNode;
  searchPlaceholder?: string;
  emptyText?: ReactNode;
  className?: string;
}) {
  const field = useField();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => options.filter((o) => o.label.toLowerCase().includes(query.trim().toLowerCase())), [options, query]);
  const selected = options.filter((o) => value.includes(o.value));
  const toggle = (v: string) => onChange(value.includes(v) ? value.filter((x) => x !== v) : [...value, v]);

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={(o) => (setOpen(o), o || setQuery(""))}>
      <PopoverPrimitive.Trigger asChild>
        <div
          id={field?.id}
          role="button"
          aria-haspopup="listbox"
          tabIndex={0}
          className={cn(
            "group flex min-h-11 w-full cursor-pointer items-center gap-2 rounded-md border border-line bg-surface px-3 py-2 text-start outline-none transition-colors",
            "focus-visible:border-primary-600 data-[state=open]:border-primary-600",
            className,
          )}
        >
          <div className="flex flex-1 flex-wrap gap-1.5">
            {selected.length ? (
              selected.map((o) => (
                <span key={o.value} className="inline-flex h-6 items-center gap-1 rounded-pill bg-gray-100 ps-2.5 pe-1 text-xs text-heading">
                  {o.label}
                  <button
                    type="button"
                    aria-label={`remove ${o.label}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggle(o.value);
                    }}
                    className="flex size-4 items-center justify-center rounded-full text-muted hover:bg-gray-200 hover:text-heading"
                  >
                    <CloseIcon className="size-3" />
                  </button>
                </span>
              ))
            ) : (
              <span className="text-sm text-placeholder">{placeholder}</span>
            )}
          </div>
          <ChevronDownIcon className="size-4 shrink-0 text-gray-400 transition-transform group-data-[state=open]:rotate-180" />
        </div>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content sideOffset={8} align="start" className="z-50 w-[var(--radix-popover-trigger-width)] rounded-md bg-surface p-2 shadow-popper data-[state=open]:animate-popper-in">
          <div className="mb-1 flex h-10 items-center gap-2 rounded-md border border-line px-3 focus-within:border-focus">
            <SearchIcon className="size-4 text-gray-400" />
            <input autoFocus value={query} onChange={(e) => setQuery(e.target.value)} placeholder={searchPlaceholder} className="h-full w-full bg-transparent text-xs font-medium text-heading outline-none" />
          </div>
          <div className="flex max-h-64 flex-col gap-0.5 overflow-y-auto">
            {filtered.length === 0 ? (
              <p className="p-3 text-center text-sm text-muted">{emptyText}</p>
            ) : (
              filtered.map((o) => (
                <label key={o.value} className="flex cursor-pointer items-center gap-3 rounded-sm p-2.5 hover:bg-surface-subtle">
                  <Checkbox size="sm" checked={value.includes(o.value)} onCheckedChange={() => toggle(o.value)} />
                  {o.avatar}
                  <span className="flex min-w-0 flex-col">
                    <span className="truncate text-sm text-heading">{o.label}</span>
                    {o.description ? <span className="truncate text-xs text-muted">{o.description}</span> : null}
                  </span>
                </label>
              ))
            )}
          </div>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
