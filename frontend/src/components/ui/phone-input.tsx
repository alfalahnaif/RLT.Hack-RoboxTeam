"use client";

import { Select as SelectPrimitive } from "radix-ui";
import { cn } from "@/lib/utils";
import { CheckIcon, ChevronDownIcon } from "./_glyphs";
import { useField } from "./field";

export type Country = { code: string; dial: string; name: string };

/** Default Russia-first list (names in Russian); pass `countries` to override. */
export const DEFAULT_COUNTRIES: Country[] = [
  { code: "RU", dial: "+7", name: "Россия" },
  { code: "BY", dial: "+375", name: "Беларусь" },
  { code: "KZ", dial: "+7", name: "Казахстан" },
  { code: "AM", dial: "+374", name: "Армения" },
  { code: "KG", dial: "+996", name: "Киргизия" },
  { code: "UZ", dial: "+998", name: "Узбекистан" },
];

type PhoneInputProps = {
  country?: string;
  onCountryChange?: (code: string) => void;
  value?: string;
  onChange?: (value: string) => void;
  countries?: Country[];
  placeholder?: string;
  disabled?: boolean;
  invalid?: boolean;
  className?: string;
};

/**
 * Source: `.phone-number-input` (intl-tel-input). Always laid out LTR: a 64px gray-100 dial-code
 * segment (radius 8 on the outer corners) + number field (12px regular). Same 44px control box.
 */
export function PhoneInput({ country = "RU", onCountryChange, value, onChange, countries = DEFAULT_COUNTRIES, placeholder = "9XX XXX-XX-XX", disabled, invalid, className }: PhoneInputProps) {
  const field = useField();
  const current = countries.find((c) => c.code === country) ?? countries[0];
  const isInvalid = invalid ?? field?.invalid ?? false;
  return (
    <div
      dir="ltr"
      data-invalid={isInvalid || undefined}
      className={cn(
        "flex h-11 w-full items-stretch overflow-hidden rounded-md border border-line bg-surface transition-colors focus-within:border-focus data-[invalid]:border-danger-300",
        disabled && "cursor-not-allowed bg-surface-subtle",
        className,
      )}
    >
      <SelectPrimitive.Root dir="ltr" value={current.code} onValueChange={onCountryChange} disabled={disabled}>
        <SelectPrimitive.Trigger className="flex w-16 shrink-0 items-center justify-center gap-1 bg-gray-100 px-2 text-xs text-muted outline-none">
          <span>{current.dial}</span>
          <ChevronDownIcon className="size-3.5 text-gray-400" />
        </SelectPrimitive.Trigger>
        <SelectPrimitive.Portal>
          <SelectPrimitive.Content position="popper" sideOffset={8} align="start" className="z-50 max-h-64 min-w-56 overflow-hidden rounded-md bg-white p-2 shadow-popper">
            <SelectPrimitive.Viewport>
              {countries.map((c) => (
                <SelectPrimitive.Item
                  key={c.code}
                  value={c.code}
                  className="relative flex cursor-pointer items-center justify-between gap-3 rounded-sm p-3 pe-9 text-sm text-heading outline-none data-[highlighted]:bg-surface-subtle data-[state=checked]:bg-surface-subtle"
                >
                  <SelectPrimitive.ItemText>{c.name}</SelectPrimitive.ItemText>
                  <span className="text-xs text-muted" dir="ltr">
                    {c.dial}
                  </span>
                  <SelectPrimitive.ItemIndicator className="absolute end-3">
                    <CheckIcon className="size-4" />
                  </SelectPrimitive.ItemIndicator>
                </SelectPrimitive.Item>
              ))}
            </SelectPrimitive.Viewport>
          </SelectPrimitive.Content>
        </SelectPrimitive.Portal>
      </SelectPrimitive.Root>
      <input
        id={field?.id}
        type="tel"
        inputMode="tel"
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        aria-invalid={isInvalid || undefined}
        aria-describedby={field?.describedBy}
        className="h-full min-w-0 flex-1 bg-transparent px-2 text-xs text-heading outline-none disabled:cursor-not-allowed"
      />
    </div>
  );
}
