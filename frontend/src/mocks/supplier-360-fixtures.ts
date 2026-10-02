/**
 * SYNTHETIC Supplier 360 fixtures (mock mode only, BR-20): fictitious INNs (0000…), names, example.* domains and +7 000
 * phone numbers. Shapes follow the P5-001A contract (backend/app/api/supplier_profile_models.py) so the screen is built
 * against the real response. One fixture per state the screen must handle; listed on /supplier-360 in mock mode.
 * Only `import type` here so `node --test` can load the file (tests/supplier-360.test.mjs).
 */
import type { EnrichmentState, ProfileFreshness, ProfileRoleItem, SupplierIdentity, SupplierProfile360 } from "@/lib/api/types";

const CHECKED = "2026-09-28T09:15:00+00:00";
const OLD = "2025-11-03T10:00:00+00:00";
const NOTE_FRESH = "Retrieved recently is not the same as fresh: an outdated source page stays STALE; undated pages are UNKNOWN.";
const NOTE_HISTORY = "Organizer procurement data (2024–2025). No cross-platform win rate is computed (АИС ГЗ rows are winner-only).";

const emptyIdentity = (inn: string, historically_known: boolean): SupplierIdentity => ({
  inn,
  entity_kind: null,
  display_name: null,
  legal_name: null,
  short_name: null,
  legal_status: null,
  ogrn: null,
  kpp: null,
  region: null,
  registered_address: null,
  registration_date: null,
  primary_okved: null,
  identity_source_url: null,
  identity_source_type: null,
  historically_known,
});

const notEnriched: EnrichmentState = {
  status: "NOT_ENRICHED",
  reasons: [],
  retryable: false,
  last_enriched_at: null,
  official_website: null,
  website_confidence: "NONE",
  website_candidate: null,
  pipeline_version: null,
  cache: "NONE",
};

const unknownFreshness: ProfileFreshness = {
  policy_version: "p5-001a-v1",
  identity: "UNKNOWN",
  identity_checked_at: null,
  contacts: "UNKNOWN",
  contacts_last_checked_at: null,
  content_currency: null,
  profile_cache_valid_until: null,
  note: NOTE_FRESH,
};

const historyRole = (awards: number, from: string, to: string): ProfileRoleItem => ({
  role: "SUPPLIER",
  status: "VERIFIED",
  basis: "PROCUREMENT_HISTORY_AWARDS",
  claim: `${awards} awarded supply relations in the organizer procurement data (${from} – ${to}).`,
  strength: "STRONG",
  source_url: null,
  source_type: "ORGANIZER_PROCUREMENT_DATA",
  checked_at: null,
  origin: "PROCUREMENT_HISTORY",
});

const EGRUL = "https://egrul.example.org/extract/";

