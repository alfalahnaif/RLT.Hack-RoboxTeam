"use client";

import type { ReactNode } from "react";
import { BellIcon, SearchIcon, StoreIcon } from "@/components/icons";
import { CountBadge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Kbd } from "@/components/ui/separator";
import { ChevronDownIcon } from "@/components/ui/_glyphs";
import { cn } from "@/lib/utils";

/**
 * Desktop header (source `.app-header`): 60px, white, 1px gray-100 bottom border, sticky.
 * Start: 400px search (38px control + "Ctrl + K" hint). End (`.app-navbar`, gap 16):
 * notification button (40×40, 8px radius, gray-100 border, counter bubble), 1×30 divider,
 * account button (32px store avatar + name 14/22 medium + code 12/18 gray-700 + chevron).
 * Below 960px: dark header — primary-1000, 72px, light logo, translucent 40px icon buttons.
 */
export function HeaderIconButton({ className, children, count, ...props }: React.ComponentProps<"button"> & { count?: number }) {
  return (
    <button
      type="button"
      className={cn(
        "relative flex size-10 shrink-0 items-center justify-center rounded-md border border-line-subtle bg-white p-[9px] text-gray-500 outline-none transition-colors hover:text-heading focus-visible:ring-4 focus-visible:ring-primary-600/15 [&_svg]:size-5",
        className,
      )}
      {...props}
    >
      {children}
      {count ? <CountBadge className="absolute -top-1.5 -start-1.5">{count}</CountBadge> : null}
    </button>
  );
}

export function AccountButton({ name, code, avatar, className, ...props }: React.ComponentProps<"button"> & { name: ReactNode; code?: ReactNode; avatar?: ReactNode }) {
  return (
    <button
      type="button"
      className={cn("flex h-10 items-center gap-2 rounded-md bg-white py-1 ps-1.5 pe-1 text-start outline-none focus-visible:ring-4 focus-visible:ring-primary-600/15", className)}
      {...props}
    >
      <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-gray-100 text-gray-500 [&_svg]:size-5">{avatar ?? <StoreIcon />}</span>
      <span className="flex flex-col">
        <span className="max-w-40 truncate text-sm font-medium text-heading">{name}</span>
        {code ? <span className="text-xs text-subtle">{code}</span> : null}
      </span>
      <ChevronDownIcon className="size-4 text-gray-400" />
    </button>
  );
}

export function HeaderSearch({ placeholder, onOpen }: { placeholder: string; onOpen?: () => void }) {
  return (
    <div className="w-full max-w-[400px]" onClick={onOpen}>
      <Input
        size="md"
        placeholder={placeholder}
        prefix={<SearchIcon className="text-muted" />}
        suffix={<Kbd>Ctrl + K</Kbd>}
        wrapperClassName="cursor-pointer border-line-subtle bg-white"
        className="cursor-pointer"
        onFocus={onOpen}
      />
    </div>
  );
}

export function Header({
  searchPlaceholder,
  onSearchOpen,
  notifications,
  account,
  actions,
  logoLight = "/brand/logo-light.svg",
}: {
  searchPlaceholder: string;
  /** Extra icon buttons shown before notifications (quick actions, language…). */
  actions?: ReactNode;
  /** Logo for the dark mobile header. */
  logoLight?: string;
  onSearchOpen?: () => void;
  /** Usually a `<Popover>` wrapping `<HeaderIconButton>`. */
  notifications?: ReactNode;
  /** Usually a `<Popover>` wrapping `<AccountButton>`. */
  account?: ReactNode;
}) {
  return (
    <>
      <header className="sticky top-0 z-20 hidden h-header print:hidden! items-center justify-between gap-4 border-b border-line-subtle bg-white px-6 lg:flex 2xl:px-0">
        <div className="mx-auto flex w-full max-w-[1224px] items-center justify-between gap-4">
          <HeaderSearch placeholder={searchPlaceholder} onOpen={onSearchOpen} />
          <div className="flex shrink-0 items-center gap-4">
            {actions}
            {notifications}
            <span className="h-[30px] w-px bg-line-subtle" />
            {account}
          </div>
        </div>
      </header>
      <header className="sticky top-0 z-20 flex h-[72px] print:hidden! items-center justify-between bg-primary-1000 px-4 lg:hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={logoLight} alt="" className="h-10 w-auto max-w-[140px] object-contain" />
        <div className="flex items-center gap-3">
          <HeaderIconButton onClick={onSearchOpen} className="border-white/15 bg-white/10 text-white hover:text-white" aria-label="search">
            <SearchIcon />
          </HeaderIconButton>
          {notifications ? (
            <HeaderIconButton className="border-white/15 bg-white/10 text-white hover:text-white" aria-label="notifications">
              <BellIcon />
            </HeaderIconButton>
          ) : null}
        </div>
      </header>
    </>
  );
}
