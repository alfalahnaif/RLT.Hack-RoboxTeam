"use client";

import { useTranslations } from "next-intl";
import type { ConfidenceComponent, ErrorCode, EvidenceType, LegalStatus, RankingFeature, ReasonCode, ReasonParams, RiskFlag, SupplierType, WarningCode } from "@/lib/api/types";

/**
 * Human-readable labels for the controlled vocabularies (reason codes, risk flags, features…).
 * The UI only renders codes the API returned — it never derives them (BR-12).
 */
export function useVocab() {
  const t = useTranslations("vocab");
  return {
    supplierType: (v: SupplierType) => t(`supplierType.${v}`),
    reason: (code: ReasonCode, params: ReasonParams = {}) => {
      const p = params[code] ?? {};
      if (code === "PROCUREMENT_EXPERIENCE" && p.count !== undefined) return t("reasonWithParams.PROCUREMENT_EXPERIENCE", { count: Number(p.count) });
      if (code === "ATTRIBUTE_MATCH" && p.requested !== undefined) return t("reasonWithParams.ATTRIBUTE_MATCH", { matched: Number(p.matched), requested: Number(p.requested) });
      if (code === "MULTI_SOURCE_VERIFICATION" && p.count !== undefined) return t("reasonWithParams.MULTI_SOURCE_VERIFICATION", { count: Number(p.count) });
      return t(`reason.${code}`);
    },
    risk: (flag: RiskFlag) => t(`risk.${flag}.label`),
    riskMeaning: (flag: RiskFlag) => t(`risk.${flag}.meaning`),
    feature: (f: RankingFeature) => t(`feature.${f}`),
    evidenceType: (e: EvidenceType) => t(`evidenceType.${e}`),
    warning: (w: WarningCode) => t(`warning.${w}`),
    error: (e: ErrorCode) => t(`error.${e}`),
    confidenceComponent: (c: ConfidenceComponent) => t(`confidenceComponent.${c}`),
    legalStatus: (s: LegalStatus) => t(`legalStatus.${s}`),
    scope: (s: "all" | "known" | "external") => t(`scope.${s}`),
  };
}

export const evidenceColor = (e: EvidenceType) =>
  (
    {
      PRODUCT_CATALOG: "primary",
      MANUFACTURER_REGISTRY: "success",
      LEGAL_REGISTRY: "info",
      PROCUREMENT_HISTORY: "purple",
      COMPANY_WEBSITE: "gray",
      DELIVERY_REGION: "gray",
      CERTIFICATION: "success",
      OPEN_WEB_MENTION: "orange",
    } as const
  )[e];