/** 1. COMPLETE profile, verified manufacturer, fresh contacts, procurement history. */
const complete: SupplierProfile360 = {
  supplier: {
    inn: "0000000001",
    entity_kind: "LEGAL_ENTITY",
    display_name: "ООО «Демо Молочный Комбинат»",
    legal_name: "ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ «ДЕМО МОЛОЧНЫЙ КОМБИНАТ»",
    short_name: "ООО «ДЕМО МОЛОЧНЫЙ КОМБИНАТ»",
    legal_status: "ACTIVE",
    ogrn: "0000000000001",
    kpp: "000001001",
    region: "Санкт-Петербург",
    registered_address: "190000, г. Санкт-Петербург, ул. Демонстрационная, д. 1, лит. А",
    registration_date: "2011-04-12",
    primary_okved: "10.51 Производство молока и молочной продукции",
    identity_source_url: `${EGRUL}0000000001`,
    identity_source_type: "FNS_EGRUL",
    historically_known: true,
  },
  enrichment: {
    status: "COMPLETE",
    reasons: [],
    retryable: false,
    last_enriched_at: CHECKED,
    official_website: "https://dairy-demo.example.com/",
    website_confidence: "HIGH",
    website_candidate: null,
    website_verification: { status: "VERIFIED_STRONG", signals: ["INN_ON_SITE", "OGRN_ON_SITE"], discovered_via: "EGRUL_EMAIL_DOMAIN", checked_at: CHECKED },
    pipeline_version: "p5-001a.1",
    cache: "HIT",
  },
  contacts: [
    { type: "PHONE", value: "+7 (000) 000-00-01", label: "Отдел продаж", source_url: "https://dairy-demo.example.com/contacts", source_type: "FIRST_PARTY", checked_at: CHECKED, freshness_status: "FRESH", verified: true, origin: "ENRICHMENT_PIPELINE", verification_basis: "OFFICIAL_SITE_VERIFIED_STRONG:INN_ON_SITE+OGRN_ON_SITE" },
    { type: "EMAIL", value: "sales@dairy-demo.example.com", label: null, source_url: "https://dairy-demo.example.com/contacts", source_type: "FIRST_PARTY", checked_at: CHECKED, freshness_status: "FRESH", verified: true, origin: "ENRICHMENT_PIPELINE", verification_basis: "OFFICIAL_SITE_VERIFIED_STRONG:INN_ON_SITE+OGRN_ON_SITE|COMPANY_DOMAIN" },
    { type: "WEBSITE", value: "https://dairy-demo.example.com/", label: null, source_url: "https://dairy-demo.example.com/", source_type: "FIRST_PARTY", checked_at: CHECKED, freshness_status: "FRESH", verified: true, origin: "ENRICHMENT_PIPELINE" },
    { type: "ADDRESS", value: "190000, г. Санкт-Петербург, ул. Демонстрационная, д. 1, лит. А", label: "registered legal address", source_url: `${EGRUL}0000000001`, source_type: "FNS_EGRUL", checked_at: CHECKED, freshness_status: "FRESH", verified: true, origin: "ENRICHMENT_PIPELINE" },
  ],
  roles: [
    {
      role: "MANUFACTURER",
      status: "VERIFIED",
      basis: "CURATED_EVIDENCE_POLICY:10.51.11.110",
      claim: "Conformity declaration names the company as manufacturer of drinking milk (strength STRONG; reasons ACTIVE_DECLARATION_AS_MANUFACTURER)",
      strength: "STRONG",
      source_url: "https://registry.example.org/declarations/RU-D-DEMO-0001",
      source_type: "REGULATORY_REGISTRY",
      checked_at: CHECKED,
      origin: "CURATED_P3_002B",
    },
    historyRole(42, "2024-01-15", "2025-11-20"),
  ],
  evidence: [
    { evidence_type: "LEGAL_IDENTITY", claim: "INN 0000000001 is registered as «ООО «ДЕМО МОЛОЧНЫЙ КОМБИНАТ»» (OGRN 0000000000001)", value: null, source_url: `${EGRUL}0000000001`, source_type: "FNS_EGRUL", checked_at: CHECKED, valid_until: null, strength: "STRONG" },
    { evidence_type: "LEGAL_STATUS", claim: "Registry status: ACTIVE", value: "ACTIVE", source_url: `${EGRUL}0000000001`, source_type: "FNS_EGRUL", checked_at: CHECKED, valid_until: null, strength: "STRONG" },
    { evidence_type: "OKVED_PRIMARY", claim: "Primary OKVED: 10.51", value: "10.51", source_url: `${EGRUL}0000000001`, source_type: "FNS_EGRUL", checked_at: CHECKED, valid_until: null, strength: "MODERATE" },
    { evidence_type: "WEBSITE_IDENTITY", claim: "Official website: the company's requisites (INN, OGRN) are published on the site", value: "https://dairy-demo.example.com/", source_url: "https://dairy-demo.example.com/requisites", source_type: "FIRST_PARTY", checked_at: CHECKED, valid_until: null, strength: "STRONG" },
  ],
  freshness: {
    policy_version: "p5-001a-v1",
    identity: "FRESH",
    identity_checked_at: CHECKED,
    contacts: "FRESH",
    contacts_last_checked_at: CHECKED,
    content_currency: "CURRENT",
    profile_cache_valid_until: "2026-10-28T09:15:00+00:00",
    note: NOTE_FRESH,
  },
  procurement_history_summary: {
    observed_relations: 57,
    relevant_awards: 42,
    distinct_lots: 49,
    first_observed_activity: "2024-01-15",
    last_observed_activity: "2025-11-20",
    platforms: { AIS_GZ: 38, EM: 19 },
    top_okpd2: [
      { okpd2: "10.51.11.110", awarded_lots: 21 },
      { okpd2: "10.51.40.300", awarded_lots: 9 },
      { okpd2: "10.51.52.110", awarded_lots: 6 },
    ],
    note: NOTE_HISTORY,
  },
  sources: [
    { source_url: `${EGRUL}0000000001`, source_type: "FNS_EGRUL", last_checked_at: CHECKED, used_for: ["LEGAL_IDENTITY", "LEGAL_STATUS", "OKVED_PRIMARY", "CONTACT_ADDRESS"] },
    { source_url: "https://dairy-demo.example.com/contacts", source_type: "FIRST_PARTY", last_checked_at: CHECKED, used_for: ["CONTACT_PHONE", "CONTACT_EMAIL"] },
    { source_url: "https://dairy-demo.example.com/requisites", source_type: "FIRST_PARTY", last_checked_at: CHECKED, used_for: ["WEBSITE_IDENTITY"] },
    { source_url: "https://registry.example.org/declarations/RU-D-DEMO-0001", source_type: "REGULATORY_REGISTRY", last_checked_at: CHECKED, used_for: ["ROLE_MANUFACTURER"] },
  ],
  last_run_attempts: [],
  website_checks: [
    { candidate_url: "https://dairy-demo.example.com/", official_url: "https://dairy-demo.example.com/", status: "VERIFIED_STRONG", signals: ["INN_ON_SITE", "OGRN_ON_SITE", "EXACT_LEGAL_NAME"], discovered_via: "EGRUL_EMAIL_DOMAIN", reason: null, checked_at: CHECKED },
  ],
};

