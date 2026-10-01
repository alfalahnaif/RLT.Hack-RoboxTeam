import { cn } from "@/lib/utils";

/**
 * Linear progress (DS tokens): 8px pill track gray-100, primary-700 fill, 300ms width transition.
 * `tone` switches the fill for status meters. Fills from the start side (right in RTL).
 */
export function Progress({
  value,
  tone = "primary",
  className,
  label,
}: {
  value: number;
  tone?: "primary" | "success" | "warning" | "danger";
  className?: string;
  label?: string;
}) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div
      role="progressbar"
      aria-valuenow={v}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
      className={cn("h-2 w-full overflow-hidden rounded-pill bg-gray-100", className)}
    >
      <div
        className={cn(
          "h-full rounded-pill transition-[width] duration-300",
          tone === "primary" && "bg-primary-700",
          tone === "success" && "bg-success-600",
          tone === "warning" && "bg-warning-600",
          tone === "danger" && "bg-danger-600",
        )}
        style={{ width: `${v}%` }}
      />
    </div>
  );
}
