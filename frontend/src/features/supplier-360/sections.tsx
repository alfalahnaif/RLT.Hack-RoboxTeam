"use client";

import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import {
  BuildingIcon,
  ClockDashedIcon,
  CopyIcon,
  GlobeIcon,
  HistoryIcon,
  IdCardIcon,
  InfoCircleSmIcon,
  MailIcon,
  ShieldInfoIcon,
  TelephoneIcon,
  UsersIcon,
  VerifiedIcon,
  WarningTriangleIcon,
} from "@/components/icons";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody } from "@/components/ui/card";
import { DescriptionList } from "@/components/ui/description-list";
import { EvidenceItem } from "@/components/ui/evidence-item";
import { IconChip } from "@/components/ui/metric-card";
import { useToast } from "@/components/ui/toast";
import type { FreshnessStatus, ProfileContact, ProfileContactType, ProfileRoleStatus, SupplierProfile360 } from "@/lib/api/types";
import { fmtDate, fmtNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import { evidenceCheckedAt, hasMarketRoleEvidence, hasReachableContact, humanizeCode, mailHref, orderedContacts, profileName, roleGroups, safeHttpUrl, sourceClass, telHref, type RoleGroup, type SourceClass } from "./model";

/** Vocabulary label with a readable fallback for codes the copy does not know yet (never hides the API value). */
export function useLabel() {
  const t = useTranslations("supplier360");
  return (ns: string, code: string, values?: Record<string, string>) => (t.has(`${ns}.${code}`) ? t(`${ns}.${code}`, values) : humanizeCode(code));
}

export async function copyText(value: string) {
  if (navigator.clipboard?.writeText) return navigator.clipboard.writeText(value);
  const el = document.createElement("textarea");
  el.value = value;
  el.setAttribute("readonly", "");
  el.style.position = "fixed";
  el.style.opacity = "0";
  document.body.appendChild(el);
  el.select();
  const ok = document.execCommand("copy");
  el.remove();
  if (!ok) throw new Error("copy failed");
}

export function useCopy() {
  const t = useTranslations("supplier360.contacts");
  const toast = useToast();
  return (value: string) =>
    copyText(value).then(
      () => toast({ tone: "success", title: t("copied") }),
      () => toast({ tone: "danger", title: t("copyFailed") }),
    );
}

/* ------------------------------------------------------------------ shared bits */

export function SectionCard({ icon, title, subtitle, extra, children, className, id }: { icon: ReactNode; title: ReactNode; subtitle?: ReactNode; extra?: ReactNode; children: ReactNode; className?: string; id?: string }) {
  return (
    <Card className={className} aria-labelledby={id}>
      <CardBody className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <IconChip tone="primary">{icon}</IconChip>
            <div className="flex min-w-0 flex-col gap-0.5">
              <h2 id={id} className="text-base font-semibold text-heading">
                {title}
              </h2>
              {subtitle ? <p className="text-xs text-muted">{subtitle}</p> : null}
            </div>
          </div>
          {extra}
        </div>
        {children}
      </CardBody>
    </Card>
  );
}

/** Wrapping external link for long URLs (sources, websites): http(s) only, new tab, noopener. */
export function WrapLink({ href, children, className }: { href: string | null; children: ReactNode; className?: string }) {
  if (!href) return <span className={cn("break-all text-body", className)}>{children}</span>;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" dir="ltr" className={cn("break-all text-primary-700 underline-offset-2 hover:underline", className)}>
      {children}
    </a>
  );
}

const FRESH_TONE: Record<FreshnessStatus, "success" | "warning" | "gray"> = { FRESH: "success", STALE: "warning", UNKNOWN: "gray" };

export function FreshnessBadge({ status, size = "sm" }: { status: FreshnessStatus; size?: "sm" | "default" }) {
  const t = useTranslations("supplier360.freshness.status");
  return (
    <Badge size={size} color={FRESH_TONE[status]}>
      {status === "STALE" ? <WarningTriangleIcon aria-hidden /> : status === "FRESH" ? <VerifiedIcon aria-hidden /> : <InfoCircleSmIcon aria-hidden />}
      {t(status)}
    </Badge>
  );
}

/**
 * Role status badge. VERIFIED is solid success with a check; UNDER_REVIEW soft warning; INFERRED stays visibly weaker
 * (soft gray, dashed outline) so it never reads as equivalent to VERIFIED.
 */
