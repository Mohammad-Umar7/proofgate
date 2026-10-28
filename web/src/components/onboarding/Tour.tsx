"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { samePage, scrollBehavior } from "@/lib/onboarding";
import { dock, place } from "./place";
import { REPO_URL, STEPS, VIDEO_URL } from "./steps";
import { useBox, useTarget } from "./useTarget";
import styles from "./onboarding.module.css";

const PAD = 8; // spotlight margin around the element

const typing = (t: EventTarget | null) =>
  t instanceof HTMLElement && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName));

/** The guided tour. It walks STEPS across pages: opens each step's page, waits for its element,
 *  scrolls it into view, dims everything else and explains it in a card beside it. The page stays
 *  usable underneath: a visitor can click what the card points at. */
export function Tour({ index, onGo, onClose, onLeave }: {
  index: number; onGo: (i: number) => void; onClose: () => void;
  /** the visitor left the step's page on their own (the nav, a link): stop following them */
  onLeave: () => void;
}) {
  const step = STEPS[index];
  const last = index === STEPS.length - 1;
  const path = usePathname();
  const router = useRouter();
  const here = samePage(path, step.route);

  // open the step's page; but once the visitor has been on it and goes elsewhere, they chose to
  const arrived = useRef(false);
  useEffect(() => { arrived.current = false; }, [index]);
  useEffect(() => {
    if (here) { arrived.current = true; return; }
    if (arrived.current) onLeave();
    else router.push(step.route);
  }, [here, step.route, router, onLeave]);

  const el = useTarget(here ? step.target : undefined, index);
  const box = useBox(el);

  // the card's own size, for placing it
  const card = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 360, height: 220 });
  useLayoutEffect(() => {
    const c = card.current;
    if (!c) return;
    const measure = () => setSize({ width: c.offsetWidth, height: c.offsetHeight });
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(c);
    return () => ro.disconnect();
  }, []);

  // bring the step's element into view once, leaving room for the card below it
  useEffect(() => {
    if (!here) return;
    if (step.top) { window.scrollTo({ top: 0, behavior: scrollBehavior() }); return; }
    if (!el) return;
    const r = el.getBoundingClientRect(), vh = window.innerHeight;
    if (r.top >= 76 && r.bottom + size.height + 30 <= vh) return;
    const room = vh - 84 - (r.height + 14 + size.height);
    const top = window.scrollY + r.top - 84 - (room > 0 ? room / 2 : 0);
    window.scrollTo({ top: Math.max(0, top), behavior: scrollBehavior() });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [el, here, index]);

  // keyboard: arrows move, Escape ends; never while the visitor is typing in the page
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (typing(e.target)) return;
      if (e.key === "Escape") { e.preventDefault(); onClose(); }
      else if (e.key === "ArrowRight" && !last) { e.preventDefault(); onGo(index + 1); }
      else if (e.key === "ArrowLeft" && index > 0) { e.preventDefault(); onGo(index - 1); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [index, last, onGo, onClose]);

  const next = useRef<HTMLButtonElement>(null);
  useEffect(() => { next.current?.focus({ preventScroll: true }); }, [index]);

  const [view, setView] = useState({ width: 1280, height: 800 });
  useEffect(() => {
    const r = () => setView({ width: window.innerWidth, height: window.innerHeight });
    r();
    window.addEventListener("resize", r);
    return () => window.removeEventListener("resize", r);
  }, []);

  const hole = box && { top: box.top - PAD, left: box.left - PAD, width: box.width + PAD * 2, height: box.height + PAD * 2 };
  const pos = step.dock ? dock(step.dock, size, view) : place(hole, size, view);
  const waiting = here && step.target && !el;

  return createPortal(
    <div className={styles.tour}>
      {step.clear ? null : hole ? <div className={styles.hole} style={hole} /> : <div className={styles.dim} />}
      <div ref={card} className={styles.card} style={{ top: pos.top, left: pos.left }} data-side={pos.side}
        role="dialog" aria-modal="false" aria-labelledby="pg-tour-title" aria-describedby="pg-tour-body">
        <div className={styles.cardHead}>
          <span className={styles.count}>Guided tour · {index + 1} of {STEPS.length}</span>
          <button className={styles.skip} onClick={onClose}>End tour</button>
        </div>
        <h3 id="pg-tour-title" className={styles.cardTitle}>{step.title}</h3>
        <p id="pg-tour-body" className={styles.cardBody}>{step.body}</p>
        {waiting && step.waiting && <p className={styles.waiting}><i aria-hidden />{step.waiting}</p>}
        <div className={styles.progress} aria-hidden><i style={{ width: `${((index + 1) / STEPS.length) * 100}%` }} /></div>
        <div className={styles.cardActions}>
          {index > 0 && <button className="btn" onClick={() => onGo(index - 1)}>Back</button>}
          {last ? (
            <>
              <a className="btn" href={VIDEO_URL} target="_blank" rel="noreferrer">Video ↗</a>
              <a className="btn" href={REPO_URL} target="_blank" rel="noreferrer">GitHub ↗</a>
              <button ref={next} className="btn btn-primary" onClick={onClose}>Finish</button>
            </>
          ) : (
            <button ref={next} className="btn btn-primary" onClick={() => onGo(index + 1)}>
              {STEPS[index + 1].route !== step.route ? "Next page →" : "Next →"}
            </button>
          )}
        </div>
        <p className={styles.keys}>← → to move · Esc to end</p>
      </div>
    </div>,
    document.body,
  );
}
