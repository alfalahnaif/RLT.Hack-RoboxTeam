"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { BadgeStarIcon, BoxIcon, SparklesIcon, UsersIcon } from "@/components/icons";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { ContributionList } from "@/components/ui/contribution-list";
import { IconChip } from "@/components/ui/metric-card";
import { ScoreStat } from "@/components/ui/score";
import { ChevronDownIcon } from "@/components/ui/_glyphs";
import type { RankedSupplier, Recommendations } from "@/lib/api/types";
import { fmtDate, toPct } from "@/lib/format";
import { cn } from "@/lib/utils";
import { SupplierProfileLink } from "../supplier-360/profile-link";

const INITIAL_VISIBLE = 5;

/** B/C — ranked historical suppliers. Rendered exactly as the API ranked them; reasons are built from the structured fields. */
export function SupplierList({ data, procurementCodes }: { data: Recommendations | null; procurementCodes: string[] }) {
  const t = useTranslations("analysis.suppliers");
  const [all, setAll] = useState(false);

  if (!data)
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
        </CardHeader>
        <CardBody>
          <Alert tone="warning" appearance="inline" description={t("unavailable")} />
        </CardBody>
      </Card>
    );

  const shown = all ? data.results : data.results.slice(0, INITIAL_VISIBLE);
  return (
    <section id="suppliers" aria-labelledby="suppliers-title" className="flex scroll-mt-4 flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex items-center gap-3">
          <IconChip tone="primary">
            <UsersIcon />
          </IconChip>
          <div className="flex flex-col gap-0.5">
            <h2 id="suppliers-title" className="text-lg font-semibold text-heading">
              {t("title")}
            </h2>
            <p className="text-sm text-muted">{t("subtitle", { count: data.candidate_count, shown: Math.min(data.results.length, shown.length) })}</p>
          </div>
        </div>
      </div>
      {data.results.length === 0 ? (
        <Alert tone="default" appearance="inline" description={t("none")} />
      ) : (
        <ol className="flex flex-col gap-3">
          {shown.map((s) => (
            <li key={s.supplier_id}>
              <SupplierCard supplier={s} top={s.rank === 1} procurementCodes={procurementCodes} />
            </li>
          ))}
        </ol>
      )}
      {data.results.length > INITIAL_VISIBLE ? (
        <Button variant="secondary" size="sm" className="self-start" onClick={() => setAll((a) => !a)}>
          {all ? t("showLess", { count: INITIAL_VISIBLE }) : t("showAll", { count: data.results.length })}
        </Button>
      ) : null}
    </section>
  );
}

function headlineReasons(s: RankedSupplier, codes: string[], t: ReturnType<typeof useTranslations<"analysis.suppliers">>) {
  const out: string[] = [];
  if (s.best_products[0]) out.push(t("reasons.product", { name: s.best_products[0] }));
  // "Exact" when the supplier's best evidence code is one of this procurement's item codes (multi-item lots average the component).
  if (s.best_okpd2 && ((s.components.okpd2 ?? 0) >= 1 || codes.includes(s.best_okpd2))) out.push(t("reasons.okpd2Exact", { code: s.best_okpd2 }));
  else if (s.best_okpd2 && (s.components.okpd2 ?? 0) > 0) out.push(t("reasons.okpd2Related", { code: s.best_okpd2 }));
  out.push(
    s.relevant_ais_awards && s.relevant_awards
      ? t("reasons.awardsAis", { count: s.relevant_awards, ais: s.relevant_ais_awards })
      : t("reasons.awards", { count: s.relevant_awards }),
  );
  if (s.same_customer_history) out.push(t("reasons.sameCustomer"));
  return out;
}