/** 2. PARTIAL: website not confirmed, stale registry-mirror contacts, inferred distributor + manufacturer under review. */
const partial: SupplierProfile360 = {
  supplier: {
    ...emptyIdentity("0000000002", true),
    entity_kind: "LEGAL_ENTITY",
    display_name: "ООО «Демо Торговый Дом Северо-Запад с очень длинным наименованием для проверки переноса строк»",
    legal_name: "ООО «Демо Торговый Дом Северо-Запад с очень длинным наименованием для проверки переноса строк»",
    legal_status: "ACTIVE",
    ogrn: "0000000000002",
    kpp: "000002001",
    region: "Ленинградская область",
    registered_address: "188000, Ленинградская обл., г. Демоград, промзона «Демо», зд. 7",
    primary_okved: "46.33 Торговля оптовая молочными продуктами",
    identity_source_url: "https://registry-mirror.example.org/company/0000000002",
    identity_source_type: "FNS_EGRUL_DERIVED_REGISTRY",
  },
  enrichment: {
    status: "PARTIAL",
    reasons: ["PRIMARY_REGISTRY_UNAVAILABLE_MIRROR_USED", "WEBSITE_IDENTITY_NOT_CONFIRMED"],
    retryable: true,
    last_enriched_at: OLD,
    official_website: null,
    website_confidence: "MEDIUM",
    website_candidate: "https://td-severo-zapad-demo.example.net/catalog/molochnaya-produkciya/very/long/path/for/wrapping",
    pipeline_version: "p5-001a.1",
    cache: "HIT",
  },
  contacts: [
    { type: "PHONE", value: "+7 (000) 000-00-02", label: null, source_url: "https://registry-mirror.example.org/company/0000000002", source_type: "FNS_EGRUL_DERIVED_REGISTRY", checked_at: OLD, freshness_status: "STALE", verified: false, origin: "ENRICHMENT_PIPELINE" },
    { type: "ADDRESS", value: "188000, Ленинградская обл., г. Демоград, промзона «Демо», зд. 7", label: "registered legal address", source_url: "https://registry-mirror.example.org/company/0000000002", source_type: "FNS_EGRUL_DERIVED_REGISTRY", checked_at: OLD, freshness_status: "STALE", verified: false, origin: "ENRICHMENT_PIPELINE" },
  ],
  roles: [
    { role: "DISTRIBUTOR", status: "INFERRED", basis: "OKVED_PRIMARY", claim: "Primary OKVED 46.33 (wholesale of dairy products) suggests a distribution role.", strength: "WEAK", source_url: "https://registry-mirror.example.org/company/0000000002", source_type: "FNS_EGRUL_DERIVED_REGISTRY", checked_at: OLD, origin: "ENRICHMENT_PIPELINE" },
    { role: "MANUFACTURER", status: "UNDER_REVIEW", basis: "FIRST_PARTY_PRODUCTION_CLAIM", claim: "Candidate website says «собственное производство»; the site is not confirmed as official.", strength: "WEAK", source_url: "https://td-severo-zapad-demo.example.net/about", source_type: "FIRST_PARTY", checked_at: OLD, origin: "ENRICHMENT_PIPELINE" },
    historyRole(3, "2024-06-02", "2024-12-10"),
  ],
  evidence: [
    { evidence_type: "LEGAL_IDENTITY", claim: "INN 0000000002 is registered as «ООО «Демо Торговый Дом Северо-Запад…»»", value: null, source_url: "https://registry-mirror.example.org/company/0000000002", source_type: "FNS_EGRUL_DERIVED_REGISTRY", checked_at: OLD, valid_until: null, strength: "MODERATE" },
    { evidence_type: "WEBSITE_CANDIDATE", claim: "Candidate website found via registry hint; legal name matches but no INN/OGRN on the site.", value: "https://td-severo-zapad-demo.example.net/", source_url: "https://td-severo-zapad-demo.example.net/catalog/molochnaya-produkciya/very/long/path/for/wrapping", source_type: "FIRST_PARTY", checked_at: OLD, valid_until: null, strength: "WEAK" },
  ],
  freshness: {
    policy_version: "p5-001a-v1",
    identity: "STALE",
    identity_checked_at: OLD,
    contacts: "STALE",
    contacts_last_checked_at: OLD,
    content_currency: "OUTDATED",
    profile_cache_valid_until: null,
    note: NOTE_FRESH,
  },
  procurement_history_summary: {
    observed_relations: 5,
    relevant_awards: 3,
    distinct_lots: 4,
    first_observed_activity: "2024-06-02",
    last_observed_activity: "2024-12-10",
    platforms: { EM: 5 },
    top_okpd2: [{ okpd2: "10.51.11.110", awarded_lots: 2 }, { okpd2: "10.51.30.100", awarded_lots: 1 }],
    note: NOTE_HISTORY,
  },
  sources: [
    { source_url: "https://registry-mirror.example.org/company/0000000002", source_type: "FNS_EGRUL_DERIVED_REGISTRY", last_checked_at: OLD, used_for: ["LEGAL_IDENTITY", "CONTACT_PHONE", "CONTACT_ADDRESS", "ROLE_DISTRIBUTOR"] },
    { source_url: "https://td-severo-zapad-demo.example.net/catalog/molochnaya-produkciya/very/long/path/for/wrapping", source_type: "FIRST_PARTY", last_checked_at: OLD, used_for: ["WEBSITE_CANDIDATE"] },
    { source_url: "https://td-severo-zapad-demo.example.net/about", source_type: "FIRST_PARTY", last_checked_at: OLD, used_for: ["ROLE_MANUFACTURER"] },
  ],
  last_run_attempts: [
    { source: "FNS_EGRUL", outcome: "UNAVAILABLE", detail: "timeout", duration_ms: 8000 },
    { source: "CHECKO_REGISTRY_MIRROR", outcome: "OK", detail: null, duration_ms: 1200 },
  ],
  // a similar-name site that was checked and rejected (shape of the P5-002A history)
  website_checks: [
    { candidate_url: "https://td-severo-zapad-demo.example.net/", official_url: null, status: "REJECTED", signals: ["EXACT_LEGAL_NAME", "REGISTERED_LOCALITY"], discovered_via: "LEGAL_NAME_DOMAIN", reason: "IDENTITY_NOT_CONFIRMED_ON_SITE", checked_at: OLD },
  ],
};

