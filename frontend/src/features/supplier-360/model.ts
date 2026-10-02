/**
 * Supplier 360 view helpers (P5-001B). Pure functions over the P5-001A response: ordering, grouping and safe links only —
 * no statuses, roles or freshness are computed here; the UI shows what the API returned (BR-02, BR-35).
 * Only `import type` is used so `node --test` can load this module directly (tests/supplier-360.test.mjs).
 */
import type {
  EnrichmentState,
  ProfileContact,
  ProfileContactType,
  ProfileRole,
  ProfileRoleItem,
  ProfileRoleStatus,
  SupplierIdentity,
  SupplierProfile360,
} from "@/lib/api/types";

export const ROLE_STATUS_ORDER: readonly ProfileRoleStatus[] = ["VERIFIED", "UNDER_REVIEW", "INFERRED", "UNKNOWN"];
export const ROLE_ORDER: readonly ProfileRole[] = ["MANUFACTURER", "OFFICIAL_DISTRIBUTOR", "DISTRIBUTOR", "SUPPLIER", "UNKNOWN"];
export const CONTACT_ORDER: readonly ProfileContactType[] = ["PHONE", "EMAIL", "WEBSITE", "ADDRESS"];

/** Company name exactly as returned; null means "unknown" and the UI shows the INN instead (never an invented name). */
export function profileName(s: SupplierIdentity): string | null {
  return s.display_name?.trim() || s.legal_name?.trim() || s.short_name?.trim() || null;
}

/** Short name is shown under the legal name only when it adds information. */
export function secondaryName(s: SupplierIdentity): string | null {
  const name = profileName(s);
  const short = s.short_name?.trim() || null;
  return short && short.toLocaleLowerCase("ru") !== name?.toLocaleLowerCase("ru") ? short : null;
}

export type LegalStatusTone = "success" | "danger" | "warning" | "gray";
export function legalStatusTone(status: string | null): LegalStatusTone {
  if (!status) return "gray";
  const s = status.toUpperCase();
  if (s === "ACTIVE") return "success";
  if (s === "CEASED" || s === "LIQUIDATED") return "danger";
  return "warning";
}

const rankOf = (status: ProfileRoleStatus) => ROLE_STATUS_ORDER.indexOf(status);

export type RoleGroup = { role: ProfileRole; status: ProfileRoleStatus; items: ProfileRoleItem[] };

/**
 * One group per role: the group status is the strongest status the API gave for that role (VERIFIED > UNDER_REVIEW >
 * INFERRED > UNKNOWN); every evidence item stays inspectable. UNKNOWN roles are dropped when any known role exists.
 */
export function roleGroups(roles: ProfileRoleItem[]): RoleGroup[] {
  const byRole = new Map<ProfileRole, ProfileRoleItem[]>();
  for (const r of roles) byRole.set(r.role, [...(byRole.get(r.role) ?? []), r]);
  const groups = [...byRole.entries()].map(([role, items]) => {
    const sorted = [...items].sort((a, b) => rankOf(a.status) - rankOf(b.status));
    return { role, status: sorted[0].status, items: sorted };
  });
  const known = groups.filter((g) => g.role !== "UNKNOWN");
  return (known.length ? known : groups).sort((a, b) => rankOf(a.status) - rankOf(b.status) || ROLE_ORDER.indexOf(a.role) - ROLE_ORDER.indexOf(b.role));
}

/** Header badges: known roles with a known status. Empty → the header says "Role unknown". */
export function headerRoles(roles: ProfileRoleItem[]): { role: ProfileRole; status: ProfileRoleStatus }[] {
  return roleGroups(roles)
    .filter((g) => g.role !== "UNKNOWN" && g.status !== "UNKNOWN")
    .map(({ role, status }) => ({ role, status }));
}

/** Non-empty contact values in a stable order (phone, email, website, address); API order is kept within a type. */
export function orderedContacts(contacts: ProfileContact[]): ProfileContact[] {
  return contacts
    .filter((c) => c.value?.trim())
    .map((c, i) => ({ c, i }))
    .sort((a, b) => CONTACT_ORDER.indexOf(a.c.type) - CONTACT_ORDER.indexOf(b.c.type) || a.i - b.i)
    .map(({ c }) => c);
}

