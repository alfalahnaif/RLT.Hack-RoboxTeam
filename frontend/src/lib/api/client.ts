/**
 * Thin API client. `NEXT_PUBLIC_API_MODE=live` calls the FastAPI backend at NEXT_PUBLIC_API_BASE_URL
 * (default http://localhost:8000/api/v1); anything else uses the in-browser mock server (synthetic data).
 * Both paths raise `ApiError` with the error-envelope code (ED-07) so screens handle one shape.
 * P6-004 replaces the hand-written DTOs with generated types; the function signatures stay.
 */
import * as mock from "@/mocks/server";
import * as mock360 from "@/mocks/supplier-360";
import type {
  ApiErrorEnvelope,
  BackendHealth,
  ErrorCode,
  FeedbackRequest,
  FilterMeta,
  HealthStatus,
  ProcurementAnalysis,
  SearchRequest,
  SearchResponse,
  SearchRunSummary,
  SupplierSearchRequest,
  SupplierSearchResponse,
  SupplierProfile,
  SupplierProfile360,
} from "./types";

export const API_MODE: "live" | "mock" = process.env.NEXT_PUBLIC_API_MODE === "live" ? "live" : "mock";
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

/** Export links come from the API; keep downloads on the configured API origin. */
export function supplierExportUrl(path: string, format: "json" | "csv"): string | null {
  if (!path.trim()) return null;
  try {
    const base = new URL(BASE);
    const url = new URL(path, `${BASE.replace(/\/$/, "")}/`);
    if (url.origin !== base.origin || !["http:", "https:"].includes(url.protocol)) return null;
    url.searchParams.set("format", format);
    return url.toString();
  } catch {
    return null;
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: ErrorCode,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "network error");
  }
  if (!res.ok) {
    // ED-07 envelope `{error: {code, message}}`, or the FastAPI form `{detail: {code, message}}` used by the P3/P4 routes.
    const body = (await res.json().catch(() => null)) as (ApiErrorEnvelope & { detail?: { code?: ErrorCode; message?: string } }) | null;
    const err = body?.error ?? (body?.detail && typeof body.detail === "object" ? body.detail : undefined);
    throw new ApiError(res.status, err?.code ?? (res.status === 503 ? "SEARCH_UNAVAILABLE" : "VALIDATION_ERROR"), err?.message ?? res.statusText);
  }
  return (await res.json()) as T;
}

async function viaMock<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (e) {
    if (e instanceof mock.MockApiError) throw new ApiError(e.status, e.code, e.message);
    throw e;
  }
}

const live = API_MODE === "live";

/** P4-001 `/health` → the shell's `HealthStatus` shape (status pill + component tooltip). */
const adaptHealth = (h: BackendHealth): HealthStatus => ({
  status: h.status === "unavailable" ? "down" : h.status,
  components: {
    postgres: h.postgres === "reachable" ? "ok" : "down",
    semantic: h.semantic.status === "ready" ? "ok" : "degraded",
    evidence: h.curated_evidence_catalog.status === "ready" ? "ok" : "degraded",
  },
  versions: {},
});

/**
 * One in-flight request per lot: React dev StrictMode (and quick re-renders) start the same effect twice, and two concurrent
 * multi-second analyses would double the backend time. Nothing is cached once the request settles.
 */
const inflight = new Map<string, Promise<ProcurementAnalysis>>();
const analysisOnce = (lotId: string) => {
  const pending = inflight.get(lotId);
  if (pending) return pending;
  const p = http<ProcurementAnalysis>(`/procurements/${encodeURIComponent(lotId)}/analysis`).finally(() => inflight.delete(lotId));
  inflight.set(lotId, p);
  return p;
};

/** The integrated analysis exists only in the live backend; mock mode reports it as unavailable. */
const analysisUnavailable = () => Promise.reject(new ApiError(503, "SEARCH_UNAVAILABLE", "analysis requires NEXT_PUBLIC_API_MODE=live"));

export const api = {
  supplierSearch: (req: SupplierSearchRequest) => http<SupplierSearchResponse>("/supplier-search", { method: "POST", body: JSON.stringify(req) }),
  search: (req: SearchRequest) => (live ? http<SearchResponse>("/search", { method: "POST", body: JSON.stringify(req) }) : viaMock(() => mock.search(req))),
  getSearch: (requestId: string) => (live ? http<SearchResponse>(`/searches/${encodeURIComponent(requestId)}`) : viaMock(() => mock.getSearch(requestId))),
  listSearches: () => (live ? http<SearchRunSummary[]>("/searches") : viaMock(() => mock.listSearches())),
  getSupplier: (id: string, requestId?: string | null) =>
    live
      ? http<SupplierProfile>(`/suppliers/${encodeURIComponent(id)}${requestId ? `?request_id=${encodeURIComponent(requestId)}` : ""}`)
      : viaMock(() => mock.getSupplier(id, requestId)),
  sendFeedback: (req: FeedbackRequest) => (live ? http<{ feedback_id: string }>("/feedback", { method: "POST", body: JSON.stringify(req) }) : viaMock(() => mock.sendFeedback(req))),
  health: () => (live ? http<BackendHealth>("/health").then(adaptHealth) : viaMock(() => mock.health())),
  /** P4-002 main page request: procurement + recommendations + market intelligence in one response. */
  analysis: (lotId: string) => (live ? analysisOnce(lotId) : analysisUnavailable()),
  filterMeta: () => (live ? http<FilterMeta>("/meta/filters") : viaMock(() => mock.filterMeta())),
  /** P5-001A Supplier 360: stored profile, read-only (never queries external sources). */
  supplierProfile: (inn: string) =>
    live ? http<SupplierProfile360>(`/suppliers/${encodeURIComponent(inn)}/profile`) : viaMock(() => mock360.getProfile(inn)),
  /** P5-001A on-demand enrichment: synchronous and cache-first; `refresh` forces re-querying the sources. */
  enrichSupplier: (inn: string, refresh = false) =>
    live
      ? http<SupplierProfile360>(`/suppliers/${encodeURIComponent(inn)}/enrich${refresh ? "?refresh=true" : ""}`, { method: "POST" })
      : viaMock(() => mock360.enrich(inn, refresh)),
};

/** P5-001A exposes `POST /suppliers/{inn}/enrich`; `NEXT_PUBLIC_SUPPLIER_ENRICH=off` hides the trigger for a deployment without it. */
export const SUPPLIER_ENRICH_AVAILABLE = process.env.NEXT_PUBLIC_SUPPLIER_ENRICH !== "off";

export const isApiError = (e: unknown): e is ApiError => e instanceof ApiError;
