/**
 * In-browser stand-in for the FastAPI backend (mock mode only — NEXT_PUBLIC_API_MODE !== "live").
 * It plays the server role: parsing, scoring and reason codes happen HERE, never in UI components.
 * Formulas follow SEARCH_AND_RANKING §3–§6 so the screens receive realistic, internally consistent data:
 * contributions are integer points that sum exactly to Match × 100.
 * Runs are persisted in sessionStorage to emulate `GET /searches/{id}` (ED-02, US-08).
 */
import type {
  ConfidenceComponent,
  Contribution,
  ErrorCode,
  Evidence,
  FeedbackRequest,
  FilterMeta,
  HealthStatus,
  IntentField,
  ParsedQuery,
  RankingFeature,
  ReasonCode,
  ReasonParams,
  SearchIntent,
  SearchRequest,
  SearchResponse,
  SearchResult,
  SearchRunSummary,
  SupplierProfile,
  SupplierType,
  WarningCode,
} from "@/lib/api/types";
import { ADJACENT, REDIRECTS, REGIONS, SPB, SUPPLIERS, type MockEvidence, type MockSupplier, type Topic } from "./fixtures";

export class MockApiError extends Error {
  constructor(
    public status: number,
    public code: ErrorCode,
    message: string,
  ) {
    super(message);
  }
}

/* ---------------------------------------------------------------- scenarios */

export type Scenario = "normal" | "unavailable" | "llm_down" | "semantic_down" | "slow";
export const SCENARIOS: Scenario[] = ["normal", "unavailable", "llm_down", "semantic_down", "slow"];

const SCENARIO_KEY = "sr.mock.scenario";
const RUNS_KEY = "sr.mock.runs";
const FEEDBACK_KEY = "sr.mock.feedback";

const read = <T,>(key: string, fallback: T): T => {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
};
const write = (key: string, value: unknown) => {
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage full / disabled — runs simply are not restorable */
  }
};

export const getScenario = (): Scenario => read<Scenario>(SCENARIO_KEY, "normal");
export const setScenario = (s: Scenario) => write(SCENARIO_KEY, s);

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

/* ------------------------------------------------------------------- config */

const RANKING_VERSION = "1.0.0-mock";
const WEIGHTS: Record<RankingFeature, number> = {
  semantic: 0.3,
  lexical: 0.2,
  category: 0.15,
  attributes: 0.15,
  experience: 0.08,
  geography: 0.05,
  supplier_type: 0.04,
  delivery: 0.03,
};
const CONF_WEIGHTS: Record<ConfidenceComponent, number> = { product_evidence: 0.3, legal_identity: 0.25, recency: 0.15, multi_source: 0.15, completeness: 0.15 };

/* ------------------------------------------------------------------- parser */

const TOPIC_RULES: { topic: Topic; re: RegExp; product: string; categories: string[] }[] = [
  { topic: "panels", re: /панел|interactive|panel|доск/i, product: "интерактивная панель", categories: ["интерактивные панели", "образовательное оборудование"] },
  { topic: "laptops", re: /ноутбук|laptop|notebook/i, product: "ноутбук", categories: ["ноутбуки", "вычислительная техника"] },
  { topic: "furniture", re: /парт|мебел|desk|furniture/i, product: "парта ученическая", categories: ["школьная мебель"] },
];

function detectTopic(intent: SearchIntent): Topic | null {
  const text = [intent.product, ...intent.category_terms].join(" ");
  return TOPIC_RULES.find((r) => r.re.test(text))?.topic ?? null;
}

