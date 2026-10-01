import { defineRouting } from "next-intl/routing";

/** UI locales (OQ-22): Russian is the primary UI language, English secondary. Both are LTR. */
export const routing = defineRouting({
  locales: ["ru", "en"],
  defaultLocale: "ru",
});

export type Locale = (typeof routing.locales)[number];

/** Direction per locale. Components read direction from here — never compare against a locale string. */
export const localeDirection: Record<Locale, "rtl" | "ltr"> = {
  ru: "ltr",
  en: "ltr",
};

export const isRtl = (locale: string) => localeDirection[locale as Locale] === "rtl";
