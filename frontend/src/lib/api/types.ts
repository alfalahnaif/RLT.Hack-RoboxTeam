/**
 * API DTOs — hand-mirrored from docs/architecture/API_CONTRACTS.md until P6-004 generates them from
 * `/openapi.json`. Scores are 0–1 floats exactly as the API returns them; the UI only formats them
 * (0–100 integers, ED-01) and never recomputes ranking, scores or reason codes (BR-02).
 * Fields marked [ER] are proposed additive extensions listed in SCREENS.md → "Contract notes".
 */

export type SupplierType = "manufacturer" | "distributor" | "supplier" | "service_provider" | "unknown";
export type MarketScope = "all" | "known" | "external";

/** Controlled reason-code vocabulary (SEARCH_AND_RANKING §6). */
export type ReasonCode =
  | "CATEGORY_MATCH"
  | "ATTRIBUTE_MATCH"
  | "SEMANTIC_MATCH"
  | "PROCUREMENT_EXPERIENCE"
  | "VERIFIED_MANUFACTURER"
  | "STRONG_PRODUCT_EVIDENCE"
  | "MULTI_SOURCE_VERIFICATION"
  | "KNOWN_SUPPLIER"
  | "EXTERNAL_SUPPLIER";

export type RiskFlag =
  | "LOW_EVIDENCE"
  | "STALE_INFORMATION"
  | "UNVERIFIED_MANUFACTURER"
  | "UNKNOWN_LEGAL_STATUS"
  | "AMBIGUOUS_ENTITY"
  | "NO_PROCUREMENT_HISTORY";

export type EvidenceType =
  | "PRODUCT_CATALOG"
  | "MANUFACTURER_REGISTRY"
  | "LEGAL_REGISTRY"
  | "PROCUREMENT_HISTORY"
  | "COMPANY_WEBSITE"
  | "DELIVERY_REGION"
  | "CERTIFICATION"
  | "OPEN_WEB_MENTION";

export type WarningCode =
  | "SEMANTIC_UNAVAILABLE"
  | "LLM_UNAVAILABLE"
  | "PARSER_FALLBACK"
  | "HISTORY_UNAVAILABLE"
  | "STALE_EXTERNAL_DATA"
  | "MULTI_ITEM_QUERY_DETECTED"
  | "LOW_INFORMATION_QUERY"
  | "FILTER_REGION_OVERRIDES_QUERY"
  | "NO_RESULTS";

export type ErrorCode =
  | "QUERY_TOO_SHORT"
  | "QUERY_TOO_LONG"
  | "INVALID_FILTER"
  | "VALIDATION_ERROR"
  | "SEARCH_UNAVAILABLE"
  | "SUPPLIER_NOT_FOUND"
  | "REQUEST_NOT_FOUND"
  | "NETWORK_ERROR"
  | "LOT_NOT_FOUND"
  | "HISTORICAL_DATA_UNAVAILABLE"
  | "INVALID_INN"
  | "CURATED_DATA_UNAVAILABLE"
  | "DATA_UNAVAILABLE";

/** Match Score features (SEARCH_AND_RANKING §3). */
export type RankingFeature = "semantic" | "lexical" | "category" | "attributes" | "experience" | "geography" | "supplier_type" | "delivery";

/** Confidence components (SEARCH_AND_RANKING §4). */
export type ConfidenceComponent = "product_evidence" | "legal_identity" | "recency" | "multi_source" | "completeness";

export type FieldOrigin = "extracted" | "user_edited";

export type SearchIntent = {
  product: string | null;
  category_terms: string[];
  attributes: Record<string, string | number>;
  quantity: number | null;
  region: string | null;
  supplier_types: SupplierType[];
  mandatory_constraints: string[];
};

export type IntentField = keyof SearchIntent;

export type ParsedQuery = SearchIntent & {
  field_origin: Partial<Record<IntentField, FieldOrigin>>;
};

export type SearchFilters = {
  region: string | null;
  supplier_type: SupplierType | null;
  market_scope: MarketScope;
  /** [ER] only suppliers with ≥1 relevant procurement record. */
  has_experience?: boolean;
  /** [ER] 0–1. */
  min_confidence?: number | null;
};

export type SearchRequest = {
  query: string;
  filters: SearchFilters;
  intent_overrides: Partial<SearchIntent> | null;
  limit: number;
};

export type Contribution = { feature: RankingFeature; points: number; applicable: boolean };

export type Evidence = {
  evidence_id: string;
  evidence_type: EvidenceType;
  claim: string;
  source_name: string;
  source_url: string | null;
  observed_at: string;
  /** 0–1. */
  confidence: number;
};

