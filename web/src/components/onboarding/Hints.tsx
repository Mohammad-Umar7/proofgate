"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { command, KEYS, read, write } from "@/lib/onboarding";
import { type Hint, hintsFor } from "./pageHints";
import { useIdle } from "./useIdle";
import { useBox, useTarget } from "./useTarget";
import styles from "./onboarding.module.css";

const page = (path: string | null) => (path ?? "/").replace(/\/+$/, "") || "/";
const hinted = (): string[] => {
  try { return JSON.parse(read(KEYS.hinted, "session") ?? "[]"); } catch { return []; }
};

/** Shown when a page has no hint of its own, or on request from the Guide on such a page. */
const GENERAL: Hint = {
  text: "Not sure where to look? The guided tour walks through every page in about two minutes.",
  actions: [{ label: "Take the tour", run: () => command("tour") }],
};

/** When a page sits idle, one quiet hint: what to do here, a pulse on where to do it, and a button
 *  that does it. Once per page per visit, never over the welcome or the tour. `ask` (a counter)
 *  shows the page's hint right away, for the Guide's "Tips for this page". */
export function Hints({ suppressed, ask }: { suppressed: boolean; ask: number }) {
  const path = usePathname();
  const router = useRouter();
  const def = hintsFor(path);
  const [done, setDone] = useState(true);
  const [hint, setHint] = useState<Hint | null>(null);

  useEffect(() => { setHint(null); setDone(hinted().includes(page(path))); }, [path]);

  const idle = useIdle(def?.after ?? 0, path, Boolean(def) && !done && !suppressed);
  useEffect(() => {
    if (!idle || !def || done || suppressed) return;
    const h = def.build((href) => router.push(href));
    if (!h) return;
    setHint(h);
    setDone(true);
    write(KEYS.hinted, JSON.stringify([...hinted(), page(path)]), "session");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idle]);

  useEffect(() => {
    if (!ask) return;
    setHint(def?.build((href) => router.push(href)) ?? GENERAL);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ask]);

  useEffect(() => { if (suppressed) setHint(null); }, [suppressed]);
  useEffect(() => {
    if (!hint) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setHint(null); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [hint]);

  const el = useTarget(hint?.target);
  const box = useBox(el);
  if (!hint) return null;
  const visible = box && box.top + box.height > 64 && box.top < window.innerHeight;

  return createPortal(
    <>
      {visible && <div className={styles.beacon} style={{ top: box.top - 6, left: box.left - 6, width: box.width + 12, height: box.height + 12 }} aria-hidden />}
      <div className={styles.hint} role="status" aria-live="polite">
        <span className={styles.hintDot} aria-hidden />
        <p>{hint.text}</p>
        <div className={styles.hintActions}>
          {hint.actions.map((a, i) => (
            <button key={a.label} className={`btn ${i === 0 ? "btn-primary" : ""}`}
              onClick={() => { setHint(null); a.run(); }}>{a.label}</button>
          ))}
          <button className={styles.hintClose} onClick={() => setHint(null)} aria-label="Dismiss the hint">×</button>
        </div>
      </div>
    </>,
    document.body,
  );
}
