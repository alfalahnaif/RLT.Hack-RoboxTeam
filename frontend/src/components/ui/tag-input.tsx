"use client";

import { useState, type KeyboardEvent } from "react";
import { cn } from "@/lib/utils";
import { CloseIcon } from "./_glyphs";
import { useField } from "./field";

/**
 * Free-text tags inside the standard 44px control box. Enter / comma adds a tag, Backspace on an empty
 * input removes the last one. Tags render as soft primary chips (24px, pill, 12/18) with a remove button.
 * `suggestions` shows existing tags as clickable gray chips below the control.
 */
export function TagInput({
  value,
  onChange,
  placeholder,
  suggestions = [],
  removeLabel = "remove",
  className,
}: {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  suggestions?: string[];
  removeLabel?: string;
  className?: string;
}) {
  const field = useField();
  const [draft, setDraft] = useState("");
  const add = (raw: string) => {
    const tag = raw.trim().replace(/,$/, "");
    if (tag && !value.includes(tag)) onChange([...value, tag]);
    setDraft("");
  };
  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      add(draft);
    } else if (e.key === "Backspace" && !draft && value.length) {
      onChange(value.slice(0, -1));
    }
  };
  const available = suggestions.filter((s) => !value.includes(s));

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div className="flex min-h-11 w-full flex-wrap items-center gap-1.5 rounded-md border border-line bg-surface px-3 py-2 transition-colors focus-within:border-focus">
        {value.map((tag) => (
          <span key={tag} className="inline-flex h-6 items-center gap-1 rounded-pill bg-primary-50 ps-2.5 pe-1 text-xs text-primary-700">
            {tag}
            <button type="button" aria-label={`${removeLabel} ${tag}`} onClick={() => onChange(value.filter((t) => t !== tag))} className="flex size-4 items-center justify-center rounded-full hover:bg-primary-100">
              <CloseIcon className="size-3" />
            </button>
          </span>
        ))}
        <input
          id={field?.id}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={() => draft && add(draft)}
          placeholder={value.length ? undefined : placeholder}
          className="h-6 min-w-24 flex-1 bg-transparent text-xs font-medium text-heading outline-none"
        />
      </div>
      {available.length ? (
        <div className="flex flex-wrap gap-1.5">
          {available.map((s) => (
            <button key={s} type="button" onClick={() => add(s)} className="h-6 rounded-pill bg-gray-100 px-2.5 text-xs text-subtle transition-colors hover:bg-gray-200">
              + {s}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