export type MatchedOffering = { offering_id: string; title: string; category_name: string };

/** [ER] Parameters used by the reason-code templates (counts, attribute names). */
export type ReasonParams = Partial<Record<ReasonCode, Record<string, string | number>>>;

export type SearchResult = {
  rank: number;
  supplier_id: string;
  supplier_name: string;
  supplier_type: SupplierType;
  supplier_type_verified: boolean;
  region_name: string | null;
  is_known_supplier: boolean;
  matched_offering: MatchedOffering;
  match_score: number;
  confidence_score: number | null;
  contributions: Contribution[];
  reason_codes: ReasonCode[];
  reason_params: ReasonParams;
  explanation: string;
  risk_flags: RiskFlag[];
  top_evidence: Evidence[];
};

export type MarketSummary = {
  known: number;
  external: number;
  by_type: Partial<Record<SupplierType, number>>;
  new_to_category: number | null;
};

export type SearchResponse = {
  request_id: string;
  query: string;
  created_at: string;
  filters: SearchFilters;
  intent_overrides: Partial<SearchIntent> | null;
  limit: number;
  parsed_query: ParsedQuery | null;
  total_candidates: number;
  market_summary: MarketSummary | null;
  results: SearchResult[];
  versions: { parser: string; ranking: string; index: string; embedding: string | null };
  timings: { parse_ms?: number; retrieval_ms: number; ranking_ms?: number; total_ms: number };
  warnings: WarningCode[];
  /** [ER] true when the corpus is the synthetic seed (BR-20). */
  synthetic_data: boolean;
};

export type LegalStatus = "active" | "liquidating" | "liquidated" | "unknown";

export type Offering = {
  offering_id: string;
  title: string;
  category_name: string;
  attributes: Record<string, string | number>;
  source_name: string;
  /** Matched the query of `query_context` (query-matched first). */
  matched: boolean;
};

export type ProcurementRecord = {
  record_id: string;
  title: string;
  date: string;
  role: "winner" | "participant";
  amount_rub: number | null;
  region_name: string | null;
  customer_name: string;
  /** Relevant to the query of `query_context`. */
  relevant: boolean;
};

export type DataSourceRef = { source_name: string; source_type: string; observed_at: string; is_synthetic: boolean };

export type QueryContext = {
  request_id: string;
  query: string;
  rank: number;
  match_score: number;
  confidence_score: number | null;
  contributions: Contribution[];
  reason_codes: ReasonCode[];
  reason_params: ReasonParams;
  explanation: string;
  matched_offering_ids: string[];
};

export type SupplierProfile = {
  supplier_id: string;
  /** [ER] set when the requested ID was merged into this supplier (EC-22). */
  redirected_from: string | null;
  legal_name: string;
  inn: string | null;
  ogrn: string | null;
  kpp: string | null;
  legal_status: LegalStatus;
  region_name: string | null;
  city: string | null;
  website: string | null;
  okved: { code: string; name: string }[];
  supplier_type: SupplierType;
  supplier_type_basis: { source_name: string; source_url: string | null; observed_at: string } | null;
  is_known_supplier: boolean;
  first_seen_at: string | null;
  confidence_score: number | null;
  confidence_breakdown: { component: ConfidenceComponent; value: number | null; weight: number }[];
  risk_flags: RiskFlag[];
  offerings: Offering[];
  procurement_history: ProcurementRecord[];
  evidence: Evidence[];
  sources: DataSourceRef[];
  data_quality_flags: string[];
  /** Present only when a known `request_id` was supplied. */
  query_context: QueryContext | null;
  /** "expired" when a `request_id` was supplied but is unknown (show profile without context). */
  context_status: "ok" | "expired" | "none";
};

export type Relevance = "relevant" | "not_relevant" | "unsure";
export type FeedbackRequest = { request_id: string; supplier_id: string; relevance: Relevance };

export type HealthStatus = {
  status: "ok" | "degraded" | "down";
  components: Record<string, "ok" | "degraded" | "down">;
  versions: Record<string, string>;
};

export type FilterMeta = {
  regions: { code: string; name: string; count: number }[];
  supplier_types: SupplierType[];
};

/** S-05 list item. */
export type SearchRunSummary = {
  request_id: string;
  query: string;
  created_at: string;
  result_count: number;
  market_scope: MarketScope;
};

export type ApiErrorEnvelope = { error: { code: ErrorCode; message: string; details?: Record<string, unknown>; request_id?: string } };

