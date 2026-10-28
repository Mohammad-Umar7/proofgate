"use client";

import { useEffect, useState } from "react";
import type { Box } from "./place";

export const selector = (target: string) => `[data-tour="${target}"]`;

/** The visible element marked `data-tour=<target>`. It may arrive late (after data loads, or when a
 *  replay finishes) and be replaced (a replay restarting), so it is looked up again a few times a
 *  second rather than once. */
export function useTarget(target: string | undefined, key?: unknown): HTMLElement | null {
  const [el, setEl] = useState<HTMLElement | null>(null);
  useEffect(() => {
    if (!target) { setEl(null); return; }
    let current: HTMLElement | null = null;
    const tick = () => {
      const found = document.querySelector<HTMLElement>(selector(target));
      const visible = found && found.getClientRects().length ? found : null;
      if (visible !== current) { current = visible; setEl(visible); }
    };
    tick();
    const id = window.setInterval(tick, 200);
    return () => clearInterval(id);
  }, [target, key]);
  return el;
}

/** The element's box in the viewport, followed every frame (the page scrolls, panels resize). */
export function useBox(el: HTMLElement | null): Box | null {
  const [box, setBox] = useState<Box | null>(null);
  useEffect(() => {
    if (!el) { setBox(null); return; }
    let raf = 0, last = "";
    const loop = () => {
      const r = el.getBoundingClientRect();
      const key = `${Math.round(r.top)},${Math.round(r.left)},${Math.round(r.width)},${Math.round(r.height)}`;
      if (key !== last) { last = key; setBox({ top: r.top, left: r.left, width: r.width, height: r.height }); }
      raf = requestAnimationFrame(loop);
    };
    loop();
    return () => cancelAnimationFrame(raf);
  }, [el]);
  return box;
}
