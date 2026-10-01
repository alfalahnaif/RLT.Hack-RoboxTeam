import { redirect } from "@/i18n/navigation";
import { API_MODE } from "@/lib/api/client";

/** `/ru` and `/en` open S-06 Procurement analysis in live mode (S-01 Search in mock mode). The gallery stays at `/design-system`. */
export default async function LocaleIndex({ params }: PageProps<"/[locale]">) {
  const { locale } = await params;
  redirect({ href: API_MODE === "live" ? "/analysis" : "/search", locale });
}
