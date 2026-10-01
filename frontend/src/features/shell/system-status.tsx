"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Tooltip } from "@/components/ui/tooltip";
import { api } from "@/lib/api/client";
import type { HealthStatus } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const POLL_MS = 30_000;

/**
 * System status from `/health` (S-00, optional): dot + text pill; the component list is in a tooltip.
 * Unreachable API → "down". Re-polls every 30 s.
 */
export function SystemStatus({ variant = "light" }: { variant?: "light" | "dark" }) {
  const t = useTranslations("shell.status");
  const [health, setHealth] = useState<HealthStatus | "unreachable" | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () => api.health().then((h) => alive && setHealth(h), () => alive && setHealth("unreachable"));
    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const status = health === null ? "checking" : health === "unreachable" ? "down" : health.status;
  const dot = { checking: "bg-gray-400", ok: "bg-success-600", degraded: "bg-warning-600", down: "bg-danger-600" }[status];
  const detail =
    health && health !== "unreachable"
      ? Object.entries(health.components)
          .map(([k, v]) => `${k}: ${t(`component.${v}`)}`)
          .join(" · ")
      : t(status === "checking" ? "checking" : "unreachable");

  return (
    <Tooltip content={detail}>
      <span
        tabIndex={0}
        role="status"
        className={cn(
          "inline-flex h-8 items-center gap-2 rounded-pill px-3 text-xs font-medium outline-none focus-visible:ring-4 focus-visible:ring-primary-600/15",
          variant === "light" ? "border border-line-subtle bg-surface-subtle text-subtle" : "bg-white/10 text-white",
        )}
      >
        <span aria-hidden className={cn("size-2 rounded-full", dot)} />
        <span className={variant === "dark" ? "sr-only" : undefined}>{t(status)}</span>
      </span>
    </Tooltip>
  );
}
