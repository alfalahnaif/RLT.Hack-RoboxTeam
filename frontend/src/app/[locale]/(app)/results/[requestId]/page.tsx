import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { ResultsScreen } from "@/features/results/results-screen";

export async function generateMetadata({ params }: PageProps<"/[locale]/results/[requestId]">): Promise<Metadata> {
  const t = await getTranslations({ locale: (await params).locale, namespace: "results" });
  return { title: `${t("title")} · Supplier Radar` };
}

/** S-02 Search Results for one persisted search run. */
export default async function ResultsPage({ params }: PageProps<"/[locale]/results/[requestId]">) {
  const { locale, requestId } = await params;
  setRequestLocale(locale);
  return <ResultsScreen requestId={requestId} />;
}
