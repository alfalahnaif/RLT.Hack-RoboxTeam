import { redirect } from "@/i18n/navigation";

/** `/ru` and `/en` open S-01 Search. The design-system gallery stays at `/design-system`. */
export default async function LocaleIndex({ params }: PageProps<"/[locale]">) {
  const { locale } = await params;
  redirect({ href: "/search", locale });
}
