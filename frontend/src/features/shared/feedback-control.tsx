"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { FaceHappyIcon, FaceNeutralIcon, FaceSadIcon } from "@/components/icons";
import { useToast } from "@/components/ui/toast";
import { api, API_MODE } from "@/lib/api/client";
import type { Relevance } from "@/lib/api/types";
import { getStoredFeedback } from "@/mocks/server";
import { cn } from "@/lib/utils";

const OPTIONS: { value: Relevance; icon: typeof FaceHappyIcon }[] = [
  { value: "relevant", icon: FaceHappyIcon },
  { value: "unsure", icon: FaceNeutralIcon },
  { value: "not_relevant", icon: FaceSadIcon },
];

/**
 * Relevance feedback (FR-15, P6-010 UI): three toggle buttons (icon + accessible label + tooltip text),
 * pressed state shown by fill AND aria-pressed. Re-sending overwrites (upsert). Confirmation via toast.
 */
export function FeedbackControl({ requestId, supplierId, compact }: { requestId: string; supplierId: string; compact?: boolean }) {
  const t = useTranslations("feedback");
  const toast = useToast();
  const [value, setValue] = useState<Relevance | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (API_MODE === "mock") setValue(getStoredFeedback(requestId, supplierId));
  }, [requestId, supplierId]);

  const send = async (relevance: Relevance) => {
    setBusy(true);
    try {
      await api.sendFeedback({ request_id: requestId, supplier_id: supplierId, relevance });
      setValue(relevance);
      toast({ tone: "success", title: t("saved") });
    } catch {
      toast({ tone: "danger", title: t("failed") });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div role="group" aria-label={t("label")} className="flex items-center gap-1.5">
      {compact ? null : <span className="me-1 text-xs text-muted">{t("label")}</span>}
      {OPTIONS.map(({ value: v, icon: Icon }) => {
        const pressed = value === v;
        return (
          <button
            key={v}
            type="button"
            aria-pressed={pressed}
            aria-label={t(v)}
            title={t(v)}
            disabled={busy}
            onClick={() => send(v)}
            className={cn(
              "flex size-8 items-center justify-center rounded-full border text-muted outline-none transition-colors [&_svg]:size-4",
              "hover:bg-surface-subtle hover:text-heading focus-visible:ring-4 focus-visible:ring-primary-600/15 disabled:opacity-50",
              pressed ? "border-primary-300 bg-primary-50 text-primary-700" : "border-line bg-white",
            )}
          >
            <Icon aria-hidden />
          </button>
        );
      })}
    </div>
  );
}
