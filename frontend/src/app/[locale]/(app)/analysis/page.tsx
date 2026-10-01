import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { AnalysisScreen } from "@/features/analysis/analysis-screen";

export async function generateMetadata({ params }: PageProps<"/[locale]/analysis">): Promise<Metadata> {
  const t = await getTranslations({ locale: (await params).locale, namespace: "analysis" });
  return { title: `${t("title")} · Supplier Radar` };
}

/** S-06 Procurement analysis (P4-002). `?lot=<lot_id>` loads `/procurements/{lot_id}/analysis` from the live API. */
export default async function AnalysisPage({ params, searchParams }: PageProps<"/[locale]/analysis">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const { lot } = await searchParams;
  return <AnalysisScreen lotId={typeof lot === "string" && lot.trim() ? lot.trim() : undefined} />;
}
