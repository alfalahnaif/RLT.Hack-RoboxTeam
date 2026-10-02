"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { ScoreStat } from "@/components/ui/score";
import type { SupplierContact, SupplierFreshness, SupplierSearchResponse, SupplierSearchResult } from "@/lib/api/types";

type ExternalResult = SupplierSearchResponse["external_expansion"][number]["candidates"][number];

function httpUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

function roleKey(value: string | null): "manufacturer" | "distributor" | "supplier" {
  const upper = value?.toUpperCase() ?? "";
  if (upper.includes("MANUFACTURER")) return "manufacturer";
  if (upper.includes("DISTRIBUTOR")) return "distributor";
  return "supplier";
}

function VerificationBadge({ status }: { status: "VERIFIED" | "UNDER_REVIEW" | "UNVERIFIED" | "NO_EVIDENCE" }) {
  const t = useTranslations("marketProduct");
  return <Badge size="sm" color={status === "VERIFIED" ? "success" : status === "UNDER_REVIEW" ? "warning" : "gray"}>{t(`verification.${status}`)}</Badge>;
}

export function FreshnessLabel({ freshness }: { freshness: SupplierFreshness | null }) {
  const t = useTranslations("marketProduct");
  const locale = useLocale();
  const date = freshness?.last_checked_at ? new Date(freshness.last_checked_at) : null;
  const checked = date && !Number.isNaN(date.getTime())
    ? t("freshChecked", { date: new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", year: "numeric" }).format(date) })
    : null;
  if (!freshness || freshness.status === "UNKNOWN") return <span className="text-xs text-muted">{t("freshUnknown")}</span>;
  return (
    <span className={freshness.status === "STALE" ? "text-xs text-warning-800" : "text-xs text-muted"}>
      {freshness.status === "STALE" ? t("freshStale") : checked ?? t("freshUnknown")}
      {freshness.status === "STALE" && checked ? ` · ${checked}` : null}
    </span>
  );
}

export function ContactActions({ contact }: { contact: SupplierContact | null }) {
  const t = useTranslations("marketProduct");
  const [copied, setCopied] = useState(false);
  const phone = contact?.phone?.trim() || null;
  const email = contact?.email?.trim() || null;
  const website = httpUrl(contact?.website ?? null);
  const callable = phone?.replace(/[^\d+]/g, "") || null;
  if (!phone && !email && !website) return <span className="text-xs text-muted">{t("noContact")}</span>;
  const primary = email ? `mailto:${email}` : callable ? `tel:${callable}` : website;
  return (
    <div className="flex flex-wrap items-center gap-2">
      {primary ? <Button asChild size="sm"><a href={primary} target={primary.startsWith("http") ? "_blank" : undefined} rel={primary.startsWith("http") ? "noopener noreferrer" : undefined}>{t("contact")}</a></Button> : null}
      {phone ? (
        <>
          {callable ? <a href={`tel:${callable}`} className="rounded-pill border border-line px-3 py-1.5 text-xs text-primary-700">{t("call")}: <span dir="ltr">{phone}</span></a> : <span dir="ltr" className="text-xs text-body">{phone}</span>}
          <button type="button" className="rounded-pill border border-line px-3 py-1.5 text-xs text-subtle hover:text-primary-700"
            onClick={() => void navigator.clipboard.writeText(phone).then(() => setCopied(true)).catch(() => setCopied(false))}>
            {copied ? t("copied") : t("copyPhone")}
          </button>
        </>
      ) : null}
      {email ? <a href={`mailto:${email}`} className="rounded-pill border border-line px-3 py-1.5 text-xs text-primary-700">{t("email")}</a> : null}
      {website ? <a href={website} target="_blank" rel="noopener noreferrer" className="rounded-pill border border-line px-3 py-1.5 text-xs text-primary-700">{t("website")}</a> : null}
    </div>
  );
}

export function HistoricalSupplierCard({ supplier }: { supplier: SupplierSearchResult }) {
  const t = useTranslations("marketProduct");
  const name = supplier.company_name || t("companyUnavailable");
  return (
    <Card>
      <CardBody className="flex flex-col gap-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 items-start gap-3">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-md bg-primary-700 text-sm font-semibold text-white" aria-label={t("rank", { rank: supplier.rank })}>{supplier.rank}</span>
            <div className="min-w-0">
              <h3 className="break-words text-base font-semibold text-heading">{name}</h3>
              <p className="mt-0.5 text-xs text-muted">{t("inn")}: <span dir="ltr">{supplier.inn}</span></p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge size="sm" color="info">{t(`role.${roleKey(supplier.role)}`)}</Badge>
                <VerificationBadge status={supplier.role_evidence_status} />
              </div>
            </div>
          </div>
          <div className="rounded-lg border border-line-subtle bg-surface-subtle px-4 py-3 sm:min-w-36">
            <ScoreStat label={t("score")} value={Math.round(supplier.score * 100)} size="sm" />
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-heading">{t("why")}</span>
          <p className="text-sm text-body">{supplier.reasons[0] ?? t("noEvidenceDetail")}</p>
        </div>
        <FreshnessLabel freshness={supplier.freshness} />
        <ContactActions contact={supplier.contact} />
        <details className="rounded-md border border-line-subtle bg-surface-subtle p-3 text-sm">
          <summary className="cursor-pointer font-medium text-primary-700">{t("evidence")}</summary>
          <div className="mt-3 flex flex-col gap-2 text-sm text-subtle">
            <p>{t("historicalLots", { count: supplier.historical_evidence.relevant_lots })} · {t("historicalAwards", { count: supplier.historical_evidence.relevant_awards })}</p>
            <p>{t("recentEvidence", { date: supplier.historical_evidence.most_recent_relevant })}</p>
            {supplier.reasons.length > 1 ? <ul className="list-inside list-disc">{supplier.reasons.slice(1).map((reason, index) => <li key={index}>{reason}</li>)}</ul> : null}
            {supplier.historical_evidence.evidence_lot_ids.length ? <p>Lot IDs: <span dir="ltr">{supplier.historical_evidence.evidence_lot_ids.join(", ")}</span></p> : null}
            {supplier.semantic_evidence.length ? <p>{t("evidence")}: {supplier.semantic_evidence.length}</p> : null}
          </div>
        </details>
      </CardBody>
    </Card>
  );
}

export function ExternalSupplierCard({ candidate }: { candidate: ExternalResult }) {
  const t = useTranslations("marketProduct");
  return (
    <Card>
      <CardBody className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="break-words text-base font-semibold text-heading">{candidate.company_name}</h3>
            <p className="mt-0.5 text-xs text-muted">{t("inn")}: <span dir="ltr">{candidate.supplier_inn}</span></p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge size="sm" color="info">{t(`role.${roleKey(candidate.market_role)}`)}</Badge>
            <VerificationBadge status={candidate.verification_status} />
          </div>
        </div>
        <p className="text-sm text-body"><span className="font-medium">{t("whyExternal")}:</span> {candidate.why_candidate}</p>
        <FreshnessLabel freshness={candidate.freshness} />
        <ContactActions contact={candidate.contact} />
        <details className="rounded-md border border-line-subtle bg-surface-subtle p-3 text-sm">
          <summary className="cursor-pointer font-medium text-primary-700">{t("evidence")}</summary>
          <ul className="mt-3 flex flex-col gap-3">
            {candidate.evidence_summary.map((item, index) => (
              <li key={`${item.source_record_id ?? item.source_name}-${index}`} className="border-b border-line-subtle pb-2 last:border-0 last:pb-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge size="sm" color={item.evidence_status === "ACTIVE" ? "success" : "gray"}>{item.evidence_status}</Badge>
                  <span className="text-xs text-body">{item.evidence_type}</span>
                </div>
                <p className="mt-1 text-xs text-subtle">{item.product_scope.join("; ") || item.source_record_id || item.source_name}</p>
                {httpUrl(item.source_url) ? <a href={httpUrl(item.source_url)!} target="_blank" rel="noopener noreferrer" className="text-xs text-primary-700 underline">{t("evidenceSource")}: {item.source_name}</a> : <span className="text-xs text-muted">{t("evidenceSource")}: {item.source_name}</span>}
              </li>
            ))}
          </ul>
        </details>
      </CardBody>
    </Card>
  );
}
