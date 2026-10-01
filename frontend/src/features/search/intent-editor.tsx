"use client";

import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { TrashIcon } from "@/components/icons";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Combobox } from "@/components/ui/combobox";
import { Field, FieldGrid } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { MultiSelect } from "@/components/ui/multi-select";
import { TagInput } from "@/components/ui/tag-input";
import type { FieldOrigin, IntentField, ParsedQuery, SearchIntent, SupplierType, WarningCode } from "@/lib/api/types";
import { useVocab } from "../shared/use-vocab";

const SUPPLIER_TYPES: SupplierType[] = ["manufacturer", "distributor", "supplier", "service_provider"];

/**
 * Parsed intent with per-field origin (extracted / user-edited / not set) and edit + clear actions (FR-18, C-07).
 * Only fields the user touched are sent back as `intent_overrides`; clearing a field sends an empty value,
 * which makes the matching ranking feature N/A on the server (BR-05).
 */
export function IntentEditor({
  parsed,
  warnings,
  parserVersion,
  regions,
  submitting,
  onSubmit,
}: {
  parsed: ParsedQuery;
  warnings: WarningCode[];
  parserVersion: string;
  regions: string[];
  submitting: boolean;
  onSubmit: (overrides: Partial<SearchIntent>) => void;
}) {
  const t = useTranslations("search.intent");
  const v = useVocab();
  const [draft, setDraft] = useState<SearchIntent>(() => ({
    product: parsed.product,
    category_terms: parsed.category_terms,
    attributes: parsed.attributes,
    quantity: parsed.quantity,
    region: parsed.region,
    supplier_types: parsed.supplier_types,
    mandatory_constraints: parsed.mandatory_constraints,
  }));
  const [edited, setEdited] = useState<Set<IntentField>>(new Set());

  const set = <K extends IntentField>(k: K, value: SearchIntent[K]) => {
    setDraft((d) => ({ ...d, [k]: value }));
    setEdited((e) => new Set(e).add(k));
  };
  const origin = (k: IntentField): FieldOrigin | "empty" => (edited.has(k) ? "user_edited" : (parsed.field_origin[k] ?? "empty"));
  const fallback = warnings.includes("LLM_UNAVAILABLE") || warnings.includes("PARSER_FALLBACK");
  const mode = fallback ? "fallback" : parserVersion.startsWith("llm") ? "llm" : "rules";

  const label = (k: IntentField, text: ReactNode) => (
    <span className="flex w-full items-center gap-2">
      <span className="flex-1">{text}</span>
      <OriginBadge origin={origin(k)} />
    </span>
  );
  const clear = (k: IntentField, empty: SearchIntent[typeof k]) => (
    <Button type="button" variant="ghost" size="icon" aria-label={t("clearField")} title={t("clearField")} onClick={() => set(k, empty)} className="shrink-0">
      <TrashIcon />
    </Button>
  );

  const attrs = Object.entries(draft.attributes);

  return (
    <Card>
      <CardHeader className="flex-wrap items-start">
        <div className="flex flex-col gap-1">
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </div>
        <Badge color={mode === "fallback" ? "warning" : mode === "llm" ? "purple" : "gray"}>{t(`parser.${mode}`)}</Badge>
      </CardHeader>
      <CardBody>
        <FieldGrid>
          <Field label={label("product", t("fields.product"))}>
            <div className="flex items-center gap-2">
              <Input value={draft.product ?? ""} placeholder={t("placeholders.product")} onChange={(e) => set("product", e.target.value || null)} />
              {clear("product", null)}
            </div>
          </Field>
          <Field label={label("quantity", t("fields.quantity"))}>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                min={1}
                inputMode="numeric"
                value={draft.quantity ?? ""}
                placeholder={t("placeholders.quantity")}
                onChange={(e) => set("quantity", e.target.value ? Math.max(1, Number(e.target.value)) : null)}
              />
              {clear("quantity", null)}
            </div>
          </Field>
          <Field label={label("category_terms", t("fields.category"))} className="md:col-span-2">
            <TagInput value={draft.category_terms} onChange={(val) => set("category_terms", val)} placeholder={t("placeholders.tags")} removeLabel={t("remove")} />
          </Field>
          <Field label={label("attributes", t("fields.attributes"))} className="md:col-span-2">
            {attrs.length ? (
              <ul className="flex flex-col gap-2">
                {attrs.map(([key, value]) => (
                  <li key={key} className="flex items-center gap-2">
                    <span className="w-44 shrink-0 truncate text-xs text-subtle">{t.has(`attributes.${key}`) ? t(`attributes.${key}`) : key}</span>
                    <Input
                      size="sm"
                      aria-label={t.has(`attributes.${key}`) ? t(`attributes.${key}`) : key}
                      value={String(value)}
                      onChange={(e) => set("attributes", { ...draft.attributes, [key]: typeof value === "number" && e.target.value !== "" && !Number.isNaN(Number(e.target.value)) ? Number(e.target.value) : e.target.value })}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label={t("removeAttribute")}
                      title={t("removeAttribute")}
                      onClick={() => {
                        const next = { ...draft.attributes };
                        delete next[key];
                        set("attributes", next);
                      }}
                    >
                      <TrashIcon />
                    </Button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rounded-md border border-dashed border-line px-3 py-2.5 text-xs text-muted">{t("noAttributes")}</p>
            )}
          </Field>
          <Field label={label("region", t("fields.region"))}>
            <div className="flex items-center gap-2">
              <Combobox
                options={regions.map((r) => ({ value: r, label: r }))}
                value={draft.region ?? undefined}
                onValueChange={(r) => set("region", r)}
                placeholder={t("placeholders.region")}
                searchPlaceholder={t("placeholders.search")}
                emptyText={t("nothingFound")}
              />
              {clear("region", null)}
            </div>
          </Field>
          <Field label={label("supplier_types", t("fields.supplierTypes"))} hint={t("hints.supplierTypes")}>
            <MultiSelect
              options={SUPPLIER_TYPES.map((s) => ({ value: s, label: v.supplierType(s) }))}
              value={draft.supplier_types}
              onChange={(val) => set("supplier_types", val as SupplierType[])}
              placeholder={t("placeholders.any")}
              searchPlaceholder={t("placeholders.search")}
              emptyText={t("nothingFound")}
            />
          </Field>
          <Field label={label("mandatory_constraints", t("fields.constraints"))} hint={t("hints.constraints")} className="md:col-span-2">
            <TagInput value={draft.mandatory_constraints} onChange={(val) => set("mandatory_constraints", val)} placeholder={t("placeholders.tags")} removeLabel={t("remove")} />
          </Field>
        </FieldGrid>
      </CardBody>
      <CardFooter className="flex-wrap justify-between">
        <span className="text-xs text-muted" aria-live="polite">
          {edited.size ? t("editedCount", { count: edited.size }) : t("noEdits")}
        </span>
        <div className="flex gap-3">
          <Button
            type="button"
            variant="secondary"
            disabled={!edited.size || submitting}
            onClick={() => {
              setDraft({
                product: parsed.product,
                category_terms: parsed.category_terms,
                attributes: parsed.attributes,
                quantity: parsed.quantity,
                region: parsed.region,
                supplier_types: parsed.supplier_types,
                mandatory_constraints: parsed.mandatory_constraints,
              });
              setEdited(new Set());
            }}
          >
            {t("reset")}
          </Button>
          <Button
            type="button"
            loading={submitting}
            disabled={!edited.size}
            onClick={() => onSubmit(Object.fromEntries([...edited].map((k) => [k, draft[k]])) as Partial<SearchIntent>)}
          >
            {t("apply")}
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}

function OriginBadge({ origin }: { origin: FieldOrigin | "empty" }) {
  const t = useTranslations("search.intent.origin");
  return (
    <Badge size="sm" color={origin === "user_edited" ? "warning" : origin === "extracted" ? "info" : "gray"} className="min-w-0">
      {t(origin)}
    </Badge>
  );
}
