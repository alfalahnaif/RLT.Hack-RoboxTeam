"use client";

import { useLocale, useTranslations } from "next-intl";
import { BoxIcon, SparklesIcon, UsersIcon } from "@/components/icons";
import { Card } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { StackedBar, type StackedSegment } from "@/components/ui/stacked-bar";
import type { SearchResponse, SupplierType } from "@/lib/api/types";
import { useVocab } from "../shared/use-vocab";

const TYPE_TONE: Record<SupplierType, StackedSegment["tone"]> = {
  manufacturer: "primary",
  distributor: "info",
  supplier: "success",
  service_provider: "purple",
  unknown: "gray",
};

/** S-02 summary: suppliers found, new-to-AIS (market expansion, FR-17), known, offering candidates, types. */
export function MarketSummary({ run }: { run: SearchResponse }) {
  const t = useTranslations("results.summary");
  const v = useVocab();
  const locale = useLocale();
  const n = (x: number) => new Intl.NumberFormat(locale).format(x);
  const s = run.market_summary;
  if (!s) return null;
  const total = s.known + s.external;
  const segments = (Object.keys(TYPE_TONE) as SupplierType[])
    .filter((k) => (s.by_type[k] ?? 0) > 0)
    .map((k) => ({ key: k, label: v.supplierType(k), value: s.by_type[k] ?? 0, tone: TYPE_TONE[k] }));

  return (
    <section aria-label={t("label")} className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <MetricCard label={t("suppliers")} value={n(total)} icon={<UsersIcon />} trend={<span className="text-xs text-muted">{t("candidates", { count: run.total_candidates })}</span>} />
      <MetricCard
        label={t("external")}
        value={n(s.external)}
        icon={<SparklesIcon />}
        className="border-purple/20"
        trend={<span className="text-xs text-muted">{total ? t("share", { value: Math.round((s.external / total) * 100) }) : t("none")}</span>}
      />
      <MetricCard label={t("known")} value={n(s.known)} icon={<BoxIcon />} trend={<span className="text-xs text-muted">{t("knownHint")}</span>} />
      <Card variant="panel" className="col-span-2 gap-3 p-4 sm:p-5 lg:col-span-1">
        <span className="text-sm text-body">{t("byType")}</span>
        {segments.length ? <StackedBar segments={segments} legend="inline" size="sm" /> : <span className="text-sm text-muted">{t("none")}</span>}
      </Card>
    </section>
  );
}
