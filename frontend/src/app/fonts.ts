import { Inter } from "next/font/google";

/**
 * Primary UI typeface for Russian and English. Replaces the design system's GraphikArabic,
 * which has no Cyrillic glyphs; Inter is already the design system's first fallback.
 * next/font self-hosts the files at build time (no runtime request to Google).
 */
export const inter = Inter({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});
