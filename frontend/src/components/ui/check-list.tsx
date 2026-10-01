import type { ReactNode } from "react";
import { CheckCircleSmIcon, InfoCircleSmIcon, WarningTriangleIcon } from "@/components/icons";
import { cn } from "@/lib/utils";

export type CheckListItem = { key: string; label: ReactNode; tone?: "positive" | "risk" | "neutral"; description?: ReactNode };

const toneCls = {
  positive: "text-success-600",
  risk: "text-warning-800",
  neutral: "text-muted",
};
const toneIcon = {
  positive: <CheckCircleSmIcon />,
  risk: <WarningTriangleIcon />,
  neutral: <InfoCircleSmIcon />,
};

/**
 * Reason / flag checklist (Supplier Radar DS extension): 16px status glyph + 14/22 text, 6px row gap.
 * Every row carries an icon AND text so status never depends on colour alone.
 */
export function CheckList({ items, size = "default", className }: { items: CheckListItem[]; size?: "sm" | "default"; className?: string }) {
  return (
    <ul className={cn("flex flex-col", size === "sm" ? "gap-1" : "gap-1.5", className)}>
      {items.map((it) => {
        const tone = it.tone ?? "positive";
        return (
          <li key={it.key} className="flex items-start gap-2">
            <span className={cn("mt-[3px] flex shrink-0 [&_svg]:size-4", toneCls[tone])} aria-hidden>
              {toneIcon[tone]}
            </span>
            <span className="flex min-w-0 flex-col">
              <span className={cn(size === "sm" ? "text-xs" : "text-sm", tone === "risk" ? "text-heading" : "text-body")}>{it.label}</span>
              {it.description ? <span className="text-xs text-muted">{it.description}</span> : null}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
