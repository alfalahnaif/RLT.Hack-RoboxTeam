import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { SupplierScreen } from "@/features/supplier/supplier-screen";

export async function generateMetadata({ params }: PageProps<"/[locale]/suppliers/[supplierId]">): Promise<Metadata> {
  const t = await getTranslations({ locale: (await params).locale, namespace: "supplier" });
  return { title: `${t("title")} · Supplier Radar` };
}

/** S-03 Supplier Profile. `?request_id=` adds the query context of that search run. */
export default async function SupplierPage({ params, searchParams }: PageProps<"/[locale]/suppliers/[supplierId]">) {
  const { locale, supplierId } = await params;
  setRequestLocale(locale);
  const { request_id } = await searchParams;
  return <SupplierScreen supplierId={supplierId} requestId={typeof request_id === "string" ? request_id : undefined} />;
}
