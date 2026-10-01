import type { ReactNode } from "react";
import { MinusIcon } from "./_glyphs";
import { cn } from "@/lib/utils";
import { Card, CardBody, CardHeader, CardSubtitle } from "./card";

/**
 * KPI card (source `.card.chart-type1`): compact card (12px paddings), title 14/22 regular,
 * value 20/30 semibold (with optional unit), trend line 10/14 gray-700 with a 12px icon,
 * sparkline slot (96×48) at the end.
 */
export function StatCard({
  title,
  value,
  unit,
  trend,
  trendLabel,
  trendDirection = "flat",
  chart,
  className,
}: {
  title: ReactNode;
  value: ReactNode;
  unit?: ReactNode;
  trend?: ReactNode;
  trendLabel?: ReactNode;
  trendDirection?: "up" | "down" | "flat";
  chart?: ReactNode;
  className?: string;
}) {
  return (
    <Card compact className={className}>
      <CardHeader>
        <CardSubtitle>{title}</CardSubtitle>
      </CardHeader>
      <CardBody className="flex items-end justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-0.5">
          <h3 className="flex items-center gap-1 text-xl font-semibold text-heading">
            {value}
            {unit ? <span className="text-xs font-normal text-subtle">{unit}</span> : null}
          </h3>
          {trend !== undefined ? (
            <div className="flex items-center gap-1 text-2xs text-subtle">
              <span
                className={cn(
                  "flex size-3 items-center justify-center",
                  trendDirection === "up" && "text-success-600",
                  trendDirection === "down" && "text-danger-600",
                )}
              >
                {trendDirection === "flat" ? <MinusIcon className="size-3" /> : trendDirection === "up" ? "▲" : "▼"}
              </span>
              <span className={cn("text-xs text-muted", trendDirection === "up" && "text-success-600", trendDirection === "down" && "text-danger-600")}>{trend}</span>
              {trendLabel}
            </div>
          ) : null}
        </div>
        {chart ? <div className="h-12 w-24 shrink-0">{chart}</div> : null}
      </CardBody>
    </Card>
  );
}
