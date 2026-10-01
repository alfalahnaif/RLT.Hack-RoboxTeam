import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/**
 * Floating action bar (Supplier Radar DS extension, e.g. compare tray): fixed to the bottom centre,
 * white, 20px radius, gray-100 border, popper shadow, 12/16 padding, content packed with 12px gaps.
 * Sits above page content (z-30) but below overlays (z-50). Respects the 16px page gutter on mobile.
 */
export function ActionBar({ className, ...props }: ComponentProps<"div">) {
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-4 z-30 flex justify-center px-4 print:hidden">
      <div
        role="region"
        className={cn(
          "pointer-events-auto flex w-full max-w-[720px] flex-wrap items-center gap-3 rounded-xl border border-line-subtle bg-white px-4 py-3 shadow-popper animate-popper-in",
          className,
        )}
        {...props}
      />
    </div>
  );
}