/* ------------------------------------------------------------------------------------------------
 * P4-002 — integrated procurement analysis (`GET /procurements/{lot_id}/analysis`, P4-001 backend).
 * Mirrors backend/app/api/recommendation_models.py + market_models.py. Rendered as returned; never recomputed.
 * ---------------------------------------------------------------------------------------------- */

export type SectionStatus = "OK" | "UNAVAILABLE";
export type SectionError = { code: string; message: string };

export type ProcurementItem = { line_no: number; product_name: string; okpd2_code: string | null; okpd2_code_raw: string };

export type Procurement = {
  lot_id: string;
  subject: string | null;
  publish_date: string;
  platform: "AIS_GZ" | "EM";
  start_price: number | null;
  customer_inn: string | null;
  items_total: number;
  items: ProcurementItem[];
};

export type SemanticEvidence = {
  lot_id: string;
  publish_date: string;
  product: string | null;
  okpd2: string | null;
  cosine: number;
  discovered_only_by_semantic: boolean;
  semantic_score_won: boolean;
};

export type RankedSupplier = {
  rank: number;
  supplier_id: string;
  supplier_inn: string;
  score: number;
  components: Record<string, number>;
  contributions: Record<string, number>;
  relevant_lots: number;
  relevant_awards: number;
  relevant_em_participations: number;
  relevant_ais_awards: number;
  best_products: string[];
  best_okpd2: string | null;
  most_recent_relevant: string;
  same_customer_history: boolean;
  evidence_lot_ids: string[];
  reasons: string[];
  semantic_evidence: SemanticEvidence[];
};

export type Recommendations = {
  lot_id: string;
  as_of: string;
  recommendation_version: string;
  config_name: string;
  semantic_enabled: boolean;
  warnings: string[];
  candidate_count: number;
  results: RankedSupplier[];
  timings_ms: Record<string, number>;
};

export type PoolStatus = "INSUFFICIENT_DATA" | "LOW" | "MODERATE" | "HIGH" | "VERY_HIGH";
export type ExpansionSignal = "EXPANSION_RECOMMENDED" | "REVIEW_POOL" | "NO_EXPANSION_SIGNAL" | "INSUFFICIENT_DATA";
export type VerificationStatus = "UNVERIFIED" | "UNDER_REVIEW" | "VERIFIED";
export type Strength = "NONE" | "WEAK" | "MODERATE" | "STRONG";

export type PoolHealth = {
  status: PoolStatus;
  lot_count: number;
  procurement_count: number;
  known_customer_count: number;
  observed_supplier_count: number;
  winning_supplier_count: number;
  recent_winning_supplier_count: number;
  award_count: number;
  top1_share: number | null;
  top3_share: number | null;
  hhi: number | null;
  alternative_supplier_count: number;
};

export type HistoricalAlternative = {
  supplier_id: string;
  supplier_inn: string | null;
  historical_award_count: number;
  observed_relation_count: number;
  is_winner_in_category: boolean;
};

export type ExternalEvidence = {
  evidence_type: string;
  source_name: string;
  source_url: string | null;
  source_record_id: string | null;
  source_authority: string;
  evidence_status: "ACTIVE" | "SUSPENDED" | "TERMINATED" | "UNKNOWN";
  verification_strength: Strength;
  target_product_support: "DIRECT" | "RELATED" | "NONE";
  product_scope: string[];
  evidence_date: string | null;
  valid_until: string | null;
  retrieved_at: string;
  role_assertion: string;
};

export type ExternalCandidate = {
  supplier_inn: string;
  company_name: string;
  aliases: string[];
  reconciliation_status: "CATEGORY_HISTORICAL" | "HISTORICAL_OTHER_CATEGORY" | "EXTERNAL_NEW" | "INVALID_INN";
  market_role: string;
  verification_status: VerificationStatus;
  verification_strength: Strength;
  target_product_match: string;
  exact_okpd2_asserted_by_source: boolean;
  why_candidate: string;
  verification_reason_codes: string[];
  review_reasons: string[];
  evidence_count: number;
  active_evidence_count: number;
  evidence_summary: ExternalEvidence[];
};

export type MarketIntelligence = {
  category: { okpd2: string; as_of: string };
  pool_health: PoolHealth;
  concentration: { signal: ExpansionSignal; reason_codes: string[] };
  historical_alternatives: HistoricalAlternative[];
  external_expansion: {
    available: boolean;
    evidence_checked_at: string | null;
    verified_count: number;
    under_review_count: number;
    candidates: ExternalCandidate[];
  };
};