/** 3. INN-only historical supplier, NOT_ENRICHED: name unknown, history only. Enrichment turns it into a profile. */
const innOnly: SupplierProfile360 = {
  supplier: emptyIdentity("0000000003", true),
  enrichment: notEnriched,
  contacts: [],
  roles: [historyRole(2, "2025-02-11", "2025-03-30")],
  evidence: [],
  freshness: unknownFreshness,
  procurement_history_summary: {
    observed_relations: 2,
    relevant_awards: 2,
    distinct_lots: 2,
    first_observed_activity: "2025-02-11",
    last_observed_activity: "2025-03-30",
    platforms: { AIS_GZ: 2 },
    top_okpd2: [{ okpd2: "10.51.11.110", awarded_lots: 2 }],
    note: NOTE_HISTORY,
  },
  sources: [],
  last_run_attempts: [],
};

/** 4. Individual entrepreneur, COMPLETE identity, no contacts (not collected for individuals), unknown freshness, role unknown. */
const noContacts: SupplierProfile360 = {
  supplier: {
    ...emptyIdentity("000000000004", true),
    entity_kind: "INDIVIDUAL_ENTREPRENEUR",
    display_name: "ИП Демонстрационный Д. Д.",
    legal_name: "ИП Демонстрационный Д. Д.",
    legal_status: "ACTIVE",
    ogrn: "000000000000004",
    region: "Санкт-Петербург",
    identity_source_url: `${EGRUL}000000000004`,
    identity_source_type: "FNS_EGRUL",
  },
  enrichment: { ...notEnriched, status: "COMPLETE", reasons: ["INDIVIDUAL_ENTREPRENEUR_CONTACTS_NOT_COLLECTED"], last_enriched_at: CHECKED, pipeline_version: "p5-001a.1", cache: "HIT" },
  contacts: [],
  roles: [{ role: "UNKNOWN", status: "UNKNOWN", basis: "NO_ROLE_EVIDENCE", claim: "No role evidence was found in the checked sources.", strength: "WEAK", source_url: null, source_type: "FNS_EGRUL", checked_at: CHECKED, origin: "ENRICHMENT_PIPELINE" }],
  evidence: [
    { evidence_type: "LEGAL_IDENTITY", claim: "INN 000000000004 is registered as «ИП Демонстрационный Д. Д.»", value: null, source_url: `${EGRUL}000000000004`, source_type: "FNS_EGRUL", checked_at: CHECKED, valid_until: null, strength: "STRONG" },
  ],
  freshness: { ...unknownFreshness, identity: "FRESH", identity_checked_at: CHECKED },
  procurement_history_summary: {
    observed_relations: 1,
    relevant_awards: 0,
    distinct_lots: 1,
    first_observed_activity: "2025-05-14",
    last_observed_activity: "2025-05-14",
    platforms: { EM: 1 },
    top_okpd2: [],
    note: NOTE_HISTORY,
  },
  sources: [{ source_url: `${EGRUL}000000000004`, source_type: "FNS_EGRUL", last_checked_at: CHECKED, used_for: ["LEGAL_IDENTITY"] }],
  last_run_attempts: [],
};

