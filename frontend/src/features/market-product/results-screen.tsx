"use client";

import { useTranslations } from "next-intl";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Link } from "@/i18n/navigation";
import { api, supplierExportUrl } from "@/lib/api/client";
import type { SupplierSearchResponse } from "@/lib/api/types";
import { useAsync } from "@/lib/use-async";
import { PageSkeleton } from "../shared/skeletons";
import { ExternalSupplierCard, HistoricalSupplierCard } from "./supplier-cards";

export function MarketProductResultsScreen({ query, okpd2, region }: { query: string; okpd2: string | null; region: string | null }) {
  const t = useTranslations("marketProduct");
  const run = useAsync(
    () => api.supplierSearch({ query, okpd2, region, limit: 20 }),
    [query, okpd2, region],
  );

  if (run.status === "loading") return <><PageHeader title={t("resultsTitle")} description={t("loading")} /><PageSkeleton blocks={3} /></>;
  if (run.status === "error") return (
    <>
      <PageHeader title={t("resultsTitle")} actions={<Button asChild variant="secondary"><Link href="/search">{t("searchAgain")}</Link></Button>} />
      <Alert tone="danger" title={t("error")} actions={<Button variant="secondary" onClick={run.reload}>{t("retry")}</Button>} />
    </>
  );

  const data = run.data;
  const classification = data.classification;
  const hasWarning = (code: string) => classification.warnings.some((warning) => warning.startsWith(code));
  const categoryUncertain = hasWarning("CATEGORY_UNCERTAIN");
  const categoryAmbiguous = hasWarning("CATEGORY_AMBIGUOUS");
  const resolvedNotObserved = hasWarning("RESOLVED_CATEGORY_NOT_OBSERVED");
  const exploratory = categoryUncertain || categoryAmbiguous || resolvedNotObserved;
  const leadingSuggestion = classification.suggested_okpd2[0];
  const selectedPool = data.pool_health.find((entry) => entry.okpd2 === classification.ranking_okpd2) ?? data.pool_health[0];
  const externalGroups = data.external_expansion.filter((entry) => entry.available && entry.candidates.length);
  return (
    <>
      <PageHeader title={t("resultsTitle")} description={t("resultsSubtitle")}
        actions={<div className="flex flex-wrap gap-2"><Button asChild variant="secondary"><Link href="/search">{t("searchAgain")}</Link></Button><Button asChild variant="link"><Link href="/analysis">{t("lotOptionShort")}</Link></Button></div>} />
      <div className="flex flex-col gap-5">
        <Card><CardBody className="flex flex-col gap-4">
          <h2 className="text-base font-semibold text-heading">{t("interpreted")}</h2>
          <p className="text-lg text-heading">{data.query.text}</p>
          {data.query.normalized_text && data.query.normalized_text !== data.query.text ? <p className="text-xs text-muted">{t("interpretedAs")}: {data.query.normalized_text}</p> : null}
          <div className="flex flex-wrap gap-2">
            {classification.provided_okpd2 ? <Badge color="primary">{t("providedCode")}: <span dir="ltr">{classification.provided_okpd2}</span></Badge> : null}
            {classification.suggested_okpd2.length ? classification.suggested_okpd2.map((s, i) => (
              <Badge key={s.okpd2} color="info">{i === 0 ? `${t("suggestedCode")}: ` : ""}<span dir="ltr">{s.okpd2}</span>{s.supporting_items ? ` · ${Math.round(s.share * 100)}%` : ""}</Badge>
            )) : <Badge color="gray">{t("noCode")}</Badge>}
            <Badge color={classification.history_status === "SUFFICIENT" ? "success" : "warning"}>{t(`historyStatus.${classification.history_status}`)}</Badge>
          </div>
          {classification.text_okpd2_alignment ? <p className="text-xs text-muted">{t("alignmentLabel")}: <span className="font-medium text-heading">{t(`alignment.${classification.text_okpd2_alignment}`)}</span></p> : null}
          {leadingSuggestion?.confidence !== undefined && leadingSuggestion.basis ? <p className="text-xs text-muted">{t("categoryConfidence", { percent: Math.round(leadingSuggestion.confidence * 100) })} · {t(`categoryBasis.${leadingSuggestion.basis}`)}</p> : null}
          {classification.ranking_okpd2 ? <p className="text-xs text-muted">{t("rankingCode")}: <span dir="ltr">{classification.ranking_okpd2}</span></p>
            : <p className="text-xs text-muted">{t("rankingTextOnly")}</p>}
        </CardBody></Card>

        {categoryAmbiguous ? <CategoryChoice candidates={classification.top_candidates} query={query} region={region} /> : null}
        {categoryUncertain ? <Alert tone="warning" appearance="inline" description={t("categoryUncertain")} /> : null}
        {resolvedNotObserved ? <Alert tone="warning" appearance="inline" description={t("resolvedNotObserved")} /> : null}
        {!exploratory && classification.history_status !== "SUFFICIENT" ? <Alert tone="warning" appearance="inline" description={t("sparseWarning")} /> : null}
        {classification.text_okpd2_alignment === "MISMATCH" ? <Alert tone="warning" appearance="inline" description={t("mismatchWarning")} /> : null}

        <PoolHealthPanel entry={selectedPool} />

        <section aria-labelledby="historical-title" className="flex flex-col gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2"><h2 id="historical-title" className="text-lg font-semibold text-heading">{t("historicalTitle")}</h2>
              {exploratory ? <Badge color="warning">{t("exploratoryBadge")}</Badge> : null}</div>
            <p className="text-sm text-muted">{exploratory ? t("exploratorySubtitle") : t("historicalSubtitle")}</p>
          </div>
          {data.suppliers.length ? <ol className="grid gap-3 lg:grid-cols-2">{data.suppliers.map((supplier) => <li key={supplier.supplier_id}><HistoricalSupplierCard supplier={supplier} rankingCode={classification.ranking_okpd2} /></li>)}</ol>
            : <Alert tone="info" appearance="inline" description={t("noHistorical")} />}
        </section>

        <section aria-labelledby="external-title" className="flex flex-col gap-3">
          <div><h2 id="external-title" className="text-lg font-semibold text-heading">{t("externalTitle")}</h2><p className="text-sm text-muted">{t("externalSubtitle")}</p>
            <p className="mt-1 text-xs text-muted">{t("verifiedNotApproval")}</p></div>
          {externalGroups.length ? externalGroups.map((group) => (
            <div key={group.okpd2} className="flex flex-col gap-3">
              <Badge color="primary" className="self-start"><span dir="ltr">{group.okpd2}</span></Badge>
              <ul className="grid gap-3 lg:grid-cols-2">{group.candidates.map((candidate) => <li key={candidate.supplier_inn}><ExternalSupplierCard candidate={candidate} /></li>)}</ul>
            </div>
          )) : <Alert tone="info" appearance="inline" description={t("noExternal")} />}
        </section>

        {!data.price_intelligence.available ? <p className="text-xs text-muted">{t("priceUnavailable")}</p> : null}
        <ExportControl data={data} />
      </div>
    </>
  );
}