function parse(query: string): ParsedQuery {
  const q = query.toLowerCase();
  const rule = TOPIC_RULES.find((r) => r.re.test(q));
  const attributes: Record<string, string | number> = {};
  const size = q.match(/(\d{2}(?:[.,]\d)?)\s*(?:"|дюйм|inch|”)/);
  if (size) attributes.screen_size_inches = Number(size[1].replace(",", "."));
  const ram = q.match(/(\d{1,2})\s*(?:гб|gb)/);
  if (ram) attributes.ram_gb = Number(ram[1]);
  if (/регулируем|adjustable/.test(q)) attributes.adjustable = "да";
  const qty = q.match(/(\d+)\s*(?:шт|pcs|units|штук)/);
  const region = /петербург|спб|saint|petersburg/.test(q) ? SPB : null;
  const supplier_types: SupplierType[] = [];
  if (/производител|manufacturer/.test(q)) supplier_types.push("manufacturer");
  if (/дистрибьют|distributor/.test(q)) supplier_types.push("distributor");
  const mandatory_constraints: string[] = [];
  if (/только\s+(от\s+)?производител|only\s+manufacturer/.test(q)) mandatory_constraints.push("только производитель");

  const intent: SearchIntent = {
    product: rule?.product ?? null,
    category_terms: rule?.categories ?? [],
    attributes,
    quantity: qty ? Number(qty[1]) : null,
    region,
    supplier_types,
    mandatory_constraints,
  };
  const field_origin: ParsedQuery["field_origin"] = {};
  (Object.keys(intent) as IntentField[]).forEach((k) => {
    const v = intent[k];
    const present = Array.isArray(v) ? v.length > 0 : v && typeof v === "object" ? Object.keys(v).length > 0 : v !== null;
    if (present) field_origin[k] = "extracted";
  });
  return { ...intent, field_origin };
}

function applyOverrides(parsed: ParsedQuery, overrides: Partial<SearchIntent> | null): ParsedQuery {
  if (!overrides) return parsed;
  const next: ParsedQuery = { ...parsed, field_origin: { ...parsed.field_origin } };
  (Object.keys(overrides) as IntentField[]).forEach((k) => {
    (next as Record<string, unknown>)[k] = overrides[k];
    next.field_origin[k] = "user_edited";
  });
  return next;
}

/* ------------------------------------------------------------------ scoring */

const withoutTopic = (e: MockEvidence): Evidence => {
  const { topic, ...rest } = e;
  void topic;
  return rest;
};

const relevantHistory = (s: MockSupplier, topic: Topic) => s.history.filter((h) => h.topic === topic);

function featureValues(s: MockSupplier, topic: Topic, intent: SearchIntent): Record<RankingFeature, number> {
  const sig = s.signals[topic] ?? {};
  const n = relevantHistory(s, topic).length;
  const geo = !intent.region ? 0 : s.region === intent.region ? 1 : ADJACENT[intent.region]?.includes(s.region) ? 0.5 : 0;
  const typeFit = !intent.supplier_types.length ? 0 : s.type === "unknown" ? 0.5 : intent.supplier_types.includes(s.type) ? 1 : 0;
  return {
    semantic: sig.semantic ?? 0,
    lexical: sig.lexical ?? 0,
    category: sig.category ?? 0,
    attributes: sig.attributes ?? 0,
    experience: 1 - Math.exp(-n / 3),
    geography: geo,
    supplier_type: typeFit,
    delivery: intent.region ? (sig.delivery ?? 0) : 0,
  };
}

/** Applicability is decided per query, never per supplier (BR-05). */
function applicableFeatures(intent: SearchIntent, semanticUp: boolean): Record<RankingFeature, boolean> {
  return {
    semantic: semanticUp,
    lexical: true,
    category: intent.category_terms.length > 0,
    attributes: Object.keys(intent.attributes).length > 0,
    experience: true,
    geography: Boolean(intent.region),
    supplier_type: intent.supplier_types.length > 0,
    delivery: Boolean(intent.region),
  };
}

function contributionsFor(values: Record<RankingFeature, number>, applicable: Record<RankingFeature, boolean>): Contribution[] {
  const features = Object.keys(WEIGHTS) as RankingFeature[];
  const denom = features.filter((f) => applicable[f]).reduce((s, f) => s + WEIGHTS[f], 0);
  return features.map((f) => ({ feature: f, applicable: applicable[f], points: applicable[f] ? Math.round((100 * WEIGHTS[f] * values[f]) / denom) : 0 }));
}

export function confidenceOf(s: MockSupplier): number | null {
  const parts = (Object.keys(CONF_WEIGHTS) as ConfidenceComponent[]).filter((c) => s.confidence[c] !== null);
  if (!parts.length) return null;
  const w = parts.reduce((a, c) => a + CONF_WEIGHTS[c], 0);
  return Math.round((parts.reduce((a, c) => a + CONF_WEIGHTS[c] * (s.confidence[c] as number), 0) / w) * 100) / 100;
}

function reasonsFor(s: MockSupplier, topic: Topic, v: Record<RankingFeature, number>, app: Record<RankingFeature, boolean>, intent: SearchIntent) {
  const codes: ReasonCode[] = [];
  const params: ReasonParams = {};
  if (app.category && v.category === 1) codes.push("CATEGORY_MATCH");
  if (app.attributes && v.attributes >= 0.5) {
    codes.push("ATTRIBUTE_MATCH");
    const requested = Object.keys(intent.attributes).length;
    params.ATTRIBUTE_MATCH = { matched: Math.round(v.attributes * requested), requested };
  }
  if (app.semantic && v.semantic >= 0.6) codes.push("SEMANTIC_MATCH");
  const n = relevantHistory(s, topic).length;
  if (n >= 1) {
    codes.push("PROCUREMENT_EXPERIENCE");
    params.PROCUREMENT_EXPERIENCE = { count: n };
  }
  if (s.type === "manufacturer" && s.type_verified) codes.push("VERIFIED_MANUFACTURER");
  if ((s.confidence.product_evidence ?? 0) >= 0.7) codes.push("STRONG_PRODUCT_EVIDENCE");
  if ((s.confidence.multi_source ?? 0) >= 0.7) {
    codes.push("MULTI_SOURCE_VERIFICATION");
    params.MULTI_SOURCE_VERIFICATION = { count: s.sources.length };
  }
  codes.push(s.known ? "KNOWN_SUPPLIER" : "EXTERNAL_SUPPLIER");
  return { codes, params };
}

/* -------------------------------------------------------------------- store */

type StoredRun = { response: SearchResponse; topic: Topic | null };

const loadRuns = () => read<StoredRun[]>(RUNS_KEY, []);
const saveRun = (run: StoredRun) => write(RUNS_KEY, [run, ...loadRuns().filter((r) => r.response.request_id !== run.response.request_id)].slice(0, 25));
const findRun = (id: string) => loadRuns().find((r) => r.response.request_id === id);

const uuid = () => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `req-${Date.now()}-${Math.random().toString(16).slice(2)}`);

/* --------------------------------------------------------------- endpoints */

export async function search(req: SearchRequest): Promise<SearchResponse> {
  const started = performance.now();
  const scenario = getScenario();
  const query = req.query.trim();
  await delay(scenario === "slow" ? 2600 : 650);

  if (query.length < 3) throw new MockApiError(422, "QUERY_TOO_SHORT", "query must be at least 3 characters");
  if (query.length > 1000) throw new MockApiError(422, "QUERY_TOO_LONG", "query must be at most 1000 characters");
  if (scenario === "unavailable") throw new MockApiError(503, "SEARCH_UNAVAILABLE", "search index is not reachable");

  const warnings: WarningCode[] = [];
  if (scenario === "llm_down") warnings.push("LLM_UNAVAILABLE", "PARSER_FALLBACK");
  const semanticUp = scenario !== "semantic_down";
  if (!semanticUp) warnings.push("SEMANTIC_UNAVAILABLE");

  const intent = applyOverrides(parse(query), req.intent_overrides);
  const topic = detectTopic(intent);
  if (!intent.product && query.split(/\s+/).length < 3) warnings.push("LOW_INFORMATION_QUERY");
  if (req.filters.region && intent.region && req.filters.region !== intent.region) warnings.push("FILTER_REGION_OVERRIDES_QUERY");
  if (topic === "furniture") warnings.push("STALE_EXTERNAL_DATA");

  const effective: SearchIntent = { ...intent, region: req.filters.region ?? intent.region };
  const app = applicableFeatures(effective, semanticUp);
  const onlyManufacturers = effective.mandatory_constraints.some((c) => /производител|manufacturer/i.test(c));

  const candidates = topic ? SUPPLIERS.filter((s) => s.signals[topic]) : [];
  const scored: SearchResult[] = candidates
    .filter((s) => {
      if (onlyManufacturers && s.type !== "manufacturer") return false;
      if (req.filters.market_scope === "known" && !s.known) return false;
      if (req.filters.market_scope === "external" && s.known) return false;
      if (req.filters.supplier_type && s.type !== req.filters.supplier_type) return false;
      if (req.filters.region && s.region !== req.filters.region) return false;
      if (req.filters.has_experience && topic && relevantHistory(s, topic).length === 0) return false;
      const conf = confidenceOf(s);
      if (req.filters.min_confidence && (conf ?? 0) < req.filters.min_confidence) return false;
      return true;
    })
    .map((s) => {
      const t = topic as Topic;
      const v = featureValues(s, t, effective);
      const contributions = contributionsFor(v, app);
      const match = contributions.reduce((a, c) => a + c.points, 0) / 100;
      const { codes, params } = reasonsFor(s, t, v, app, effective);
      const offering = s.offerings.filter((o) => o.topic === t).sort((a, b) => Number(b.attributes.screen_size_inches === effective.attributes.screen_size_inches) - Number(a.attributes.screen_size_inches === effective.attributes.screen_size_inches))[0];
      return {
        rank: 0,
        supplier_id: s.id,
        supplier_name: s.legal_name,
        supplier_type: s.type,
        supplier_type_verified: s.type_verified,
        region_name: s.region,
        is_known_supplier: s.known,
        matched_offering: { offering_id: offering.id, title: offering.title, category_name: offering.category },
        match_score: match,
        confidence_score: confidenceOf(s),
        contributions,
        reason_codes: codes,
        reason_params: params,
        explanation: "",
        risk_flags: s.risk_flags,
        top_evidence: s.evidence.filter((e) => e.topic === t || e.topic === null).slice(0, 3).map(withoutTopic),
      } satisfies SearchResult;
    })
    // Tie-break ED-09: Match desc → Confidence desc → supplier_id asc.
    .sort((a, b) => b.match_score - a.match_score || (b.confidence_score ?? 0) - (a.confidence_score ?? 0) || a.supplier_id.localeCompare(b.supplier_id))
    .map((r, i) => ({ ...r, rank: i + 1 }));

  if (!scored.length) warnings.push("NO_RESULTS");
  const results = scored.slice(0, req.limit);
  const by_type: Partial<Record<SupplierType, number>> = {};
  scored.forEach((r) => (by_type[r.supplier_type] = (by_type[r.supplier_type] ?? 0) + 1));

  const response: SearchResponse = {
    request_id: uuid(),
    query,
    created_at: new Date().toISOString(),
    filters: req.filters,
    intent_overrides: req.intent_overrides,
    limit: req.limit,
    parsed_query: intent,
    total_candidates: candidates.reduce((a, s) => a + s.offerings.filter((o) => o.topic === topic).length, 0),
    market_summary: {
      known: scored.filter((r) => r.is_known_supplier).length,
      external: scored.filter((r) => !r.is_known_supplier).length,
      by_type,
      new_to_category: null,
    },
    results,
    versions: { parser: "rules-0.1.0", ranking: RANKING_VERSION, index: "seed-2026-09-29", embedding: semanticUp ? "e5-base@mock" : null },
    timings: { parse_ms: 4, retrieval_ms: 0, ranking_ms: 0, total_ms: 0 },
    warnings,
    synthetic_data: true,
  };
  const total = Math.round(performance.now() - started);
  response.timings = { parse_ms: 4, retrieval_ms: Math.round(total * 0.7), ranking_ms: Math.round(total * 0.1), total_ms: total };
  saveRun({ response, topic });
  return response;
}

export async function getSearch(requestId: string): Promise<SearchResponse> {
  await delay(120);
  const run = findRun(requestId);
  if (!run) throw new MockApiError(404, "REQUEST_NOT_FOUND", "search run not found");
  return run.response;
}

export async function listSearches(): Promise<SearchRunSummary[]> {
  await delay(150);
  return loadRuns().map(({ response: r }) => ({ request_id: r.request_id, query: r.query, created_at: r.created_at, result_count: r.results.length, market_scope: r.filters.market_scope }));
}

export async function getSupplier(id: string, requestId?: string | null): Promise<SupplierProfile> {
  await delay(getScenario() === "slow" ? 1500 : 350);
  const resolved = REDIRECTS[id] ?? id;
  const s = SUPPLIERS.find((x) => x.id === resolved);
  if (!s) throw new MockApiError(404, "SUPPLIER_NOT_FOUND", "supplier not found");

  const run = requestId ? findRun(requestId) : undefined;
  const result = run?.response.results.find((r) => r.supplier_id === s.id);
  const topic = run?.topic ?? null;
  const offerings = s.offerings.map((o) => ({ offering_id: o.id, title: o.title, category_name: o.category, attributes: o.attributes, source_name: o.source, matched: topic !== null && o.topic === topic }));
  offerings.sort((a, b) => Number(b.matched) - Number(a.matched));
  const history = s.history
    .map((h) => ({ record_id: h.id, title: h.title, date: h.date, role: h.role, amount_rub: h.amount, region_name: h.region, customer_name: h.customer, relevant: topic !== null && h.topic === topic }))
    .sort((a, b) => Number(b.relevant) - Number(a.relevant) || b.date.localeCompare(a.date));

  return {
    supplier_id: s.id,
    redirected_from: resolved !== id ? id : null,
    legal_name: s.legal_name,
    inn: s.inn,
    ogrn: s.ogrn,
    kpp: s.kpp,
    legal_status: s.legal_status,
    region_name: s.region,
    city: s.city,
    website: s.website,
    okved: s.okved,
    supplier_type: s.type,
    supplier_type_basis: s.type_basis,
    is_known_supplier: s.known,
    first_seen_at: s.first_seen,
    confidence_score: confidenceOf(s),
    confidence_breakdown: (Object.keys(CONF_WEIGHTS) as ConfidenceComponent[]).map((c) => ({ component: c, value: s.confidence[c], weight: CONF_WEIGHTS[c] })),
    risk_flags: s.risk_flags,
    offerings,
    procurement_history: history,
    evidence: s.evidence.map(withoutTopic),
    sources: s.sources.map((x) => ({ ...x, is_synthetic: true })),
    data_quality_flags: s.data_quality_flags,
    query_context:
      run && result
        ? {
            request_id: run.response.request_id,
            query: run.response.query,
            rank: result.rank,
            match_score: result.match_score,
            confidence_score: result.confidence_score,
            contributions: result.contributions,
            reason_codes: result.reason_codes,
            reason_params: result.reason_params,
            explanation: result.explanation,
            matched_offering_ids: offerings.filter((o) => o.matched).map((o) => o.offering_id),
          }
        : null,
    context_status: !requestId ? "none" : run && result ? "ok" : "expired",
  };
}

export async function sendFeedback(req: FeedbackRequest): Promise<{ feedback_id: string }> {
  await delay(250);
  if (!findRun(req.request_id)) throw new MockApiError(404, "REQUEST_NOT_FOUND", "search run not found");
  const all = read<Record<string, FeedbackRequest>>(FEEDBACK_KEY, {});
  const key = `${req.request_id}:${req.supplier_id}`;
  all[key] = req; // upsert on (request_id, supplier_id)
  write(FEEDBACK_KEY, all);
  return { feedback_id: key };
}

export function getStoredFeedback(requestId: string, supplierId: string) {
  return read<Record<string, FeedbackRequest>>(FEEDBACK_KEY, {})[`${requestId}:${supplierId}`]?.relevance ?? null;
}

export async function health(): Promise<HealthStatus> {
  await delay(100);
  const sc = getScenario();
  const status = sc === "unavailable" ? "down" : sc === "normal" || sc === "slow" ? "ok" : "degraded";
  return {
    status,
    components: {
      api: "ok",
      db: sc === "unavailable" ? "down" : "ok",
      search_index: sc === "unavailable" ? "down" : "ok",
      embedding_model: sc === "semantic_down" ? "down" : "ok",
      llm: sc === "llm_down" ? "down" : "ok",
    },
    versions: { ranking: RANKING_VERSION, parser: "rules-0.1.0" },
  };
}

export async function filterMeta(): Promise<FilterMeta> {
  await delay(80);
  return {
    regions: REGIONS.map((name) => ({ code: name, name, count: SUPPLIERS.filter((s) => s.region === name).length })),
    supplier_types: ["manufacturer", "distributor", "supplier", "service_provider", "unknown"],
  };
}
