"use client";

import { useState, type ReactNode } from "react";
import { MenuAlignIcon } from "@/components/icons";
import { Drawer, DrawerBody, DrawerContent, DrawerHeader, DrawerTitle } from "@/components/ui/drawer";
import { Link, usePathname } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { DEFAULT_BRAND, type Brand, type NavItem } from "./types";

const isActive = (pathname: string, href?: string) => !!href && (pathname === href || pathname.startsWith(href + "/"));

/**
 * Top-navigation shell (Supplier Radar DS extension — chosen instead of the sidebar AppShell).
 * Desktop (≥960px): 60px white header, 1px gray-100 bottom border, sticky; content aligned to the
 * 1224px container: logo · horizontal nav · end actions. Nav item: 38px, 8/12 padding, 8px radius,
 * 20px gray-500 icon + 14/22 gray-700 label; active → white fill + 1px gray-200 border + heading text
 * (same treatment as the sidebar link). Below 960px: dark primary-1000 72px header with the light logo,
 * end actions and a menu button opening a start-side drawer with the same nav as a vertical list.
 * `notice` renders a full-width strip under the header (e.g. demo-data notice, BR-20).
 */
export function TopBar({
  items,
  actions,
  mobileActions,
  notice,
  brand = DEFAULT_BRAND,
  homeHref = "/",
  menuLabel,
}: {
  items: NavItem[];
  actions?: ReactNode;
  mobileActions?: ReactNode;
  notice?: ReactNode;
  brand?: Brand;
  homeHref?: string;
  menuLabel: string;
}) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <div className="sticky top-0 z-20 print:static">
      <header className="hidden h-header items-center border-b border-line-subtle bg-white px-6 lg:flex">
        <div className="mx-auto flex w-full max-w-[1224px] items-center gap-6">
          <Link href={homeHref} className="flex shrink-0 items-center rounded-md outline-none focus-visible:ring-4 focus-visible:ring-primary-600/15">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={brand.logo} alt={brand.name} className="h-8 w-auto max-w-[160px] object-contain" />
          </Link>
          <nav aria-label={menuLabel} className="min-w-0 flex-1">
            <ul className="flex items-center gap-1">
              {items.map((item) => (
                <li key={item.key}>
                  <TopBarLink item={item} active={isActive(pathname, item.href)} />
                </li>
              ))}
            </ul>
          </nav>
          {actions ? <div className="flex shrink-0 items-center gap-3">{actions}</div> : null}
        </div>
      </header>

      <header className="flex h-[72px] items-center justify-between gap-3 bg-primary-1000 px-4 lg:hidden">
        <Link href={homeHref} className="flex items-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={brand.logoLight} alt={brand.name} className="h-9 w-auto max-w-[140px] object-contain" />
        </Link>
        <div className="flex items-center gap-2">
          {mobileActions}
          <Drawer open={open} onOpenChange={setOpen}>
            <button
              type="button"
              onClick={() => setOpen(true)}
              aria-label={menuLabel}
              className="relative flex size-10 items-center justify-center rounded-md border border-white/15 bg-white/10 text-white outline-none focus-visible:ring-4 focus-visible:ring-white/30 [&_svg]:size-5"
            >
              <MenuAlignIcon />
              {items.some((i) => i.badge) ? <span className="absolute -top-1 -end-1 size-2.5 rounded-full bg-secondary-500 ring-2 ring-primary-1000" aria-hidden /> : null}
            </button>
            <DrawerContent side="start">
              <DrawerHeader>
                <DrawerTitle>{menuLabel}</DrawerTitle>
              </DrawerHeader>
              <DrawerBody>
                <nav aria-label={menuLabel}>
                  <ul className="flex flex-col gap-1 px-3 pb-4">
                    {items.map((item) => (
                      <li key={item.key}>
                        <TopBarLink item={item} active={isActive(pathname, item.href)} onNavigate={() => setOpen(false)} block />
                      </li>
                    ))}
                  </ul>
                </nav>
              </DrawerBody>
            </DrawerContent>
          </Drawer>
        </div>
      </header>
      {notice}
    </div>
  );
}

function TopBarLink({ item, active, onNavigate, block }: { item: NavItem; active: boolean; onNavigate?: () => void; block?: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href ?? "#"}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={cn(
        "group/link flex items-center gap-2 rounded-md border border-transparent px-3 text-sm text-gray-700 outline-none transition-all duration-300 ease-in-out hover:text-heading focus-visible:ring-4 focus-visible:ring-primary-600/15",
        block ? "h-11 w-full text-base" : "h-[38px]",
        active && "border-line bg-white text-heading",
        active && !block && "bg-surface-subtle",
      )}
    >
      <Icon className={cn("size-5 shrink-0 text-gray-500 transition-colors group-hover/link:text-heading", active && "text-heading")} />
      <span className={cn("truncate", block && "flex-1")}>{item.label}</span>
      {item.badge}
    </Link>
  );
}
