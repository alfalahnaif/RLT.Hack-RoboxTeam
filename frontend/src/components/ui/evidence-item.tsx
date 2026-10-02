import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Badge } from "./badge";
import { ExternalLink } from "./external-link";

/**
 * Evidence row (Supplier Radar DS extension): type badge (soft, sm) + claim 14/22, then a 12/18 meta line
 * "source (link) · observed date · confidence". Every external fact shows source + link/ref + observed_at (BR-35).
 * Claims are untrusted text and rendered as text only.
 */
export function EvidenceItem({
  type,
  typeColor = "gray",
  claim,
  sourceName,
  sourceUrl,
  observedLabel,
  confidenceLabel,
  noLinkLabel,
  compact,
  className,
}: {
  type: ReactNode;
  typeColor?: "gray" | "primary" | "success" | "info" | "purple" | "orange";
  claim: string;
  sourceName: string;
  sourceUrl: string | null;
  observedLabel: ReactNode;
  confidenceLabel?: ReactNode;
  noLinkLabel?: ReactNode;
  compact?: boolean;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-1.5", compact ? "py-2" : "rounded-md border border-line p-3", className)}>
      <div className="flex flex-wrap items-start gap-2">
        <Badge size="sm" color={typeColor}>
          {type}
        </Badge>
        <p className="min-w-0 flex-1 text-sm text-heading [overflow-wrap:anywhere]">{claim}</p>
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
        {sourceUrl ? (
          <ExternalLink href={sourceUrl} className="text-xs">
            {sourceName}
          </ExternalLink>
        ) : (
          <span>
            {sourceName}
            {noLinkLabel ? <span className="text-disabled"> · {noLinkLabel}</span> : null}
          </span>
        )}
        <span>{observedLabel}</span>
        {confidenceLabel ? <span>{confidenceLabel}</span> : null}
      </div>
    </div>
  );
}