function SupplierCard({ supplier: s, top, procurementCodes }: { supplier: RankedSupplier; top: boolean; procurementCodes: string[] }) {
  const t = useTranslations("analysis.suppliers");
  const [open, setOpen] = useState(false);
  const panelId = `why-${s.supplier_id}`;
  const reasons = headlineReasons(s, procurementCodes, t);
  const rows = Object.entries(s.components).map(([key]) => ({
    key,
    label: t.has(`components.${key}`) ? t(`components.${key}`) : key,
    points: Math.round((s.contributions[key] ?? 0) * 100),
    applicable: key in s.contributions,
  }));

  return (
    <Card className={cn(top && "border-primary-300")}>
      <CardBody className="flex flex-col gap-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-start">
          <div className="flex min-w-0 flex-1 flex-col gap-3">
            <div className="flex items-start gap-3">
              <span
                className={cn(
                  "flex size-10 shrink-0 items-center justify-center rounded-md border text-sm font-semibold",
                  top ? "border-primary-700 bg-primary-700 text-white" : "border-line-subtle bg-surface-subtle text-heading",
                )}
              >
                {s.rank}
              </span>
              <div className="flex min-w-0 flex-col gap-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-base font-medium text-heading">
                    {t("inn")} <span dir="ltr">{s.supplier_inn}</span>
                  </h3>
                  {top ? (
                    <Badge color="primary" appearance="solid" size="sm">
                      <BadgeStarIcon aria-hidden />
                      {t("top")}
                    </Badge>
                  ) : null}
                </div>
                <span className="text-xs text-muted">{t("nameUnavailable")}</span>
              </div>
            </div>
            <ul className="flex flex-col gap-1.5">
              {reasons.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-body">
                  {i === 0 ? <BoxIcon className="mt-0.5 size-4 shrink-0 text-muted" aria-hidden /> : <span aria-hidden className="mt-2 size-1.5 shrink-0 rounded-full bg-primary-600 mx-[5px]" />}
                  <span className="min-w-0">{r}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="shrink-0 rounded-lg border border-line-subtle bg-surface-subtle p-4 md:w-52">
            <ScoreStat label={t("score")} value={toPct(s.score)} />
          </div>
        </div>

        {open ? (
          <div id={panelId} className="flex flex-col gap-4 rounded-lg border border-line-subtle bg-surface-subtle p-4">
            <ul className="flex flex-col gap-1.5 text-sm text-body">
              <li>{t("reasons.lots", { count: s.relevant_lots })}</li>
              {s.relevant_em_participations ? <li>{t("reasons.em", { count: s.relevant_em_participations })}</li> : null}
              <li>{t("reasons.recent", { date: fmtDate(s.most_recent_relevant) })}</li>
            </ul>
            <div className="flex flex-col gap-2">
              <span className="text-sm font-medium text-heading">{t("breakdown")}</span>
              <ContributionList rows={rows} naLabel={t("notApplicable")} total={{ label: t("score"), value: toPct(s.score) ?? 0 }} />
            </div>
            {s.evidence_lot_ids.length ? (
              <p className="text-xs text-muted">
                {t("evidenceLots")}: <span dir="ltr">{s.evidence_lot_ids.join(", ")}</span>
              </p>
            ) : null}
            {s.semantic_evidence.length ? <SemanticEvidence supplier={s} /> : null}
          </div>
        ) : null}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line-subtle pt-3">
          <Button variant="link" className="text-primary-700 hover:text-primary-800" aria-expanded={open} aria-controls={panelId} onClick={() => setOpen((o) => !o)}>
            {open ? t("hideWhy") : t("why")}
            <ChevronDownIcon className={cn("transition-transform", open && "rotate-180")} />
          </Button>
          <SupplierProfileLink inn={s.supplier_inn} />
        </div>
      </CardBody>
    </Card>
  );
}

/** Secondary, collapsed by default: semantic retrieval provenance (text, cosine, lot, date, OKPD2) — never the headline reason. */
function SemanticEvidence({ supplier }: { supplier: RankedSupplier }) {
  const t = useTranslations("analysis.suppliers.semantic");
  return (
    <Accordion type="single" collapsible variant="flush" className="rounded-md border border-line bg-surface pt-3">
      <AccordionItem value="semantic">
        <AccordionTrigger icon={<SparklesIcon />}>{t("title")}</AccordionTrigger>
        <AccordionContent className="flex flex-col gap-3">
          <p className="text-xs text-muted">{t("hint")}</p>
          <ul className="flex flex-col gap-2">
            {supplier.semantic_evidence.map((e) => (
              <li key={`${e.lot_id}-${e.product}`} className="flex flex-col gap-1 rounded-md border border-line-subtle p-3">
                <span className="text-sm text-heading">«{e.product}»</span>
                <span className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted">
                  <span dir="ltr">{t("similarity", { value: e.cosine.toFixed(2) })}</span>
                  <span>{t("lot", { lot: e.lot_id })}</span>
                  <span dir="ltr">{fmtDate(e.publish_date)}</span>
                  {e.okpd2 ? <span dir="ltr">{t("okpd2", { code: e.okpd2 })}</span> : null}
                  {e.discovered_only_by_semantic ? <span>{t("onlySemantic")}</span> : null}
                </span>
              </li>
            ))}
          </ul>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
