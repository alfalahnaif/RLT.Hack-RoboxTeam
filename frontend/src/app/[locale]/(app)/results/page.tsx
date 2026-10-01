import { setRequestLocale } from "next-intl/server";
import { ResultsIndex } from "@/features/results/results-index";

/** "Results" without a run: reopen the last run of this session, or invite to search. */
export default async function ResultsIndexPage({ params }: PageProps<"/[locale]/results">) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <ResultsIndex />;
}
