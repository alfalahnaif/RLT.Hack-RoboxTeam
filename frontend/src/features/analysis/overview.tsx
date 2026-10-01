"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { PieChartIcon, SparklesIcon, UsersIcon } from "@/components/icons";
import { Card } from "@/components/ui/card";
import { IconChip } from "@/components/ui/metric-card";
import type { ProcurementAnalysis } from "@/lib/api/types";

/** Story at a glance: suppliers → concentrated categories → external candidates. Counts are read from the response only. */
export function AnalysisOverview({ analysis }: { analysis: ProcurementAnalysis }) {
  const t = useTranslations("analysis.overview");
  const rec = analysis.recommendations.data;
  const mi = analysis.market_intelligence.filter((e) => e.data);
  const concentrated = mi.filter((e) => e.data!.pool_health.status === "VERY_HIGH" || e.data!.pool_health.status === "HIGH");
  const external = mi.filter((e) => e.data!.external_expansion.available);
  const verified = external.reduce((n, e) => n + e.data!.external_expansion.verified_count, 0);
  const review = external.reduce((n, e) => n + e.data!.external_expansion.under_review_count, 0);

  return (
    <section className="grid gap-4 md:grid-cols-3">
      <Tile
        href="#suppliers"
        jump={t("jump")}
        icon={<UsersIcon />}
        tone="primary"
        label={t("suppliers")}
        value={rec ? t("suppliersValue", { count: rec.candidate_count }) : "—"}
        hint={rec?.results[0] ? t("suppliersHint", { inn: rec.results[0].supplier_inn }) : t("suppliersNone")}
      />
      <Tile
        href="#market"
        jump={t("jump")}
        icon={<PieChartIcon />}
        tone={concentrated.length ? "danger" : "success"}
        label={t("concentrated")}
        value={String(concentrated.length)}
        hint={
          concentrated.length ? (
            <>
              <span dir="ltr">{concentrated.map((e) => e.okpd2).join(", ")}</span> · {t("concentratedHint", { total: analysis.market_intelligence.length })}
            </>
          ) : (
            t("concentratedNone", { total: analysis.market_intelligence.length })
          )
        }
      />
      <Tile
        href="#market"
        jump={t("jump")}
        icon={<SparklesIcon />}
        tone="purple"
        label={t("external")}
        value={external.length ? t("externalValue", { verified }) : "—"}
        hint={external.length ? t("externalHint", { review, codes: external.map((e) => e.okpd2).join(", ") }) : t("externalNone")}
      />
    </section>
  );
}

function Tile({
  href,
  jump,
  icon,
  tone,
  label,
  value,
  hint,
}: {
  href: string;
  jump: string;
  icon: ReactNode;
  tone: "primary" | "danger" | "success" | "purple";
  label: string;
  value: string;
  hint: ReactNode;
}) {
  return (
    <Card variant="panel" className="p-0">
      <a
        href={href}
        aria-label={`${label} · ${jump}`}
        className="flex h-full flex-col gap-3 rounded-xl p-4 outline-none transition-colors hover:bg-surface-subtle focus-visible:ring-4 focus-visible:ring-primary-600/15 sm:p-5"
      >
        <div className="flex items-start justify-between gap-3">
          <span className="text-sm text-body">{label}</span>
          {tone === "purple" ? (
            <span className="flex size-9 shrink-0 items-center justify-center rounded-full border border-purple/20 bg-purple-light text-purple [&_svg]:size-[18px]">{icon}</span>
          ) : (
            <IconChip tone={tone}>{icon}</IconChip>
          )}
        </div>
        <span className="text-2xl font-semibold tracking-tight text-heading">{value}</span>
        <span className="text-xs text-muted">{hint}</span>
      </a>
    </Card>
  );
}
