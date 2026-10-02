import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin();

/** NEXT_DIST_DIR lets verification builds write elsewhere, so a running `next dev` (which owns .next) is never disturbed. */
const nextConfig: NextConfig = { distDir: process.env.NEXT_DIST_DIR || ".next" };

export default withNextIntl(nextConfig);
