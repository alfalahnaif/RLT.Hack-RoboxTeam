import { redirect } from "@/i18n/navigation";

/** Free-text supplier discovery is the primary live entry; the Lot ID demo remains at /analysis. */
export default async function LocaleIndex({ params }: PageProps<"/[locale]">) {
  const { locale } = await params;
  redirect({ href: "/search", locale });
}