export function RoleBadge({ label, status, size = "default", historyOnly = false }: { label: ReactNode; status: ProfileRoleStatus; size?: "sm" | "default"; historyOnly?: boolean }) {
  const t = useTranslations("supplier360.roleStatus");
  // "Supplier" backed only by procurement awards: a fact about observed history, not manufacturer/distributor evidence.
  if (historyOnly)
    return (
      <Badge size={size} color="primary">
        {label} — {t("HISTORY")}
      </Badge>
    );
  if (status === "VERIFIED")
    return (
      <Badge size={size} appearance="solid" color="success">
        <VerifiedIcon aria-hidden />
        {label} — {t(status)}
      </Badge>
    );
  if (status === "UNDER_REVIEW")
    return (
      <Badge size={size} color="warning">
        <WarningTriangleIcon aria-hidden />
        {label} — {t(status)}
      </Badge>
    );
  return (
    <Badge size={size} color="gray" className="border border-dashed border-gray-400">
      <InfoCircleSmIcon aria-hidden />
      {label} — {t(status)}
    </Badge>
  );
}

/** A role group supported only by organizer procurement awards (the backend's SUPPLIER / PROCUREMENT_HISTORY item). */
export const isHistoryOnly = (g: Pick<RoleGroup, "role" | "items">) => g.role === "SUPPLIER" && g.items.every((r) => r.origin === "PROCUREMENT_HISTORY");

const CLASS_TONE: Record<SourceClass, "success" | "info" | "gray" | "primary" | "purple"> = {
  OFFICIAL_REGISTRY: "success",
  COMPANY_WEBSITE: "info",
  SECONDARY_PROVIDER: "gray",
  PROCUREMENT_HISTORY: "primary",
  CURATED_REGULATORY: "purple",
  OTHER: "gray",
};

export function SourceClassBadge({ sourceType }: { sourceType: string }) {
  const t = useTranslations("supplier360.sourceClass");
  const c = sourceClass(sourceType);
  return (
    <Badge size="sm" color={CLASS_TONE[c]} className="h-auto min-h-[22px] whitespace-normal text-start">
      {t(c)}
    </Badge>
  );
}

/* ------------------------------------------------------------------ contacts */

const CONTACT_ICON: Record<ProfileContactType, ReactNode> = {
  PHONE: <TelephoneIcon aria-hidden />,
  EMAIL: <MailIcon aria-hidden />,
  WEBSITE: <GlobeIcon aria-hidden />,
  ADDRESS: <BuildingIcon aria-hidden />,
};

const chip = "inline-flex min-h-8 items-center gap-1.5 rounded-pill border border-line px-3 py-1 text-xs text-primary-700 transition-colors hover:border-primary-300 hover:bg-primary-50 [&_svg]:size-3.5";

function ContactActions({ c }: { c: ProfileContact }) {
  const t = useTranslations("supplier360.contacts");
  const copy = useCopy();
  if (c.type === "PHONE") {
    const tel = telHref(c.value);
    return (
      <>
        {tel ? <a href={tel} className={chip}><TelephoneIcon aria-hidden />{t("call")}</a> : null}
        <button type="button" className={chip} onClick={() => void copy(c.value)}><CopyIcon aria-hidden />{t("copyPhone")}</button>
      </>
    );
  }
  if (c.type === "EMAIL") {
    const mail = mailHref(c.value);
    return mail ? <a href={mail} className={chip}><MailIcon aria-hidden />{t("email")}</a> : null;
  }
  if (c.type === "WEBSITE") {
    const url = safeHttpUrl(c.value, true);
    return url ? <a href={url} target="_blank" rel="noopener noreferrer" className={chip}><GlobeIcon aria-hidden />{t("openWebsite")}</a> : null;
  }
  return <button type="button" className={chip} onClick={() => void copy(c.value)}><CopyIcon aria-hidden />{t("copyAddress")}</button>;
}

