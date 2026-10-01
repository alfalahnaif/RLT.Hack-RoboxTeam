"use client";

import { useLocale, useTranslations } from "next-intl";
import { GlobeIcon } from "@/components/icons";
import { usePathname, useRouter } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

/** Text + globe language toggle ("EN" / "RU") — shows the locale it switches to. */
export function LocaleSwitch({ className }: { className?: string }) {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations("common");
  const target = locale === "ru" ? "en" : "ru";
  return (
    <button
      type="button"
      aria-label={t("switchLanguage")}
      onClick={() => router.replace(pathname, { locale: target })}
      className={cn("inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-sm font-medium text-muted transition-colors hover:text-heading", className)}
    >
      {target.toUpperCase()}
      <GlobeIcon className="size-5" />
    </button>
  );
}
