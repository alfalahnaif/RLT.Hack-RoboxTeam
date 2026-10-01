"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { BoxIcon, BuildingIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { CheckboxLabel } from "@/components/ui/checkbox";
import { ScoreStat } from "@/components/ui/score";
import { ChevronDownIcon } from "@/components/ui/_glyphs";
import { confidenceTone } from "@/config/ui";
import { Link } from "@/i18n/navigation";
import type { SearchResult } from "@/lib/api/types";
import { toPct } from "@/lib/format";
import { cn } from "@/lib/utils";
import { FeedbackControl } from "../shared/feedback-control";
import { MarketBadge, RiskBadges, TypeBadge } from "../shared/supplier-badges";
import { Reasons, WhyMatched } from "./why-matched";

const VISIBLE_REASONS = 4;

/** S-02 result card: identity, Match & Confidence kept separate (BR-02), top reasons, risk flags, actions. */
export function ResultCard({
  result,
  requestId,
  selected,
  onToggleCompare,
}: {
  result: SearchResult;
  requestId: string;
  selected: boolean;
  onToggleCompare: () => void;
}) {
  const t = useTranslations("results.card");
  const [open, setOpen] = useState(false);
  const panelId = `why-${result.supplier_id}`;
  const profileHref = `/suppliers/${result.supplier_id}?request_id=${requestId}`;
  const reasons = result.reason_codes.filter((c) => c !== "KNOWN_SUPPLIER" && c !== "EXTERNAL_SUPPLIER");

  return (
    <Card className={cn("transition-colors", selected && "border-primary-300")} aria-labelledby={`name-${result.supplier_id}`}>
      <CardBody className="flex flex-col gap-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-start">
          <div className="flex min-w-0 flex-1 flex-col gap-3">
            <div className="flex items-start gap-3">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-md border border-line-subtle bg-surface-subtle text-sm font-semibold text-heading" aria-label={t("rank", { rank: result.rank })}>
                {result.rank}
              </span>
              <div className="flex min-w-0 flex-col gap-1.5">
                <h3 id={`name-${result.supplier_id}`} className="text-base font-medium text-heading">
                  <Link href={profileHref} className="rounded-xs outline-none hover:text-primary-700 focus-visible:ring-4 focus-visible:ring-primary-600/15">
                    {result.supplier_name}
                  </Link>
                </h3>
                <div className="flex flex-wrap items-center gap-2">
                  <MarketBadge known={result.is_known_supplier} />
                  <TypeBadge type={result.supplier_type} verified={result.supplier_type_verified} />
                  <span className="inline-flex items-center gap-1 text-xs text-muted">
                    <BuildingIcon className="size-3.5" aria-hidden />
                    {result.region_name ?? t("regionUnknown")}
                  </span>
                </div>
              </div>
            </div>
            <p className="flex items-start gap-2 text-sm text-subtle">
              <BoxIcon className="mt-0.5 size-4 shrink-0 text-muted" aria-hidden />
              <span className="min-w-0">
                <span className="text-muted">{t("bestOffering")}: </span>
                <span className="text-heading">{result.matched_offering.title}</span>
                <span className="text-muted"> · {result.matched_offering.category_name}</span>
              </span>
            </p>
            <Reasons codes={reasons.slice(0, VISIBLE_REASONS)} params={result.reason_params} />
            {reasons.length > VISIBLE_REASONS && !open ? <span className="text-xs text-muted">{t("moreReasons", { count: reasons.length - VISIBLE_REASONS })}</span> : null}
            <RiskBadges flags={result.risk_flags} />
          </div>
          <div className="grid shrink-0 grid-cols-2 gap-4 rounded-lg border border-line-subtle bg-surface-subtle p-4 md:w-60 md:grid-cols-1">
            <ScoreStat label={t("match")} value={toPct(result.match_score)} />
            <ScoreStat label={t("confidence")} value={toPct(result.confidence_score)} tone={confidenceTone(result.confidence_score)} unknownLabel={t("unknown")} />
          </div>
        </div>

        {open ? (
          <WhyMatched
            id={panelId}
            matchScore={result.match_score}
            contributions={result.contributions}
            reasonCodes={result.reason_codes}
            reasonParams={result.reason_params}
            evidence={result.top_evidence}
          />
        ) : null}

        <div className="flex flex-wrap items-center gap-x-4 gap-y-3 border-t border-line-subtle pt-4">
          <Button variant="link" className="text-primary-700 hover:text-primary-800" aria-expanded={open} aria-controls={panelId} onClick={() => setOpen((o) => !o)}>
            {open ? t("hideWhy") : t("why")}
            <ChevronDownIcon className={cn("transition-transform", open && "rotate-180")} />
          </Button>
          <CheckboxLabel label={t("compare")} checked={selected} onCheckedChange={onToggleCompare} className="text-sm" />
          <div className="ms-auto flex flex-wrap items-center gap-3">
            <FeedbackControl requestId={requestId} supplierId={result.supplier_id} compact />
            <Button asChild variant="secondary" size="sm">
              <Link href={profileHref}>{t("openProfile")}</Link>
            </Button>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}