function ContactRow({ c }: { c: ProfileContact }) {
  const t = useTranslations("supplier360.contacts");
  const label = useLabel();
  // P4-005C address labels arrive as "registered legal address" / "published company address"; other labels are shown as given.
  const key = `label.${c.label?.trim().toUpperCase().replaceAll(" ", "_")}`;
  const contactLabel = (raw: string) => (t.has(key) ? t(key) : raw);
  const isUrl = c.type === "WEBSITE" || c.type === "EMAIL";
  return (
    <li className="flex flex-col gap-2 border-b border-line-subtle py-3 first:pt-0 last:border-0 last:pb-0">
      <div className="flex min-w-0 items-start gap-3">
        <span className="mt-0.5 shrink-0 text-muted [&_svg]:size-4">{CONTACT_ICON[c.type]}</span>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="text-xs text-muted">
            {t(`type.${c.type}`)}
            {c.label ? ` · ${contactLabel(c.label)}` : null}
          </span>
          <span dir={c.type === "ADDRESS" ? undefined : "ltr"} className={cn("w-fit max-w-full text-sm text-heading", isUrl ? "break-all" : "break-words")}>
            {c.value}
          </span>
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-2xs text-muted">
            <FreshnessBadge status={c.freshness_status} />
            <Badge size="sm" color={c.verified ? "success" : "gray"}>{c.verified ? t("verified") : t("unverified")}</Badge>
            <SourceClassBadge sourceType={c.source_type} />
            <WrapLink href={safeHttpUrl(c.source_url)} className="text-2xs">{label("sourceType", c.source_type)}</WrapLink>
            <span>{t("checked", { date: fmtDate(c.checked_at) })}</span>
          </span>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 ps-7">
        <ContactActions c={c} />
      </div>
    </li>
  );
}

export function ContactsSection({ profile }: { profile: SupplierProfile360 }) {
  const t = useTranslations("supplier360.contacts");
  const contacts = orderedContacts(profile.contacts);
  const e = profile.enrichment;
  const candidate = !e.official_website ? safeHttpUrl(e.website_candidate, true) : null;
  return (
    <SectionCard id="s360-contacts" icon={<TelephoneIcon />} title={t("title")}
      extra={e.official_website && e.website_confidence === "HIGH" ? <Badge size="sm" color="success"><VerifiedIcon aria-hidden />{t("officialWebsite")}</Badge> : null}>
      {contacts.length ? <ul className="flex flex-col">{contacts.map((c, i) => <ContactRow key={`${c.type}-${c.value}-${i}`} c={c} />)}</ul> : null}
      {!hasReachableContact(profile.contacts) ? (
        <div className="flex items-start gap-2 rounded-md border border-line-subtle bg-surface-subtle p-3">
          <InfoCircleSmIcon className="mt-0.5 size-4 shrink-0 text-muted" aria-hidden />
          <div className="flex flex-col gap-0.5">
            <p className="text-sm text-heading">{t("none")}</p>
            <p className="text-xs text-muted">{profile.supplier.entity_kind === "INDIVIDUAL_ENTREPRENEUR" ? t("noneEntrepreneur") : t("noneHint")}</p>
          </div>
        </div>
      ) : null}
      {candidate ? (
        <p className="flex flex-col gap-0.5 rounded-md border border-dashed border-line p-3 text-xs text-muted">
          <span>{t("websiteCandidate")}</span>
          <WrapLink href={candidate} className="text-xs">{e.website_candidate}</WrapLink>
        </p>
      ) : null}
    </SectionCard>
  );
}

/* ------------------------------------------------------------------ freshness */

function FreshRow({ label, children }: { label: ReactNode; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 border-b border-line-subtle pb-3 last:border-0 last:pb-0 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      <dt className="text-sm text-heading">{label}</dt>
      <dd className="flex flex-wrap items-center gap-2 text-xs text-muted sm:justify-end">{children}</dd>
    </div>
  );
}

export function FreshnessSection({ profile }: { profile: SupplierProfile360 }) {
  const t = useTranslations("supplier360.freshness");
  const f = profile.freshness;
  const last = profile.enrichment.last_enriched_at;
  const evidenceAt = evidenceCheckedAt(profile);
  return (
    <SectionCard id="s360-freshness" icon={<ClockDashedIcon />} title={t("title")}>
      <dl className="flex flex-col gap-3">
        <FreshRow label={t("lastUpdate")}>{last ? <span className="text-heading" dir="ltr">{fmtDate(last)}</span> : <span>{t("never")}</span>}</FreshRow>
        <FreshRow label={t("identity")}>
          <FreshnessBadge status={f.identity} />
          {f.identity_checked_at ? <span>{t("checkedOn", { date: fmtDate(f.identity_checked_at) })}</span> : null}
        </FreshRow>
        <FreshRow label={t("contacts")}>
          <FreshnessBadge status={f.contacts} />
          {f.contacts_last_checked_at ? <span>{t("checkedOn", { date: fmtDate(f.contacts_last_checked_at) })}</span> : null}
          {f.content_currency && t.has(`currency.${f.content_currency}`) ? <span className="basis-full sm:basis-auto">{t(`currency.${f.content_currency}`)}</span> : null}
        </FreshRow>
        <FreshRow label={t("evidence")}>{evidenceAt ? <span>{t("evidenceChecked", { date: fmtDate(evidenceAt) })}</span> : <span>{t("noDate")}</span>}</FreshRow>
      </dl>
      <p className="text-2xs text-muted">{t("note")}</p>
    </SectionCard>
  );
}

