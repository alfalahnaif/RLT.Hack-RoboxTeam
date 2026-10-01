"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { ClipboardListIcon, HistoryIcon, InfoCircleSmIcon, ListTreeIcon, ScalesIcon, SearchIcon } from "@/components/icons";
import { LocaleSwitch } from "@/components/layout/locale-switch";
import { TopBar } from "@/components/layout/top-bar";
import type { NavItem } from "@/components/layout/types";
import { CountBadge } from "@/components/ui/badge";
import { ToastProvider } from "@/components/ui/toast";
import { API_MODE } from "@/lib/api/client";
import { SessionProvider, useSession } from "./session-store";
import { SystemStatus } from "./system-status";

/** S-00 global shell: top navigation, system status, language, demo-data notice (BR-20). */
export function AppFrame({ children }: { children: ReactNode }) {
  return (
    <SessionProvider>
      <ToastProvider>
        <Frame>{children}</Frame>
      </ToastProvider>
    </SessionProvider>
  );
}

function Frame({ children }: { children: ReactNode }) {
  const t = useTranslations("shell");
  const { tray, lastRequestId } = useSession();

  const analysis: NavItem = { key: "analysis", label: t("nav.analysis"), icon: ClipboardListIcon, href: "/analysis" };
  // Live mode: only screens backed by the real API (P4-001). The mock search/compare/history screens stay available in mock mode.
  const mockNav: NavItem[] = [
    { key: "search", label: t("nav.search"), icon: SearchIcon, href: "/search" },
    { key: "results", label: t("nav.results"), icon: ListTreeIcon, href: lastRequestId ? `/results/${lastRequestId}` : "/results" },
    {
      key: "compare",
      label: t("nav.compare"),
      icon: ScalesIcon,
      href: "/compare",
      badge: tray.ids.length ? <CountBadge aria-label={t("nav.compareCount", { count: tray.ids.length })}>{tray.ids.length}</CountBadge> : undefined,
    },
    { key: "history", label: t("nav.history"), icon: HistoryIcon, href: "/history" },
  ];
  const nav = API_MODE === "live" ? [analysis] : [analysis, ...mockNav];

  return (
    <div className="flex min-h-dvh flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:start-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-white focus:px-3 focus:py-2 focus:shadow-popper">
        {t("skipToContent")}
      </a>
      <TopBar
        items={nav}
        homeHref={API_MODE === "live" ? "/analysis" : "/search"}
        menuLabel={t("menu")}
        actions={
          <>
            <SystemStatus />
            <span className="h-[30px] w-px bg-line-subtle" aria-hidden />
            <LocaleSwitch />
          </>
        }
        mobileActions={
          <>
            <SystemStatus variant="dark" />
            <LocaleSwitch className="text-white/80 hover:text-white" />
          </>
        }
        // notice={API_MODE === "mock" ? <DemoNotice /> : null}
      />
      <main id="main" className="mx-auto w-full max-w-[1224px] flex-1 px-4 pb-28 lg:px-6 2xl:px-0">
        {children}
      </main>
    </div>
  );
}

function DemoNotice() {
  const t = useTranslations("shell");
  return (
    <div role="note" className="border-b border-warning-300 bg-warning-100 px-4 py-2 text-xs text-warning-950 lg:px-6">
      <div className="mx-auto flex max-w-[1224px] items-center gap-2">
        <InfoCircleSmIcon className="size-4 shrink-0 text-warning-800" aria-hidden />
        <span>
          <span className="font-medium">{t("demo.title")}</span> {t("demo.text")}
        </span>
      </div>
    </div>
  );
}
