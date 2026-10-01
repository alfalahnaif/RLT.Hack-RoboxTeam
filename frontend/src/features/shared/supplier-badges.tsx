"use client";

import { useTranslations } from "next-intl";
import { SparklesIcon, VerifiedIcon, WarningTriangleIcon } from "@/components/icons";
import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/tooltip";
import type { RiskFlag, SupplierType } from "@/lib/api/types";
import { useVocab } from "./use-vocab";

/** Known (in AIS history) vs external (new to the customer) — text + icon, never colour only. */
export function MarketBadge({ known, size = "default" }: { known: boolean; size?: "sm" | "default" }) {
  const t = useTranslations("vocab");
  return known ? (
    <Badge color="gray" size={size}>
      {t("market.known")}
    </Badge>
  ) : (
    <Badge color="purple" size={size}>
      <SparklesIcon aria-hidden />
      {t("market.external")}
    </Badge>
  );
}

export function TypeBadge({ type, verified, size = "default" }: { type: SupplierType; verified: boolean; size?: "sm" | "default" }) {
  const v = useVocab();
  const t = useTranslations("vocab");
  return (
    <Badge color={verified ? "info" : "gray"} size={size}>
      {verified ? <VerifiedIcon aria-hidden /> : null}
      {v.supplierType(type)}
      {type !== "unknown" ? <span className="sr-only">, {verified ? t("verified") : t("unverified")}</span> : null}
    </Badge>
  );
}

/** Risk flags as warning badges with the human-readable meaning in a tooltip (S-02/S-03). */
export function RiskBadges({ flags, size = "sm" }: { flags: RiskFlag[]; size?: "sm" | "default" }) {
  const v = useVocab();
  if (!flags.length) return null;
  return (
    <ul className="flex flex-wrap gap-1.5">
      {flags.map((f) => (
        <li key={f}>
          <Tooltip content={v.riskMeaning(f)}>
            <span tabIndex={0} className="inline-flex rounded-pill outline-none focus-visible:ring-4 focus-visible:ring-primary-600/15">
              <Badge color="warning" size={size}>
                <WarningTriangleIcon aria-hidden />
                {v.risk(f)}
              </Badge>
            </span>
          </Tooltip>
        </li>
      ))}
    </ul>
  );
}
