"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { BoxIcon, ClipboardListIcon, DocumentIcon, ScalesIcon, SearchIcon, VerifiedIcon } from "@/components/icons";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckList } from "@/components/ui/check-list";
import { Card, CardBody, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog, DialogClose } from "@/components/ui/dialog";
import { DescriptionList } from "@/components/ui/description-list";
import { EmptyState } from "@/components/ui/empty-state";
import { ExternalLink } from "@/components/ui/external-link";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { Progress } from "@/components/ui/progress";
import { ScoreStat } from "@/components/ui/score";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsCount, TabsHeader, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import { confidenceTone, UI_CONFIG } from "@/config/ui";
import { Link } from "@/i18n/navigation";
import { api, isApiError } from "@/lib/api/client";
import type { SupplierProfile } from "@/lib/api/types";
import { fmtDate, fmtRub, toPct } from "@/lib/format";
import { useAsync } from "@/lib/use-async";
import { cn } from "@/lib/utils";
import { Contributions, EvidenceList, Reasons } from "../results/why-matched";
import { ErrorPanel } from "../shared/error-panel";
import { FeedbackControl } from "../shared/feedback-control";
import { PageSkeleton } from "../shared/skeletons";
import { MarketBadge, TypeBadge } from "../shared/supplier-badges";
import { useVocab } from "../shared/use-vocab";
import { useSession } from "../shell/session-store";

const OFFERINGS_PAGE = 5;
const HISTORY_PAGE = 8;

/** S-03 Supplier Profile — optional query context via `?request_id=` (UF-08, EC-46). */
export function SupplierScreen({ supplierId, requestId }: { supplierId: string; requestId?: string }) {
  const t = useTranslations("supplier");
  const profile = useAsync(() => api.getSupplier(supplierId, requestId), [supplierId, requestId]);
  const back = requestId ? `/results/${requestId}` : "/search";

  if (profile.status === "loading")
    return (
      <>
        <PageHeader title={t("loading")} backHref={back} />
        <PageSkeleton blocks={3} />
      </>
    );
  if (profile.status === "error") {
    if (isApiError(profile.error) && profile.error.code === "SUPPLIER_NOT_FOUND")
      return (
        <>
          <PageHeader title={t("notFound.title")} backHref={back} />
          <Card>
            <EmptyState
              icon={<SearchIcon />}
              title={t("notFound.title")}
              description={t("notFound.text")}
              actions={
                <Button asChild variant="secondary">
                  <Link href={back}>{requestId ? t("backToResults") : t("toSearch")}</Link>
                </Button>
              }
            />
          </Card>
        </>
      );
    return (
      <>
        <PageHeader title={t("title")} backHref={back} />
        <ErrorPanel error={profile.error} onRetry={profile.reload} />
      </>
    );
  }
  return <Profile p={profile.data} back={back} requestId={requestId} />;
}