/** 5. FAILED and retryable (registry outage). Retry in mock mode returns a PARTIAL profile. */
const failed: SupplierProfile360 = {
  supplier: emptyIdentity("0000000005", true),
  enrichment: { ...notEnriched, status: "FAILED", reasons: ["PRIMARY_REGISTRY_UNAVAILABLE", "REGISTRY_MIRROR_RATE_LIMITED"], retryable: true, last_enriched_at: CHECKED, pipeline_version: "p5-001a.1" },
  contacts: [],
  roles: [historyRole(1, "2024-09-03", "2024-09-03")],
  evidence: [],
  freshness: unknownFreshness,
  procurement_history_summary: {
    observed_relations: 1,
    relevant_awards: 1,
    distinct_lots: 1,
    first_observed_activity: "2024-09-03",
    last_observed_activity: "2024-09-03",
    platforms: { AIS_GZ: 1 },
    top_okpd2: [{ okpd2: "10.51.40.300", awarded_lots: 1 }],
    note: NOTE_HISTORY,
  },
  sources: [],
  last_run_attempts: [
    { source: "FNS_EGRUL", outcome: "UNAVAILABLE", detail: "HTTP 503", duration_ms: 3100 },
    { source: "CHECKO_REGISTRY_MIRROR", outcome: "RATE_LIMITED", detail: "HTTP 429", duration_ms: 900 },
  ],
};

