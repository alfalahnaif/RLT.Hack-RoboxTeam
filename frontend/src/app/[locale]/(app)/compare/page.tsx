import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { CompareScreen } from "@/features/compare/compare-screen";

export async function generateMetadata({ params }: PageProps<"/[locale]/compare">): Promise<Metadata> {
  const t = await getTranslations({ locale: (await params).locale, namespace: "compare" });
  return { title: `${t("title")} · Supplier Radar` };
}

/** S-04 Compare Suppliers (tray from the current search). */
export default async function ComparePage({ params }: PageProps<"/[locale]/compare">) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <CompareScreen />;
}
