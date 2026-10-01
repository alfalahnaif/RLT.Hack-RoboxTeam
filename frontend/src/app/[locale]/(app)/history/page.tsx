import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { HistoryScreen } from "@/features/history/history-screen";

export async function generateMetadata({ params }: PageProps<"/[locale]/history">): Promise<Metadata> {
  const t = await getTranslations({ locale: (await params).locale, namespace: "history" });
  return { title: `${t("title")} · Supplier Radar` };
}

/** S-05 Search History. */
export default async function HistoryPage({ params }: PageProps<"/[locale]/history">) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <HistoryScreen />;
}
