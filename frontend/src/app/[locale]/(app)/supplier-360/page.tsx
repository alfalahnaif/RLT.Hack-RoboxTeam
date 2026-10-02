import { getTranslations, setRequestLocale } from "next-intl/server";
import { Card, CardBody } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Link, redirect } from "@/i18n/navigation";
import { API_MODE } from "@/lib/api/client";
import { SUPPLIER_360_FIXTURES, type Supplier360FixtureKey } from "@/mocks/supplier-360-fixtures";

/** Mock mode: index of the synthetic Supplier 360 states (for review). Live mode: profiles open from supplier cards only. */
export default async function Supplier360Index({ params }: PageProps<"/[locale]/supplier-360">) {
  const { locale } = await params;
  setRequestLocale(locale);
  if (API_MODE === "live") redirect({ href: "/search", locale });
  const t = await getTranslations({ locale, namespace: "supplier360.fixtures" });
  const keys = Object.keys(SUPPLIER_360_FIXTURES) as Supplier360FixtureKey[];
  return (
    <>
      <PageHeader title={t("title")} description={t("description")} />
      <Card>
        <CardBody>
          <ul className="flex flex-col divide-y divide-line-subtle">
            {keys.map((k) => (
              <li key={k} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <Link href={`/supplier-360/${SUPPLIER_360_FIXTURES[k].supplier.inn}?back=/supplier-360`} className="text-sm text-primary-700 hover:underline">
                  {t(k)}
                </Link>
                <span dir="ltr" className="text-xs text-muted">{SUPPLIER_360_FIXTURES[k].supplier.inn}</span>
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>
    </>
  );
}
