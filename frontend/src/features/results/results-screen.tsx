"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { EditIcon, FaceFrownIcon, FilterIcon, PlusIcon, ScalesIcon, SearchIcon, WarningTriangleIcon } from "@/components/icons";
import { ActionBar } from "@/components/ui/action-bar";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog, DialogClose } from "@/components/ui/dialog";
import { Drawer, DrawerBody, DrawerContent, DrawerHeader, DrawerTitle } from "@/components/ui/drawer";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { useToast } from "@/components/ui/toast";
import { UI_CONFIG } from "@/config/ui";
import { Link, useRouter } from "@/i18n/navigation";
import { api, isApiError } from "@/lib/api/client";
import type { SearchFilters, SearchResponse, WarningCode } from "@/lib/api/types";
import { fmtDateTime } from "@/lib/format";
import { useAsync } from "@/lib/use-async";
import { ErrorPanel } from "../shared/error-panel";
import { PageSkeleton, ResultCardSkeleton } from "../shared/skeletons";
import { useVocab } from "../shared/use-vocab";
import { useSession } from "../shell/session-store";
import { activeFilterCount, DEFAULT_FILTERS, FiltersForm } from "./filters-panel";
import { MarketSummary } from "./market-summary";
import { ResultCard } from "./result-card";

const SCROLL_KEY = (id: string) => `sr.scroll.${id}`;

