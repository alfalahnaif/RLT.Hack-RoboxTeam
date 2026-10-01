"use client";

import { Tooltip as TooltipPrimitive } from "radix-ui";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Source: `.el-popper.is-dark` — dark fill, white 12/20 text, 4px radius, 5/11 padding, arrow.
 * Max-width 280. Provider lives in `components/providers.tsx`.
 */
export const TooltipProvider = TooltipPrimitive.Provider;

export function Tooltip({
  content,
  children,
  side = "top",
  ...props
}: Omit<ComponentProps<typeof TooltipPrimitive.Root>, "children"> & {
  content: ReactNode;
  children: ReactNode;
  side?: "top" | "right" | "bottom" | "left";
}) {
  return (
    <TooltipPrimitive.Root {...props}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          sideOffset={6}
          className={cn("z-50 max-w-[280px] rounded-xs bg-gray-900 px-[11px] py-[5px] text-xs leading-5 text-white data-[state=delayed-open]:animate-fade-in")}
        >
          {content}
          <TooltipPrimitive.Arrow className="fill-gray-900" width={10} height={5} />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