/**
 * 6. Curated external candidate (shape of the six P3-002B / P4-005C candidates): not in procurement history, pipeline not
 * run yet, but curated contacts (undated page → UNKNOWN freshness) and a curated VERIFIED manufacturer role.
 */
const external: SupplierProfile360 = {
  supplier: { ...emptyIdentity("0000000006", false), display_name: "АО «Демо Агрохолдинг»" },
  enrichment: notEnriched,
  contacts: [
    { type: "WEBSITE", value: "https://agro-demo.example.com", label: null, source_url: "https://agro-demo.example.com/", source_type: "FIRST_PARTY", checked_at: CHECKED, freshness_status: "UNKNOWN", verified: true, origin: "CURATED_P4_005C" },
    { type: "PHONE", value: "+7 (000) 000-00-06", label: null, source_url: "https://agro-demo.example.com/contacts", source_type: "FIRST_PARTY", checked_at: CHECKED, freshness_status: "UNKNOWN", verified: true, origin: "CURATED_P4_005C" },
    { type: "EMAIL", value: "info@agro-demo.example.com", label: null, source_url: "https://agro-demo.example.com/contacts", source_type: "FIRST_PARTY", checked_at: CHECKED, freshness_status: "UNKNOWN", verified: true, origin: "CURATED_P4_005C" },
    { type: "ADDRESS", value: "000000, Демонстрационная обл., с. Демо, ул. Полевая, 1", label: "published company address", source_url: "https://agro-demo.example.com/contacts", source_type: "FIRST_PARTY", checked_at: CHECKED, freshness_status: "UNKNOWN", verified: true, origin: "CURATED_P4_005C" },
  ],
  roles: [
    {
      role: "MANUFACTURER",
      status: "VERIFIED",
      basis: "CURATED_EVIDENCE_POLICY:10.51.11.110",
      claim: "Active conformity declaration lists the company as manufacturer and applicant (strength STRONG; reasons ACTIVE_DECLARATION_AS_MANUFACTURER, EXACT_PRODUCT_SCOPE)",
      strength: "STRONG",
      source_url: "https://registry.example.org/declarations/RU-D-DEMO-0006",
      source_type: "REGULATORY_REGISTRY",
      checked_at: CHECKED,
      origin: "CURATED_P3_002B",
    },
  ],
  evidence: [],
  freshness: { ...unknownFreshness, contacts_last_checked_at: CHECKED, content_currency: "UNDATED" },
  procurement_history_summary: null,
  sources: [
    { source_url: "https://agro-demo.example.com/", source_type: "FIRST_PARTY", last_checked_at: CHECKED, used_for: ["CONTACT_WEBSITE"] },
    { source_url: "https://agro-demo.example.com/contacts", source_type: "FIRST_PARTY", last_checked_at: CHECKED, used_for: ["CONTACT_PHONE", "CONTACT_EMAIL", "CONTACT_ADDRESS"] },
    { source_url: "https://registry.example.org/declarations/RU-D-DEMO-0006", source_type: "REGULATORY_REGISTRY", last_checked_at: CHECKED, used_for: ["ROLE_MANUFACTURER"] },
    { source_url: "https://registry-mirror.example.org/company/0000000006", source_type: "FNS_EGRUL_DERIVED_REGISTRY", last_checked_at: CHECKED, used_for: ["CURATED_IDENTITY_BASIS"] },
  ],
  last_run_attempts: [],
};

