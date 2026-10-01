"use client";

import { useLocale, useTranslations } from "next-intl";
import { HistoryIcon, PieChartIcon, SparklesIcon, VerifiedIcon, WarningTriangleIcon } from "@/components/icons";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody } from "@/components/ui/card";
import { EvidenceItem } from "@/components/ui/evidence-item";
import { IconChip } from "@/components/ui/metric-card";
import { Progress } from "@/components/ui/progress";
import { Tooltip } from "@/components/ui/tooltip";
import type {
  ExpansionSignal,
  ExternalCandidate,
  HistoricalAlternative,
  MarketIntelligence,
  MarketIntelligenceEntry,
  PoolStatus,
  ProcurementItem,
} from "@/lib/api/types";
import { fmtDate } from "@/lib/format";
import { cn } from "@/lib/utils";

const STATUS_TONE: Record<PoolStatus, "danger" | "warning" | "primary" | "success" | "gray"> = {
  VERY_HIGH: "danger",
  HIGH: "warning",
  MODERATE: "primary",
  LOW: "success",
  INSUFFICIENT_DATA: "gray",
};
const SIGNAL_ORDER: Record<ExpansionSignal, number> = { EXPANSION_RECOMMENDED: 0, REVIEW_POOL: 1, INSUFFICIENT_DATA: 2, NO_EXPANSION_SIGNAL: 3 };

/** Display order only (the API order is by code): categories that need attention first, then by code. */
export function prioritized(entries: MarketIntelligenceEntry[]) {
  const rank = (e: MarketIntelligenceEntry) =>
    e.data ? (e.data.external_expansion.available ? -1 : SIGNAL_ORDER[e.data.concentration.signal]) : 4;
  return [...entries].sort((a, b) => rank(a) - rank(b) || a.okpd2.localeCompare(b.okpd2));
}

