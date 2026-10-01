"use client";

import { useTranslations } from "next-intl";
import { useEffect } from "react";
import { SearchIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Link, useRouter } from "@/i18n/navigation";
import { PageSkeleton } from "../shared/skeletons";
import { useSession } from "../shell/session-store";

export function ResultsIndex() {
  const t = useTranslations("results");
  const router = useRouter();
  const { ready, lastRequestId } = useSession();

  useEffect(() => {
    if (ready && lastRequestId) router.replace(`/results/${lastRequestId}`);
  }, [ready, lastRequestId, router]);

  return (
    <>
      <PageHeader title={t("title")} />
      {!ready || lastRequestId ? (
        <PageSkeleton blocks={1} />
      ) : (
        <Card>
          <EmptyState
            icon={<SearchIcon />}
            title={t("noRun.title")}
            description={t("noRun.text")}
            actions={
              <Button asChild>
                <Link href="/search">{t("newSearch")}</Link>
              </Button>
            }
          />
        </Card>
      )}
    </>
  );
}
