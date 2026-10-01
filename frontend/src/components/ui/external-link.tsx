import type { ComponentProps } from "react";
import { LinkIcon } from "@/components/icons";
import { cn } from "@/lib/utils";

/**
 * Safe external link (NFR-SEC-01): new tab, `rel="noopener noreferrer"`, only http(s) URLs are linked —
 * anything else renders as plain text. 14/22 primary-700, underline on hover, 14px link glyph.
 */
export function ExternalLink({ href, className, children, icon = true, ...props }: Omit<ComponentProps<"a">, "href" | "target" | "rel"> & { href: string; icon?: boolean }) {
  const safe = /^https?:\/\//i.test(href);
  if (!safe) return <span className={cn("text-sm text-body", className)}>{children}</span>;
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "inline-flex max-w-full items-center gap-1 rounded-xs text-sm text-primary-700 underline-offset-2 transition-colors hover:text-primary-800 hover:underline focus-visible:outline-2 focus-visible:outline-primary-600",
        className,
      )}
      {...props}
    >
      <span className="truncate">{children}</span>
      {icon ? <LinkIcon className="size-3.5 shrink-0" aria-hidden /> : null}
    </a>
  );
}
