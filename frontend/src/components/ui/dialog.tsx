"use client";

import { Dialog as DialogPrimitive } from "radix-ui";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";
import { CloseIcon } from "./_glyphs";

/**
 * Source: `.el-dialog` + `.wameed-dialog-*`.
 * Backdrop rgba(8,44,103,.3). Panel: white, 1px gray-100 border, 12px radius, overlay shadow,
 * top offset 135px (15vh), width 500 (form) / 400 (confirm). Header 16px padding, title 16/24 medium,
 * 20px close X at the end. Footer: padding 0/16/16, gap 12, packed at the end side.
 * Button order in JSX is always [cancel, primary] → primary ends up at the far end (left in RTL).
 */
export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

export function DialogOverlay({ className, ...props }: ComponentProps<typeof DialogPrimitive.Overlay>) {
  return (
    <DialogPrimitive.Overlay
      className={cn("fixed inset-0 z-50 bg-overlay data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out", className)}
      {...props}
    />
  );
}

type ContentProps = ComponentProps<typeof DialogPrimitive.Content> & {
  size?: "sm" | "default" | "lg";
  hideClose?: boolean;
};

const widths = { sm: "max-w-[400px]", default: "max-w-[500px]", lg: "max-w-[720px]" };

export function DialogContent({ className, children, size = "default", hideClose, ...props }: ContentProps) {
  return (
    <DialogPrimitive.Portal>
      <DialogOverlay />
      <DialogPrimitive.Content
        className={cn(
          "fixed start-1/2 top-[15vh] z-50 flex max-h-[80vh] w-[calc(100%-32px)] -translate-x-1/2 flex-col overflow-hidden rounded-lg border border-line-subtle bg-white shadow-overlay outline-none rtl:translate-x-1/2",
          "data-[state=open]:animate-dialog-in",
          widths[size],
          className,
        )}
        {...props}
      >
        {children}
        {hideClose ? null : (
          <DialogPrimitive.Close className="absolute end-4 top-4 flex size-5 items-center justify-center rounded-sm text-gray-500 outline-none transition-colors hover:text-heading focus-visible:ring-4 focus-visible:ring-primary-600/15">
            <CloseIcon className="size-5" />
            <span className="sr-only">Close</span>
          </DialogPrimitive.Close>
        )}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function DialogHeader({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("flex flex-col gap-1 p-4 pe-12", className)} {...props} />;
}

export function DialogTitle({ className, ...props }: ComponentProps<typeof DialogPrimitive.Title>) {
  return <DialogPrimitive.Title className={cn("text-base font-medium text-heading", className)} {...props} />;
}

export function DialogDescription({ className, ...props }: ComponentProps<typeof DialogPrimitive.Description>) {
  return <DialogPrimitive.Description className={cn("text-sm text-subtle", className)} {...props} />;
}

/** Scrollable body; forms inside use `flex-col gap-4` between fields. */
export function DialogBody({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("flex flex-col gap-4 overflow-y-auto px-4 pb-4", className)} {...props} />;
}

export function DialogFooter({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("flex items-center justify-end gap-3 px-4 pb-4 [&>*]:min-w-[100px]", className)} {...props} />;
}

type ConfirmDialogProps = {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  trigger?: ReactNode;
  tone?: "danger" | "warning" | "success" | "info";
  icon: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  /** Typically `<Button variant="danger">حذف</Button>` */
  confirm: ReactNode;
  /** Typically `<DialogClose asChild><Button variant="secondary">تراجع</Button></DialogClose>` */
  cancel: ReactNode;
};

const toneIcon = {
  danger: "bg-danger-200 border-danger-50 text-danger-600",
  warning: "bg-warning-200 border-warning-50 text-warning-700",
  success: "bg-success-100 border-success-50 text-success-600",
  info: "bg-primary-100 border-primary-50 text-primary-700",
};

/**
 * Action/confirmation dialog (source `.wameed-dialog-action`): 400px, centered content,
 * 56px icon bubble with a 10px tinted ring, title 16/24 medium, text 16/24 gray-700,
 * footer buttons centered.
 */
export function ConfirmDialog({ open, onOpenChange, trigger, tone = "danger", icon, title, description, confirm, cancel }: ConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {trigger ? <DialogTrigger asChild>{trigger}</DialogTrigger> : null}
      <DialogContent size="sm">
        <div className="flex flex-col items-center gap-2 px-4 pt-12 pb-6 text-center">
          <div className={cn("mb-2 flex size-14 items-center justify-center rounded-full border-[10px] [&_svg]:size-5", toneIcon[tone])}>{icon}</div>
          <DialogTitle>{title}</DialogTitle>
          {description ? <DialogDescription className="text-base">{description}</DialogDescription> : null}
        </div>
        <div className="flex items-center justify-center gap-3 px-4 pb-4 [&>*]:min-w-[100px]">
          {cancel}
          {confirm}
        </div>
      </DialogContent>
    </Dialog>
  );
}