/** 7. NOT_ENRICHED where the enrichment call itself fails (503) — exercises the action error state. */
const enrichError: SupplierProfile360 = { ...innOnly, supplier: emptyIdentity("0000000007", true) };

/** 8. Enrichment already running elsewhere (IN_PROGRESS): no second trigger. */
const inProgress: SupplierProfile360 = { ...innOnly, supplier: emptyIdentity("0000000008", true), enrichment: { ...notEnriched, status: "IN_PROGRESS" } };

/** 9. P5-002A: verified official website with a phone but no e-mail (COMPLETE). */
const sitePhoneOnly: SupplierProfile360 = {
  ...complete,
  supplier: { ...complete.supplier, inn: "0000000009", display_name: "ООО «Демо Хлеб»", legal_name: "ООО «ДЕМО ХЛЕБ»", short_name: null },
  contacts: complete.contacts.filter((c) => c.type !== "EMAIL").map((c) => ({ ...c, value: c.value.replace("dairy-demo", "bread-demo") })),
  enrichment: { ...complete.enrichment, official_website: "https://bread-demo.example.com/" },
  website_checks: [{ candidate_url: "https://bread-demo.example.com/", official_url: "https://bread-demo.example.com/", status: "VERIFIED_STRONG", signals: ["INN_ON_SITE"], discovered_via: "EGRUL_EMAIL_DOMAIN", reason: null, checked_at: CHECKED }],
};

/** 10. P5-002A: verified official website (composite) that publishes no phone / e-mail (PARTIAL). */
const siteNoContacts: SupplierProfile360 = {
  ...complete,
  supplier: { ...complete.supplier, inn: "0000000010", display_name: "ООО «Демо Овощи»", legal_name: "ООО «ДЕМО ОВОЩИ»", short_name: null },
  enrichment: { ...complete.enrichment, status: "PARTIAL", reasons: ["NO_PUBLIC_PHONE_OR_EMAIL_ON_OFFICIAL_SITE"], official_website: "https://veg-demo.example.com/",
    website_verification: { status: "VERIFIED_COMPOSITE", signals: ["EXACT_LEGAL_NAME", "REGISTERED_STREET_ADDRESS"], discovered_via: "BRAVE_SEARCH_API", checked_at: CHECKED } },
  contacts: [
    { type: "WEBSITE", value: "https://veg-demo.example.com/", label: null, source_url: "https://veg-demo.example.com/", source_type: "FIRST_PARTY", checked_at: CHECKED, freshness_status: "UNKNOWN", verified: true, origin: "ENRICHMENT_PIPELINE", verification_basis: "OFFICIAL_SITE_VERIFIED_COMPOSITE:EXACT_LEGAL_NAME+REGISTERED_STREET_ADDRESS" },
    complete.contacts[3],
  ],
  freshness: { ...complete.freshness, contacts: "UNKNOWN", content_currency: "UNDATED" },
  website_checks: [{ candidate_url: "https://veg-demo.example.com/", official_url: "https://veg-demo.example.com/", status: "VERIFIED_COMPOSITE", signals: ["EXACT_LEGAL_NAME", "REGISTERED_STREET_ADDRESS"], discovered_via: "BRAVE_SEARCH_API", reason: null, checked_at: CHECKED }],
};

