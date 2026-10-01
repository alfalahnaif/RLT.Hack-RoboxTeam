"use client";

import { createContext, useContext, useId, type ComponentProps, type ReactNode } from "react";
import { cn } from "@/lib/utils";

type FieldCtx = { id: string; invalid: boolean; describedBy?: string };
const FieldContext = createContext<FieldCtx | null>(null);

/** Read by controls to wire `id`, `aria-invalid` and `aria-describedby` automatically. */
export function useField() {
  return useContext(FieldContext);
}

type FieldProps = Omit<ComponentProps<"div">, "children"> & {
  label?: ReactNode;
  /** Shows the lighter "إختياري / Optional" suffix after the label. */
  optionalLabel?: ReactNode;
  required?: boolean;
  /** Helper text below the control (12/18 subtle, 8px top margin). */
  hint?: ReactNode;
  /** Error message — also switches the control to its error state. */
  error?: ReactNode;
  id?: string;
  children: ReactNode;
};

/**
 * Source: `.wameed-input-group` — label 12/18 medium gray-700 with 8px bottom margin,
 * hint `.wameed-input-group-span`, error `.el-form-item__error` (12/18 danger-600).
 */
export function Field({ label, optionalLabel, required, hint, error, id, className, children, ...props }: FieldProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  const msgId = error || hint ? `${fieldId}-msg` : undefined;
  return (
    <FieldContext.Provider value={{ id: fieldId, invalid: Boolean(error), describedBy: msgId }}>
      <div data-slot="field" data-invalid={error ? true : undefined} className={cn("flex w-full flex-col", className)} {...props}>
        {label ? (
          <FieldLabel htmlFor={fieldId} required={required} optionalLabel={optionalLabel}>
            {label}
          </FieldLabel>
        ) : null}
        {children}
        {error ? (
          <p id={msgId} className="mt-2 text-xs text-danger-600">
            {error}
          </p>
        ) : hint ? (
          <p id={msgId} className="mt-2 text-xs text-subtle">
            {hint}
          </p>
        ) : null}
      </div>
    </FieldContext.Provider>
  );
}

export function FieldLabel({
  className,
  required,
  optionalLabel,
  children,
  ...props
}: ComponentProps<"label"> & { required?: boolean; optionalLabel?: ReactNode }) {
  return (
    <label className={cn("mb-2 flex items-center gap-1 text-xs font-medium text-subtle", className)} {...props}>
      {children}
      {required ? <span className="text-danger-600">*</span> : null}
      {optionalLabel ? <span className="font-normal text-muted">{optionalLabel}</span> : null}
    </label>
  );
}

/** Two-column responsive grid used by settings/forms (gap 16). */
export function FieldGrid({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("grid grid-cols-1 gap-4 md:grid-cols-2", className)} {...props} />;
}