/* ------------------------------------------------------------------ roles */

function basisLabel(basis: string, label: ReturnType<typeof useLabel>) {
  const [key, code] = basis.split(":");
  return label("basis", key, { code: code ?? "" });
}

export function RolesSection({ profile }: { profile: SupplierProfile360 }) {
  const t = useTranslations("supplier360");
  const label = useLabel();
  const groups = roleGroups(profile.roles).filter((g) => g.role !== "UNKNOWN");
  const marketKnown = hasMarketRoleEvidence(profile.roles);
  return (
    <SectionCard id="s360-roles" icon={<UsersIcon />} title={t("roles.title")} subtitle={t("roles.subtitle")}>
      {groups.length && !marketKnown ? (
        <div className="flex flex-col gap-1 rounded-md border border-dashed border-line p-3">
          <span className="text-sm font-medium text-heading">{t("roles.marketUnknown")}</span>
          <span className="text-xs text-muted">{t("roles.marketUnknownDescription")}</span>
        </div>
      ) : null}
      {groups.length ? (
        <ul className="flex flex-col gap-3">
          {groups.map((g) => (
            <li key={g.role} className={cn("flex flex-col gap-2 rounded-md border p-3", isHistoryOnly(g) ? "border-primary-200" : g.status === "VERIFIED" ? "border-success-300" : g.status === "UNDER_REVIEW" ? "border-warning-300" : "border-dashed border-line")}>
              <div className="flex flex-wrap items-center gap-2">
                <RoleBadge label={t(`role.${g.role}`)} status={g.status} historyOnly={isHistoryOnly(g)} />
                <span className="text-xs text-muted">{isHistoryOnly(g) ? t("roles.statusHint.HISTORY") : t(`roles.statusHint.${g.status}`)}</span>
              </div>
              <Accordion type="single" collapsible variant="flush">
                <AccordionItem value="evidence">
                  <AccordionTrigger className="px-0 pt-1 pb-1 text-primary-700">{t("roles.evidence", { count: g.items.length })}</AccordionTrigger>
                  <AccordionContent className="flex flex-col gap-2 px-0 pt-2 pb-0">
                    {g.items.map((r, i) => (
                      <EvidenceItem
                        key={`${r.basis}-${i}`}
                        type={t(`roleStatus.${r.status}`)}
                        typeColor={r.status === "VERIFIED" ? "success" : "gray"}
                        claim={r.claim}
                        sourceName={label("sourceType", r.source_type)}
                        sourceUrl={safeHttpUrl(r.source_url)}
                        noLinkLabel={t("roles.noSourceLink")}
                        observedLabel={`${t("roles.basis")}: ${basisLabel(r.basis, label)}${r.checked_at ? ` · ${t("sources.checked", { date: fmtDate(r.checked_at) })}` : ""}`}
                        confidenceLabel={`${t("roles.strength")}: ${label("strength", r.strength)} · ${label("roles.origin", r.origin)}`}
                      />
                    ))}
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </li>
          ))}
        </ul>
      ) : (
        <div className="flex flex-col gap-1 rounded-md border border-dashed border-line p-3">
          <span className="text-sm font-medium text-heading">{t("header.roleUnknown")}</span>
          <span className="text-xs text-muted">{t("roles.unknownDescription")}</span>
        </div>
      )}
    </SectionCard>
  );
}

/* ------------------------------------------------------------------ procurement history */

function Stat({ label, value }: { label: ReactNode; value: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col gap-1 rounded-md border border-line-subtle bg-surface-subtle p-3">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="text-lg font-semibold text-heading">{value}</dd>
    </div>
  );
}

