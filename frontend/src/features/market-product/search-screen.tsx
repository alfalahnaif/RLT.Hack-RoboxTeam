"use client";

import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { SearchIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input, Textarea } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { Link, useRouter } from "@/i18n/navigation";

/** Primary live entry point. The Lot ID analysis remains at /analysis. */
export function MarketProductSearchScreen() {
  const t = useTranslations("marketProduct");
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [okpd2, setOkpd2] = useState("");
  const [region, setRegion] = useState("");
  const [error, setError] = useState<"required" | "invalidRegion" | null>(null);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const text = query.trim();
    if (text.length < 3) return setError("required");
    if (region.trim() && !/^\d{2}$/.test(region.trim())) return setError("invalidRegion");
    setError(null);
    const params = new URLSearchParams({ q: text });
    if (okpd2.trim()) params.set("okpd2", okpd2.trim());
    if (region.trim()) params.set("region", region.trim());
    router.push(`/results?${params.toString()}`);
  };

  return (
    <>
      <PageHeader title={t("title")} description={t("subtitle")} />
      <div className="mx-auto flex max-w-4xl flex-col gap-5">
        <Card className="border-primary-200">
          <CardBody className="flex flex-col gap-6 p-5 sm:p-7">
            <form onSubmit={submit} className="flex flex-col gap-5">
              <Field label={t("queryLabel")} required error={error === "required" ? t("required") : undefined}>
                <Textarea
                  autoFocus
                  value={query}
                  onChange={(event) => { setQuery(event.target.value); setError(null); }}
                  placeholder={t("queryPlaceholder")}
                  rows={4}
                  maxLength={1000}
                  showCount
                  className="min-h-36 text-base leading-relaxed sm:text-lg"
                />
              </Field>
              <button type="button" onClick={() => setQuery(t("sampleQuery"))}
                className="self-start rounded-pill border border-line px-3 py-1.5 text-xs text-subtle hover:border-primary-300 hover:text-primary-700">
                {t("example")}
              </button>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label={t("okpd2Label")} hint={t("okpd2Hint")}>
                  <Input value={okpd2} onChange={(event) => setOkpd2(event.target.value)} placeholder="10.51.11.141" inputMode="decimal" />
                </Field>
                <Field label={t("regionLabel")} hint={t("regionHint")} error={error === "invalidRegion" ? t("invalidRegion") : undefined}>
                  <Input value={region} onChange={(event) => { setRegion(event.target.value); setError(null); }} placeholder="77" inputMode="numeric" maxLength={2} />
                </Field>
              </div>
              <div className="flex flex-col gap-3 border-t border-line-subtle pt-5 sm:flex-row sm:items-center sm:justify-between">
                <Button type="submit" size="lg" strong className="w-full sm:w-auto"><SearchIcon />{t("submit")}</Button>
                <Button asChild variant="link" className="self-center sm:self-auto"><Link href="/analysis">{t("lotOption")}</Link></Button>
              </div>
            </form>
          </CardBody>
        </Card>
      </div>
    </>
  );
}