export type MarketIntelligenceEntry = {
  okpd2: string;
  item_lines: number[];
  status: SectionStatus;
  data: MarketIntelligence | null;
  error: SectionError | null;
};

export type ProcurementAnalysis = {
  procurement: Procurement;
  recommendations: { status: SectionStatus; data: Recommendations | null; error: SectionError | null };
  market_intelligence: MarketIntelligenceEntry[];
  market_intelligence_as_of: string;
  items_without_okpd2: number[];
  availability: "COMPLETE" | "PARTIAL";
  timings_ms: Record<string, number>;
};

/** P4-001 `/health` as returned by the backend (adapted to `HealthStatus` for the shell status pill). */
export type BackendHealth = {
  status: "ok" | "degraded" | "unavailable";
  api: "ready";
  postgres: "reachable" | "unreachable";
  semantic: { status: "ready" | "unavailable"; reason: string | null; pinned_revision: string | null; hnsw_ready: boolean; model_loaded: boolean };
  curated_evidence_catalog: { status: "ready" | "unavailable"; seed_files: number; reason: string | null };
};

/** P4-005 fixed free-text discovery contract (`POST /supplier-search`). */
export type SupplierSearchRequest = {
  query: string;
  okpd2: string | null;
  region: string | null;
  limit: number;
};

export type SupplierFreshness = { last_checked_at: string | null; source_url: string | null; status: "FRESH" | "STALE" | "UNKNOWN" };
/** P4-005C: provenance of one populated contact field. */
export type ContactSource = {
  value: string;
  source_url: string;
  source_authority: "FIRST_PARTY" | "FNS_EGRUL_DERIVED_REGISTRY" | "REGULATORY_REGISTRY";
  checked_at: string;
  address_type?: "PUBLISHED_COMPANY_ADDRESS" | "REGISTERED_LEGAL_ADDRESS" | null;
};
export type SupplierContact = {
  phone: string | null;
  email: string | null;
  website: string | null;
  address: string | null;
  /** P4-005C additions (optional for backward safety). */
  sources?: Partial<Record<"phone" | "email" | "website" | "address", ContactSource>>;
  identity_basis?: string | null;
  /** Freshness of the contact information itself (an outdated page is STALE even if checked today). */
  freshness?: SupplierFreshness | null;
};

export type SupplierSearchResult = {
  rank: number;
  supplier_id: string;
  inn: string;
  company_name: string | null;
  registration_region: string | null;
  score: number;
  role: string | null;
  role_evidence_status: VerificationStatus | "NO_EVIDENCE";
  reasons: string[];
  historical_evidence: {
    relevant_lots: number;
    relevant_awards: number;
    relevant_ais_awards: number;
    relevant_em_participations: number;
    most_recent_relevant: string;
    best_products: string[];
    best_okpd2: string | null;
    evidence_lot_ids: string[];
    components: Record<string, number>;
    contributions: Record<string, number>;
  };
  semantic_evidence: SemanticEvidence[];
  contact: SupplierContact | null;
  freshness: SupplierFreshness | null;
};

export type SupplierSearchResponse = {
  search_id: string;
  query: {
    text: string;
    normalized_text: string;
    technical_tokens: string[];
    okpd2: string | null;
    region: string | null;
    limit: number;
    as_of: string;
  };
  classification: {
    provided_okpd2: string | null;
    suggested_okpd2: { okpd2: string; share: number; supporting_items: number; supporting_lots: number; example_products: string[] }[];
    history_status: "SUFFICIENT" | "SPARSE" | "NONE";
    history: { okpd2: string; lots: number; awards: number; status: "SUFFICIENT" | "SPARSE" | "NONE" } | null;
    text_okpd2_alignment: "ALIGNED" | "UNCERTAIN" | "MISMATCH" | null;
    ranking_okpd2: string | null;
    warnings: string[];
  };
  candidate_count: number;
  suppliers: SupplierSearchResult[];
  pool_health: {
    okpd2: string;
    source: "PROVIDED" | "SUGGESTED";
    status: SectionStatus;
    error: SectionError | null;
    pool_health: PoolHealth | null;
    concentration: { signal: ExpansionSignal; reason_codes: string[] } | null;
    historical_alternatives: HistoricalAlternative[];
  }[];
  external_expansion: {
    okpd2: string;
    source: "PROVIDED" | "SUGGESTED";
    available: boolean;
    evidence_checked_at: string | null;
    verified_count: number;
    under_review_count: number;
    candidates: (ExternalCandidate & { contact: SupplierContact; freshness: SupplierFreshness })[];
  }[];
  price_intelligence: { available: boolean; reason: string };
  integration: { export_available: boolean; export_formats: ("json" | "csv")[]; export_url: string };
  semantic_enabled: boolean;
  warnings: string[];
  timings_ms: Record<string, number>;
};

