import { format, isValid, parseISO } from "date-fns";

/** Stored dates are ISO `yyyy-MM-dd`; UI shows `yyyy/MM/dd` (design-system convention). */
export const fromIso = (iso?: string) => (iso ? parseISO(iso) : undefined);
export const toIso = (d?: Date) => (d && isValid(d) ? format(d, "yyyy-MM-dd") : undefined);
export const fmtDate = (iso?: string | null) => (iso ? format(parseISO(iso), "yyyy/MM/dd") : "--");
export const fmtDateTime = (iso?: string | null) => (iso ? format(parseISO(iso), "yyyy/MM/dd HH:mm") : "--");

/** API scores are 0–1 floats; the UI shows 0–100 integers (ED-01). `null` stays unknown (EC-30). */
export const toPct = (score: number | null | undefined) => (score === null || score === undefined ? null : Math.round(score * 100));

/** Money: always RUB, Russian grouping regardless of UI locale. */
export const fmtRub = (amount: number | null | undefined) =>
  amount === null || amount === undefined ? null : new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 }).format(amount);

export const fmtNumber = (n: number, locale: string) => new Intl.NumberFormat(locale).format(n);
