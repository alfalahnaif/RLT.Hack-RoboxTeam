import type { SVGProps } from "react";

/**
 * Tiny stroke glyphs used internally by primitives (check, chevrons, close, minus).
 * They mirror the element-plus / bootstrap glyphs of the source UI. For product icons use
 * `@/components/icons` instead.
 */
type P = SVGProps<SVGSVGElement>;

export const CheckIcon = (p: P) => (
  <svg viewBox="0 0 16 16" fill="none" aria-hidden {...p}>
    <path d="M13.33 4 6 11.33 2.67 8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const ChevronDownIcon = (p: P) => (
  <svg viewBox="0 0 16 16" fill="none" aria-hidden {...p}>
    <path d="m4 6 4 4 4-4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

/** Points to the reading "end" in LTR; add `rtl-flip` to mirror in RTL. */
export const ChevronEndIcon = (p: P) => (
  <svg viewBox="0 0 16 16" fill="none" aria-hidden {...p}>
    <path d="m6 4 4 4-4 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const CloseIcon = (p: P) => (
  <svg viewBox="0 0 20 20" fill="none" aria-hidden {...p}>
    <path d="M15 5 5 15M5 5l10 10" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
  </svg>
);

export const MinusIcon = (p: P) => (
  <svg viewBox="0 0 16 16" fill="none" aria-hidden {...p}>
    <path d="M3.5 8h9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);
