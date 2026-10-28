"use client";

import { useEffect, useRef, useState } from "react";
import { command, KEYS, read } from "@/lib/onboarding";
import { REPO_URL, STEPS, VIDEO_URL } from "./steps";
import styles from "./onboarding.module.css";

const typing = (t: EventTarget | null) =>
  t instanceof HTMLElement && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName));

/** The Guide button, bottom right on every page: the way back to the tour, this page's tip and the
 *  welcome after they were dismissed. "?" opens it from the keyboard. */
export function Guide({ offer = true }: { offer?: boolean }) {
  const [open, setOpen] = useState(false);
  const [paused, setPaused] = useState<number | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  // until the visitor has taken the tour, a glowing button above the Guide offers it in one click
  const [toured, setToured] = useState(true);
  useEffect(() => { setToured(read(KEYS.toured) !== null); }, []);

  useEffect(() => {
    if (!open) return;
    const p = read(KEYS.tourPaused, "session");
    setPaused(p !== null && Number.isInteger(Number(p)) ? Number(p) : null);
    const away = (e: PointerEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { setOpen(false); button.current?.focus(); } };
    window.addEventListener("pointerdown", away);
    window.addEventListener("keydown", onKey);
    root.current?.querySelector<HTMLElement>("[role=menuitem]")?.focus();
    return () => { window.removeEventListener("pointerdown", away); window.removeEventListener("keydown", onKey); };
  }, [open]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "?" && !typing(e.target) && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); setOpen((o) => !o); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const run = (c: Parameters<typeof command>[0]) => () => { setOpen(false); command(c); };

  return (
    <div ref={root} className={styles.guide}>
      {open && (
        <div className={styles.menu} role="menu" aria-label="Guide">
          <p className={styles.menuHead}>Guide</p>
          {paused !== null && (
            <button role="menuitem" onClick={run("resume")}>
              <b>Resume the tour</b><span>where you left it, step {paused + 1} of {STEPS.length}</span>
            </button>
          )}
          <button role="menuitem" onClick={run("tour")}>
            <b>{paused !== null ? "Restart the tour" : "Take the guided tour"}</b><span>every page in about two minutes</span>
          </button>
          <button role="menuitem" onClick={run("hint")}>
            <b>Tips for this page</b><span>what to try here</span>
          </button>
          <button role="menuitem" onClick={run("welcome")}>
            <b>What is ProofGate?</b><span>the one-minute overview</span>
          </button>
          <div className={styles.menuSep} />
          <a role="menuitem" href={VIDEO_URL} target="_blank" rel="noreferrer"><b>Watch the 2:46 video ↗</b></a>
          <a role="menuitem" href={`${REPO_URL}#live-mode`} target="_blank" rel="noreferrer"><b>How live mode works ↗</b></a>
          <a role="menuitem" href={REPO_URL} target="_blank" rel="noreferrer"><b>Source on GitHub ↗</b></a>
        </div>
      )}
      {offer && !toured && !open && (
        <button className={`${styles.tourBtn} ${styles.glow}`} onClick={() => command("tour")}>
          <b aria-hidden>▶</b> Take the guided tour
        </button>
      )}
      <button ref={button} className={styles.guideBtn} onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu" aria-expanded={open} title="Guide (press ?)">
        <span aria-hidden>?</span> Guide
      </button>
    </div>
  );
}