/* ------------------------------------------------------------------------------------------------
 * P5-001A — Supplier 360 profile (`GET /suppliers/{inn}/profile`, `POST /suppliers/{inn}/enrich?refresh=`).
 * Mirrors backend/app/api/supplier_profile_models.py. Dates are ISO strings; datetimes carry a timezone.
 * ---------------------------------------------------------------------------------------------- */

export type FreshnessStatus = "FRESH" | "STALE" | "UNKNOWN";
export type EnrichmentStatus = "NOT_ENRICHED" | "IN_PROGRESS" | "COMPLETE" | "PARTIAL" | "FAILED";
export type ProfileRole = "MANUFACTURER" | "OFFICIAL_DISTRIBUTOR" | "DISTRIBUTOR" | "SUPPLIER" | "UNKNOWN";
export type ProfileRoleStatus = "VERIFIED" | "INFERRED" | "UNDER_REVIEW" | "UNKNOWN";
export type ProfileContactType = "PHONE" | "EMAIL" | "WEBSITE" | "ADDRESS";

export type SupplierIdentity = {
  inn: string;
  entity_kind: string | null;
  /** Registry legal name, else the accepted curated name, else null (never invented). */
  display_name: string | null;
  legal_name: string | null;
  short_name: string | null;
  /** ACTIVE / CEASED as published by the registry; null when not enriched. */
  legal_status: string | null;
  ogrn: string | null;
  kpp: string | null;
  region: string | null;
  registered_address: string | null;
  registration_date: string | null;
  primary_okved: string | null;
  identity_source_url: string | null;
  identity_source_type: string | null;
  /** INN appears in the organizer procurement data. */
  historically_known: boolean;
};

export type EnrichmentState = {
  status: EnrichmentStatus;
  reasons: string[];
  retryable: boolean;
  last_enriched_at: string | null;
  official_website: string | null;
  website_confidence: "HIGH" | "MEDIUM" | "LOW" | "NONE";
  /** Website considered but not proven official (MEDIUM/LOW). */
  website_candidate: string | null;
  pipeline_version: string | null;
  cache: "HIT" | "MISS" | "REFRESHED" | "NONE";
};

export type ProfileContact = {
  type: ProfileContactType;
  value: string;
  label: string | null;
  source_url: string;
  source_type: string;
  checked_at: string;
  freshness_status: FreshnessStatus;
  verified: boolean;
  origin: "ENRICHMENT_PIPELINE" | "CURATED_P4_005C";
};

export type ProfileRoleItem = {
  role: ProfileRole;
  status: ProfileRoleStatus;
  basis: string;
  claim: string;
  strength: string;
  source_url: string | null;
  source_type: string;
  checked_at: string | null;
  origin: "ENRICHMENT_PIPELINE" | "CURATED_P3_002B" | "PROCUREMENT_HISTORY";
};

export type ProfileEvidence = {
  evidence_type: string;
  claim: string;
  value: string | null;
  source_url: string;
  source_type: string;
  checked_at: string;
  valid_until: string | null;
  strength: string;
};

export type ProfileFreshness = {
  policy_version: string;
  identity: FreshnessStatus;
  identity_checked_at: string | null;
  contacts: FreshnessStatus;
  contacts_last_checked_at: string | null;
  /** CURRENT / UNDATED / OUTDATED of the contact source page. */
  content_currency: string | null;
  profile_cache_valid_until: string | null;
  note: string;
};

export type ProcurementHistorySummary = {
  observed_relations: number;
  relevant_awards: number;
  distinct_lots: number;
  first_observed_activity: string | null;
  last_observed_activity: string | null;
  platforms: Record<string, number>;
  top_okpd2: { okpd2: string; awarded_lots: number }[];
  note: string;
};

export type ProfileSource = { source_url: string; source_type: string; last_checked_at: string | null; used_for: string[] };

export type SupplierProfile360 = {
  supplier: SupplierIdentity;
  enrichment: EnrichmentState;
  contacts: ProfileContact[];
  roles: ProfileRoleItem[];
  evidence: ProfileEvidence[];
  freshness: ProfileFreshness;
  procurement_history_summary: ProcurementHistorySummary | null;
  sources: ProfileSource[];
  last_run_attempts: { source: string; outcome: string; detail: string | null; duration_ms: number }[];
};
