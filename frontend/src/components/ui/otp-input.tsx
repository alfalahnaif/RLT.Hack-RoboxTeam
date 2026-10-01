"use client";

import { useRef } from "react";
import { cn } from "@/lib/utils";

/**
 * Source: `.wameed-otp-input` — each box 44px high, 12px padding, 8px radius, gray-200 border,
 * centered 12/18 medium heading. Always LTR. Focus → primary-300 border.
 */
export function OtpInput({ length = 4, value, onChange, invalid, className }: { length?: number; value: string; onChange: (v: string) => void; invalid?: boolean; className?: string }) {
  const refs = useRef<(HTMLInputElement | null)[]>([]);
  const chars = value.padEnd(length, " ").slice(0, length).split("");

  const setAt = (i: number, ch: string) => {
    const next = chars.map((c, idx) => (idx === i ? ch : c)).join("").trimEnd();
    onChange(next.replace(/\s/g, ""));
  };

  return (
    <div dir="ltr" className={cn("flex w-full gap-2", className)}>
      {chars.map((c, i) => (
        <input
          key={i}
          ref={(el) => {
            refs.current[i] = el;
          }}
          inputMode="numeric"
          autoComplete={i === 0 ? "one-time-code" : "off"}
          maxLength={1}
          value={c.trim()}
          aria-invalid={invalid || undefined}
          placeholder="-"
          onChange={(e) => {
            const ch = e.target.value.replace(/\D/g, "").slice(-1);
            setAt(i, ch || " ");
            if (ch) refs.current[i + 1]?.focus();
          }}
          onKeyDown={(e) => {
            if (e.key === "Backspace" && !c.trim()) refs.current[i - 1]?.focus();
          }}
          onPaste={(e) => {
            const digits = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, length);
            if (digits) {
              e.preventDefault();
              onChange(digits);
              refs.current[Math.min(digits.length, length - 1)]?.focus();
            }
          }}
          className="h-11 w-full min-w-0 rounded-md border border-line bg-white p-3 text-center text-xs font-medium text-heading outline-none transition-colors focus:border-focus aria-[invalid=true]:border-danger-300"
        />
      ))}
    </div>
  );
}
