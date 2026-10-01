"use client";

import { Direction, Tooltip } from "radix-ui";
import type { ReactNode } from "react";

/** Client-side providers: RTL/LTR direction for Radix primitives + tooltip timing. */
export function Providers({ dir, children }: { dir: "rtl" | "ltr"; children: ReactNode }) {
  return (
    <Direction.Provider dir={dir}>
      <Tooltip.Provider delayDuration={200}>{children}</Tooltip.Provider>
    </Direction.Provider>
  );
}
