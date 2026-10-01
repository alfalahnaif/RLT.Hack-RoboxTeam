"use client";

import { useTranslations } from "next-intl";
import { type FormEvent, useEffect, useState } from "react";
import { CheckCircleSmIcon, FaceFrownIcon, RocketIcon, SearchIcon } from "@/components/icons";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { Spinner } from "@/components/ui/spinner";
import { DEMO_LOTS } from "@/config/ui";
import { useRouter } from "@/i18n/navigation";
import { api, isApiError } from "@/lib/api/client";
import { useAsync } from "@/lib/use-async";
import { cn } from "@/lib/utils";
import { ErrorPanel } from "../shared/error-panel";
import { PageSkeleton, ResultCardSkeleton } from "../shared/skeletons";
import { MarketSection } from "./market-section";
import { AnalysisOverview } from "./overview";
import { EvidenceTimeline, ProcurementSummary } from "./procurement-summary";
import { SupplierList } from "./supplier-list";

/** S-06 Procurement analysis: one request to `/procurements/{lot_id}/analysis`, rendered section by section. */
export function AnalysisScreen({ lotId }: { lotId?: string }) {
  const t = useTranslations("analysis");
  const router = useRouter();
  const [draft, setDraft] = useState(lotId ?? "");
  const [invalid, setInvalid] = useState(false);

  const [shownLot, setShownLot] = useState(lotId);
  if (shownLot !== lotId) {
    // URL changed (back/forward or shortcut): show the lot being analyzed in the field.
    setShownLot(lotId);
    setDraft(lotId ?? "");
  }

  const open = (lot: string) => {
    const v = lot.trim();
    if (!v) return setInvalid(true);
    setInvalid(false);
    setDraft(v);
    router.push(`/analysis?lot=${encodeURIComponent(v)}`);
  };
  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    open(draft);
  };

  return (
    <>
      <PageHeader title={t("title")} description={t("description")} />
      <Card className="mb-5">
        <CardBody className="flex flex-col gap-4">
          <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <Field label={t("form.label")} error={invalid ? t("form.required") : undefined} className="flex-1 sm:max-w-80">
              <Input
                value={draft}
                inputMode="numeric"
                placeholder={t("form.placeholder")}
                invalid={invalid}
                onChange={(e) => setDraft(e.target.value)}
                prefix={<SearchIcon />}
              />
            </Field>
            <Button type="submit">
              {t("form.analyze")}
            </Button>
          </form>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted">{t("form.demos")}:</span>
            <Button variant="secondary" size="sm" onClick={() => open(DEMO_LOTS.primary)} className="h-auto min-h-8 max-w-full whitespace-normal border-primary-300 py-1.5 text-start text-primary-700">
              <RocketIcon />
              {t("form.primaryDemo", { lot: DEMO_LOTS.primary })}
            </Button>
            <Button variant="secondary" size="sm" onClick={() => open(DEMO_LOTS.fallback)} className="h-auto min-h-8 max-w-full whitespace-normal py-1.5 text-start">
              {t("form.fallbackDemo", { lot: DEMO_LOTS.fallback })}
            </Button>
          </div>
        </CardBody>
      </Card>
      {lotId ? (
        <AnalysisResult key={lotId} lotId={lotId} />
      ) : (
        <Card>
          <EmptyState icon={<SearchIcon />} title={t("initial.title")} description={t("initial.description")} />
        </Card>
      )}
    </>
  );
}

function AnalysisResult({ lotId }: { lotId: string }) {
  const t = useTranslations("analysis");
  const run = useAsync(() => api.analysis(lotId), [lotId]);

  if (run.status === "loading") return <AnalysisLoading lotId={lotId} />;
  if (run.status === "error") {
    if (isApiError(run.error) && run.error.code === "LOT_NOT_FOUND")
      return (
        <Card>
          <EmptyState
            icon={<FaceFrownIcon />}
            title={t("notFound.title")}
            description={t("notFound.description", { lot: lotId })}
          />
        </Card>
      );
    return <ErrorPanel error={run.error} onRetry={run.reload} />;
  }

  const a = run.data;
  const rec = a.recommendations.data;
  const semanticOff = rec?.warnings.some((w) => w.startsWith("SEMANTIC_UNAVAILABLE"));
  return (
    <div className="flex flex-col gap-5">
      {a.availability === "PARTIAL" ? <Alert tone="warning" appearance="inline" title={t("partial.title")} description={t("partial.description")} /> : null}
      <ProcurementSummary analysis={a} />
      <AnalysisOverview analysis={a} />
      <EvidenceTimeline analysis={a} />
      {semanticOff ? <Alert tone="info" appearance="inline" description={t("semanticUnavailable")} /> : null}
      <SupplierList data={rec} procurementCodes={a.market_intelligence.map((e) => e.okpd2)} />
      {a.market_intelligence.length ? <MarketSection entries={a.market_intelligence} items={a.procurement.items} /> : null}
      <p className="text-xs text-muted">{t("disclaimer")}</p>
    </div>
  );
}

const STEPS = ["items", "suppliers", "pool", "external"] as const;
const STEP_MS = 900;

/** Loading state for the 1–4 s analysis: named stages advance on a timer so a longer case reads as work in progress, not a freeze. */
function AnalysisLoading({ lotId }: { lotId: string }) {
  const t = useTranslations("analysis.loading");
  const [step, setStep] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), STEP_MS);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="flex flex-col gap-5" aria-busy>
      <Card>
        <CardBody className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <Spinner size={20} className="text-primary-700" />
            <span className="text-base font-medium text-heading">{t("title", { lot: lotId })}</span>
          </div>
          <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4" role="status">
            {STEPS.map((s, i) => (
              <li
                key={s}
                className={cn(
                  "flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors",
                  i < step ? "border-success-300 bg-success-50 text-success-700" : i === step ? "border-primary-300 bg-primary-50 text-primary-700" : "border-line-subtle text-muted",
                )}
              >
                {i < step ? <CheckCircleSmIcon className="size-4 shrink-0" aria-hidden /> : i === step ? <Spinner size={14} /> : <span className="size-4 shrink-0" aria-hidden />}
                {t(`steps.${s}`)}
              </li>
            ))}
          </ol>
          <span className="text-xs text-muted">{t("hint")}</span>
        </CardBody>
      </Card>
      <PageSkeleton blocks={1} />
      <ResultCardSkeleton />
      <ResultCardSkeleton />
    </div>
  );
}