/** D/E/F — one accordion item per OKPD2: pool health, historical alternatives, external market expansion. */
export function MarketSection({ entries, items }: { entries: MarketIntelligenceEntry[]; items: ProcurementItem[] }) {
  const t = useTranslations("analysis.market");
  const ordered = prioritized(entries);
  const defaultOpen = ordered
    .filter((e, i) => i === 0 || e.data?.concentration.signal === "EXPANSION_RECOMMENDED" || e.data?.external_expansion.available)
    .map((e) => e.okpd2);
  const names = (lines: number[]) => lines.map((l) => items.find((i) => i.line_no === l)?.product_name).filter(Boolean) as string[];

  return (
    <section id="market" aria-labelledby="market-title" className="flex scroll-mt-4 flex-col gap-4">
      <div className="flex items-center gap-3">
        <IconChip tone="primary">
          <PieChartIcon />
        </IconChip>
        <div className="flex flex-col gap-0.5">
          <h2 id="market-title" className="text-lg font-semibold text-heading">
            {t("title")}
          </h2>
          <p className="text-sm text-muted">{t("subtitle")}</p>
        </div>
      </div>
      <Accordion type="multiple" defaultValue={defaultOpen} className="flex flex-col gap-3">
        {ordered.map((e) => (
          <AccordionItem key={e.okpd2} value={e.okpd2} className="rounded-xl border border-line-subtle bg-surface shadow-card">
            <AccordionTrigger
              className="rounded-xl"
              extra={
                e.data ? (
                  <span className="hidden flex-wrap items-center gap-2 sm:flex">
                    <Badge size="sm" color={STATUS_TONE[e.data.pool_health.status]}>
                      {t(`status.${e.data.pool_health.status}`)}
                    </Badge>
                    {e.data.concentration.signal === "EXPANSION_RECOMMENDED" ? (
                      <Badge size="sm" color="purple">
                        {t("signal.EXPANSION_RECOMMENDED")}
                      </Badge>
                    ) : null}
                  </span>
                ) : (
                  <Badge size="sm" color="warning">
                    {t("unavailable")}
                  </Badge>
                )
              }
            >
              <span className="flex min-w-0 flex-col gap-0.5">
                <span dir="ltr" className="w-fit text-sm font-semibold text-heading">
                  {e.okpd2}
                </span>
                <span className="line-clamp-1 text-xs font-normal text-muted">
                  {t("items", { count: e.item_lines.length, lines: e.item_lines.join(", ") })} · {names(e.item_lines).join("; ")}
                </span>
              </span>
            </AccordionTrigger>
            <AccordionContent className="flex flex-col gap-4 rounded-b-xl">
              {e.data ? (
                <CategoryBody data={e.data} />
              ) : (
                <Alert tone="warning" appearance="inline" description={t("unavailable")} />
              )}
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </section>
  );
}

function CategoryBody({ data }: { data: MarketIntelligence }) {
  return (
    <>
      <PoolHealthPanel data={data} />
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <AlternativesPanel alternatives={data.historical_alternatives} total={data.pool_health.alternative_supplier_count} />
        <ExternalPanel data={data} />
      </div>
    </>
  );
}

function PoolHealthPanel({ data }: { data: MarketIntelligence }) {
  const t = useTranslations("analysis.market");
  const locale = useLocale();
  const p = data.pool_health;
  const tone = STATUS_TONE[p.status];
  const pct = (x: number | null) => (x === null ? "—" : `${Math.round(x * 100)}%`);
  const n = (x: number) => new Intl.NumberFormat(locale).format(x);
  const metrics: { key: string; value: string; hint?: string }[] = [
    { key: "lots", value: n(p.lot_count) },
    { key: "awards", value: n(p.award_count) },
    { key: "observed", value: n(p.observed_supplier_count) },
    { key: "winners", value: n(p.winning_supplier_count) },
    { key: "top3", value: pct(p.top3_share) },
    { key: "hhi", value: p.hhi === null ? "—" : p.hhi.toFixed(2), hint: t("hhiHint") },
  ];

  return (
    <div
      className={cn(
        "flex flex-col gap-4 rounded-lg border p-4",
        tone === "danger" ? "border-danger-300 bg-danger-50" : tone === "warning" ? "border-warning-300 bg-warning-50" : "border-line-subtle bg-surface-subtle",
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <IconChip tone={tone}>
            {tone === "danger" || tone === "warning" ? <WarningTriangleIcon /> : <PieChartIcon />}
          </IconChip>
          <div className="flex flex-col gap-0.5">
            <span className="text-base font-semibold text-heading">{t(`headline.${p.status}`)}</span>
            <span className="text-xs text-muted">{t(`status.${p.status}`)}</span>
          </div>
        </div>
        <Badge color={data.concentration.signal === "EXPANSION_RECOMMENDED" ? "purple" : data.concentration.signal === "REVIEW_POOL" ? "warning" : "gray"} size="md">
          {t(`signal.${data.concentration.signal}`)}
        </Badge>
      </div>
      {p.top1_share !== null ? (
        <div className="flex flex-col gap-2">
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-sm text-body">{t("metrics.top1")}</span>
            <span dir="ltr" className="text-xl font-semibold text-heading">
              {pct(p.top1_share)}
            </span>
          </div>
          <Progress value={Math.round(p.top1_share * 100)} tone={tone === "danger" ? "danger" : tone === "warning" ? "warning" : "primary"} label={t("metrics.top1")} />
          <span className="text-xs text-subtle">{t("top1Explain", { share: Math.round(p.top1_share * 100) })}</span>
        </div>
      ) : null}
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {metrics.map((m) => (
          <div key={m.key} className="flex flex-col gap-1 rounded-md border border-line-subtle bg-surface p-3">
            <dt className="text-xs text-muted">
              {m.hint ? (
                <Tooltip content={m.hint}>
                  <span tabIndex={0} className="cursor-help underline decoration-dotted underline-offset-2 outline-none">
                    {t(`metrics.${m.key}`)}
                  </span>
                </Tooltip>
              ) : (
                t(`metrics.${m.key}`)
              )}
            </dt>
            <dd dir="ltr" className="w-fit text-base font-semibold text-heading">
              {m.value}
            </dd>
          </div>
        ))}
      </dl>
      <p className="text-xs text-muted">{t("caveat")}</p>
    </div>
  );
}

function AlternativesPanel({ alternatives, total }: { alternatives: HistoricalAlternative[]; total: number }) {
  const t = useTranslations("analysis.alternatives");
  return (
    <Card variant="outlined">
      <CardBody className="flex flex-col gap-3">
        <div className="flex items-start gap-2">
          <HistoryIcon className="mt-0.5 size-5 shrink-0 text-muted" aria-hidden />
          <div className="flex flex-col gap-0.5">
            <h3 className="text-base font-medium text-heading">{t("title")}</h3>
            <p className="text-xs text-muted">{t("subtitle")}</p>
          </div>
        </div>
        {alternatives.length ? (
          <>
            <ul className="flex flex-col divide-y divide-line-subtle">
              {alternatives.map((a) => (
                <li key={a.supplier_id} className="flex flex-col gap-0.5 py-2">
                  <span dir="ltr" className="w-fit text-sm font-medium text-heading">
                    {a.supplier_inn ?? "—"}
                  </span>
                  <span className="text-xs text-muted">
                    {t("awards", { count: a.historical_award_count })} · {t("relations", { count: a.observed_relation_count })} ·{" "}
                    {a.is_winner_in_category ? t("winner") : t("participant")}
                  </span>
                </li>
              ))}
            </ul>
            {total > alternatives.length ? <span className="text-xs text-muted">{t("total", { shown: alternatives.length, total })}</span> : null}
          </>
        ) : (
          <p className="text-sm text-muted">{t("none")}</p>
        )}
      </CardBody>
    </Card>
  );
}

function ExternalPanel({ data }: { data: MarketIntelligence }) {
  const t = useTranslations("analysis.external");
  const x = data.external_expansion;
  return (
    <Card variant="outlined" className="border-purple/30">
      <CardBody className="flex flex-col gap-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex items-start gap-2">
            <SparklesIcon className="mt-0.5 size-5 shrink-0 text-purple" aria-hidden />
            <div className="flex flex-col gap-0.5">
              <h3 className="text-base font-medium text-heading">{t("title")}</h3>
              <p className="text-xs text-muted">{t("subtitle")}</p>
            </div>
          </div>
          {x.available ? (
            <Badge color="purple" size="md">
              {t("counts", { verified: x.verified_count, review: x.under_review_count })}
            </Badge>
          ) : null}
        </div>
        {x.available ? (
          <>
            {x.evidence_checked_at ? (
              <p className="text-xs text-muted">
                {t("retrieved", { date: fmtDate(x.evidence_checked_at) })} · {t("disclaimer")}
              </p>
            ) : null}
            <ul className="flex flex-col gap-3">
              {x.candidates.map((c) => (
                <li key={c.supplier_inn}>
                  <CandidateCard c={c} />
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="text-sm text-muted">{t("notAvailable")}</p>
        )}
      </CardBody>
    </Card>
  );
}

function CandidateCard({ c }: { c: ExternalCandidate }) {
  const t = useTranslations("analysis.external");
  const label = (ns: string, key: string) => (t.has(`${ns}.${key}`) ? t(`${ns}.${key}`) : key.replaceAll("_", " ").toLowerCase());
  const verified = c.verification_status === "VERIFIED";
  return (
    <Card variant="internal" className={cn("gap-3", verified ? "border-success-300" : c.verification_status === "UNDER_REVIEW" ? "border-warning-300" : "")}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex min-w-0 flex-col gap-1">
          <span className="text-sm font-semibold text-heading">{c.company_name}</span>
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
            <span>{t("inn", { inn: c.supplier_inn })}</span>
            <span>· {label("role", c.market_role)}</span>
            <span>· {label("strength", c.verification_strength)}</span>
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge size="sm" color="purple">
            {label("reconciliation", c.reconciliation_status)}
          </Badge>
          <Badge size="md" appearance="solid" color={verified ? "success" : c.verification_status === "UNDER_REVIEW" ? "warning" : "gray"}>
            {verified ? <VerifiedIcon aria-hidden /> : <WarningTriangleIcon aria-hidden />}
            {label("status", c.verification_status)}
          </Badge>
        </div>
      </div>
      {c.verification_reason_codes.length ? (
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-heading">{t("reasons")}</span>
          <ul className="flex flex-wrap gap-1.5">
            {c.verification_reason_codes.map((r) => (
              <li key={r}>
                <Badge size="sm" color="success">
                  {label("code", r)}
                </Badge>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {c.review_reasons.length ? (
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-heading">{t("review")}</span>
          <ul className="flex flex-wrap gap-1.5">
            {c.review_reasons.map((r) => (
              <li key={r}>
                <Badge size="sm" color="warning">
                  {label("code", r)}
                </Badge>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="text-xs text-muted">{c.exact_okpd2_asserted_by_source ? t("exactOkpd2Yes") : t("exactOkpd2No")}</p>
      <Accordion type="single" collapsible variant="flush" className="-mx-3 border-t border-line-subtle pt-3">
        <AccordionItem value="evidence">
          <AccordionTrigger>{t("evidence", { count: c.evidence_count })}</AccordionTrigger>
          <AccordionContent className="flex flex-col gap-2">
            {c.evidence_summary.map((ev, i) => (
              <EvidenceItem
                key={`${ev.source_record_id ?? ev.source_url ?? i}-${i}`}
                type={label("evidenceType", ev.evidence_type)}
                typeColor={ev.evidence_type === "CONFORMITY_DECLARATION" ? "primary" : "gray"}
                claim={ev.product_scope.length ? ev.product_scope.join("; ") : label("role", c.market_role)}
                sourceName={ev.source_name}
                sourceUrl={ev.source_url}
                observedLabel={`${t("retrieved", { date: fmtDate(ev.retrieved_at) })} · ${label("evidenceStatus", ev.evidence_status)}${ev.valid_until ? ` · ${t("validUntil", { date: fmtDate(ev.valid_until) })}` : ""}`}
                confidenceLabel={label("strength", ev.verification_strength)}
              />
            ))}
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </Card>
  );
}
