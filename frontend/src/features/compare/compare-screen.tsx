"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { CloseIcon, ScalesIcon } from "@/components/icons";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { CompareCell, CompareHeadCell, CompareHeadRow, CompareRow, CompareSection, CompareTable } from "@/components/ui/compare-table";
import { EmptyState } from "@/components/ui/empty-state";
import { ExternalLink } from "@/components/ui/external-link";
import { PageHeader } from "@/components/ui/page-header";
import { ScoreStat } from "@/components/ui/score";
import { Tooltip } from "@/components/ui/tooltip";
import { confidenceTone, UI_CONFIG } from "@/config/ui";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api/client";
import type { RankingFeature, SearchResponse, SearchResult, SupplierProfile } from "@/lib/api/types";
import { toPct } from "@/lib/format";
import { useAsync } from "@/lib/use-async";
import { ErrorPanel } from "../shared/error-panel";
import { PageSkeleton } from "../shared/skeletons";
import { MarketBadge, RiskBadges, TypeBadge } from "../shared/supplier-badges";
import { useVocab } from "../shared/use-vocab";
import { useSession } from "../shell/session-store";

type Column = { id: string; result: SearchResult | null; profile: SupplierProfile };
type Data = { run: SearchResponse | null; columns: Column[] };

/** Largest spread across columns → the features that best explain "why A above B" (US-07). */
const HIGHLIGHTS = 2;

/** S-04 Compare 2–5 suppliers from ONE search (EC-43). Missing values show "—" with a reason, never 0. */
export function CompareScreen() {
  const t = useTranslations("compare");
  const { tray, ready } = useSession();
  const key = `${tray.requestId}:${tray.ids.join(",")}`;
  const data = useAsync<Data>(async () => {
    if (tray.ids.length < UI_CONFIG.compareMin) return { run: null, columns: [] };
    const run = tray.requestId ? await api.getSearch(tray.requestId).catch(() => null) : null;
    const profiles = await Promise.all(tray.ids.map((id) => api.getSupplier(id, tray.requestId)));
    return {
      run,
      columns: profiles.map((profile, i) => ({ id: tray.ids[i], profile, result: run?.results.find((r) => r.supplier_id === tray.ids[i]) ?? null })),
    };
  }, [key]);

  const back = tray.requestId ? `/results/${tray.requestId}` : "/search";

  if (!ready)
    return (
      <>
        <PageHeader title={t("title")} description={t("subtitle", { max: UI_CONFIG.compareMax })} />
        <PageSkeleton blocks={1} />
      </>
    );

  if (tray.ids.length < UI_CONFIG.compareMin)
    return (
      <>
        <PageHeader title={t("title")} description={t("subtitle", { max: UI_CONFIG.compareMax })} />
        <Card>
          <EmptyState
            icon={<ScalesIcon />}
            title={tray.ids.length ? t("needMore.title", { min: UI_CONFIG.compareMin }) : t("empty.title")}
            description={t("empty.text", { min: UI_CONFIG.compareMin, max: UI_CONFIG.compareMax })}
            actions={
              <Button asChild>
                <Link href={back}>{tray.requestId ? t("backToResults") : t("toSearch")}</Link>
              </Button>
            }
          />
        </Card>
      </>
    );

  return (
    <>
      <PageHeader
        title={t("title")}
        description={t("subtitle", { max: UI_CONFIG.compareMax })}
        backHref={back}
        actions={
          <Button asChild variant="secondary">
            <Link href={back}>{t("backToResults")}</Link>
          </Button>
        }
      />
      {data.status === "loading" ? <PageSkeleton blocks={1} /> : data.status === "error" ? <ErrorPanel error={data.error} onRetry={data.reload} /> : <CompareView data={data.data} />}
    </>
  );
}

