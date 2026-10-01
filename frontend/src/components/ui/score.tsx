import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Progress } from "./progress";

type Tone = "primary" | "success" | "warning" | "danger";

/**
 * Score read-out (Supplier Radar DS extension): 12/18 label, 20/30 semibold value with a muted "/100",
 * and an optional 8px meter underneath. `value={null}` renders an explicit unknown ("—" + `unknownLabel`),
 * never 0 (EC-30). Status is carried by the number and label, the meter colour only reinforces it.
 */
export function ScoreStat({
  label,
  value,
  tone = "primary",
  unknownLabel,
  meter = true,
  size = "default",
  hint,
  className,
}: {
  label: ReactNode;
  /** 0–100 integer, or null when unknown. */
  value: number | null;
  tone?: Tone;
  unknownLabel?: ReactNode;
  meter?: boolean;
  size?: "sm" | "default";
  hint?: ReactNode;
  className?: string;
}) {
  const known = value !== null;
  return (
    <div className={cn("flex min-w-0 flex-col gap-1.5", className)}>
      <span className="text-xs text-muted">{label}</span>
      <span className="flex items-baseline gap-1">
        <span className={cn("font-semibold tracking-tight text-heading", size === "sm" ? "text-base" : "text-xl")}>{known ? value : "—"}</span>
        {known ? <span className="text-xs text-muted">/100</span> : unknownLabel ? <span className="text-xs text-muted">{unknownLabel}</span> : null}
      </span>
      {meter ? <Progress value={known ? value : 0} tone={tone} className="h-1.5" label={typeof label === "string" ? label : undefined} /> : null}
      {hint ? <span className="text-2xs text-muted">{hint}</span> : null}
    </div>
  );
}

/** Compact inline score pill: "Match 87" — 26px soft pill used inside dense rows and compare headers. */
export function ScorePill({ label, value, tone = "primary", className }: { label: ReactNode; value: number | null; tone?: Tone | "gray"; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex h-[26px] items-center gap-1.5 rounded-pill px-3 text-xs",
        tone === "primary" && "bg-primary-50 text-primary-700",
        tone === "success" && "bg-success-50 text-success-700",
        tone === "warning" && "bg-warning-100 text-warning-800",
        tone === "danger" && "bg-danger-50 text-danger-700",
        tone === "gray" && "bg-gray-50 text-gray-700",
        className,
      )}
    >
      <span>{label}</span>
      <span className="font-semibold">{value ?? "—"}</span>
    </span>
  );
}