function Profile({ p, back, requestId }: { p: SupplierProfile; back: string; requestId?: string }) {
  const t = useTranslations("supplier");
  const v = useVocab();
  const toast = useToast();
  const { tray, toggle, replace } = useSession();
  const [conflict, setConflict] = useState(false);
  const ctx = p.query_context;
  const inTray = Boolean(ctx) && tray.requestId === ctx?.request_id && tray.ids.includes(p.supplier_id);

  const onCompare = () => {
    if (!ctx) return;
    const r = toggle(ctx.request_id, p.supplier_id);
    if (r === "limit") toast({ tone: "warning", title: t("compareLimit", { max: UI_CONFIG.compareMax }) });
    if (r === "conflict") setConflict(true);
    if (r === "added") toast({ tone: "success", title: t("compareAdded") });
  };

  return (
    <>
      <PageHeader
        title={p.legal_name}
        backHref={back}
        description={[p.inn ? `${t("inn")} ${p.inn}` : t("innUnknown"), p.region_name ?? t("unknown")].join(" · ")}
        actions={
          <>
            {ctx ? (
              <Button variant={inTray ? "secondary" : "outline"} onClick={onCompare}>
                <ScalesIcon />
                {inTray ? t("inCompare") : t("addToCompare")}
              </Button>
            ) : null}
            {requestId ? (
              <Button asChild variant="secondary">
                <Link href={back}>{t("backToResults")}</Link>
              </Button>
            ) : null}
          </>
        }
      />

      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-center gap-2">
          <MarketBadge known={p.is_known_supplier} />
          <TypeBadge type={p.supplier_type} verified={Boolean(p.supplier_type_basis)} />
          <Badge color={p.legal_status === "active" ? "success" : p.legal_status === "unknown" ? "gray" : "danger"}>{v.legalStatus(p.legal_status)}</Badge>
        </div>

        {p.redirected_from ? <Alert tone="info" appearance="inline" description={t("redirected", { id: p.redirected_from })} /> : null}
        {p.context_status === "expired" ? <Alert tone="warning" appearance="inline" title={t("contextExpired.title")} description={t("contextExpired.text")} /> : null}

        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="flex min-w-0 flex-col gap-5">
            {ctx ? (
              <Card className="border-primary-100">
                <CardHeader className="flex-wrap items-start">
                  <div className="flex flex-col gap-1">
                    <CardTitle>{t("context.title")}</CardTitle>
                    <CardDescription>
                      «{ctx.query}» · {t("context.rank", { rank: ctx.rank })}
                    </CardDescription>
                  </div>
                  <FeedbackControl requestId={ctx.request_id} supplierId={p.supplier_id} />
                </CardHeader>
                <CardBody className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  <div className="flex flex-col gap-5">
                    <div className="grid grid-cols-2 gap-4">
                      <ScoreStat label={t("match")} value={toPct(ctx.match_score)} />
                      <ScoreStat label={t("confidenceLabel")} value={toPct(ctx.confidence_score)} tone={confidenceTone(ctx.confidence_score)} unknownLabel={t("unknown")} />
                    </div>
                    <Reasons codes={ctx.reason_codes} params={ctx.reason_params} />
                  </div>
                  <div className="flex flex-col gap-3">
                    <h4 className="text-sm font-medium text-heading">{t("context.contributions")}</h4>
                    <Contributions contributions={ctx.contributions} matchScore={ctx.match_score} />
                  </div>
                </CardBody>
              </Card>
            ) : null}

            <Card>
              <Tabs defaultValue="offerings" className="gap-0">
                <TabsHeader className="px-5 pt-4">
                  <TabsList>
                    <TabsTrigger value="offerings">
                      <BoxIcon />
                      {t("tabs.offerings")}
                      <TabsCount value={p.offerings.length} />
                    </TabsTrigger>
                    <TabsTrigger value="history">
                      <ClipboardListIcon />
                      {t("tabs.history")}
                      <TabsCount value={p.procurement_history.length} />
                    </TabsTrigger>
                    <TabsTrigger value="evidence">
                      <DocumentIcon />
                      {t("tabs.evidence")}
                      <TabsCount value={p.evidence.length} />
                    </TabsTrigger>
                  </TabsList>
                </TabsHeader>
                <TabsContent value="offerings">
                  <Offerings p={p} />
                </TabsContent>
                <TabsContent value="history">
                  <History p={p} />
                </TabsContent>
                <TabsContent value="evidence" className="p-5">
                  <EvidenceList evidence={p.evidence} />
                </TabsContent>
              </Tabs>
            </Card>
          </div>

          <aside className="flex flex-col gap-5">
            <Identity p={p} />
            <Role p={p} />
            <Confidence p={p} />
            <Risks p={p} />
            <Sources p={p} />
          </aside>
        </div>
      </div>

      <ConfirmDialog
        open={conflict}
        onOpenChange={setConflict}
        tone="warning"
        icon={<ScalesIcon />}
        title={t("conflictTitle")}
        description={t("conflictText")}
        cancel={
          <DialogClose asChild>
            <Button variant="secondary">{t("keep")}</Button>
          </DialogClose>
        }
        confirm={
          <Button
            onClick={() => {
              if (ctx) replace(ctx.request_id, p.supplier_id);
              setConflict(false);
            }}
          >
            {t("startNew")}
          </Button>
        }
      />
    </>
  );
}

function SideCard({ title, children, description }: { title: ReactNode; description?: ReactNode; children: ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-1">
          <CardTitle>{title}</CardTitle>
          {description ? <CardDescription>{description}</CardDescription> : null}
        </div>
      </CardHeader>
      <CardBody className="pt-3">{children}</CardBody>
    </Card>
  );
}

