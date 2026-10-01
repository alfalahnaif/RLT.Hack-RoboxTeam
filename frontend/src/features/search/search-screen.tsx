"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { BoltIcon, ScalesIcon, SearchIcon, SparklesIcon } from "@/components/icons";
import { IconChip } from "@/components/ui/metric-card";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Textarea } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { RadioCard, RadioCards } from "@/components/ui/radio-group";
import { Spinner } from "@/components/ui/spinner";
import { UI_CONFIG } from "@/config/ui";
import { useRouter } from "@/i18n/navigation";
import { api, API_MODE, isApiError } from "@/lib/api/client";
import type { MarketScope, SearchIntent, SearchResponse } from "@/lib/api/types";
import { useAsync } from "@/lib/use-async";
import { DEMO_QUERIES } from "@/mocks/fixtures";
import { ErrorPanel } from "../shared/error-panel";
import { PageSkeleton } from "../shared/skeletons";
import { useVocab } from "../shared/use-vocab";
import { useSession } from "../shell/session-store";
import { IntentEditor } from "./intent-editor";
import { ScenarioPanel } from "./scenario-panel";

/**
 * S-01 Search. Fresh mode: capture the requirement + market scope and run the search.
 * Refine mode (`?from=<request_id>`): reopen a run, show the parsed intent and re-search with overrides.
 */
export function SearchScreen({ fromRequestId }: { fromRequestId?: string }) {
  const source = useAsync<SearchResponse | null>(() => (fromRequestId ? api.getSearch(fromRequestId) : Promise.resolve(null)), [fromRequestId]);
  const regions = useAsync(() => api.filterMeta().then((m) => m.regions.map((r) => r.name)), []);

  if (fromRequestId && source.status === "loading") {
    return (
      <>
        <Header />
        <PageSkeleton blocks={2} />
      </>
    );
  }
  const run = source.status === "success" ? source.data : null;
  return <SearchForm key={run?.request_id ?? "fresh"} run={run} expired={Boolean(fromRequestId) && source.status === "error"} regions={regions.status === "success" ? regions.data : []} />;
}

function Header() {
  const t = useTranslations("search");
  return <PageHeader title={t("title")} description={t("subtitle")} />;
}

