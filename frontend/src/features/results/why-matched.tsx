"use client";

import { useLocale, useTranslations } from "next-intl";
import { CheckList } from "@/components/ui/check-list";
import { ContributionList } from "@/components/ui/contribution-list";
import { EvidenceItem } from "@/components/ui/evidence-item";
import type { Contribution, Evidence, ReasonCode, ReasonParams } from "@/lib/api/types";
import { fmtDate, toPct } from "@/lib/format";
import { evidenceColor, useVocab } from "../shared/use-vocab";

/**
 * Why-matched panel (P6-007, UF-05): contribution breakdown that sums to the displayed Match,
 * every reason code as text, and the top evidence with safe source links. Pure rendering of API data.
 */
export function WhyMatched({
  matchScore,
  contributions,
  reasonCodes,
  reasonParams,
  evidence,
  id,
}: {
  matchScore: number;
  contributions: Contribution[];
  reasonCodes: ReasonCode[];
  reasonParams: ReasonParams;
  evidence: Evidence[];
  id?: string;
}) {
  const t = useTranslations("results.why");
  return (
    <div id={id} className="grid grid-cols-1 gap-6 border-t border-line-subtle pt-5 lg:grid-cols-2">
      <section className="flex flex-col gap-3" aria-labelledby={id ? `${id}-contrib` : undefined}>
        <div className="flex flex-col gap-0.5">
          <h4 id={id ? `${id}-contrib` : undefined} className="text-sm font-medium text-heading">
            {t("contributions")}
          </h4>
          <p className="text-xs text-muted">{t("contributionsHint")}</p>
        </div>
        <Contributions contributions={contributions} matchScore={matchScore} />
      </section>
      <div className="flex flex-col gap-5">
        <section className="flex flex-col gap-3">
          <h4 className="text-sm font-medium text-heading">{t("reasons")}</h4>
          <Reasons codes={reasonCodes} params={reasonParams} />
        </section>
        <section className="flex flex-col gap-1">
          <h4 className="text-sm font-medium text-heading">{t("evidence")}</h4>
          <EvidenceList evidence={evidence} compact />
        </section>
      </div>
    </div>
  );
}

export function Contributions({ contributions, matchScore, highlight = [] }: { contributions: Contribution[]; matchScore: number; highlight?: string[] }) {
  const t = useTranslations("results.why");
  const v = useVocab();
  return (
    <ContributionList
      naLabel={t("notApplicable")}
      rows={contributions.map((c) => ({ key: c.feature, label: v.feature(c.feature), points: c.points, applicable: c.applicable, highlight: highlight.includes(c.feature) }))}
      total={{ label: t("total"), value: toPct(matchScore) ?? 0 }}
    />
  );
}

export function Reasons({ codes, params, size }: { codes: ReasonCode[]; params: ReasonParams; size?: "sm" | "default" }) {
  const v = useVocab();
  return <CheckList size={size} items={codes.map((c) => ({ key: c, label: v.reason(c, params), tone: c === "EXTERNAL_SUPPLIER" || c === "KNOWN_SUPPLIER" ? "neutral" : "positive" }))} />;
}

export function EvidenceList({ evidence, compact }: { evidence: Evidence[]; compact?: boolean }) {
  const t = useTranslations("results.why");
  const v = useVocab();
  const locale = useLocale();
  if (!evidence.length) return <p className="py-2 text-sm text-muted">{t("noEvidence")}</p>;
  return (
    <ul className={compact ? "flex flex-col divide-y divide-line-subtle" : "flex flex-col gap-3"}>
      {evidence.map((e) => (
        <li key={e.evidence_id}>
          <EvidenceItem
            compact={compact}
            type={v.evidenceType(e.evidence_type)}
            typeColor={evidenceColor(e.evidence_type)}
            claim={e.claim}
            sourceName={e.source_name}
            sourceUrl={e.source_url}
            noLinkLabel={t("internalSource")}
            observedLabel={t("observed", { date: fmtDate(e.observed_at) })}
            confidenceLabel={t("evidenceConfidence", { value: new Intl.NumberFormat(locale).format(toPct(e.confidence) ?? 0) })}
          />
        </li>
      ))}
    </ul>
  );
}
