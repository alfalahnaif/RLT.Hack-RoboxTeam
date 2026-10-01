import { setRequestLocale } from "next-intl/server";
import { Gallery } from "./gallery";

/**
 * Internal design-system gallery (dev reference). Renders every token and component in all
 * documented states inside the real application shell. Safe to delete for production.
 */
export default async function DesignSystemPage({ params }: PageProps<"/[locale]/design-system">) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <Gallery />;
}
