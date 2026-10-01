"use client";

import { useTranslations } from "next-intl";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { isApiError } from "@/lib/api/client";
import { useVocab } from "./use-vocab";

/** API error → danger announcement with the mapped message and an optional retry (S-01/S-02 503 state). */
export function ErrorPanel({ error, onRetry, title }: { error: unknown; onRetry?: () => void; title?: string }) {
  const t = useTranslations("common");
  const v = useVocab();
  const code = isApiError(error) ? error.code : "NETWORK_ERROR";
  return (
    <Alert
      tone="danger"
      title={title ?? t("errorTitle")}
      description={v.error(code)}
      actions={
        onRetry ? (
          <Button variant="secondary" size="sm" onClick={onRetry}>
            {t("retry")}
          </Button>
        ) : undefined
      }
    />
  );
}