function Identity({ p }: { p: SupplierProfile }) {
  const t = useTranslations("supplier.identity");
  const ltr = (x: string | null) => (x ? <span dir="ltr">{x}</span> : undefined);
  return (
    <SideCard title={t("title")}>
      <DescriptionList
        className="grid-cols-2"
        columns={2}
        items={[
          { label: t("legalName"), value: p.legal_name, wide: true },
          { label: t("inn"), value: ltr(p.inn) },
          { label: t("ogrn"), value: ltr(p.ogrn) },
          { label: t("kpp"), value: ltr(p.kpp) },
          { label: t("region"), value: p.region_name ?? undefined },
          { label: t("city"), value: p.city ?? undefined },
          { label: t("firstSeen"), value: p.first_seen_at ? fmtDate(p.first_seen_at) : p.is_known_supplier ? undefined : t("neverSupplied") },
          { label: t("website"), value: p.website ? <ExternalLink href={p.website}>{p.website.replace(/^https?:\/\//, "")}</ExternalLink> : undefined, wide: true },
          {
            label: t("okved"),
            wide: true,
            value: p.okved.length ? (
              <ul className="flex flex-col gap-1">
                {p.okved.map((o) => (
                  <li key={o.code}>
                    <span dir="ltr" className="font-medium">
                      {o.code}
                    </span>{" "}
                    <span className="text-subtle">{o.name}</span>
                  </li>
                ))}
              </ul>
            ) : undefined,
          },
        ]}
      />
      <p className="mt-3 text-2xs text-muted">{t("unknownHint")}</p>
    </SideCard>
  );
}

function Role({ p }: { p: SupplierProfile }) {
  const t = useTranslations("supplier.role");
  const v = useVocab();
  return (
    <SideCard title={t("title")}>
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <TypeBadge type={p.supplier_type} verified={Boolean(p.supplier_type_basis)} />
        </div>
        {p.supplier_type_basis ? (
          <p className="flex flex-wrap items-center gap-1 text-sm text-subtle">
            <VerifiedIcon className="size-4 text-info-700" aria-hidden />
            {t("basis")}{" "}
            {p.supplier_type_basis.source_url ? <ExternalLink href={p.supplier_type_basis.source_url}>{p.supplier_type_basis.source_name}</ExternalLink> : p.supplier_type_basis.source_name}
            <span className="text-muted">· {fmtDate(p.supplier_type_basis.observed_at)}</span>
          </p>
        ) : (
          <p className="text-sm text-subtle">{p.supplier_type === "manufacturer" ? v.riskMeaning("UNVERIFIED_MANUFACTURER") : t("noBasis")}</p>
        )}
      </div>
    </SideCard>
  );
}

function Confidence({ p }: { p: SupplierProfile }) {
  const t = useTranslations("supplier.confidence");
  const v = useVocab();
  return (
    <SideCard title={t("title")} description={t("subtitle")}>
      <div className="flex flex-col gap-4">
        <ScoreStat label={t("total")} value={toPct(p.confidence_score)} tone={confidenceTone(p.confidence_score)} unknownLabel={t("noData")} />
        <ul className="flex flex-col gap-3">
          {p.confidence_breakdown.map((c) => (
            <li key={c.component} className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="text-body">{v.confidenceComponent(c.component)}</span>
                <span className={cn("font-medium", c.value === null ? "text-muted" : "text-heading")}>{c.value === null ? t("noData") : toPct(c.value)}</span>
              </div>
              <Progress value={toPct(c.value) ?? 0} className="h-1.5" tone="primary" label={v.confidenceComponent(c.component)} />
              <span className="text-2xs text-muted">{t("weight", { value: Math.round(c.weight * 100) })}</span>
            </li>
          ))}
        </ul>
      </div>
    </SideCard>
  );
}

function Risks({ p }: { p: SupplierProfile }) {
  const t = useTranslations("supplier.risks");
  const v = useVocab();
  return (
    <SideCard title={t("title")} description={t("subtitle")}>
      {p.risk_flags.length ? (
        <CheckList items={p.risk_flags.map((f) => ({ key: f, tone: "risk", label: v.risk(f), description: v.riskMeaning(f) }))} />
      ) : (
        <CheckList items={[{ key: "none", tone: "positive", label: t("none") }]} />
      )}
    </SideCard>
  );
}

function Sources({ p }: { p: SupplierProfile }) {
  const t = useTranslations("supplier.sources");
  return (
    <SideCard title={t("title")}>
      <ul className="flex flex-col divide-y divide-line-subtle">
        {p.sources.map((s) => (
          <li key={s.source_name} className="flex items-center justify-between gap-3 py-2 text-sm first:pt-0 last:pb-0">
            <span className="flex min-w-0 flex-col">
              <span className="truncate text-heading">{s.source_name}</span>
              <span className="text-xs text-muted">{t("observed", { date: fmtDate(s.observed_at) })}</span>
            </span>
            {s.is_synthetic ? (
              <Badge color="warning" size="sm">
                {t("synthetic")}
              </Badge>
            ) : null}
          </li>
        ))}
      </ul>
      {p.data_quality_flags.length ? (
        <div className="mt-4 flex flex-col gap-2 border-t border-line-subtle pt-3">
          <span className="text-xs font-medium text-subtle">{t("quality")}</span>
          <ul className="flex flex-wrap gap-1.5">
            {p.data_quality_flags.map((f) => (
              <li key={f}>
                <Badge size="sm" color="gray">
                  {t.has(`flags.${f}`) ? t(`flags.${f}`) : f}
                </Badge>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </SideCard>
  );
}

function Offerings({ p }: { p: SupplierProfile }) {
  const t = useTranslations("supplier.offerings");
  const [page, setPage] = useState(1);
  if (!p.offerings.length) return <EmptyState size="small" icon={<BoxIcon />} title={t("empty")} />;
  const pages = Math.ceil(p.offerings.length / OFFERINGS_PAGE);
  const items = p.offerings.slice((page - 1) * OFFERINGS_PAGE, page * OFFERINGS_PAGE);
  return (
    <div className="flex flex-col">
      <ul className="flex flex-col divide-y divide-line">
        {items.map((o) => (
          <li key={o.offering_id} className="flex flex-col gap-1.5 px-5 py-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium text-heading">{o.title}</span>
              {o.matched ? (
                <Badge size="sm" color="success">
                  {t("matched")}
                </Badge>
              ) : null}
            </div>
            <span className="text-xs text-muted">
              {o.category_name} · {t("source", { source: o.source_name })}
            </span>
            {Object.keys(o.attributes).length ? (
              <ul className="flex flex-wrap gap-1.5">
                {Object.entries(o.attributes).map(([k, val]) => (
                  <li key={k}>
                    <Badge size="sm" color="gray" className="min-w-0">
                      {t.has(`attr.${k}`) ? t(`attr.${k}`) : k}: {String(val)}
                    </Badge>
                  </li>
                ))}
              </ul>
            ) : null}
          </li>
        ))}
      </ul>
      {pages > 1 ? <Pagination className="border-t border-line px-5 py-4" page={page} pageCount={pages} onPageChange={setPage} /> : null}
    </div>
  );
}

function History({ p }: { p: SupplierProfile }) {
  const t = useTranslations("supplier.history");
  const locale = useLocale();
  const [page, setPage] = useState(1);
  if (!p.procurement_history.length) return <EmptyState size="small" icon={<ClipboardListIcon />} title={t("empty")} description={t("emptyHint")} />;
  const pages = Math.ceil(p.procurement_history.length / HISTORY_PAGE);
  const rows = p.procurement_history.slice((page - 1) * HISTORY_PAGE, page * HISTORY_PAGE);
  return (
    <div className="flex flex-col max-xl:px-5">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("titleCol")}</TableHead>
            <TableHead className="min-w-[110px]">{t("date")}</TableHead>
            <TableHead className="min-w-[110px]">{t("role")}</TableHead>
            <TableHead className="min-w-[130px]">{t("amount")}</TableHead>
            <TableHead className="last:static last:w-auto last:max-w-none">{t("customer")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r) => (
            <TableRow key={r.record_id} className="max-xl:pt-2">
              <TableCell label={t("titleCol")} className="max-xl:items-start">
                <span className="flex flex-col gap-1 max-xl:items-end max-xl:text-end">
                  <span className="text-sm text-heading">{r.title}</span>
                  {r.relevant ? (
                    <Badge size="sm" color="success" className="min-w-0">
                      {t("relevant")}
                    </Badge>
                  ) : null}
                </span>
              </TableCell>
              <TableCell label={t("date")}>{fmtDate(r.date)}</TableCell>
              <TableCell label={t("role")}>
                <Badge size="sm" color={r.role === "winner" ? "primary" : "gray"}>
                  {t(r.role)}
                </Badge>
              </TableCell>
              <TableCell label={t("amount")}>{fmtRub(r.amount_rub) ?? <span className="text-muted">{t("amountUnknown")}</span>}</TableCell>
              <TableCell label={t("customer")} className="last:static last:w-auto last:max-w-none last:bg-transparent group-hover/row:last:bg-transparent max-xl:last:static max-xl:last:w-full max-xl:last:justify-between max-xl:last:border-0 max-xl:last:pt-2 max-xl:last:pb-0 max-xl:last:before:block">
                <span className="flex flex-col max-xl:items-end max-xl:text-end">
                  <span>{r.customer_name}</span>
                  <span className="text-xs text-muted">{r.region_name ?? ""}</span>
                </span>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {pages > 1 ? (
        <div className="flex items-center justify-between gap-3 border-t border-line px-5 py-4 max-xl:border-0 max-xl:px-0">
          <span className="text-xs text-muted">{t("pageOf", { page: new Intl.NumberFormat(locale).format(page), pages })}</span>
          <Pagination page={page} pageCount={pages} onPageChange={setPage} />
        </div>
      ) : null}
    </div>
  );
}
