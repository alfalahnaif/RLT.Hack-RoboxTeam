"use client";

import { useState, type ReactNode } from "react";
import { MenuAlignIcon } from "@/components/icons";
import { Link, usePathname } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { Drawer, DrawerBody, DrawerContent, DrawerHeader, DrawerTitle } from "@/components/ui/drawer";
import { Sidebar, SidebarNav } from "./sidebar";
import type { Brand, NavItem } from "./types";

/**
 * Application frame.
 * ≥960px: fixed sidebar (250 / 64 collapsed) + sticky 60px header + content column.
 * <960px: dark header + fixed bottom bar (first 4 `inBottomBar` items + "more" drawer with the full menu).
 * Content container: max-width 1224, centered, 16px (mobile) / 24px (tablet) / 0 (≥1400) side padding,
 * 46px bottom padding (+ bottom-bar height on mobile).
 */
export function AppShell({
  nav,
  footerNav = [],
  header,
  moreLabel,
  brand,
  sidebarTop,
  sidebarBottom,
  children,
}: {
  nav: NavItem[];
  footerNav?: NavItem[];
  header: ReactNode;
  moreLabel: ReactNode;
  brand?: Brand;
  sidebarTop?: ReactNode;
  sidebarBottom?: ReactNode;
  children: ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const pathname = usePathname();
  const bottom = nav.filter((n) => n.inBottomBar).slice(0, 4);

  return (
    <div className="min-h-dvh bg-canvas">
      <Sidebar items={nav} footerItems={footerNav} collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} brand={brand} top={sidebarTop} bottom={sidebarBottom} />
      <div className={cn("flex min-h-dvh flex-col transition-[padding] duration-300", collapsed ? "lg:ps-16" : "lg:ps-sidebar", "print:ps-0")}>
        {header}
        <main className="mx-auto w-full max-w-[1224px] flex-1 px-4 pb-28 lg:px-6 lg:pb-12 2xl:px-0 print:max-w-none print:p-0">{children}</main>
      </div>

      {/* Mobile bottom bar (source `.app-bottom-bar`) */}
      <nav className="fixed inset-x-0 bottom-0 z-30 print:hidden! grid grid-cols-5 gap-4 border-t border-line-subtle bg-white px-4 py-2.5 shadow-[0_-2px_8px_0_rgb(239_241_245/0.6)] lg:hidden">
        {bottom.map((item) => {
          const Icon = item.icon;
          const href = item.href ?? item.children?.[0]?.href ?? "#";
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={item.key}
              href={href}
              className={cn(
                "flex flex-col items-center gap-0.5 rounded-md border border-transparent py-1.5 text-center text-xs text-muted",
                active && "border-line bg-surface-subtle text-heading",
              )}
            >
              <Icon className="size-5" />
              <span className="line-clamp-2">{item.label}</span>
            </Link>
          );
        })}
        <button
          type="button"
          onClick={() => setMoreOpen(true)}
          className={cn("flex flex-col items-center gap-0.5 rounded-md border border-transparent py-1.5 text-xs text-muted", moreOpen && "border-line bg-surface-subtle text-heading")}
        >
          <MenuAlignIcon className="size-5" />
          {moreLabel}
        </button>
      </nav>

      <Drawer open={moreOpen} onOpenChange={setMoreOpen}>
        <DrawerContent side="start">
          <DrawerHeader>
            <DrawerTitle>{moreLabel}</DrawerTitle>
          </DrawerHeader>
          <DrawerBody className="pb-4">
            <SidebarNav items={[...nav, ...footerNav]} onNavigate={() => setMoreOpen(false)} />
          </DrawerBody>
        </DrawerContent>
      </Drawer>
    </div>
  );
}
