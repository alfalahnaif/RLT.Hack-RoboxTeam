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
  | "NETWORK_ERROR";

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
