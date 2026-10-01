"use client";

import { useLocale } from "next-intl";
import { Collapsible } from "radix-ui";
import { useState } from "react";
import { MenuAlignIcon } from "@/components/icons";
import { Link, usePathname } from "@/i18n/navigation";
import { isRtl } from "@/i18n/routing";
import { cn } from "@/lib/utils";
import { ChevronDownIcon } from "@/components/ui/_glyphs";
import { Tooltip } from "@/components/ui/tooltip";
import type { ReactNode } from "react";
import { DEFAULT_BRAND, type Brand, type NavItem } from "./types";

const isActive = (pathname: string, href?: string) => !!href && (pathname === href || pathname.startsWith(href + "/"));

/**
 * Source: `.app-sidebar` (250px, white, fixed). Logo row 88px (padding 16/12/0) with the collapse toggle
 * at the end. Menu: 12px side padding, 4px gap. Link: 44px, 10px padding, 8px radius, 8px icon gap,
 * 20px gray-500 icon, 16/24 gray-700 label. Hover → heading text. Active → white fill + 1px gray-200 border,
 * heading text/icon. Sub-menu: 1px gray-200 start border, 17px start margin, 8px start padding;
 * sub-link 38px, padding 8/10, 14/22 label. Collapsed rail: 64px, icon-only 40×44 links.
 */
export function SidebarNav({ items, collapsed = false, onNavigate }: { items: NavItem[]; collapsed?: boolean; onNavigate?: () => void }) {
  const pathname = usePathname();
  const tipSide = isRtl(useLocale()) ? "left" : "right";
  return (
    <ul className={cn("flex flex-col gap-1", collapsed ? "items-center px-3" : "px-3")}>
      {items.map((item) => (
        <SidebarItem key={item.key} item={item} pathname={pathname} collapsed={collapsed} onNavigate={onNavigate} tipSide={tipSide} />
      ))}
    </ul>
  );
}

const linkBase =
  "group/link flex w-full items-center gap-2 rounded-md border border-transparent text-gray-700 outline-none transition-all duration-300 ease-in-out hover:text-heading focus-visible:ring-4 focus-visible:ring-primary-600/15";

function SidebarItem({
  item,
  pathname,
  collapsed,
  onNavigate,
  tipSide,
}: {
  item: NavItem;
  pathname: string;
  collapsed: boolean;
  onNavigate?: () => void;
  tipSide: "left" | "right";
}) {
  const Icon = item.icon;
  const childActive = item.children?.some((c) => isActive(pathname, c.href)) ?? false;
  const active = isActive(pathname, item.href);
  const [open, setOpen] = useState(childActive);

  const inner = (
    <>
      <Icon className={cn("size-5 shrink-0 text-gray-500 transition-colors group-hover/link:text-heading", (active || childActive) && "text-heading")} />
      {collapsed ? null : (
        <>
          <span className="flex-1 truncate text-base">{item.label}</span>
          {item.badge}
        </>
      )}
    </>
  );

  const linkCls = cn(linkBase, collapsed ? "h-11 w-10 justify-center p-2.5" : "h-11 p-2.5", active && "border-line bg-white text-heading");

  if (item.children?.length && !collapsed) {
    return (
      <Collapsible.Root asChild open={open} onOpenChange={setOpen}>
        <li>
          <Collapsible.Trigger className={cn(linkCls, "group/trigger text-start")}>
            {inner}
            <ChevronDownIcon className="size-5 shrink-0 opacity-0 transition-all group-hover/link:opacity-100 group-data-[state=open]/trigger:opacity-100 group-data-[state=closed]/trigger:-rotate-90 rtl:group-data-[state=closed]/trigger:rotate-90" />
          </Collapsible.Trigger>
          <Collapsible.Content>
            <ul className="ms-[17px] mt-0.5 flex flex-col gap-1 border-s border-line ps-2">
              {item.children.map((c) => {
                const a = isActive(pathname, c.href);
                return (
                  <li key={c.key}>
                    <Link
                      href={c.href}
                      onClick={onNavigate}
                      aria-current={a ? "page" : undefined}
                      className={cn(
                        "flex h-[38px] items-center rounded-md border border-transparent px-2.5 py-2 text-sm text-gray-700 transition-colors hover:text-heading",
                        a && "border-line bg-white text-heading",
                      )}
                    >
                      {c.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </Collapsible.Content>
        </li>
      </Collapsible.Root>
    );
  }

  const href = item.href ?? item.children?.[0]?.href ?? "#";
  const link = (
    <Link href={href} onClick={onNavigate} aria-current={active ? "page" : undefined} className={cn(linkCls, collapsed && childActive && "border-line bg-white text-heading")}>
      {inner}
    </Link>
  );
  return <li className={collapsed ? "w-10" : undefined}>{collapsed ? <Tooltip content={item.label} side={tipSide}>{link}</Tooltip> : link}</li>;
}

export function Sidebar({
  items,
  footerItems = [],
  collapsed,
  onToggle,
  brand = DEFAULT_BRAND,
  top,
  bottom,
}: {
  items: NavItem[];
  footerItems?: NavItem[];
  collapsed: boolean;
  onToggle: () => void;
  brand?: Brand;
  /** Rendered under the logo row (e.g. signed-in user block). Hidden when collapsed. */
  top?: ReactNode;
  /** Rendered at the very bottom (e.g. logout + version). Hidden when collapsed. */
  bottom?: ReactNode;
}) {
  return (
    <aside
      className={cn(
        "fixed inset-y-0 start-0 z-30 hidden flex-col bg-white transition-[width] duration-300 lg:flex print:hidden!",
        "bg-[radial-gradient(90%_40%_at_100%_0%,rgb(141_213_255/0.18),transparent_70%)] ltr:bg-[radial-gradient(90%_40%_at_0%_0%,rgb(141_213_255/0.18),transparent_70%)]",
        collapsed ? "w-16" : "w-sidebar",
      )}
    >
      <div className={cn("flex h-[88px] shrink-0 items-start justify-between px-3 pt-4", collapsed && "justify-center")}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={collapsed ? brand.mark : brand.logo} alt={brand.name} className={cn("w-auto object-contain", collapsed ? "h-7 max-w-10" : "h-8 max-w-[160px]")} />
        {collapsed ? null : (
          <button type="button" onClick={onToggle} aria-label="toggle sidebar" className="mt-1.5 text-heading">
            <MenuAlignIcon className="size-5" />
          </button>
        )}
      </div>
      {top && !collapsed ? <div className="shrink-0 px-3 pb-3">{top}</div> : null}
      <nav className="min-h-0 flex-1 overflow-y-auto">
        <SidebarNav items={items} collapsed={collapsed} />
      </nav>
      {footerItems.length ? (
        <div className="shrink-0 py-2">
          <SidebarNav items={footerItems} collapsed={collapsed} />
        </div>
      ) : null}
      {bottom && !collapsed ? <div className="shrink-0 border-t border-line-subtle px-3 py-3">{bottom}</div> : null}
      {collapsed ? (
        <button type="button" onClick={onToggle} aria-label="expand sidebar" className="mx-auto mb-3 flex size-9 items-center justify-center rounded-md text-heading hover:bg-surface-subtle">
          <MenuAlignIcon className="size-5 rtl:-scale-x-100" />
        </button>
      ) : null}
    </aside>
  );
}
