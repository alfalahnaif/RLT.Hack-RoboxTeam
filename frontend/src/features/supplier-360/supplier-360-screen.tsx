"use client";

import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { BoltIcon, CloudDownloadIcon, CopyIcon, SendIcon } from "@/components/icons";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Spinner } from "@/components/ui/spinner";
import { useToast } from "@/components/ui/toast";
import { API_MODE, SUPPLIER_ENRICH_AVAILABLE, api, isApiError } from "@/lib/api/client";
import type { SupplierProfile360 } from "@/lib/api/types";
import { useAsync } from "@/lib/use-async";
import { PageSkeleton } from "../shared/skeletons";
import { enrichmentView, headerRoles, legalStatusTone, primaryContactHref, profileName, secondaryName, type EnrichmentAction } from "./model";
import { ContactsSection, FreshnessSection, HistorySection, IdentitySection, RoleBadge, RolesSection, SourcesSection, useCopy, useLabel } from "./sections";

/**
 * P5-001B Supplier 360 — one profile experience for every supplier (historical and curated external), keyed by INN.
 * Renders the P5-001A response as returned: identity, role evidence, contacts, freshness and history stay separate.
 */
export function Supplier360Screen({ inn, backHref }: { inn: string; backHref: string }) {
  const t = useTranslations("supplier360");
  const toast = useToast();
  const run = useAsync(() => api.supplierProfile(inn), [inn]);
  // Profile returned by an enrichment call replaces the loaded one (keyed by INN so navigation never shows a stale profile).
  const [updated, setUpdated] = useState<SupplierProfile360 | null>(null);
  const [enrich, setEnrich] = useState<{ inn: string; status: "running" | "error" } | null>(null);
  const enrichStatus = enrich?.inn === inn ? enrich.status : null;

  const header = <PageHeader title={t("title")} backHref={backHref} />;
  const synthetic = API_MODE === "mock" ? <Alert tone="info" appearance="inline" description={t("syntheticNotice")} className="mb-4" /> : null;

  if (run.status === "loading")
    return (
      <>
        {header}
        <span className="sr-only" role="status">{t("loading")}</span>
        <PageSkeleton blocks={3} />
      </>
    );
  if (run.status === "error") {
    const code = isApiError(run.error) ? run.error.code : null;
    const notFound = code === "SUPPLIER_NOT_FOUND" || code === "INVALID_INN";
    return (
      <>
        {header}
        {synthetic}
        <Alert
          tone={notFound ? "warning" : "danger"}
          title={notFound ? t("error.notFoundTitle") : t("error.unavailableTitle")}
          description={code === "INVALID_INN" ? t("error.invalidInn") : notFound ? t("error.notFound", { inn }) : t("error.unavailable")}
          actions={notFound ? undefined : <Button variant="secondary" onClick={run.reload}>{t("error.retry")}</Button>}
        />
      </>
    );
  }

  const profile = updated && updated.supplier.inn === inn ? updated : run.data;

  const runEnrichment = async (action: NonNullable<EnrichmentAction>) => {
    setEnrich({ inn, status: "running" });
    try {
      const next = await api.enrichSupplier(inn, action.refresh);
      setUpdated(next);
      setEnrich(null);
      toast(next.enrichment.cache === "HIT" ? { tone: "info", title: t("actions.enrichCached") } : { tone: "success", title: t("actions.enrichDone") });
    } catch {
      setEnrich({ inn, status: "error" });
      toast({ tone: "danger", title: t("actions.enrichFailed") });
    }
  };

  return (
    <>
      {header}
      {synthetic}
      <div className="flex flex-col gap-4">
        <ProfileHeader profile={profile} />
        <EnrichmentPanel profile={profile} status={enrichStatus} onRun={runEnrichment} />
        <div className="grid items-start gap-4 lg:grid-cols-2">
          <ContactsSection profile={profile} />
          <RolesSection profile={profile} />
          <FreshnessSection profile={profile} />
          <IdentitySection profile={profile} />
        </div>
        <HistorySection profile={profile} />
        <SourcesSection profile={profile} />
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ header */

function ProfileHeader({ profile }: { profile: SupplierProfile360 }) {
  const t = useTranslations("supplier360");
  const label = useLabel();
  const copy = useCopy();
  const s = profile.supplier;
  const name = profileName(s);
  const short = secondaryName(s);
  const roles = headerRoles(profile.roles);

  return (
    <Card>
      <CardBody className="flex flex-col gap-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="flex min-w-0 flex-col gap-1.5">
            {name ? (
              <h2 className="break-words text-xl font-semibold text-heading">{name}</h2>
            ) : (
              <>
                <h2 className="break-all text-xl font-semibold text-heading">
                  {t("header.inn")} <span dir="ltr">{s.inn}</span>
                </h2>
                <p className="text-sm text-muted">{t("header.nameUnknown")}</p>
              </>
            )}
            {short ? <p className="break-words text-sm text-subtle">{short}</p> : null}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-subtle">
              <span className="inline-flex flex-wrap items-center gap-1">
                {t("header.inn")}: <span dir="ltr" className="break-all font-medium text-heading">{s.inn}</span>
                <button type="button" aria-label={t("header.copyInn")} title={t("header.copyInn")} onClick={() => void copy(s.inn)}
                  className="inline-flex size-7 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface-subtle hover:text-primary-700 [&_svg]:size-3.5">
                  <CopyIcon aria-hidden />
                </button>
              </span>
              {s.ogrn ? <span>{t("header.ogrn")}: <span dir="ltr" className="break-all">{s.ogrn}</span></span> : null}
              {s.kpp ? <span>{t("header.kpp")}: <span dir="ltr">{s.kpp}</span></span> : null}
              {s.region ? <span>{s.region}</span> : null}
            </div>
          </div>
          <ProfileActions profile={profile} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {s.legal_status ? (
            <Badge appearance="solid" color={legalStatusTone(s.legal_status)}>{label("legalStatus", s.legal_status)}</Badge>
          ) : (
            <Badge color="gray">{t("header.statusUnknown")}</Badge>
          )}
          {roles.length ? roles.map((r) => <RoleBadge key={r.role} label={t(`role.${r.role}`)} status={r.status} />) : <Badge color="gray" className="border border-dashed border-gray-400">{t("header.roleUnknown")}</Badge>}
          <Badge color={s.historically_known ? "primary" : "purple"}>{s.historically_known ? t("header.historical") : t("header.external")}</Badge>
        </div>
      </CardBody>
    </Card>
  );
}

/**
 * Header actions area. Each action is one entry; a future "Request quotation" (RFQ) action is added to `actions` here
 * without changing the profile layout. No placeholder button is rendered for actions that do not exist yet.
 */
function ProfileActions({ profile }: { profile: SupplierProfile360 }) {
  const t = useTranslations("supplier360.actions");
  const contact = primaryContactHref(profile.contacts);
  const actions: { key: string; node: ReactNode }[] = [];
  if (contact)
    actions.push({
      key: "contact",
      node: (
        <Button asChild size="sm">
          <a href={contact} {...(contact.startsWith("http") ? { target: "_blank", rel: "noopener noreferrer" } : {})}>
            <SendIcon aria-hidden />
            {t("contact")}
          </a>
        </Button>
      ),
    });
  actions.push({
    key: "export",
    node: (
      <Button variant="secondary" size="sm" onClick={() => exportProfile(profile)}>
        <CloudDownloadIcon aria-hidden />
        {t("export")}
      </Button>
    ),
  });
  return (
    <div role="group" aria-label={t("label")} className="flex shrink-0 flex-wrap gap-2">
      {actions.map((a) => <span key={a.key} className="contents">{a.node}</span>)}
    </div>
  );
}

/** Export = the profile exactly as the API returned it (no recomputed fields). */
function exportProfile(profile: SupplierProfile360) {
  const blob = new Blob([JSON.stringify(profile, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `supplier-360-${profile.supplier.inn}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/* ------------------------------------------------------------------ enrichment states */

function EnrichmentPanel({ profile, status, onRun }: { profile: SupplierProfile360; status: "running" | "error" | null; onRun: (a: NonNullable<EnrichmentAction>) => void }) {
  const t = useTranslations("supplier360");
  const label = useLabel();
  const e = profile.enrichment;
  const { notice, action } = enrichmentView(e, SUPPLIER_ENRICH_AVAILABLE);

  if (status === "running")
    return (
      <Alert tone="info" appearance="inline" icon={<Spinner size={20} className="text-primary-600" />} title={t("actions.enriching")} description={t("actions.enrichingHint")} aria-live="polite" />
    );

  const button = action ? (
    <Button variant={action.kind === "enrich" ? "primary" : "secondary"} size="sm" onClick={() => onRun(action)}>
      <BoltIcon aria-hidden />
      {action.kind === "enrich" ? t("actions.enrich") : t("actions.retry")}
    </Button>
  ) : null;
  const reasons = e.reasons.length ? (
    <div className="mt-1 flex flex-col gap-1">
      <span className="text-xs font-medium text-heading">{t("enrichment.reasons")}</span>
      <ul className="flex flex-wrap gap-1.5">
        {e.reasons.map((r) => <li key={r}><Badge size="sm" color="gray" className="h-auto min-h-[22px] whitespace-normal text-start">{label("reason", r)}</Badge></li>)}
      </ul>
    </div>
  ) : null;
  const callError = status === "error" ? <Alert tone="danger" appearance="inline" title={t("actions.enrichFailed")} description={t("actions.enrichFailedHint")} actions={button} /> : null;

  if (notice === null) return reasons && e.status === "COMPLETE" ? <Alert tone="default" appearance="inline" description={undefined}>{reasons}</Alert> : callError;

  const content = {
    notEnriched: { tone: "info" as const, title: t("enrichment.notEnrichedTitle"), text: button ? t("enrichment.notEnriched") : t("enrichment.notEnrichedNoAction") },
    inProgress: { tone: "info" as const, title: t("enrichment.inProgressTitle"), text: t("enrichment.inProgress") },
    partial: { tone: "warning" as const, title: t("enrichment.partialTitle"), text: t("enrichment.partial") },
    failed: { tone: "danger" as const, title: t("enrichment.failedTitle"), text: e.retryable ? t("enrichment.failed") : t("enrichment.failedFinal") },
  }[notice];

  return (
    <div className="flex flex-col gap-2">
      <Alert tone={content.tone} appearance="inline" title={content.title} description={content.text} actions={status === "error" ? undefined : button}
        icon={notice === "inProgress" ? <Spinner size={20} className="text-primary-600" /> : undefined}>
        {reasons}
      </Alert>
      {callError}
    </div>
  );
}
