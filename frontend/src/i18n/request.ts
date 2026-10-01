import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";
import { routing } from "./routing";

/**
 * Messages = core file (`messages/{locale}.json`) + one file per feature (`messages/{locale}/{ns}.json`).
 * Add feature namespaces to FEATURE_NAMESPACES as screens are built.
 */
const FEATURE_NAMESPACES: readonly string[] = ["shell", "vocab", "feedback", "search", "results", "supplier", "compare", "history", "analysis"];

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested) ? requested : routing.defaultLocale;

  const core = (await import(`../../messages/${locale}.json`)).default;
  const features = await Promise.all(FEATURE_NAMESPACES.map(async (ns) => [ns, (await import(`../../messages/${locale}/${ns}.json`)).default] as const));

  return { locale, messages: { ...core, ...Object.fromEntries(features) } };
});
