import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/** Loading placeholder (source `.el-skeleton__item`): gray-100 → gray-200 shimmer, 4px radius, 16px default height. */
export function Skeleton({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("h-4 w-full animate-pulse rounded-xs bg-gray-100", className)} {...props} />;
}