export function HistorySection({ profile }: { profile: SupplierProfile360 }) {
  const t = useTranslations("supplier360.history");
  const locale = useLocale();
  const h = profile.procurement_history_summary;
  const platforms = h ? Object.entries(h.platforms) : [];
  return (
    <SectionCard id="s360-history" icon={<HistoryIcon />} title={t("title")} subtitle={t("disclaimer")}>
      {h ? (
        <>
          <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label={t("observedRelations")} value={fmtNumber(h.observed_relations, locale)} />
            <Stat label={t("relevantAwards")} value={fmtNumber(h.relevant_awards, locale)} />
            <Stat label={t("distinctLots")} value={fmtNumber(h.distinct_lots, locale)} />
            <Stat label={t("lastActivity")} value={<span dir="ltr">{fmtDate(h.last_observed_activity)}</span>} />
          </dl>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
            {h.first_observed_activity && h.last_observed_activity ? <span>{t("period", { from: fmtDate(h.first_observed_activity), to: fmtDate(h.last_observed_activity) })}</span> : null}
            {platforms.length ? <span>{t("platforms")}: {platforms.map(([p, n]) => `${t.has(`platform.${p}`) ? t(`platform.${p}`) : p} ${fmtNumber(n, locale)}`).join(" · ")}</span> : null}
          </div>
          <div className="flex flex-col gap-2">
            <span className="text-xs font-medium text-heading">{t("topOkpd2")}</span>
            {h.top_okpd2.length ? (
              <ul className="flex flex-wrap gap-2">
                {h.top_okpd2.map((o) => (
                  <li key={o.okpd2}>
                    <Badge color="primary"><span dir="ltr">{o.okpd2}</span> · {t("lots", { count: o.awarded_lots })}</Badge>
                  </li>
                ))}
              </ul>
            ) : (
              <span className="text-xs text-muted">{t("noAwardsOkpd2")}</span>
            )}
          </div>
        </>
      ) : (
        <p className="text-sm text-subtle">{profile.supplier.historically_known ? t("none") : t("external")}</p>
      )}
    </SectionCard>
  );
}

/* ------------------------------------------------------------------ legal identity */

export function IdentitySection({ profile }: { profile: SupplierProfile360 }) {
  const t = useTranslations("supplier360");
  const label = useLabel();
  const s = profile.supplier;
  const has = [s.legal_name, s.short_name, s.legal_status, s.ogrn, s.region, s.registered_address, s.primary_okved, s.registration_date].some(Boolean);
  return (
    <SectionCard id="s360-identity" icon={<IdCardIcon />} title={t("identity.title")} subtitle={t("identity.subtitle")}>
      {has ? (
        <DescriptionList
          columns={2}
          items={[
            { label: t("identity.legalName"), value: s.legal_name, wide: true },
            ...(s.short_name ? [{ label: t("identity.shortName"), value: s.short_name, wide: true }] : []),
            { label: t("identity.status"), value: s.legal_status ? label("legalStatus", s.legal_status) : null },
            { label: t("identity.entityKind"), value: s.entity_kind ? label("entityKind", s.entity_kind) : null },
            { label: t("header.ogrn"), value: s.ogrn ? <span dir="ltr">{s.ogrn}</span> : null },
            { label: t("header.kpp"), value: s.kpp ? <span dir="ltr">{s.kpp}</span> : null },
            { label: t("identity.region"), value: s.region },
            { label: t("identity.registrationDate"), value: s.registration_date ? <span dir="ltr">{fmtDate(s.registration_date)}</span> : null },
            { label: t("identity.okved"), value: s.primary_okved, wide: true },
            {
              label: t("identity.address"),
              value: s.registered_address ?? (s.entity_kind === "INDIVIDUAL_ENTREPRENEUR" ? <span className="text-muted">{t("identity.addressEntrepreneur")}</span> : null),
              wide: true,
            },
            ...(s.identity_source_type
              ? [
                  {
                    label: t("identity.source"),
                    value: (
                      <span className="flex flex-wrap items-center gap-2">
                        <SourceClassBadge sourceType={s.identity_source_type} />
                        <WrapLink href={safeHttpUrl(s.identity_source_url)}>{label("sourceType", s.identity_source_type)}</WrapLink>
                      </span>
                    ),
                    wide: true,
                  },
                ]
              : []),
          ]}
        />
      ) : (
        <p className="text-sm text-subtle">
          {t("identity.unavailable")}
          {profileName(s) ? ` · ${profileName(s)}` : null}
        </p>
      )}
    </SectionCard>
  );
}

/* ------------------------------------------------------------------ sources & evidence */