/** Only http(s) URLs become links (NFR-SEC-01); bare host names from a website field get https://. */
export function safeHttpUrl(value: string | null | undefined, allowBareHost = false): string | null {
  const raw = value?.trim();
  if (!raw) return null;
  const candidate = allowBareHost && !/^[a-z][a-z0-9+.-]*:/i.test(raw) ? `https://${raw}` : raw;
  try {
    const url = new URL(candidate);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

export function telHref(phone: string): string | null {
  const digits = phone.replace(/[^\d+]/g, "");
  return digits.replace(/\D/g, "").length >= 5 ? `tel:${digits}` : null;
}

export function mailHref(email: string): string | null {
  const e = email.trim();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e) ? `mailto:${e}` : null;
}

/** Header "Contact" action: email first, then phone, then website — only from values the API returned. */
export function primaryContactHref(contacts: ProfileContact[]): string | null {
  const list = orderedContacts(contacts);
  const pick = (type: ProfileContactType, fn: (v: string) => string | null) =>
    list.filter((c) => c.type === type).map((c) => fn(c.value)).find(Boolean) ?? null;
  return pick("EMAIL", mailHref) ?? pick("PHONE", telHref) ?? pick("WEBSITE", (v) => safeHttpUrl(v, true));
}

export type EnrichmentNotice = "notEnriched" | "inProgress" | "partial" | "failed" | null;
export type EnrichmentAction = { kind: "enrich" | "retry" | "refresh"; refresh: boolean } | null;

/**
 * Which notice and which action the enrichment state allows. NOT_ENRICHED → "Enrich" (cache-first); FAILED + retryable →
 * "Retry" (forces a re-query); PARTIAL + retryable → "Refresh" (cache-first: the backend re-queries only once its retry
 * window has passed, so the optional secondary provider is not hammered); IN_PROGRESS → no second trigger.
 */
export function enrichmentView(e: EnrichmentState, enrichAvailable: boolean): { notice: EnrichmentNotice; action: EnrichmentAction } {
  const notice: EnrichmentNotice =
    e.status === "NOT_ENRICHED" ? "notEnriched" : e.status === "IN_PROGRESS" ? "inProgress" : e.status === "PARTIAL" ? "partial" : e.status === "FAILED" ? "failed" : null;
  if (!enrichAvailable) return { notice, action: null };
  if (e.status === "NOT_ENRICHED") return { notice, action: { kind: "enrich", refresh: false } };
  if (e.status === "FAILED" && e.retryable) return { notice, action: { kind: "retry", refresh: true } };
  if (e.status === "PARTIAL" && e.retryable) return { notice, action: { kind: "refresh", refresh: false } };
  return { notice, action: null };
}

/** Latest ISO timestamp of a list (string compare is not safe across offsets, so parse). */
export function latestDate(values: (string | null | undefined)[]): string | null {
  let best: { iso: string; t: number } | null = null;
  for (const v of values) {
    const t = v ? Date.parse(v) : NaN;
    if (!Number.isNaN(t) && (!best || t > best.t)) best = { iso: v!, t };
  }
  return best?.iso ?? null;
}

/** Last check date of the role/evidence sources. A date only — the API gives no evidence freshness status to show. */
export function evidenceCheckedAt(p: SupplierProfile360): string | null {
  return latestDate([...p.evidence.map((e) => e.checked_at), ...p.roles.map((r) => r.checked_at)]);
}

/** True when the profile has nothing beyond the INN (no identity fields, contacts, evidence or history). */
export function isInnOnly(p: SupplierProfile360): boolean {
  const s = p.supplier;
  const identity = [profileName(s), s.legal_status, s.ogrn, s.kpp, s.region, s.registered_address].some(Boolean);
  return !identity && !p.contacts.length && !p.evidence.length && !p.procurement_history_summary;
}

/** `?back=` accepts only same-app relative paths (no scheme, no protocol-relative `//`). */
export function safeBackHref(raw: string | null | undefined): string | null {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//") || raw.includes("\\") || /^\/[a-z]+:/i.test(raw)) return null;
  return raw;
}

/** Fallback label for a vocabulary code without a translation: "WEBSITE_IDENTITY_NOT_CONFIRMED" → "Website identity not confirmed". */
export function humanizeCode(code: string): string {
  const s = code.replaceAll("_", " ").toLowerCase().trim();
  return s ? s[0].toUpperCase() + s.slice(1) : code;
}

/** Profile link used by every supplier card (historical and external): one Supplier 360 experience. */
export function supplierProfileHref(inn: string, back?: string | null): string {
  const safe = safeBackHref(back);
  return `/supplier-360/${encodeURIComponent(inn)}${safe ? `?back=${encodeURIComponent(safe)}` : ""}`;
}

/**
 * Provenance class of a source type, so official and secondary sources never look alike:
 * the official FNS EGRUL service, the company's own website, an optional secondary provider (FNS-derived registry mirror —
 * not an official registry), organizer procurement data, and curated regulatory evidence.
 */
export type SourceClass = "OFFICIAL_REGISTRY" | "COMPANY_WEBSITE" | "SECONDARY_PROVIDER" | "PROCUREMENT_HISTORY" | "CURATED_REGULATORY" | "OTHER";
export function sourceClass(sourceType: string): SourceClass {
  const s = sourceType.toUpperCase();
  if (s === "FNS_EGRUL" || s === "FNS_EGRUL_EXTRACT") return "OFFICIAL_REGISTRY";
  if (s === "FIRST_PARTY" || s === "FIRST_PARTY_WEBSITE") return "COMPANY_WEBSITE";
  if (s === "ORGANIZER_PROCUREMENT_DATA") return "PROCUREMENT_HISTORY";
  if (s.includes("MIRROR") && !s.startsWith("REGULATORY")) return "SECONDARY_PROVIDER";
  if (s === "FNS_EGRUL_DERIVED_REGISTRY" || s === "FNS_EGRUL_DERIVED" || s === "SECONDARY_BUSINESS_PROFILE" || s === "RETAIL_SECONDARY") return "SECONDARY_PROVIDER";
  if (s.startsWith("REGULATORY") || s.startsWith("CURATED")) return "CURATED_REGULATORY";
  return "OTHER";
}

export const MARKET_ROLES: readonly ProfileRole[] = ["MANUFACTURER", "OFFICIAL_DISTRIBUTOR", "DISTRIBUTOR"];

/** True when the API returned any manufacturer / distributor evidence (any status). "Supplier" alone is not a market role. */
export function hasMarketRoleEvidence(roles: ProfileRoleItem[]): boolean {
  return roles.some((r) => MARKET_ROLES.includes(r.role) && r.status !== "UNKNOWN");
}

/** A phone or e-mail value. A website or an address alone does not let a buyer reach a person at the company. */
export function hasReachableContact(contacts: ProfileContact[]): boolean {
  return orderedContacts(contacts).some((c) => c.type === "PHONE" || c.type === "EMAIL");
}

/**
 * Parsed verification basis of a contact value: "OFFICIAL_SITE_VERIFIED_STRONG:INN_ON_SITE+OGRN_ON_SITE|COMPANY_DOMAIN"
 * -> { kind: "OFFICIAL_SITE_VERIFIED_STRONG", signals: ["INN_ON_SITE", "OGRN_ON_SITE"], qualifier: "COMPANY_DOMAIN" }.
 * Display only — the UI never re-decides trust.
 */
export function parseBasis(basis: string | null | undefined): { kind: string; signals: string[]; qualifier: string | null } | null {
  if (!basis) return null;
  const [head, qualifier = null] = basis.split("|");
  const [kind, sig = ""] = head.split(":");
  return { kind, signals: sig ? sig.split("+").filter(Boolean) : [], qualifier };
}
