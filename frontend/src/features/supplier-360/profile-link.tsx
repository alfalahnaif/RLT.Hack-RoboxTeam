"use client";

import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { IdCardIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Link, usePathname } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { supplierProfileHref } from "./model";

/**
 * "View supplier profile" entry used on every supplier card (historical, curated external, Lot-ID analysis).
 * Drill-down only: the current results stay where they are and the profile's back button returns to them.
 */
export function SupplierProfileLink({ inn, size = "sm", variant = "button", className }: { inn: string; size?: "sm" | "default"; variant?: "button" | "text"; className?: string }) {
  const t = useTranslations("supplier360");
  const pathname = usePathname();
  const search = useSearchParams()?.toString();
  const href = supplierProfileHref(inn, `${pathname}${search ? `?${search}` : ""}`);
  if (variant === "text")
    return (
      <Link href={href} className={cn("inline-flex w-fit items-center gap-1 text-xs font-medium text-primary-700 hover:underline [&_svg]:size-3.5", className)}>
        <IdCardIcon aria-hidden />
        {t("viewProfile")}
      </Link>
    );
  return (
    <Button asChild variant="outline" size={size} className={className}>
      <Link href={href}>
        <IdCardIcon aria-hidden />
        {t("viewProfile")}
      </Link>
    </Button>
  );
}
