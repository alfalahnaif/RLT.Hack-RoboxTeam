"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { Tabs as TabsPrimitive } from "radix-ui";
import { createContext, useContext, type ComponentProps } from "react";
import { cn } from "@/lib/utils";

/**
 * Two tab styles from the source:
 * - `segmented` (`.tabs-header ul`): gray-50 track, 1px gray-100 border, 8px radius, 4px padding, 8px gap.
 *    Trigger: min-width 80, padding 8/16, 14/22 gray-700; active → white, heading, medium.
 * - `pill` (`.preview-site-tabs`): gray-200 pill track, 6px padding; trigger 12/18 medium pill; active white.
 */
const listVariants = cva("inline-flex max-w-full items-center self-start overflow-x-auto", {
  variants: {
    variant: {
      segmented: "gap-2 rounded-md border border-line-subtle bg-surface-subtle p-1",
      pill: "gap-2 rounded-pill bg-gray-200 p-1.5",
    },
    fullWidth: { true: "w-full self-stretch [&>*]:flex-1" },
  },
  defaultVariants: { variant: "segmented" },
});

const triggerVariants = cva(
  "group/trigger relative inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap outline-none transition-colors [&_svg]:size-4 disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      variant: {
        segmented:
          "min-w-20 rounded-md px-4 py-2 text-sm text-subtle hover:text-heading [&_svg]:text-muted data-[state=active]:bg-white data-[state=active]:font-medium data-[state=active]:text-heading data-[state=active]:[&_svg]:text-heading aria-[invalid=true]:border aria-[invalid=true]:border-danger-600 aria-[invalid=true]:text-danger-600",
        pill: "rounded-pill px-4 py-2 text-xs font-medium text-heading data-[state=active]:bg-white",
      },
    },
    defaultVariants: { variant: "segmented" },
  },
);

type Variant = NonNullable<VariantProps<typeof listVariants>["variant"]>;
const VariantCtx = createContext<Variant>("segmented");

export function Tabs({ className, ...props }: ComponentProps<typeof TabsPrimitive.Root>) {
  return <TabsPrimitive.Root className={cn("flex flex-col gap-4", className)} {...props} />;
}

export function TabsList({ className, variant = "segmented", fullWidth, ...props }: ComponentProps<typeof TabsPrimitive.List> & VariantProps<typeof listVariants>) {
  const v = variant ?? "segmented";
  return (
    <VariantCtx.Provider value={v}>
      <TabsPrimitive.List className={cn(listVariants({ variant: v, fullWidth }), className)} {...props} />
    </VariantCtx.Provider>
  );
}

export function TabsTrigger({ className, invalid, ...props }: ComponentProps<typeof TabsPrimitive.Trigger> & { invalid?: boolean }) {
  const variant = useContext(VariantCtx);
  return <TabsPrimitive.Trigger aria-invalid={invalid || undefined} className={cn(triggerVariants({ variant }), className)} {...props} />;
}

export function TabsContent({ className, ...props }: ComponentProps<typeof TabsPrimitive.Content>) {
  return <TabsPrimitive.Content className={cn("outline-none", className)} {...props} />;
}

/** Card-wrapped tab bar used at the top of settings pages (`.card > .tabs-header`, padding 12/16). */
export function TabsHeader({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("flex items-center justify-start px-4 py-3", className)} {...props} />;
}

const dotTone = {
  primary: "bg-primary-600",
  info: "bg-info-600",
  warning: "bg-warning-600",
  danger: "bg-danger-600",
  success: "bg-success-600",
  purple: "bg-purple",
  gray: "bg-gray-400",
} as const;

/**
 * Count bubble (+ optional status dot) placed inside a `TabsTrigger` — used for status filter bars
 * ("الكل 0 · جديدة 0 · قيد التنفيذ 0 …"). Idle: white/gray-100, active trigger: primary-50/primary-700.
 */
export function TabsCount({ value, dot }: { value: number; dot?: keyof typeof dotTone }) {
  return (
    <>
      {dot ? <span aria-hidden className={cn("size-1.5 shrink-0 rounded-full", dotTone[dot])} /> : null}
      <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-pill bg-gray-100 px-1.5 text-2xs font-medium text-subtle group-data-[state=active]/trigger:bg-primary-50 group-data-[state=active]/trigger:text-primary-700">
        {value}
      </span>
    </>
  );
}
