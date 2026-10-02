/**
 * Mock stand-in for the P5-001A Supplier 360 endpoints (mock mode only). Synthetic fixtures; same error codes as the
 * backend (422 INVALID_INN, 404 SUPPLIER_NOT_FOUND, 503 DATA_UNAVAILABLE). Enrichment results live for the browser session.
 */
import type { SupplierProfile360 } from "@/lib/api/types";
import { MockApiError } from "./server";
import { SUPPLIER_360_FIXTURES, enrichedFixture } from "./supplier-360-fixtures";

const enriched = new Map<string, SupplierProfile360>();
const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

function find(inn: string): SupplierProfile360 {
  if (!/^\d{10}(\d{2})?$/.test(inn)) throw new MockApiError(422, "INVALID_INN", "INN must be 10 (legal entity) or 12 (individual entrepreneur) digits");
  const hit = enriched.get(inn) ?? Object.values(SUPPLIER_360_FIXTURES).find((p) => p.supplier.inn === inn);
  if (!hit) throw new MockApiError(404, "SUPPLIER_NOT_FOUND", `INN ${inn} is neither a historical supplier nor a curated candidate`);
  return hit;
}

export async function getProfile(inn: string): Promise<SupplierProfile360> {
  await delay(350);
  return structuredClone(find(inn));
}

export async function enrich(inn: string, refresh: boolean): Promise<SupplierProfile360> {
  const current = find(inn);
  await delay(1500);
  if (inn === SUPPLIER_360_FIXTURES.enrichError.supplier.inn) throw new MockApiError(503, "DATA_UNAVAILABLE", "enrichment sources unavailable (synthetic)");
  if (current.enrichment.status === "IN_PROGRESS") return structuredClone(current);
  if (!refresh && (current.enrichment.status === "COMPLETE" || current.enrichment.status === "PARTIAL")) {
    return structuredClone({ ...current, enrichment: { ...current.enrichment, cache: "HIT" } });
  }
  const next = enrichedFixture(current);
  enriched.set(inn, next);
  return structuredClone(next);
}
