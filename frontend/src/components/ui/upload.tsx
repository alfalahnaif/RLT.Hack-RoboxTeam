"use client";

import { useRef, useState, type ReactNode } from "react";
import { CloseIcon } from "./_glyphs";
import { CloudDownloadIcon, ImageUploadIcon } from "@/components/icons";
import { cn } from "@/lib/utils";

/**
 * Picture tile uploader (source `.wameed-upload-files` / `.el-upload--picture-card`):
 * 118×118, white, 1px gray-200 border, 8px radius; 16px icon + 10/14 muted "انقر للتحميل".
 * With a preview it shows the image cover + remove button.
 */
export function ImageUpload({
  label,
  accept = "image/png,image/jpeg",
  preview,
  onFileChange,
  onRemove,
  className,
  size = 118,
}: {
  label: ReactNode;
  accept?: string;
  preview?: string;
  onFileChange?: (file: File) => void;
  onRemove?: () => void;
  className?: string;
  size?: number;
}) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <div className={cn("relative shrink-0", className)} style={{ width: size, height: size }}>
      <button
        type="button"
        onClick={() => ref.current?.click()}
        className="flex size-full flex-col items-center justify-center overflow-hidden rounded-md border border-line bg-white text-gray-500 outline-none transition-colors hover:border-primary-300 focus-visible:border-focus"
      >
        {preview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={preview} alt="" className="size-full object-cover" />
        ) : (
          <>
            <ImageUploadIcon className="mb-1.5 size-4" />
            <span className="text-2xs text-muted">{label}</span>
          </>
        )}
      </button>
      {preview && onRemove ? (
        <button
          type="button"
          onClick={onRemove}
          aria-label="remove"
          className="absolute end-1.5 top-1.5 flex size-6 items-center justify-center rounded-full border border-line-strong bg-white text-danger-600"
        >
          <CloseIcon className="size-3.5" />
        </button>
      ) : null}
      <input ref={ref} type="file" accept={accept} hidden onChange={(e) => e.target.files?.[0] && onFileChange?.(e.target.files[0])} />
    </div>
  );
}

/**
 * Drag & drop zone (source `.wameed-drag-file .el-upload-dragger`): white, 1px gray-200 border,
 * 8px radius, 126px high, 12px padding. 24px icon (8px below), text 12/18 medium gray-700 with the
 * action word in primary-700, tip 10/14 muted. Drag-over → primary-300 border + primary-50 fill.
 */
export function FileDropzone({
  title,
  action,
  hint,
  accept,
  multiple,
  onFiles,
  className,
}: {
  title: ReactNode;
  action: ReactNode;
  hint?: ReactNode;
  accept?: string;
  multiple?: boolean;
  onFiles?: (files: File[]) => void;
  className?: string;
}) {
  const ref = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => ref.current?.click()}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && ref.current?.click()}
      onDragOver={(e) => (e.preventDefault(), setOver(true))}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        onFiles?.(Array.from(e.dataTransfer.files));
      }}
      className={cn(
        "flex h-[126px] w-full cursor-pointer flex-col items-center justify-center rounded-md border border-line bg-white p-3 text-center outline-none transition-colors focus-visible:border-dashed",
        over && "border-primary-300 bg-primary-50",
        className,
      )}
    >
      <CloudDownloadIcon className="mb-2 size-6 text-gray-500" />
      <p className="mb-1 text-xs font-medium text-subtle">
        {title} <em className="not-italic text-primary-700">{action}</em>
      </p>
      {hint ? <p className="text-2xs text-muted">{hint}</p> : null}
      <input ref={ref} type="file" hidden accept={accept} multiple={multiple} onChange={(e) => onFiles?.(Array.from(e.target.files ?? []))} />
    </div>
  );
}

/** Uploaded file row (`.el-upload-list__item`): 12px padding, 8px gap, 8px radius, gray-200 border. */
export function FileItem({
  name,
  meta,
  status = "default",
  icon,
  onRemove,
}: {
  name: ReactNode;
  meta?: ReactNode;
  status?: "default" | "success" | "error";
  icon?: ReactNode;
  onRemove?: () => void;
}) {
  return (
    <div className="flex w-full items-center gap-2 rounded-md border border-line bg-white p-3">
      <span className="flex h-7 w-6 shrink-0 items-center justify-center text-danger-600 [&_svg]:size-full">{icon}</span>
      <div className="flex min-w-0 flex-1 items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="mb-1 truncate text-xs font-medium text-subtle">{name}</p>
          {meta ? (
            <p className={cn("text-2xs text-muted", status === "success" && "text-success-600", status === "error" && "text-danger-600")}>{meta}</p>
          ) : null}
        </div>
        {onRemove ? (
          <button type="button" onClick={onRemove} aria-label="remove" className="flex size-4 items-center justify-center text-gray-500 hover:text-danger-600">
            <CloseIcon className="size-4" />
          </button>
        ) : null}
      </div>
    </div>
  );
}
