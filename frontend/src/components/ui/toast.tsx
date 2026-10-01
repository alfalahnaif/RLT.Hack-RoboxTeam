"use client";

import { Toast as ToastPrimitive } from "radix-ui";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { CheckCircleIcon, InfoCircleIcon, WarningTriangleIcon } from "@/components/icons";
import { cn } from "@/lib/utils";
import { CloseIcon } from "./_glyphs";

/**
 * Toast / flash message (source: Element Plus `ElMessage`, top-center).
 * Mapped to the palette: tinted 50 background, 200 border, 700/800 text, 8px radius, 11/15 padding,
 * 14px text, 16px icon, overlay shadow. Auto-dismiss after 3s.
 */
type Tone = "success" | "info" | "warning" | "danger";
type ToastItem = { id: number; tone: Tone; title: ReactNode; description?: ReactNode };

const tones: Record<Tone, { cls: string; icon: ReactNode }> = {
  success: { cls: "border-success-200 bg-success-50 text-success-700", icon: <CheckCircleIcon /> },
  info: { cls: "border-primary-200 bg-primary-50 text-primary-700", icon: <InfoCircleIcon /> },
  warning: { cls: "border-warning-300 bg-warning-100 text-warning-800", icon: <WarningTriangleIcon /> },
  danger: { cls: "border-danger-300 bg-danger-100 text-danger-700", icon: <WarningTriangleIcon /> },
};

const ToastContext = createContext<(t: Omit<ToastItem, "id">) => void>(() => {});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback((t: Omit<ToastItem, "id">) => setItems((s) => [...s, { ...t, id: Date.now() + Math.random() }]), []);
  return (
    <ToastContext.Provider value={push}>
      <ToastPrimitive.Provider duration={3000} swipeDirection="up">
        {children}
        {items.map((t) => (
          <ToastPrimitive.Root
            key={t.id}
            onOpenChange={(open) => !open && setItems((s) => s.filter((x) => x.id !== t.id))}
            className={cn(
              "flex w-full items-start gap-2 rounded-md border px-[15px] py-[11px] shadow-overlay data-[state=open]:animate-popper-in data-[state=closed]:animate-fade-out",
              tones[t.tone].cls,
            )}
          >
            <span className="mt-[3px] shrink-0 [&_svg]:size-4">{tones[t.tone].icon}</span>
            <div className="flex flex-1 flex-col gap-0.5">
              <ToastPrimitive.Title className="text-sm font-medium">{t.title}</ToastPrimitive.Title>
              {t.description ? <ToastPrimitive.Description className="text-xs opacity-90">{t.description}</ToastPrimitive.Description> : null}
            </div>
            <ToastPrimitive.Close aria-label="close" className="mt-[3px] shrink-0 opacity-60 hover:opacity-100">
              <CloseIcon className="size-4" />
            </ToastPrimitive.Close>
          </ToastPrimitive.Root>
        ))}
        <ToastPrimitive.Viewport className="fixed start-1/2 top-5 z-[100] flex w-[min(420px,calc(100%-32px))] -translate-x-1/2 flex-col gap-2 outline-none rtl:translate-x-1/2" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}
