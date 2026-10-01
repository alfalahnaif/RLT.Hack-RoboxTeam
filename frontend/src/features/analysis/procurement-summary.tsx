"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { CalendarClockIcon, ClipboardListIcon, SparklesIcon } from "@/components/icons";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { DescriptionList } from "@/components/ui/description-list";
import { IconChip } from "@/components/ui/metric-card";
import { ChevronDownIcon } from "@/components/ui/_glyphs";
import type { ProcurementAnalysis } from "@/lib/api/types";
import { fmtDate, fmtRub } from "@/lib/format";
import { cn } from "@/lib/utils";

/** A — compact procurement facts + the two separately labelled time references (historical cutoff vs external evidence check). */
export function ProcurementSummary({ analysis }: { analysis: ProcurementAnalysis }) {
  const t = useTranslations("analysis.summary");
  const [open, setOpen] = useState(false);
  const p = analysis.procurement;
  const codes = analysis.market_intelligence.map((e) => e.okpd2);

  return (
    <Card>
      <CardBody className="flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <IconChip tone="primary">
            <ClipboardListIcon />
          </IconChip>
          <div className="flex min-w-0 flex-col gap-1">
            <span className="text-xs text-muted">
              {t("title")} · <span dir="ltr">{p.lot_id}</span>
            </span>
            <h2 className="text-lg font-semibold text-heading">{p.subject ?? t("noSubject")}</h2>
          </div>
        </div>
        <DescriptionList
          columns={3}
          items={[
            { label: t("publishDate"), value: <span dir="ltr">{fmtDate(p.publish_date)}</span> },
            { label: t("customer"), value: p.customer_inn ? <span dir="ltr">{p.customer_inn}</span> : t("customerUnknown") },
            { label: t("platform"), value: t(`platforms.${p.platform}`) },
            { label: t("startPrice"), value: fmtRub(p.start_price) },
            { label: t("items"), value: p.items_total },
            {
              label: t("categories"),
              value: (
                <span className="flex flex-wrap gap-1.5">
                  {codes.map((c) => (
                    <Badge key={c} size="sm" color="gray" dir="ltr">
                      {c}
                    </Badge>
                  ))}
                </span>
              ),
            },
          ]}
        />
        {analysis.items_without_okpd2.length ? (
          <p className="text-xs text-warning-800">{t("itemsWithoutOkpd2", { count: analysis.items_without_okpd2.length })}</p>
        ) : null}
        {open ? (
          <ol className="flex flex-col divide-y divide-line-subtle rounded-md border border-line-subtle">
            {p.items.map((it) => (
              <li key={it.line_no} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-3 py-2 text-sm">
                <span className="w-6 text-xs text-muted">{it.line_no}</span>
                <span className="min-w-0 flex-1 text-heading">{it.product_name}</span>
                <span dir="ltr" className={cn("text-xs", it.okpd2_code ? "text-muted" : "text-warning-800")}>
                  {it.okpd2_code ?? t("noOkpd2")}
                </span>
              </li>
            ))}
          </ol>
        ) : null}
        <Button variant="link" className="self-start text-primary-700 hover:text-primary-800" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
          {open ? t("hideItems") : t("showItems")}
          <ChevronDownIcon className={cn("transition-transform", open && "rotate-180")} />
        </Button>
      </CardBody>
    </Card>
  );
}

/** The two time references are never merged: historical procurement cutoff vs. date the curated external evidence was checked. */
export function EvidenceTimeline({ analysis }: { analysis: ProcurementAnalysis }) {
  const t = useTranslations("analysis.timeline");
  const checked = analysis.market_intelligence
    .map((e) => e.data?.external_expansion.evidence_checked_at)
    .filter((d): d is string => Boolean(d))
    .sort()
    .at(-1);
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <div className="flex items-start gap-3 rounded-lg border border-line-subtle bg-surface p-3">
        <CalendarClockIcon className="mt-0.5 size-5 shrink-0 text-primary-700" aria-hidden />
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-medium text-heading">{t("historical", { date: fmtDate(analysis.market_intelligence_as_of) })}</span>
          <span className="text-xs text-muted">{t("historicalHint")}</span>
        </div>
      </div>
      <div className="flex items-start gap-3 rounded-lg border border-purple/30 bg-surface p-3">
        <SparklesIcon className="mt-0.5 size-5 shrink-0 text-purple" aria-hidden />
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-medium text-heading">{checked ? t("external", { date: fmtDate(checked) }) : t("externalNone")}</span>
          {checked ? <span className="text-xs text-muted">{t("externalHint")}</span> : null}
        </div>
      </div>
    </div>
  );
}