/** S-02 Search Results — loads the persisted run by request_id, so going back never re-runs the search (US-08). */
export function ResultsScreen({ requestId }: { requestId: string }) {
  const t = useTranslations("results");
  const run = useAsync(() => api.getSearch(requestId), [requestId]);
  const { setLastRequestId } = useSession();

  useEffect(() => {
    if (run.status === "success") setLastRequestId(run.data.request_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run.status]);

  if (run.status === "loading")
    return (
      <>
        <PageHeader title={t("title")} />
        <PageSkeleton blocks={1} />
        <div className="mt-5 flex flex-col gap-4">
          <ResultCardSkeleton />
          <ResultCardSkeleton />
        </div>
      </>
    );

  if (run.status === "error") {
    if (isApiError(run.error) && run.error.code === "REQUEST_NOT_FOUND")
      return (
        <>
          <PageHeader title={t("title")} />
          <Card>
            <EmptyState
              icon={<SearchIcon />}
              title={t("notFound.title")}
              description={t("notFound.text")}
              actions={
                <Button asChild>
                  <Link href="/search">{t("newSearch")}</Link>
                </Button>
              }
            />
          </Card>
        </>
      );
    return (
      <>
        <PageHeader title={t("title")} />
        <ErrorPanel error={run.error} onRetry={run.reload} />
      </>
    );
  }

  return <ResultsView key={run.data.request_id} run={run.data} />;
}

function ResultsView({ run }: { run: SearchResponse }) {
  const t = useTranslations("results");
  const v = useVocab();
  const router = useRouter();
  const toast = useToast();
  const { tray, toggle, replace, clear } = useSession();
  const regions = useAsync(() => api.filterMeta().then((m) => m.regions.map((r) => r.name)), []);
  const [busy, setBusy] = useState<false | "filters" | "more">(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [drawer, setDrawer] = useState(false);
  const [conflict, setConflict] = useState<string | null>(null);

  // Restore / remember scroll position for back navigation from the profile.
  useEffect(() => {
    const key = SCROLL_KEY(run.request_id);
    try {
      const y = Number(window.sessionStorage.getItem(key));
      if (y) window.scrollTo(0, y);
    } catch {
      /* ignore */
    }
    let frame = 0;
    const onScroll = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        try {
          window.sessionStorage.setItem(key, String(window.scrollY));
        } catch {
          /* ignore */
        }
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [run.request_id]);

  const filters: SearchFilters = { ...DEFAULT_FILTERS, ...run.filters };
  const filterCount = activeFilterCount(filters);

  const rerun = async (next: { filters?: SearchFilters; limit?: number }) => {
    setBusy(next.limit ? "more" : "filters");
    setFailure(null);
    try {
      const res = await api.search({ query: run.query, filters: next.filters ?? filters, intent_overrides: run.intent_overrides, limit: next.limit ?? run.limit });
      setDrawer(false);
      router.replace(`/results/${res.request_id}`, { scroll: !next.limit });
    } catch (e) {
      setFailure(e);
      setBusy(false);
    }
  };

  const onToggleCompare = (supplierId: string) => {
    const r = toggle(run.request_id, supplierId);
    if (r === "limit") toast({ tone: "warning", title: t("compare.limit", { max: UI_CONFIG.compareMax }) });
    if (r === "conflict") setConflict(supplierId);
  };

  const notices = run.warnings.filter((w): w is Exclude<WarningCode, "NO_RESULTS"> => w !== "NO_RESULTS");
  const top = run.results.slice(0, UI_CONFIG.lowConfidenceTopN);
  const lowConfidence = top.length > 0 && top.every((r) => (r.confidence_score ?? 0) < UI_CONFIG.lowConfidence);
  const empty = run.results.length === 0;
  const filteredEmpty = empty && filterCount > 0;
  const canLoadMore = run.results.length >= run.limit && run.limit < UI_CONFIG.maxLimit;
  const trayHere = tray.requestId === run.request_id ? tray.ids : [];

  const filtersForm = <FiltersForm initial={filters} regions={regions.status === "success" ? regions.data : []} busy={busy === "filters"} onApply={(f) => rerun({ filters: f })} />;

  return (
    <>
      <PageHeader
        title={t("title")}
        description={
          <span className="flex flex-wrap items-center gap-x-2">
            <span className="text-heading">«{run.query}»</span>
            <span className="text-muted">· {fmtDateTime(run.created_at)}</span>
          </span>
        }
        actions={
          <>
            <Button asChild variant="secondary">
              <Link href={`/search?from=${run.request_id}`}>
                <EditIcon />
                {t("refine")}
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/search">
                <PlusIcon />
                {t("newSearch")}
              </Link>
            </Button>
          </>
        }
      />

      <div className="flex flex-col gap-5">
        {failure ? <ErrorPanel error={failure} onRetry={() => rerun({})} /> : null}
        {notices.length ? (
          <Alert tone="warning" appearance="inline" title={t("degraded.title")}>
            <ul className="mt-1 flex list-disc flex-col gap-0.5 ps-5 text-sm text-subtle">
              {notices.map((w) => (
                <li key={w}>{v.warning(w)}</li>
              ))}
            </ul>
          </Alert>
        ) : null}
        {lowConfidence ? <Alert tone="warning" icon={<WarningTriangleIcon />} title={t("lowConfidence.title")} description={t("lowConfidence.text", { value: Math.round(UI_CONFIG.lowConfidence * 100) })} /> : null}

        {empty && !filterCount ? null : <MarketSummary run={run} />}
        <IntentSummary run={run} />

        <div className={empty && !filterCount ? "flex flex-col" : "grid grid-cols-1 gap-5 lg:grid-cols-[280px_minmax(0,1fr)]"}>
          <aside className={empty && !filterCount ? "hidden" : "hidden lg:block"} aria-label={t("filters.title")}>
            <Card className="sticky top-[76px]">
              <CardHeader>
                <CardTitle>{t("filters.title")}</CardTitle>
                {filterCount ? <Badge color="primary" size="sm">{filterCount}</Badge> : null}
              </CardHeader>
              <CardBody>{filtersForm}</CardBody>
            </Card>
          </aside>

          <section className="flex min-w-0 flex-col gap-4" aria-label={t("listLabel")} aria-busy={Boolean(busy)}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-subtle" aria-live="polite">
                {empty ? t("countNone") : t("count", { shown: run.results.length, total: (run.market_summary?.known ?? 0) + (run.market_summary?.external ?? 0) })}
                {empty ? null : <span className="text-muted"> · {t("sortedByMatch")}</span>}
              </p>
              <Drawer open={drawer} onOpenChange={setDrawer}>
                <Button variant="secondary" size="md" className={empty && !filterCount ? "hidden" : "lg:hidden"} onClick={() => setDrawer(true)}>
                  <FilterIcon />
                  {t("filters.title")}
                  {filterCount ? <Badge color="primary" size="sm" className="min-w-0">{filterCount}</Badge> : null}
                </Button>
                <DrawerContent>
                  <DrawerHeader>
                    <DrawerTitle>{t("filters.title")}</DrawerTitle>
                  </DrawerHeader>
                  <DrawerBody className="px-4 pb-4">{filtersForm}</DrawerBody>
                </DrawerContent>
              </Drawer>
            </div>

            {busy === "filters" ? (
              <>
                <ResultCardSkeleton />
                <ResultCardSkeleton />
              </>
            ) : filteredEmpty ? (
              <Card>
                <EmptyState
                  icon={<FilterIcon />}
                  title={t("filteredEmpty.title")}
                  description={t("filteredEmpty.text")}
                  actions={
                    <Button onClick={() => rerun({ filters: DEFAULT_FILTERS })}>
                      {t("filteredEmpty.clear")}
                    </Button>
                  }
                />
              </Card>
            ) : empty ? (
              <Card>
                <EmptyState
                  icon={<FaceFrownIcon />}
                  title={t("empty.title")}
                  description={t("empty.text")}
                  actions={
                    <Button asChild>
                      <Link href={`/search?from=${run.request_id}`}>{t("empty.refine")}</Link>
                    </Button>
                  }
                />
              </Card>
            ) : (
              <ol className="flex flex-col gap-4">
                {run.results.map((r) => (
                  <li key={r.supplier_id}>
                    <ResultCard result={r} requestId={run.request_id} selected={trayHere.includes(r.supplier_id)} onToggleCompare={() => onToggleCompare(r.supplier_id)} />
                  </li>
                ))}
              </ol>
            )}

            {canLoadMore && !empty ? (
              <Button variant="secondary" className="self-center" loading={busy === "more"} onClick={() => rerun({ limit: Math.min(UI_CONFIG.maxLimit, run.limit + UI_CONFIG.pageSize) })}>
                {t("loadMore")}
              </Button>
            ) : null}

            <p className="text-2xs text-muted">
              {t("meta", { ms: run.timings.total_ms, ranking: run.versions.ranking, parser: run.versions.parser })}
            </p>
          </section>
        </div>
      </div>

      {tray.ids.length ? (
        <ActionBar aria-label={t("compare.tray")}>
          <ScalesIcon className="size-5 text-muted" aria-hidden />
          <span className="text-sm text-heading" aria-live="polite">
            {t("compare.selected", { count: tray.ids.length, max: UI_CONFIG.compareMax })}
          </span>
          {tray.requestId !== run.request_id ? <span className="text-xs text-muted">{t("compare.otherSearch")}</span> : null}
          <div className="ms-auto flex items-center gap-3">
            <Button variant="link" onClick={clear}>
              {t("compare.clear")}
            </Button>
            {tray.ids.length < UI_CONFIG.compareMin ? (
              <span className="text-xs text-muted">{t("compare.needMore", { min: UI_CONFIG.compareMin })}</span>
            ) : (
              <Button asChild size="sm">
                <Link href="/compare">{t("compare.open")}</Link>
              </Button>
            )}
          </div>
        </ActionBar>
      ) : null}

      <ConfirmDialog
        open={conflict !== null}
        onOpenChange={(o) => !o && setConflict(null)}
        tone="warning"
        icon={<ScalesIcon />}
        title={t("compare.conflictTitle")}
        description={t("compare.conflictText")}
        cancel={
          <DialogClose asChild>
            <Button variant="secondary">{t("compare.keep")}</Button>
          </DialogClose>
        }
        confirm={
          <Button
            onClick={() => {
              if (conflict) replace(run.request_id, conflict);
              setConflict(null);
            }}
          >
            {t("compare.startNew")}
          </Button>
        }
      />
    </>
  );
}

/** Parsed intent + active filters at a glance, with a link back to S-01 to edit (S-02 data). */
function IntentSummary({ run }: { run: SearchResponse }) {
  const t = useTranslations("results.intent");
  const v = useVocab();
  const p = run.parsed_query;
  const chips: { key: string; label: string; edited?: boolean }[] = [];
  if (p) {
    if (p.product) chips.push({ key: "product", label: p.product, edited: p.field_origin.product === "user_edited" });
    p.category_terms.forEach((c) => chips.push({ key: `cat-${c}`, label: c, edited: p.field_origin.category_terms === "user_edited" }));
    Object.entries(p.attributes).forEach(([k, val]) => chips.push({ key: `attr-${k}`, label: `${t.has(`attr.${k}`) ? t(`attr.${k}`) : k}: ${val}`, edited: p.field_origin.attributes === "user_edited" }));
    if (p.quantity) chips.push({ key: "qty", label: t("quantity", { count: p.quantity }), edited: p.field_origin.quantity === "user_edited" });
    if (p.region) chips.push({ key: "region", label: p.region, edited: p.field_origin.region === "user_edited" });
    p.supplier_types.forEach((s) => chips.push({ key: `type-${s}`, label: v.supplierType(s), edited: p.field_origin.supplier_types === "user_edited" }));
    p.mandatory_constraints.forEach((c) => chips.push({ key: `mc-${c}`, label: `${t("mandatory")}: ${c}`, edited: p.field_origin.mandatory_constraints === "user_edited" }));
  }
  return (
    <Card variant="outlined">
      <CardBody className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center">
        <span className="shrink-0 text-xs font-medium text-subtle">{t("label")}</span>
        <ul className="flex flex-1 flex-wrap gap-1.5">
          {chips.length ? (
            chips.map((c) => (
              <li key={c.key}>
                <Badge color={c.edited ? "warning" : "primary"} className="min-w-0">
                  {c.label}
                  {c.edited ? <span className="sr-only"> ({t("edited")})</span> : null}
                </Badge>
              </li>
            ))
          ) : (
            <li className="text-sm text-muted">{t("none")}</li>
          )}
        </ul>
        <Button asChild variant="link" className="shrink-0 text-primary-700">
          <Link href={`/search?from=${run.request_id}`}>{t("edit")}</Link>
        </Button>
      </CardBody>
    </Card>
  );
}