export function SourcesSection({ profile }: { profile: SupplierProfile360 }) {
  const t = useTranslations("supplier360");
  const label = useLabel();
  const { sources, evidence, last_run_attempts: attempts } = profile;
  const history = profile.procurement_history_summary;
  return (
    <Card>
      <Accordion type="single" collapsible variant="flush">
        <AccordionItem value="sources">
          <AccordionTrigger className="px-5 py-4" icon={<ShieldInfoIcon />}>
            <span className="flex flex-col gap-0.5">
              <span className="text-base font-semibold text-heading">{t("sources.title")}</span>
              <span className="text-xs font-normal text-muted">{t("sources.summary", { sources: sources.length + (history ? 1 : 0), evidence: evidence.length })}</span>
            </span>
          </AccordionTrigger>
          <AccordionContent className="flex flex-col gap-5 px-5 pb-5">
            {!sources.length && !evidence.length && !history ? <p className="text-sm text-muted">{t("sources.none")}</p> : null}
            {sources.length || history ? (
              <div className="flex flex-col gap-2">
                <h3 className="text-sm font-medium text-heading">{t("sources.sourcesTitle")}</h3>
                <ul className="flex flex-col gap-2">
                  {sources.map((s) => (
                    <li key={`${s.source_type}-${s.source_url}`} className="flex flex-col gap-1.5 rounded-md border border-line p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <SourceClassBadge sourceType={s.source_type} />
                        <span className="text-xs font-medium text-heading">{label("sourceType", s.source_type)}</span>
                        <span className="text-xs text-muted">{s.last_checked_at ? t("sources.checked", { date: fmtDate(s.last_checked_at) }) : t("freshness.noDate")}</span>
                      </div>
                      <WrapLink href={safeHttpUrl(s.source_url)} className="text-xs">{s.source_url}</WrapLink>
                      {s.used_for.length ? (
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-2xs text-muted">{t("sources.supports")}:</span>
                          {s.used_for.map((u) => <Badge key={u} size="sm" color="gray">{label("claim", u)}</Badge>)}
                        </div>
                      ) : null}
                    </li>
                  ))}
                  {history ? (
                    <li className="flex flex-col gap-1.5 rounded-md border border-line p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <SourceClassBadge sourceType="ORGANIZER_PROCUREMENT_DATA" />
                        <span className="text-xs font-medium text-heading">{label("sourceType", "ORGANIZER_PROCUREMENT_DATA")}</span>
                      </div>
                      <span className="text-xs text-muted">
                        {t("sources.historyRow", { relations: history.observed_relations, from: fmtDate(history.first_observed_activity), to: fmtDate(history.last_observed_activity) })}
                      </span>
                    </li>
                  ) : null}
                </ul>
              </div>
            ) : null}
            {attempts.length ? (
              <div className="flex flex-col gap-2">
                <h3 className="text-sm font-medium text-heading">{t("sources.attemptsTitle")}</h3>
                <ul className="flex flex-col gap-1">
                  {attempts.map((a, i) => (
                    <li key={`${a.source}-${i}`} className="flex flex-wrap items-center gap-2 text-xs text-muted">
                      <Badge size="sm" color={a.outcome === "OK" ? "success" : a.outcome === "SKIPPED" || a.outcome === "NOT_FOUND" ? "gray" : "warning"}>
                        {label("outcome", a.outcome)}
                      </Badge>
                      <span className="text-heading">{label("attemptSource", a.source)}</span>
                    </li>
                  ))}
                </ul>
                <p className="text-2xs text-muted">{t("sources.attemptsNote")}</p>
              </div>
            ) : null}
            {evidence.length ? (
              <div className="flex flex-col gap-2">
                <h3 className="text-sm font-medium text-heading">{t("sources.evidenceTitle")}</h3>
                <ul className="flex flex-col gap-2">
                  {evidence.map((e, i) => (
                    <li key={`${e.evidence_type}-${i}`}>
                      <EvidenceItem
                        type={label("claim", e.evidence_type)}
                        typeColor="primary"
                        claim={e.claim}
                        sourceName={label("sourceType", e.source_type)}
                        sourceUrl={safeHttpUrl(e.source_url)}
                        observedLabel={`${t("sources.checked", { date: fmtDate(e.checked_at) })}${e.valid_until ? ` · ${t("sources.validUntil", { date: fmtDate(e.valid_until) })}` : ""}`}
                        confidenceLabel={t("sources.strength", { value: label("strength", e.strength) })}
                      />
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </Card>
  );
}
