"use client";

import { format } from "date-fns";
import { useLocale } from "next-intl";
import { useState, type ComponentProps, type ReactNode } from "react";
import { DayPicker } from "react-day-picker";
import { enUS, ru } from "react-day-picker/locale";
import { CalendarIcon, ChevronRightIcon } from "@/components/icons";
import { isRtl } from "@/i18n/routing";
import { cn } from "@/lib/utils";
import { useField } from "./field";
import { Popover, PopoverContent, PopoverTrigger } from "./popover";

/**
 * Source: `.wameed-datepicker` (vue-datepicker restyled).
 * Menu: white, gray-100 border, 12px radius, 12px padding, soft shadow, max-width 350.
 * Header: 14/22 medium month-year + 20px gray-700 arrows. Weekdays: 12/18 heading.
 * Day cell: 46×40 slot, 40×40 inner, 8px radius, 14/22 heading.
 * Selected / range ends → primary-600 fill + white. Range middle → primary-50 slot + primary-700 text.
 * Today → 5px primary-700 dot under the number. Outside days → gray-400. Disabled → gray-400 + line-through.
 */
export function Calendar({ className, classNames, ...props }: ComponentProps<typeof DayPicker>) {
  const locale = useLocale();
  return (
    <DayPicker
      locale={locale === "ru" ? ru : enUS}
      dir={isRtl(locale) ? "rtl" : "ltr"}
      showOutsideDays
      className={cn("w-fit", className)}
      classNames={{
        months: "relative flex flex-col gap-4 sm:flex-row",
        month: "flex flex-col gap-2",
        month_caption: "flex h-[22px] items-center",
        caption_label: "text-sm font-medium text-heading",
        nav: "absolute end-0 top-0 z-[1] flex h-[22px] items-center gap-1",
        button_previous: "flex size-5 items-center justify-center text-gray-700 disabled:opacity-40",
        button_next: "flex size-5 items-center justify-center text-gray-700 disabled:opacity-40",
        month_grid: "border-collapse",
        weekdays: "flex h-10 items-center",
        weekday: "w-[46px] text-center text-xs font-normal text-heading",
        weeks: "flex flex-col",
        week: "flex",
        day: "group/day relative flex h-10 w-[46px] items-center justify-center p-0 text-sm text-heading",
        day_button:
          "relative flex size-10 items-center justify-center rounded-md outline-none focus-visible:ring-4 focus-visible:ring-primary-600/20 disabled:cursor-not-allowed",
        selected: "[&>button]:bg-primary-600 [&>button]:text-white",
        range_start: "bg-primary-50 [&>button]:bg-primary-600 [&>button]:text-white",
        range_end: "bg-primary-50 [&>button]:bg-primary-600 [&>button]:text-white",
        range_middle: "bg-primary-50 [&>button]:bg-transparent [&>button]:text-primary-700",
        today:
          "[&>button]:after:absolute [&>button]:after:bottom-0 [&>button]:after:start-1/2 [&>button]:after:size-[5px] [&>button]:after:-translate-x-1/2 rtl:[&>button]:after:translate-x-1/2 [&>button]:after:rounded-full [&>button]:after:bg-primary-700 [&>button]:after:content-['']",
        outside: "text-disabled",
        disabled: "text-disabled line-through",
        hidden: "invisible",
        ...classNames,
      }}
      components={{
        Chevron: ({ orientation }) => (
          <ChevronRightIcon
            className={cn("size-5", orientation === "left" && "ltr:rotate-180", orientation === "right" && "rtl:rotate-180", orientation === "up" && "-rotate-90", orientation === "down" && "rotate-90")}
          />
        ),
      }}
      {...props}
    />
  );
}

type DatePickerProps = {
  value?: Date;
  onChange?: (date: Date | undefined) => void;
  placeholder?: ReactNode;
  /** date-fns format, source uses `yyyy/MM/dd`. */
  displayFormat?: string;
  disabled?: boolean;
  invalid?: boolean;
  className?: string;
  calendarProps?: Omit<ComponentProps<typeof DayPicker>, "mode" | "selected" | "onSelect">;
};

export function DatePicker({ value, onChange, placeholder, displayFormat = "yyyy/MM/dd", disabled, invalid, className, calendarProps }: DatePickerProps) {
  const [open, setOpen] = useState(false);
  const field = useField();
  const isInvalid = invalid ?? field?.invalid ?? false;
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        id={field?.id}
        disabled={disabled}
        aria-invalid={isInvalid || undefined}
        className={cn(
          "flex h-11 w-full items-center justify-between gap-2 rounded-md border border-line bg-surface px-3 text-start text-xs font-medium text-heading outline-none transition-colors",
          "data-[state=open]:border-focus focus-visible:border-focus aria-[invalid=true]:border-danger-300 disabled:cursor-not-allowed disabled:bg-surface-subtle",
          className,
        )}
      >
        <span className={cn("truncate", !value && "font-normal text-placeholder")}>{value ? format(value, displayFormat) : placeholder}</span>
        <CalendarIcon className="size-4 shrink-0 text-gray-500" />
      </PopoverTrigger>
      <PopoverContent align="start" className="max-w-[350px] p-3 shadow-soft">
        <Calendar
          mode="single"
          selected={value}
          onSelect={(d) => {
            onChange?.(d);
            setOpen(false);
          }}
          {...(calendarProps as object)}
        />
      </PopoverContent>
    </Popover>
  );
}
