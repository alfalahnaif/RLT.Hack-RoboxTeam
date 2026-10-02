import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { SearchScreen } from "@/features/search/search-screen";
import { MarketProductSearchScreen } from "@/features/market-product/search-screen";
import { API_MODE } from "@/lib/api/client";

export async function generateMetadata({ params }: PageProps<"/[locale]/search">): Promise<Metadata> {
  const t = await getTranslations({ locale: (await params).locale, namespace: "search" });
  return { title: `${t("title")} · Supplier Radar` };
}

/** S-01 Search. `?from=<request_id>` opens refine mode (edit the parsed intent). */
export default async function SearchPage({ params, searchParams }: PageProps<"/[locale]/search">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const { from } = await searchParams;
  return API_MODE === "live" ? <MarketProductSearchScreen /> : <SearchScreen fromRequestId={typeof from === "string" ? from : undefined} />;
}
