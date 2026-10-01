/**
 * Thin API client. `NEXT_PUBLIC_API_MODE=live` calls the FastAPI backend at NEXT_PUBLIC_API_BASE_URL
 * (default http://localhost:8000/api/v1); anything else uses the in-browser mock server (synthetic data).
 * Both paths raise `ApiError` with the error-envelope code (ED-07) so screens handle one shape.
 * P6-004 replaces the hand-written DTOs with generated types; the function signatures stay.
 */
import * as mock from "@/mocks/server";
import type {
  ApiErrorEnvelope,
  ErrorCode,
  FeedbackRequest,
  FilterMeta,
  HealthStatus,
  SearchRequest,
  SearchResponse,
  SearchRunSummary,
  SupplierProfile,
} from "./types";

export const API_MODE: "live" | "mock" = process.env.NEXT_PUBLIC_API_MODE === "live" ? "live" : "mock";
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

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
    const body = (await res.json().catch(() => null)) as ApiErrorEnvelope | null;
    throw new ApiError(res.status, body?.error.code ?? (res.status === 503 ? "SEARCH_UNAVAILABLE" : "VALIDATION_ERROR"), body?.error.message ?? res.statusText);
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

export const api = {
  search: (req: SearchRequest) => (live ? http<SearchResponse>("/search", { method: "POST", body: JSON.stringify(req) }) : viaMock(() => mock.search(req))),
  getSearch: (requestId: string) => (live ? http<SearchResponse>(`/searches/${encodeURIComponent(requestId)}`) : viaMock(() => mock.getSearch(requestId))),
  listSearches: () => (live ? http<SearchRunSummary[]>("/searches") : viaMock(() => mock.listSearches())),
  getSupplier: (id: string, requestId?: string | null) =>
    live
      ? http<SupplierProfile>(`/suppliers/${encodeURIComponent(id)}${requestId ? `?request_id=${encodeURIComponent(requestId)}` : ""}`)
      : viaMock(() => mock.getSupplier(id, requestId)),
  sendFeedback: (req: FeedbackRequest) => (live ? http<{ feedback_id: string }>("/feedback", { method: "POST", body: JSON.stringify(req) }) : viaMock(() => mock.sendFeedback(req))),
  health: () => (live ? http<HealthStatus>("/health") : viaMock(() => mock.health())),
  filterMeta: () => (live ? http<FilterMeta>("/meta/filters") : viaMock(() => mock.filterMeta())),
};

export const isApiError = (e: unknown): e is ApiError => e instanceof ApiError;
