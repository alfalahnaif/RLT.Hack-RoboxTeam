/**
 * UI-only constants. Ranking/confidence thresholds belong to the backend config; the values here only
 * decide *presentation* (notices, meter tones) and are working assumptions until OQ-26 is answered.
 */
export const UI_CONFIG = {
  /** Query length rule (API_CONTRACTS: 3–1000 chars, trimmed). */
  queryMin: 3,
  queryMax: 1000,
  /** Results requested per page and the API ceiling (`limit` 1–100). */
  pageSize: 20,
  maxLimit: 100,
  /** Compare tray capacity (S-04: 2–5 suppliers). */
  compareMin: 2,
  compareMax: 5,
  /** OQ-26 working assumption: "low confidence" notice when every top result is below this (0–1). */
  lowConfidence: 0.4,
  /** How many top results the low-confidence check looks at. */
  lowConfidenceTopN: 5,
  /** Show the progress hint when a search takes longer than this (S-01: >1 s). */
  slowHintMs: 1000,
  /** Min-confidence filter options (0–1). */
  minConfidenceOptions: [0, 0.5, 0.7] as const,
} as const;

/**
 * P4-002 demo shortcuts (real canonical lots, not in the replay benchmark — no holdout). The shortcuts only fill the lot ID;
 * the analysis always comes from the live API. Primary: food lot with OKPD2 10.51.11.141 (concentrated pool + verified
 * external candidates). Fallback: golden recommendation case (laptops).
 */
export const DEMO_LOTS = { primary: "5956101", fallback: "5718896" } as const;

/** Presentation tone of a 0–1 confidence value (meter colour only — the number is always shown). */
export const confidenceTone = (v: number | null) => (v === null ? "warning" : v >= 0.7 ? "success" : v >= UI_CONFIG.lowConfidence ? "warning" : "danger");
