import { Fragment, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { CheckIcon } from "./_glyphs";

export type StepperStep = { key: string; label?: ReactNode };

/**
 * Wizard progress (source `.wameed-wizard` pattern mapped to DS tokens).
 * 32px circles, 12px semibold numbers. Upcoming: gray-100 / muted. Current: primary-700 / white with a
 * 4px primary-50 ring. Complete: primary-50 fill + primary-700 check. 40px connectors: line → primary-700
 * once the previous step is complete. Optional labels 12/18 (current medium heading, others muted).
 * Flows in reading direction (step 1 at the start side — right in RTL).
 */
export function Stepper({ steps, current, className }: { steps: StepperStep[]; current: number; className?: string }) {
  return (
    <ol className={cn("flex items-start justify-center", className)} aria-label="progress">
      {steps.map((step, i) => {
        const state = i < current ? "complete" : i === current ? "current" : "upcoming";
        return (
          <Fragment key={step.key}>
            {i > 0 ? (
              <li aria-hidden className={cn("mt-4 h-px w-10 shrink-0 sm:w-12", i <= current ? "bg-primary-700" : "bg-line")} />
            ) : null}
            <li className="flex min-w-16 flex-col items-center gap-2" aria-current={state === "current" ? "step" : undefined}>
              <span
                className={cn(
                  "flex size-8 items-center justify-center rounded-full text-xs font-semibold transition-colors",
                  state === "upcoming" && "bg-gray-100 text-muted",
                  state === "current" && "bg-primary-700 text-white ring-4 ring-primary-50",
                  state === "complete" && "bg-primary-50 text-primary-700",
                )}
              >
                {state === "complete" ? <CheckIcon className="size-4" /> : i + 1}
              </span>
              {step.label ? (
                <span className={cn("text-center text-xs whitespace-nowrap", state === "current" ? "font-medium text-heading" : "text-muted")}>{step.label}</span>
              ) : null}
            </li>
          </Fragment>
        );
      })}
    </ol>
  );
}