export type Supplier360FixtureKey = "complete" | "partial" | "innOnly" | "noContacts" | "failed" | "external" | "enrichError" | "inProgress" | "sitePhoneOnly" | "siteNoContacts";

export const SUPPLIER_360_FIXTURES: Record<Supplier360FixtureKey, SupplierProfile360> = {
  complete,
  partial,
  innOnly,
  noContacts,
  failed,
  external,
  enrichError,
  inProgress,
  sitePhoneOnly,
  siteNoContacts,
};

/** What a successful mock enrichment returns, per INN (the backend would re-query sources; here a fixed synthetic result). */
export function enrichedFixture(p: SupplierProfile360): SupplierProfile360 {
  const inn = p.supplier.inn;
  if (p.enrichment.status === "FAILED") {
    return {
      ...p,
      supplier: { ...p.supplier, entity_kind: "LEGAL_ENTITY", display_name: "ООО «Демо Поставка»", legal_name: "ООО «Демо Поставка»", legal_status: "ACTIVE", region: "Санкт-Петербург", identity_source_url: `${EGRUL}${inn}`, identity_source_type: "FNS_EGRUL" },
      enrichment: { ...p.enrichment, status: "PARTIAL", reasons: ["NO_WEBSITE_CANDIDATE"], retryable: false, last_enriched_at: CHECKED, cache: "REFRESHED" },
      evidence: [{ evidence_type: "LEGAL_IDENTITY", claim: `INN ${inn} is registered as «ООО «Демо Поставка»»`, value: null, source_url: `${EGRUL}${inn}`, source_type: "FNS_EGRUL", checked_at: CHECKED, valid_until: null, strength: "STRONG" }],
      freshness: { ...p.freshness, identity: "FRESH", identity_checked_at: CHECKED },
      sources: [{ source_url: `${EGRUL}${inn}`, source_type: "FNS_EGRUL", last_checked_at: CHECKED, used_for: ["LEGAL_IDENTITY"] }],
      last_run_attempts: [{ source: "FNS_EGRUL", outcome: "OK", detail: null, duration_ms: 2100 }],
    };
  }
  if (p.enrichment.status === "PARTIAL") return { ...p, enrichment: { ...p.enrichment, cache: "REFRESHED" } };
  return {
    ...complete,
    supplier: { ...complete.supplier, inn, display_name: "ООО «Демо Снабжение»", legal_name: "ООО «Демо Снабжение»", short_name: null, historically_known: p.supplier.historically_known, identity_source_url: `${EGRUL}${inn}` },
    enrichment: { ...complete.enrichment, status: "PARTIAL", reasons: ["NO_WEBSITE_CANDIDATE"], official_website: null, website_confidence: "NONE", cache: "MISS" },
    roles: [...p.roles],
    evidence: complete.evidence.filter((e) => e.evidence_type !== "WEBSITE_IDENTITY").map((e) => ({ ...e, source_url: `${EGRUL}${inn}`, claim: e.claim.replace("0000000001", inn) })),
    contacts: complete.contacts.filter((c) => c.type === "ADDRESS").map((c) => ({ ...c, source_url: `${EGRUL}${inn}` })),
    procurement_history_summary: p.procurement_history_summary,
    freshness: { ...complete.freshness, contacts: "FRESH", content_currency: "CURRENT" },
    sources: [{ source_url: `${EGRUL}${inn}`, source_type: "FNS_EGRUL", last_checked_at: CHECKED, used_for: ["LEGAL_IDENTITY", "LEGAL_STATUS", "OKVED_PRIMARY", "CONTACT_ADDRESS"] }],
  };
}
