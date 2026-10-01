"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Card, CardBody, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RadioGroup, RadioItem } from "@/components/ui/radio-group";
import { getScenario, SCENARIOS, setScenario, type Scenario } from "@/mocks/server";

/**
 * Mock-mode only: forces backend behaviours (503, LLM fallback, semantic branch down, slow response)
 * so every S-01/S-02 state can be demonstrated and tested. Not rendered when NEXT_PUBLIC_API_MODE=live.
 */
export function ScenarioPanel() {
  const t = useTranslations("search.scenario");
  const [value, setValue] = useState<Scenario>("normal");
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setValue(getScenario());
  }, []);

  return (
    <Card variant="outlined" className="border-dashed">
      <CardHeader>
        <div className="flex flex-col gap-1">
          <CardTitle className="text-sm">{t("title")}</CardTitle>
          <CardDescription className="text-xs">{t("subtitle")}</CardDescription>
        </div>
      </CardHeader>
      <CardBody className="pt-2">
        <RadioGroup
          aria-label={t("title")}
          value={value}
          onValueChange={(s) => {
            setValue(s as Scenario);
            setScenario(s as Scenario);
          }}
          className="flex-col items-start gap-3"
        >
          {SCENARIOS.map((s) => (
            <RadioItem key={s} value={s} label={t(`options.${s}`)} />
          ))}
        </RadioGroup>
      </CardBody>
    </Card>
  );
}
