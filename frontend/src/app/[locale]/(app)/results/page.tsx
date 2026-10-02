import { setRequestLocale } from "next-intl/server";
import { ResultsIndex } from "@/features/results/results-index";
import { MarketProductResultsScreen } from "@/features/market-product/results-screen";
import { redirect } from "@/i18n/navigation";
import { API_MODE } from "@/lib/api/client";

/** "Results" without a run: reopen the last run of this session, or invite to search. */
export default async function ResultsIndexPage({ params, searchParams }: PageProps<"/[locale]/results">) {
  const { locale } = await params;
  setRequestLocale(locale);
  if (API_MODE === "live") {
    const { q, okpd2, region } = await searchParams;
    const query = typeof q === "string" ? q.trim() : "";
    if (!query) redirect({ href: "/search", locale });
    return <MarketProductResultsScreen query={query} okpd2={typeof okpd2 === "string" && okpd2.trim() ? okpd2.trim() : null}
      region={typeof region === "string" && region.trim() ? region.trim() : null} />;
  }
  return <ResultsIndex />;
}
