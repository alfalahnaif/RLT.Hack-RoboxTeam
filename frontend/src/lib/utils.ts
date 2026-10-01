import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/** tailwind-merge aware of the design-system scales (see globals.css @theme). */
const twMerge = extendTailwindMerge({
  extend: {
    theme: {
      text: ["2xs", "xs", "sm", "base", "lg", "xl", "2xl"],
      radius: ["xs", "sm", "md", "lg", "pill"],
      shadow: ["card", "soft", "overlay", "popper", "fab"],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
