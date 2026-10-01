import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";
import { UserIcon } from "@/components/icons";
import { cn } from "@/lib/utils";

/**
 * Source: `.symbol` — square/circle container for avatars, logos and icons.
 * 32px (table avatar, gray-100), 40px (notification icon), 48px (app logo tile: gray-50 + gray-100 border).
 */
export const symbolVariants = cva("relative inline-flex shrink-0 items-center justify-center overflow-hidden text-gray-400", {
  variants: {
    size: {
      xs: "size-3 rounded-sm",
      sm: "size-8 rounded-md [&_svg]:size-4",
      md: "size-10 rounded-md [&_svg]:size-5",
      lg: "size-12 rounded-md [&_svg]:size-6",
      xl: "size-20 rounded-lg border-[3px] border-white [&_svg]:size-8",
    },
    tone: {
      default: "bg-gray-100",
      subtle: "border border-line-subtle bg-gray-50",
      white: "border border-line-subtle bg-white",
      primary: "bg-primary-50 text-primary-700",
    },
    shape: { rounded: "", circle: "rounded-full" },
  },
  defaultVariants: { size: "sm", tone: "default", shape: "rounded" },
});

type SymbolProps = ComponentProps<"div"> & VariantProps<typeof symbolVariants> & { src?: string; alt?: string };

export function Symbol({ size, tone, shape, src, alt = "", className, children, ...props }: SymbolProps) {
  return (
    <div data-slot="symbol" className={cn(symbolVariants({ size, tone, shape }), className)} {...props}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      {src ? <img src={src} alt={alt} className="size-full object-cover" /> : (children ?? <UserIcon />)}
    </div>
  );
}
