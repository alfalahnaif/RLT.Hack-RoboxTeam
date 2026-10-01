"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { EyeIcon, FaceFrownIcon, HistoryIcon, SearchIcon } from "@/components/icons";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { Table, TableActions, TableBody, TableCard, TableCell, TableEmpty, TableFooter, TableHead, TableHeader, TableRow, TableToolbar, TableTitle } from "@/components/ui/table";
import { Tooltip } from "@/components/ui/tooltip";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api/client";
import { fmtDateTime } from "@/lib/format";
import { useAsync } from "@/lib/use-async";
import { ErrorPanel } from "../shared/error-panel";
import { PageSkeleton } from "../shared/skeletons";
import { useVocab } from "../shared/use-vocab";

const PAGE = 10;

/** S-05 Search History — previous runs of this browser session; reopening never re-runs a search. */
export function HistoryScreen() {
  const t = useTranslations("history");
  const v = useVocab();
  const runs = useAsync(() => api.listSearches(), []);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => (runs.status === "success" ? runs.data.filter((r) => r.query.toLowerCase().includes(q.trim().toLowerCase())) : []), [runs, q]);
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));
  const rows = filtered.slice((page - 1) * PAGE, page * PAGE);

  return (
    <>
      <PageHeader
        title={t("title")}
        description={t("subtitle")}
        actions={
          <Button asChild>
            <Link href="/search">
              <SearchIcon />
              {t("newSearch")}
            </Link>
          </Button>
        }
      />
      {runs.status === "loading" ? (
        <PageSkeleton blocks={1} />
      ) : runs.status === "error" ? (
        <ErrorPanel error={runs.error} onRetry={runs.reload} />
      ) : runs.data.length === 0 ? (
        <Card>
          <EmptyState
            icon={<HistoryIcon />}
            title={t("empty.title")}
            description={t("empty.text")}
            actions={
              <Button asChild>
                <Link href="/search">{t("newSearch")}</Link>
              </Button>
            }
          />
        </Card>
      ) : (
        <TableCard>
          <TableToolbar>
            <TableTitle title={t("tableTitle")} subtitle={t("count", { count: runs.data.length })} />
            <div className="w-full max-w-80 max-xl:max-w-none">
              <Input
                size="sm"
                aria-label={t("filter")}
                placeholder={t("filter")}
                prefix={<SearchIcon />}
                value={q}
                onChange={(e) => {
                  setQ(e.target.value);
                  setPage(1);
                }}
              />
            </div>
          </TableToolbar>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("cols.query")}</TableHead>
                <TableHead>{t("cols.date")}</TableHead>
                <TableHead>{t("cols.results")}</TableHead>
                <TableHead>{t("cols.scope")}</TableHead>
                <TableHead>
                  <span className="sr-only">{t("cols.actions")}</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length ? (
                rows.map((r) => (
                  <TableRow key={r.request_id}>
                    <TableCell label={t("cols.query")} className="max-w-[420px]">
                      <Link href={`/results/${r.request_id}`} className="line-clamp-2 rounded-xs text-heading outline-none hover:text-primary-700 focus-visible:ring-4 focus-visible:ring-primary-600/15">
                        {r.query}
                      </Link>
                    </TableCell>
                    <TableCell label={t("cols.date")}>{fmtDateTime(r.created_at)}</TableCell>
                    <TableCell label={t("cols.results")}>{r.result_count ? r.result_count : <span className="text-muted">{t("noResults")}</span>}</TableCell>
                    <TableCell label={t("cols.scope")}>
                      <Badge size="sm" color={r.market_scope === "external" ? "purple" : "gray"}>
                        {v.scope(r.market_scope)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <TableActions>
                        <Tooltip content={t("open")}>
                          <Button asChild variant="ghost" size="icon" aria-label={t("open")}>
                            <Link href={`/results/${r.request_id}`}>
                              <EyeIcon />
                            </Link>
                          </Button>
                        </Tooltip>
                      </TableActions>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableEmpty colSpan={5}>
                  <EmptyState icon={<FaceFrownIcon />} title={t("noMatch.title")} description={t("noMatch.text")} />
                </TableEmpty>
              )}
            </TableBody>
          </Table>
          {pages > 1 ? (
            <TableFooter>
              <span className="text-xs text-muted">{t("pageOf", { page, pages })}</span>
              <Pagination page={page} pageCount={pages} onPageChange={setPage} />
            </TableFooter>
          ) : null}
        </TableCard>
      )}
    </>
  );
}
