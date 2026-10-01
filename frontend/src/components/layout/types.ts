import type { ComponentType, ReactNode } from "react";
import type { IconProps } from "@/components/icons";

export type NavChild = { key: string; label: ReactNode; href: string };

export type NavItem = {
  key: string;
  label: ReactNode;
  icon: ComponentType<IconProps>;
  /** Leaf item link. Omit when the item only groups `children`. */
  href?: string;
  /** Small trailing badge (e.g. "جديد"). */
  badge?: ReactNode;
  children?: NavChild[];
  /** Show in the mobile bottom bar (max 4 + "more"). */
  inBottomBar?: boolean;
};

/** Product branding used by the shell (sidebar logo, collapsed mark, logo on the dark mobile header). */
export type Brand = { name: string; logo: string; mark: string; logoLight: string };

/** Supplier Radar placeholder wordmark (replace the files in /public/brand when a real logo exists). */
export const DEFAULT_BRAND: Brand = {
  name: "Supplier Radar",
  logo: "/brand/logo.svg",
  mark: "/brand/logo-mark.svg",
  logoLight: "/brand/logo-light.svg",
};
