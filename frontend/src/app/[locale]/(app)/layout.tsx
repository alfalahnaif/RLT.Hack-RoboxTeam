import { setRequestLocale } from "next-intl/server";
import { AppFrame } from "@/features/shell/app-frame";

/** Product screens (S-01…S-05) inside the S-00 global shell. */
export default async function AppLayout({ children, params }: LayoutProps<"/[locale]">) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <AppFrame>{children}</AppFrame>;
}
