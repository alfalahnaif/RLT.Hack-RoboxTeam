import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Supplier360Screen } from "@/features/supplier-360/supplier-360-screen";
import { safeBackHref } from "@/features/supplier-360/model";

export async function generateMetadata({ params }: PageProps<"/[locale]/supplier-360/[inn]">): Promise<Metadata> {
  const { locale, inn } = await params;
  const t = await getTranslations({ locale, namespace: "supplier360" });
  return { title: `${t("title")} ${decodeURIComponent(inn)} · Supplier Radar` };
}

/** P5-001B Supplier 360 profile by INN (`GET /suppliers/{inn}/profile`). `?back=` = the list the user came from. */
export default async function Supplier360Page({ params, searchParams }: PageProps<"/[locale]/supplier-360/[inn]">) {
  const { locale, inn } = await params;
  setRequestLocale(locale);
  const { back } = await searchParams;
  return <Supplier360Screen inn={decodeURIComponent(inn)} backHref={safeBackHref(typeof back === "string" ? back : null) ?? "/search"} />;
}
