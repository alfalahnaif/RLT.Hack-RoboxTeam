import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps, ReactNode } from "react";
import { CheckCircleIcon, InfoCircleIcon, WarningTriangleIcon } from "@/components/icons";
import { cn } from "@/lib/utils";

/**
 * Two alert styles from the source:
 * - `announcement` (default): white card, gray-100 border, soft shadow and a diagonal color glow
 *   on the start edge; title 16/24 medium, text 14/22 subtle, actions pushed to the end.
 * - `inline`: 1px tinted border + light tinted background (e.g. info note inside forms).
 */
const alertVariants = cva("flex w-full items-start gap-3 rounded-lg p-3", {
  variants: {
    tone: { default: "", info: "", success: "", warning: "", danger: "" },
    appearance: {
      announcement: "rounded-xl border border-line-subtle bg-white p-4 shadow-card",
      inline: "border",
    },
  },
  compoundVariants: [
    { appearance: "inline", tone: "default", className: "border-line bg-surface-subtle" },
    { appearance: "inline", tone: "info", className: "border-primary-300 bg-primary-50/40" },
    { appearance: "inline", tone: "success", className: "border-success-300 bg-success-50" },
    { appearance: "inline", tone: "warning", className: "border-warning-300 bg-warning-50" },
    { appearance: "inline", tone: "danger", className: "border-danger-300 bg-danger-50" },
  ],
  defaultVariants: { tone: "info", appearance: "announcement" },
});

// Diagonal glow used by `.alert.announcement.{tone}` (mirrored per direction).
const glow: Record<string, string> = {
  default: "rgba(107,114,128,.2)",
  info: "rgba(172,220,250,.2)",
  success: "rgba(136,223,198,.2)",
  warning: "rgba(253,204,87,.2)",
  danger: "rgba(255,132,132,.2)",
};

const iconTone: Record<string, string> = {
  default: "text-gray-500",
  info: "text-primary-500",
  success: "text-success-500",
  warning: "text-warning-500",
  danger: "text-danger-500",
};

const defaultIcons: Record<string, ReactNode> = {
  default: <InfoCircleIcon />,
  info: <InfoCircleIcon />,
  success: <CheckCircleIcon />,
  warning: <WarningTriangleIcon />,
  danger: <WarningTriangleIcon />,
};

type AlertProps = Omit<ComponentProps<"div">, "title"> &
  VariantProps<typeof alertVariants> & {
    title?: ReactNode;
    description?: ReactNode;
    icon?: ReactNode | false;
    /** Rendered at the end side (`.alert-content-actions`). */
    actions?: ReactNode;
  };

export function Alert({ tone = "info", appearance = "announcement", title, description, icon, actions, className, style, children, ...props }: AlertProps) {
  const t = tone ?? "info";
  const bg =
    appearance === "announcement"
      ? { backgroundImage: `linear-gradient(calc(78deg * var(--dir-sign) * -1), rgba(255,255,255,0) 22.39%, rgba(255,255,255,.1) 72.09%, ${glow[t]} 97.84%)` }
      : undefined;
  return (
    <div role="alert" data-slot="alert" className={cn(alertVariants({ tone, appearance }), className)} style={{ ...bg, ...style }} {...props}>
      {icon !== false ? (
        <div className={cn("flex size-6 shrink-0 items-center justify-center [&_svg]:size-6", iconTone[t])}>{icon ?? defaultIcons[t]}</div>
      ) : null}
      <div className={cn("flex w-full flex-wrap items-start gap-3", actions ? "justify-between md:flex-nowrap" : "flex-col")}>
        <div className="flex flex-col gap-1">
          {title ? <h3 className="text-base font-medium text-heading">{title}</h3> : null}
          {description ? <p className="text-sm text-subtle">{description}</p> : null}
          {children}
        </div>
        {actions ? <div className="ms-auto flex w-fit shrink-0 items-center justify-end gap-3 self-center">{actions}</div> : null}
      </div>
    </div>
  );
}
