"use client";

import { useEffect, useState } from "react";

const ACTIVITY = ["pointerdown", "keydown", "wheel", "touchstart", "scroll"] as const;

/** True once the visitor has done nothing with the page (no click, key, scroll or touch) for `ms`.
 *  Moving the mouse does not count: someone circling the cursor over a page that does not react is
 *  exactly who a hint is for. Starts over whenever `key` changes, e.g. on a new page. */
export function useIdle(ms: number, key: unknown, enabled = true): boolean {
  const [idle, setIdle] = useState(false);
  useEffect(() => {
    setIdle(false);
    if (!enabled) return;
    let id = window.setTimeout(() => setIdle(true), ms);
    const reset = () => {
      clearTimeout(id);
      id = window.setTimeout(() => setIdle(true), ms);
    };
    ACTIVITY.forEach((e) => window.addEventListener(e, reset, { passive: true }));
    return () => {
      clearTimeout(id);
      ACTIVITY.forEach((e) => window.removeEventListener(e, reset));
    };
  }, [ms, key, enabled]);
  return idle;
}
