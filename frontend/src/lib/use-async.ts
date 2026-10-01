"use client";

import { useCallback, useEffect, useState } from "react";

type Settled<T> = { status: "success"; data: T; error?: undefined } | { status: "error"; data?: undefined; error: unknown };
export type AsyncState<T> = { status: "loading"; data?: undefined; error?: undefined } | Settled<T>;

/**
 * Runs `fn` whenever `deps` change (deps must be primitives); `reload()` re-runs it.
 * The loading state is derived from the deps key, so stale responses never show for new deps.
 */
export function useAsync<T>(fn: () => Promise<T>, deps: readonly (string | number | boolean | null | undefined)[]) {
  const [tick, setTick] = useState(0);
  const key = JSON.stringify([...deps, tick]);
  const [settled, setSettled] = useState<{ key: string; state: Settled<T> } | null>(null);

  useEffect(() => {
    let alive = true;
    fn().then(
      (data) => alive && setSettled({ key, state: { status: "success", data } }),
      (error: unknown) => alive && setSettled({ key, state: { status: "error", error } }),
    );
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  const state: AsyncState<T> = settled && settled.key === key ? settled.state : { status: "loading" };
  return { ...state, reload };
}