function CategoryChoice({ candidates, query, region }: {
  candidates: SupplierSearchResponse["classification"]["top_candidates"]; query: string; region: string | null;
}) {
  const t = useTranslations("marketProduct");
  const href = (code: string) => {
    const params = new URLSearchParams({ q: query, okpd2: code });
    if (region) params.set("region", region);
    return `/results?${params.toString()}`;
  };
  return (
    <Alert tone="warning" title={t("categoryAmbiguousTitle")} description={t("categoryAmbiguousHint")}>
      <ul className="mt-3 flex flex-col gap-2">
        {candidates.map((c) => (
          <li key={c.code}>
            <Link href={href(c.code)} className="flex flex-col gap-0.5 rounded-md border border-line bg-surface px-3 py-2 text-start hover:border-primary-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus sm:flex-row sm:items-center sm:gap-3">
              <span dir="ltr" className="text-sm font-semibold text-heading">{c.code}</span>
              <span className="flex-1 text-sm text-body">{c.official_name ?? t("noOfficialName")}</span>
              <span className="text-xs text-muted">{t("candidateScore", { percent: Math.round(c.score * 100) })} · {t(`categoryBasis.${c.basis}`)}</span>
            </Link>
          </li>
        ))}
      </ul>
    </Alert>
  );
}

function PoolHealthPanel({ entry }: { entry: SupplierSearchResponse["pool_health"][number] | undefined }) {
  const t = useTranslations("marketProduct");
  const tm = useTranslations("analysis.market");
  if (!entry || entry.status !== "OK" || !entry.pool_health || !entry.concentration) return <Alert tone="info" appearance="inline" description={t("poolUnavailable")} />;
  const pool = entry.pool_health;
  const signal = entry.concentration.signal;
  const high = signal === "EXPANSION_RECOMMENDED";
  const headline = high ? t("poolHigh") : signal === "REVIEW_POOL" ? t("poolReview") : signal === "INSUFFICIENT_DATA" ? t("poolInsufficient") : t("poolHealthy");
  return (
    <Card><CardBody className="flex flex-col gap-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><h2 className="text-base font-semibold text-heading">{t("poolTitle")}</h2><p className="mt-1 text-sm text-body">{headline}</p></div>
        <div className="flex flex-wrap gap-2">
          <Badge color={pool.status === "VERY_HIGH" ? "danger" : pool.status === "HIGH" ? "warning" : "gray"}>{tm(`status.${pool.status}`)}</Badge>
          {high ? <Badge color="warning">{t("poolExpand")}</Badge> : null}
        </div>
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
        <span dir="ltr">OKPD2 {entry.okpd2}</span>
        <span>{t("poolObserved", { count: pool.observed_supplier_count })}</span><span>{t("poolWinners", { count: pool.winning_supplier_count })}</span>
        {pool.top1_share !== null ? <span>{t("poolTop1", { share: Math.round(pool.top1_share * 100) })}</span> : null}
        {pool.hhi !== null ? <span>HHI {pool.hhi.toFixed(2)}</span> : null}
      </div>
    </CardBody></Card>
  );
}

function ExportControl({ data }: { data: SupplierSearchResponse }) {
  const t = useTranslations("marketProduct");
  const links = data.integration.export_available
    ? data.integration.export_formats.map((format) => ({ format, url: supplierExportUrl(data.integration.export_url, format) })).filter((entry) => entry.url)
    : [];
  return (
    <Card><CardBody className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div><h2 className="text-sm font-semibold text-heading">{t("exportTitle")}</h2>{!links.length ? <p className="mt-1 text-xs text-muted">{t("exportWaiting")}</p> : null}</div>
      {links.length ? <div className="flex flex-wrap gap-2">{links.map(({ format, url }) => <Button key={format} asChild variant="secondary" size="sm"><a href={url!} download>{format === "json" ? t("exportJson") : t("exportCsv")}</a></Button>)}</div>
        : <Button disabled variant="secondary" size="sm">{t("exportTitle")}</Button>}
    </CardBody></Card>
  );
}
