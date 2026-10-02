// P5-001B Supplier 360 view-model tests over the synthetic P5-001A fixtures.
// Run: npm test  (node --test; Node >= 23.6 strips the TypeScript types of the imported modules — no extra dependencies).
import assert from "node:assert/strict";
import { test } from "node:test";
import { readFileSync } from "node:fs";
import {
  enrichmentView,
  hasMarketRoleEvidence,
  hasReachableContact,
  sourceClass,
  evidenceCheckedAt,
  headerRoles,
  isInnOnly,
  mailHref,
  orderedContacts,
  primaryContactHref,
  profileName,
  roleGroups,
  safeBackHref,
  safeHttpUrl,
  supplierProfileHref,
  telHref,
} from "../src/features/supplier-360/model.ts";
import { SUPPLIER_360_FIXTURES as F, enrichedFixture } from "../src/mocks/supplier-360-fixtures.ts";

test("complete profile: name, verified manufacturer first, no enrichment notice", () => {
  const p = F.complete;
  assert.equal(profileName(p.supplier), "ООО «Демо Молочный Комбинат»");
  assert.deepEqual(headerRoles(p.roles), [
    { role: "MANUFACTURER", status: "VERIFIED" },
    { role: "SUPPLIER", status: "VERIFIED" },
  ]);
  assert.deepEqual(enrichmentView(p.enrichment, true), { notice: null, action: null });
  assert.deepEqual(orderedContacts(p.contacts).map((c) => c.type), ["PHONE", "EMAIL", "WEBSITE", "ADDRESS"]);
  assert.equal(primaryContactHref(p.contacts), "mailto:sales@dairy-demo.example.com");
});

test("partial profile: cache-first refresh allowed, stale contacts kept visible, inferred distributor stays weaker than verified", () => {
  const p = F.partial;
  assert.deepEqual(enrichmentView(p.enrichment, true), { notice: "partial", action: { kind: "refresh", refresh: false } });
  assert.ok(p.contacts.every((c) => c.freshness_status === "STALE"));
  assert.equal(orderedContacts(p.contacts).length, p.contacts.length, "stale contacts are not filtered out");
  const groups = roleGroups(p.roles);
  assert.deepEqual(groups.map((g) => [g.role, g.status]), [
    ["SUPPLIER", "VERIFIED"],
    ["MANUFACTURER", "UNDER_REVIEW"],
    ["DISTRIBUTOR", "INFERRED"],
  ]);
  assert.equal(primaryContactHref(p.contacts), "tel:+70000000002");
});

test("INN-only profile: no invented name, enrich action without refresh", () => {
  const p = F.innOnly;
  assert.equal(profileName(p.supplier), null);
  assert.ok(isInnOnly({ ...p, procurement_history_summary: null }));
  assert.deepEqual(enrichmentView(p.enrichment, true), { notice: "notEnriched", action: { kind: "enrich", refresh: false } });
  assert.deepEqual(enrichmentView(p.enrichment, false), { notice: "notEnriched", action: null }, "no trigger when the endpoint is off");
});

test("no contacts + unknown freshness + role unknown", () => {
  const p = F.noContacts;
  assert.equal(orderedContacts(p.contacts).length, 0);
  assert.equal(primaryContactHref(p.contacts), null);
  assert.equal(p.freshness.contacts, "UNKNOWN");
  assert.deepEqual(headerRoles(p.roles), [], "UNKNOWN role produces no header badge → 'Role unknown'");
  assert.deepEqual(roleGroups(p.roles).map((g) => g.role), ["UNKNOWN"]);
});

test("failed profile: retry only when retryable", () => {
  assert.deepEqual(enrichmentView(F.failed.enrichment, true), { notice: "failed", action: { kind: "retry", refresh: true } });
  assert.deepEqual(enrichmentView({ ...F.failed.enrichment, retryable: false }, true), { notice: "failed", action: null });
  const retried = enrichedFixture(F.failed);
  assert.equal(retried.enrichment.status, "PARTIAL");
});

test("in-progress profile: no second trigger", () => {
  assert.deepEqual(enrichmentView(F.inProgress.enrichment, true), { notice: "inProgress", action: null });
});

test("external candidate renders through the same model: curated contacts, verified manufacturer, no history", () => {
  const p = F.external;
  assert.equal(p.supplier.historically_known, false);
  assert.equal(p.procurement_history_summary, null);
  assert.equal(profileName(p.supplier), "АО «Демо Агрохолдинг»");
  assert.deepEqual(headerRoles(p.roles), [{ role: "MANUFACTURER", status: "VERIFIED" }]);
  assert.ok(p.contacts.every((c) => c.origin === "CURATED_P4_005C" && c.freshness_status === "UNKNOWN"));
  assert.deepEqual(enrichmentView(p.enrichment, true).action, { kind: "enrich", refresh: false });
  assert.equal(evidenceCheckedAt(p), "2026-09-28T09:15:00+00:00");
});

test("enrichment of an INN-only supplier keeps the INN and the history", () => {
  const next = enrichedFixture(F.innOnly);
  assert.equal(next.supplier.inn, F.innOnly.supplier.inn);
  assert.deepEqual(next.procurement_history_summary, F.innOnly.procurement_history_summary);
  assert.notEqual(profileName(next.supplier), null);
});