function CompareView({ data }: { data: Data }) {
  const t = useTranslations("compare");
  const v = useVocab();
  const { remove } = useSession();
  const { run, columns } = data;
  const cols = [...columns].sort((a, b) => (a.result?.rank ?? 999) - (b.result?.rank ?? 999));
  const span = cols.length + 1;

  const features: RankingFeature[] = cols.find((c) => c.result)?.result?.contributions.map((c) => c.feature) ?? [];
  const spread = (f: RankingFeature) => {
    const pts = cols.map((c) => c.result?.contributions.find((x) => x.feature === f)).filter((x) => x?.applicable).map((x) => x!.points);
    return pts.length > 1 ? Math.max(...pts) - Math.min(...pts) : 0;
  };
  const highlighted = features
    .filter((f) => spread(f) > 0)
    .sort((a, b) => spread(b) - spread(a))
    .slice(0, HIGHLIGHTS);

  const [a, b] = cols;
  const leadReasons = a?.result && b?.result ? highlighted.filter((f) => (pts(a.result!, f) ?? 0) > (pts(b.result!, f) ?? 0)) : [];

  const unknown = (reason: string) => (
    <Tooltip content={reason}>
      <span tabIndex={0} className="cursor-help text-muted underline decoration-dotted underline-offset-4 outline-none focus-visible:ring-4 focus-visible:ring-primary-600/15">
        —<span className="sr-only">: {reason}</span>
      </span>
    </Tooltip>
  );

  const row = (label: ReactNode, render: (c: Column) => ReactNode, opts: { highlight?: boolean } = {}) => (
    <CompareRow label={label} highlight={opts.highlight} highlightLabel={t("bigDifference")}>
      {cols.map((c) => (
        <CompareCell key={c.id}>{render(c)}</CompareCell>
      ))}
    </CompareRow>
  );

  return (
    <div className="flex min-w-0 flex-col gap-5">
      {!run ? <Alert tone="warning" appearance="inline" title={t("noContext.title")} description={t("noContext.text")} /> : null}
      {a?.result && b?.result && leadReasons.length ? (
        <Alert
          tone="info"
          title={t("why.title", { a: a.profile.legal_name, b: b.profile.legal_name })}
          description={t("why.text", { features: leadReasons.map((f) => v.feature(f).toLowerCase()).join(t("why.and")) })}
        />
      ) : null}

      <CompareTable aria-label={t("tableLabel")}>
        <CompareHeadRow label={run ? t("forQuery", { query: run.query }) : t("suppliers")}>
          {cols.map((c) => (
            <CompareHeadCell key={c.id}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex min-w-0 flex-col gap-1">
                  {c.result ? <span className="text-xs font-normal text-muted">{t("rank", { rank: c.result.rank })}</span> : null}
                  <Link href={`/suppliers/${c.id}${run ? `?request_id=${run.request_id}` : ""}`} className="rounded-xs text-sm font-medium text-heading outline-none hover:text-primary-700 focus-visible:ring-4 focus-visible:ring-primary-600/15">
                    {c.profile.legal_name}
                  </Link>
                </div>
                <Button variant="ghost" size="icon" className="-me-2 -mt-1.5 size-8 min-w-8" aria-label={t("remove", { name: c.profile.legal_name })} title={t("remove", { name: c.profile.legal_name })} onClick={() => remove(c.id)}>
                  <CloseIcon />
                </Button>
              </div>
            </CompareHeadCell>
          ))}
        </CompareHeadRow>
        <tbody>
          <CompareSection label={t("sections.scores")} colSpan={span} />
          {row(t("rows.match"), (c) => (c.result ? <ScoreStat label={<span className="sr-only">{t("rows.match")}</span>} value={toPct(c.result.match_score)} size="sm" /> : unknown(t("noScore"))))}
          {row(t("rows.confidence"), (c) => {
            const conf = c.result?.confidence_score ?? c.profile.confidence_score;
            return conf === null ? unknown(t("noConfidence")) : <ScoreStat label={<span className="sr-only">{t("rows.confidence")}</span>} value={toPct(conf)} tone={confidenceTone(conf)} size="sm" />;
          })}

          <CompareSection label={t("sections.supplier")} colSpan={span} />
          {row(t("rows.type"), (c) => <TypeBadge type={c.profile.supplier_type} verified={Boolean(c.profile.supplier_type_basis)} size="sm" />)}
          {row(t("rows.market"), (c) => <MarketBadge known={c.profile.is_known_supplier} size="sm" />)}
          {row(t("rows.region"), (c) => c.profile.region_name ?? unknown(t("noRegion")))}
          {row(t("rows.status"), (c) => (c.profile.legal_status === "unknown" ? unknown(t("noStatus")) : v.legalStatus(c.profile.legal_status)))}
          {row(t("rows.contracts"), (c) => {
            if (!run) return unknown(t("noContextValue"));
            const n = c.profile.procurement_history.filter((h) => h.relevant).length;
            return n ? t("contracts", { count: n }) : <span className="text-muted">{t("noContracts")}</span>;
          })}
          {row(t("rows.evidence"), (c) => {
            const ev = c.profile.evidence.find((e) => e.evidence_type === "MANUFACTURER_REGISTRY" || e.evidence_type === "PRODUCT_CATALOG");
            if (!ev) return unknown(t("noEvidence"));
            return (
              <span className="flex flex-col gap-0.5">
                <span>{v.evidenceType(ev.evidence_type)}</span>
                {ev.source_url ? (
                  <ExternalLink href={ev.source_url} className="text-xs">
                    {ev.source_name}
                  </ExternalLink>
                ) : (
                  <span className="text-xs text-muted">{ev.source_name}</span>
                )}
              </span>
            );
          })}
          {row(t("rows.risks"), (c) => (c.profile.risk_flags.length ? <RiskBadges flags={c.profile.risk_flags} /> : <span className="text-muted">{t("noRisks")}</span>))}

          {run && features.length ? (
            <>
              <CompareSection label={t("sections.contributions")} colSpan={span} />
              {features.map((f) =>
                row(
                  v.feature(f),
                  (c) => {
                    const x = c.result?.contributions.find((y) => y.feature === f);
                    if (!x) return unknown(t("noScore"));
                    if (!x.applicable) return <span className="text-muted">{t("notApplicable")}</span>;
                    return (
                      <span className="font-medium" dir="ltr">
                        +{x.points}
                      </span>
                    );
                  },
                  { highlight: highlighted.includes(f) },
                ),
              )}
            </>
          ) : null}
        </tbody>
      </CompareTable>
      <p className="text-xs text-muted">{t("footnote")}</p>
    </div>
  );
}

const pts = (r: SearchResult, f: RankingFeature) => {
  const x = r.contributions.find((c) => c.feature === f);
  return x?.applicable ? x.points : null;
};
