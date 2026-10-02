// P5-001B Supplier 360 view-model tests over the synthetic P5-001A fixtures.
// Run: npm test  (node --test; Node >= 23.6 strips the TypeScript types of the imported modules — no extra dependencies).
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  enrichmentView,
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

test("partial profile: retry allowed, stale contacts kept visible, inferred distributor stays weaker than verified", () => {
  const p = F.partial;
  assert.deepEqual(enrichmentView(p.enrichment, true), { notice: "partial", action: { kind: "retry", refresh: true } });
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