function SearchForm({ run, expired, regions }: { run: SearchResponse | null; expired: boolean; regions: string[] }) {
  const t = useTranslations("search");
  const v = useVocab();
  const router = useRouter();
  const { setLastRequestId } = useSession();
  const [query, setQuery] = useState(run?.query ?? "");
  const [scope, setScope] = useState<MarketScope>(run?.filters.market_scope ?? "all");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [slow, setSlow] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const lastRequest = useRef<() => void>(() => {});
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!run) inputRef.current?.focus();
  }, [run]);

  const execute = async (overrides: Partial<SearchIntent> | null) => {
    const trimmed = query.trim();
    if (trimmed.length < UI_CONFIG.queryMin) return setFieldError(v.error("QUERY_TOO_SHORT"));
    if (trimmed.length > UI_CONFIG.queryMax) return setFieldError(v.error("QUERY_TOO_LONG"));
    setFieldError(null);
    setFailure(null);
    setSubmitting(true);
    const timer = setTimeout(() => setSlow(true), UI_CONFIG.slowHintMs);
    lastRequest.current = () => execute(overrides);
    try {
      const res = await api.search({
        query: trimmed,
        filters: { ...(run?.filters ?? { region: null, supplier_type: null }), market_scope: scope },
        intent_overrides: overrides ? { ...(run?.intent_overrides ?? {}), ...overrides } : (run?.intent_overrides ?? null),
        limit: UI_CONFIG.pageSize,
      });
      setLastRequestId(res.request_id);
      router.push(`/results/${res.request_id}`);
    } catch (e) {
      if (isApiError(e) && (e.code === "QUERY_TOO_SHORT" || e.code === "QUERY_TOO_LONG")) setFieldError(v.error(e.code));
      else setFailure(e);
      setSubmitting(false);
    } finally {
      clearTimeout(timer);
      setSlow(false);
    }
  };

  const onSubmit = (e: Pick<FormEvent, "preventDefault">) => {
    e.preventDefault();
    // A changed query text invalidates the old interpretation: start fresh, no overrides.
    void execute(run && query.trim() === run.query ? {} : null);
  };

  return (
    <>
      <PageHeader title={run ? t("refineTitle") : t("title")} description={run ? t("refineSubtitle") : t("subtitle")} backHref={run ? `/results/${run.request_id}` : undefined} />
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex min-w-0 flex-col gap-5">
          {expired ? <Alert tone="warning" appearance="inline" description={t("expired")} /> : null}
          {failure ? <ErrorPanel error={failure} onRetry={() => lastRequest.current()} /> : null}

          <Card>
            <form onSubmit={onSubmit} noValidate>
              <CardBody className="flex flex-col gap-5">
                <Field label={t("queryLabel")} required error={fieldError ?? undefined} hint={t("queryHint", { min: UI_CONFIG.queryMin, max: UI_CONFIG.queryMax })}>
                  <Textarea
                    ref={inputRef}
                    value={query}
                    onChange={(e) => {
                      setQuery(e.target.value);
                      if (fieldError) setFieldError(null);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) onSubmit(e);
                    }}
                    placeholder={t("queryPlaceholder")}
                    maxLength={UI_CONFIG.queryMax}
                    showCount
                    rows={3}
                    className="text-sm"
                  />
                </Field>

                <div className="flex flex-col gap-2">
                  <span id="scope-label" className="text-xs font-medium text-subtle">
                    {t("scopeLabel")}
                  </span>
                  <RadioCards aria-labelledby="scope-label" value={scope} onValueChange={(s) => setScope(s as MarketScope)} className="grid-cols-1 sm:grid-cols-3">
                    {(["all", "known", "external"] as const).map((s) => (
                      <RadioCard key={s} value={s} className="flex-col items-start gap-0.5 text-start">
                        <span>{v.scope(s)}</span>
                        <span className="text-2xs font-normal text-muted">{t(`scopeHint.${s}`)}</span>
                      </RadioCard>
                    ))}
                  </RadioCards>
                </div>

                {!run ? (
                  <div className="flex flex-col gap-2">
                    <span className="text-xs font-medium text-subtle">{t("examples")}</span>
                    <div className="flex flex-wrap gap-2">
                      {DEMO_QUERIES.map((d) => (
                        <button
                          key={d.key}
                          type="button"
                          onClick={() => {
                            setQuery(d.query);
                            setFieldError(null);
                            inputRef.current?.focus();
                          }}
                          className="max-w-full truncate rounded-pill border border-line bg-white px-3 py-1.5 text-xs text-subtle transition-colors hover:border-primary-300 hover:bg-primary-50/40 hover:text-primary-700 focus-visible:ring-4 focus-visible:ring-primary-600/15 focus-visible:outline-none"
                        >
                          {d.query}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}

                <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line-subtle pt-4">
                  <span className="text-xs text-muted" aria-live="polite">
                    {submitting && slow ? (
                      <span className="inline-flex items-center gap-2 text-primary-700">
                        <Spinner size={14} />
                        {t("slow")}
                      </span>
                    ) : (
                      t("shortcut")
                    )}
                  </span>
                  <Button type="submit" size="lg" strong loading={submitting}>
                    {!submitting ? <SearchIcon /> : null}
                    {run ? t("searchAgain") : t("submit")}
                  </Button>
                </div>
              </CardBody>
            </form>
          </Card>

          {run?.parsed_query ? (
            <IntentEditor
              parsed={run.parsed_query}
              warnings={run.warnings}
              parserVersion={run.versions.parser}
              regions={regions}
              submitting={submitting}
              onSubmit={(overrides) => void execute(overrides)}
            />
          ) : null}
        </div>

        <aside className="flex flex-col gap-5">
          <HowItWorks />
          {API_MODE === "mock" ? <ScenarioPanel /> : null}
        </aside>
      </div>
    </>
  );
}

function HowItWorks() {
  const t = useTranslations("search.how");
  const steps = [
    { key: "match", icon: <BoltIcon />, tone: "primary" as const },
    { key: "confidence", icon: <ScalesIcon />, tone: "success" as const },
    { key: "market", icon: <SparklesIcon />, tone: "warning" as const },
  ];
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-1">
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>{t("subtitle")}</CardDescription>
        </div>
      </CardHeader>
      <CardBody>
        <ul className="flex flex-col gap-4">
          {steps.map((s) => (
            <li key={s.key} className="flex gap-3">
              <IconChip tone={s.tone}>{s.icon}</IconChip>
              <div className="flex flex-col gap-0.5">
                <span className="text-sm font-medium text-heading">{t(`${s.key}.title`)}</span>
                <span className="text-xs text-subtle">{t(`${s.key}.text`)}</span>
              </div>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}
