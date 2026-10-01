"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Combobox } from "@/components/ui/combobox";
import { Field } from "@/components/ui/field";
import { RadioGroup, RadioItem } from "@/components/ui/radio-group";
import { SwitchLabel } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { UI_CONFIG } from "@/config/ui";
import type { MarketScope, SearchFilters, SupplierType } from "@/lib/api/types";
import { useVocab } from "../shared/use-vocab";

export const DEFAULT_FILTERS: SearchFilters = { region: null, supplier_type: null, market_scope: "all", has_experience: false, min_confidence: null };

export const activeFilterCount = (f: SearchFilters) =>
  [f.region, f.supplier_type, f.market_scope !== "all" ? f.market_scope : null, f.has_experience ? 1 : null, f.min_confidence ? 1 : null].filter(Boolean).length;

const TYPES: SupplierType[] = ["manufacturer", "distributor", "supplier", "service_provider"];

/**
 * S-02 filters (type, region, market scope, experience, min confidence). Applied server-side as a new
 * search run (ED-19 working assumption) so results, summary and request_id stay consistent.
 * Same content in the desktop side card and the mobile drawer.
 */
export function FiltersForm({ initial, regions, busy, onApply }: { initial: SearchFilters; regions: string[]; busy: boolean; onApply: (f: SearchFilters) => void }) {
  const t = useTranslations("results.filters");
  const v = useVocab();
  const [f, setF] = useState<SearchFilters>({ ...DEFAULT_FILTERS, ...initial });
  const patch = (p: Partial<SearchFilters>) => setF((x) => ({ ...x, ...p }));

  return (
    <form
      className="flex flex-col gap-5"
      onSubmit={(e) => {
        e.preventDefault();
        onApply(f);
      }}
    >
      <fieldset className="flex flex-col gap-3">
        <legend className="mb-3 text-xs font-medium text-subtle">{t("scope")}</legend>
        <RadioGroup value={f.market_scope} onValueChange={(s) => patch({ market_scope: s as MarketScope })} className="flex-col items-start gap-3">
          {(["all", "known", "external"] as const).map((s) => (
            <RadioItem key={s} value={s} label={v.scope(s)} className="text-sm" />
          ))}
        </RadioGroup>
      </fieldset>
      <Separator />
      <fieldset className="flex flex-col gap-3">
        <legend className="mb-3 text-xs font-medium text-subtle">{t("type")}</legend>
        <RadioGroup value={f.supplier_type ?? "any"} onValueChange={(s) => patch({ supplier_type: s === "any" ? null : (s as SupplierType) })} className="flex-col items-start gap-3">
          <RadioItem value="any" label={t("any")} className="text-sm" />
          {TYPES.map((s) => (
            <RadioItem key={s} value={s} label={v.supplierType(s)} className="text-sm" />
          ))}
        </RadioGroup>
      </fieldset>
      <Separator />
      <Field label={t("region")}>
        <div className="flex flex-col gap-1.5">
          <Combobox
            options={regions.map((r) => ({ value: r, label: r }))}
            value={f.region ?? undefined}
            onValueChange={(r) => patch({ region: r })}
            placeholder={t("anyRegion")}
            searchPlaceholder={t("searchRegion")}
            emptyText={t("nothingFound")}
          />
          {f.region ? (
            <Button type="button" variant="link" className="self-start text-xs" onClick={() => patch({ region: null })}>
              {t("clearRegion")}
            </Button>
          ) : null}
        </div>
      </Field>
      <Separator />
      <SwitchLabel label={t("experience")} checked={Boolean(f.has_experience)} onCheckedChange={(c) => patch({ has_experience: c })} />
      <Separator />
      <fieldset className="flex flex-col gap-3">
        <legend className="mb-3 text-xs font-medium text-subtle">{t("minConfidence")}</legend>
        <RadioGroup value={String(f.min_confidence ?? 0)} onValueChange={(s) => patch({ min_confidence: Number(s) || null })} className="flex-col items-start gap-3">
          {UI_CONFIG.minConfidenceOptions.map((o) => (
            <RadioItem key={o} value={String(o)} label={o ? t("atLeast", { value: Math.round(o * 100) }) : t("anyConfidence")} className="text-sm" />
          ))}
        </RadioGroup>
      </fieldset>
      <div className="flex gap-3 pt-1 [&>*]:flex-1">
        <Button type="button" variant="secondary" disabled={busy} onClick={() => setF(DEFAULT_FILTERS)}>
          {t("reset")}
        </Button>
        <Button type="submit" loading={busy}>
          {t("apply")}
        </Button>
      </div>
    </form>
  );
}
