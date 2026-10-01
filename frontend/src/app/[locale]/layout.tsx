import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale, NextIntlClientProvider } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { localeDirection, routing } from "@/i18n/routing";
import { Providers } from "@/components/providers";
import { inter } from "../fonts";
import "../globals.css";

export const metadata: Metadata = {
  title: "Supplier Radar",
  icons: { icon: "/brand/logo-mark.svg" },
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({ children, params }: LayoutProps<"/[locale]">) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);

  return (
    <html lang={locale} dir={localeDirection[locale]} className={inter.variable}>
      <body>
        <NextIntlClientProvider>
          <Providers dir={localeDirection[locale]}>{children}</Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