test("links are safe: http(s) only, tel/mailto validated, back href relative only", () => {
  assert.equal(safeHttpUrl("javascript:alert(1)"), null);
  assert.equal(safeHttpUrl("example.com"), null);
  assert.equal(safeHttpUrl("example.com", true), "https://example.com/");
  assert.equal(telHref("+7 (000) 000-00-01"), "tel:+70000000001");
  assert.equal(telHref("—"), null);
  assert.equal(mailHref("not an email"), null);
  assert.equal(safeBackHref("/results?q=молоко"), "/results?q=молоко");
  assert.equal(safeBackHref("//evil.example"), null);
  assert.equal(safeBackHref("https://evil.example"), null);
  assert.equal(safeBackHref("/javascript:alert(1)"), null);
  assert.equal(supplierProfileHref("7801234567", "/analysis?lot=1"), "/supplier-360/7801234567?back=%2Fanalysis%3Flot%3D1");
  assert.equal(supplierProfileHref("7801234567", "//x"), "/supplier-360/7801234567");
});

test("every fixture INN is unique and synthetic (0000… prefix)", () => {
  const inns = Object.values(F).map((p) => p.supplier.inn);
  assert.equal(new Set(inns).size, inns.length);
  assert.ok(inns.every((i) => /^0{6}/.test(i)));
});

test("source classes keep official, website, secondary, history and curated sources apart", () => {
  assert.equal(sourceClass("FNS_EGRUL"), "OFFICIAL_REGISTRY");
  assert.equal(sourceClass("FNS_EGRUL_EXTRACT"), "OFFICIAL_REGISTRY");
  assert.equal(sourceClass("FIRST_PARTY"), "COMPANY_WEBSITE");
  assert.equal(sourceClass("FNS_EGRUL_DERIVED_REGISTRY"), "SECONDARY_PROVIDER", "checko-derived data is never the official registry");
  assert.equal(sourceClass("CHECKO_REGISTRY_MIRROR"), "SECONDARY_PROVIDER");
  assert.equal(sourceClass("ORGANIZER_PROCUREMENT_DATA"), "PROCUREMENT_HISTORY");
  assert.equal(sourceClass("REGULATORY_REGISTRY_MIRROR_WITH_FGIS_ROSACCREDITATION_SOURCE"), "CURATED_REGULATORY");
});

/* Real P5-001A responses captured from GET /api/v1/suppliers/{inn}/profile on supplier_radar_p5 (2026-10-02). */
const real = (inn) => JSON.parse(readFileSync(new URL(`./fixtures/p5_profile_${inn}.json`, import.meta.url), "utf-8"));
const KEYS = ["supplier", "enrichment", "contacts", "roles", "evidence", "freshness", "procurement_history_summary", "sources", "last_run_attempts"];

test("real contract: top-level keys match the frontend type", () => {
  for (const inn of ["7804054351", "7810687137", "7622012124", "7814580307"]) assert.deepEqual(Object.keys(real(inn)).sort(), [...KEYS].sort(), inn);
});

test("real A: EGRUL legal entity — identity, address, OKVED; address only → no reachable contact; no market role", () => {
  const p = real("7804054351");
  assert.ok(profileName(p.supplier) && p.supplier.registered_address && p.supplier.primary_okved);
  assert.deepEqual(orderedContacts(p.contacts).map((c) => [c.type, sourceClass(c.source_type)]), [["ADDRESS", "OFFICIAL_REGISTRY"]]);
  assert.equal(hasReachableContact(p.contacts), false);
  assert.equal(hasMarketRoleEvidence(p.roles), false, "supplier from procurement history only");
  assert.deepEqual(enrichmentView(p.enrichment, true), { notice: "partial", action: { kind: "refresh", refresh: false } });
  assert.ok(Object.keys(p.procurement_history_summary.platforms).every((k) => k === "AIS_GZ" || k === "EM"));
});

test("real C: distributor INFERRED from OKVED, never manufacturer", () => {
  const p = real("7810687137");
  const groups = roleGroups(p.roles).map((g) => [g.role, g.status]);
  assert.deepEqual(groups, [["SUPPLIER", "VERIFIED"], ["DISTRIBUTOR", "INFERRED"]]);
  assert.ok(!p.roles.some((r) => r.role === "MANUFACTURER"));
});

test("real E (before): NOT_ENRICHED historical supplier → INN only + enrich action", () => {
  const p = real("7814580307");
  assert.equal(profileName(p.supplier), null);
  assert.deepEqual(enrichmentView(p.enrichment, true), { notice: "notEnriched", action: { kind: "enrich", refresh: false } });
});

test("real H: curated external candidate — curated contacts, verified manufacturer, secondary-provider address labelled as such", () => {
  const p = real("7622012124");
  assert.equal(p.supplier.historically_known, false);
  assert.equal(p.procurement_history_summary, null);
  assert.deepEqual(headerRoles(p.roles), [{ role: "MANUFACTURER", status: "VERIFIED" }]);
  assert.equal(hasReachableContact(p.contacts), true);
  const address = p.contacts.find((c) => c.type === "ADDRESS");
  assert.equal(sourceClass(address.source_type), "SECONDARY_PROVIDER");
});
