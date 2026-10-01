"use client";

import { Accordion as AccordionPrimitive } from "radix-ui";
import { createContext, useContext, type ComponentProps, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { ChevronDownIcon } from "./_glyphs";

/**
 * Source: `.wameed-collapse` (Element Plus collapse restyled).
 * Items are separate cards (gap 16): white, gray-100 border, 12px radius, soft shadow.
 * Header: 16px padding, 8px gap, 14/22 medium heading, 20px chevron at the end.
 * `highlight` variant (onboarding): the open item turns primary-600 (header text white) and the
 * content sits in an inset white panel (wrap padding 0/4/4, panel radius 12, padding 16).
 * `flush` variant (drawer filters): no card chrome; header 12/18 medium.
 */
type Variant = "default" | "highlight" | "flush";
const Ctx = createContext<Variant>("default");

type AccordionProps = ComponentProps<typeof AccordionPrimitive.Root> & { variant?: Variant };

export function Accordion({ className, variant = "default", ...props }: AccordionProps) {
  return (
    <Ctx.Provider value={variant}>
      <AccordionPrimitive.Root
        data-variant={variant}
        className={cn("flex w-full flex-col", variant === "flush" ? "gap-0" : "gap-4", className)}
        {...(props as ComponentProps<typeof AccordionPrimitive.Root>)}
      />
    </Ctx.Provider>
  );
}

export function AccordionItem({ className, ...props }: ComponentProps<typeof AccordionPrimitive.Item>) {
  const variant = useContext(Ctx);
  return (
    <AccordionPrimitive.Item
      className={cn(
        "group/item overflow-hidden",
        variant !== "flush" && "rounded-lg border border-line-subtle bg-white shadow-soft",
        variant === "highlight" && "data-[state=open]:border-primary-600 data-[state=open]:bg-primary-600",
        className,
      )}
      {...props}
    />
  );
}

type TriggerProps = ComponentProps<typeof AccordionPrimitive.Trigger> & { icon?: ReactNode; extra?: ReactNode };

export function AccordionTrigger({ className, children, icon, extra, ...props }: TriggerProps) {
  const variant = useContext(Ctx);
  return (
    <AccordionPrimitive.Header className="flex">
      <AccordionPrimitive.Trigger
        className={cn(
          "group flex flex-1 items-center gap-2 text-start font-medium text-heading outline-none transition-colors",
          variant === "flush" ? "px-4 pb-3 text-xs" : "rounded-lg bg-white p-4 text-sm",
          variant === "highlight" && "data-[state=open]:bg-primary-600 data-[state=open]:text-white",
          "focus-visible:ring-4 focus-visible:ring-primary-600/15",
          className,
        )}
        {...props}
      >
        {icon ? (
          <span className={cn("flex shrink-0 text-muted [&_svg]:size-5", variant === "highlight" && "group-data-[state=open]:text-white")}>{icon}</span>
        ) : null}
        <span className="flex-1">{children}</span>
        {extra}
        <ChevronDownIcon
          className={cn("shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180", variant === "flush" ? "size-4" : "size-5")}
        />
      </AccordionPrimitive.Trigger>
    </AccordionPrimitive.Header>
  );
}

export function AccordionContent({ className, children, ...props }: ComponentProps<typeof AccordionPrimitive.Content>) {
  const variant = useContext(Ctx);
  return (
    <AccordionPrimitive.Content className="overflow-hidden text-heading" {...props}>
      <div className={cn(variant === "highlight" ? "px-1 pb-1" : "")}>
        <div className={cn(variant === "flush" ? "px-4 pb-4" : "bg-white p-4", variant === "highlight" && "rounded-lg", className)}>{children}</div>
      </div>
    </AccordionPrimitive.Content>
  );
}
