"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { UI_CONFIG } from "@/config/ui";

/**
 * Per-tab session state that must survive navigation (US-08): the compare tray (scoped to ONE
 * request_id — EC-43) and the last opened search run (for the "Results" nav item).
 * Persisted in sessionStorage; read once on mount.
 */
type Tray = { requestId: string | null; ids: string[] };
type AddResult = "added" | "removed" | "limit" | "conflict";

type Ctx = {
  /** False until sessionStorage has been read (avoid flashing empty states). */
  ready: boolean;
  tray: Tray;
  lastRequestId: string | null;
  setLastRequestId: (id: string) => void;
  toggle: (requestId: string, supplierId: string) => AddResult;
  remove: (supplierId: string) => void;
  /** Start a new tray for another search (after the user confirmed the conflict). */
  replace: (requestId: string, supplierId: string) => void;
  clear: () => void;
};

const SessionCtx = createContext<Ctx | null>(null);
const TRAY_KEY = "sr.tray";
const LAST_KEY = "sr.lastRun";

const load = <T,>(key: string, fallback: T): T => {
  try {
    const raw = window.sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
};
const save = (key: string, value: unknown) => {
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignore */
  }
};

export function SessionProvider({ children }: { children: ReactNode }) {
  const [tray, setTray] = useState<Tray>({ requestId: null, ids: [] });
  const [lastRequestId, setLast] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Hydrate from sessionStorage after mount (not available during SSR).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTray(load<Tray>(TRAY_KEY, { requestId: null, ids: [] }));
    setLast(load<string | null>(LAST_KEY, null));
    setReady(true);
  }, []);

  const commit = useCallback((next: Tray) => {
    setTray(next);
    save(TRAY_KEY, next);
  }, []);

  const toggle = useCallback(
    (requestId: string, supplierId: string): AddResult => {
      if (tray.ids.includes(supplierId) && tray.requestId === requestId) {
        commit({ requestId: tray.ids.length > 1 ? requestId : null, ids: tray.ids.filter((x) => x !== supplierId) });
        return "removed";
      }
      if (tray.ids.length && tray.requestId !== requestId) return "conflict";
      if (tray.ids.length >= UI_CONFIG.compareMax) return "limit";
      commit({ requestId, ids: [...tray.ids, supplierId] });
      return "added";
    },
    [tray, commit],
  );

  const value = useMemo<Ctx>(
    () => ({
      ready,
      tray,
      lastRequestId,
      setLastRequestId: (id) => {
        setLast(id);
        save(LAST_KEY, id);
      },
      toggle,
      remove: (supplierId) => {
        const ids = tray.ids.filter((x) => x !== supplierId);
        commit({ requestId: ids.length ? tray.requestId : null, ids });
      },
      replace: (requestId, supplierId) => commit({ requestId, ids: [supplierId] }),
      clear: () => commit({ requestId: null, ids: [] }),
    }),
    [ready, tray, lastRequestId, toggle, commit],
  );

  return <SessionCtx.Provider value={value}>{children}</SessionCtx.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionCtx);
  if (!ctx) throw new Error("useSession must be used inside <SessionProvider>");
  return ctx;
}
