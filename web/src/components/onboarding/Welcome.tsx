"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { VIDEO_URL } from "./steps";
import styles from "./onboarding.module.css";

const PLACES = [
  { href: "/console/", name: "Console", what: "Watch a real report get proven or disproven, claim by claim, in nine stages." },
  { href: "/galaxy/", name: "Code galaxy", what: "Every function in curl. Invented ones float outside, connected to nothing." },
  { href: "/fixbench/", name: "FixBench", what: "NVIDIA Nemotron fixing real curl CVEs, judged by curl's own test suite." },
];

/** Keep Tab inside the dialog while it is open. */
function trapTab(e: KeyboardEvent, root: HTMLElement | null) {
  if (e.key !== "Tab" || !root) return;
  const items = [...root.querySelectorAll<HTMLElement>("a[href], button:not([disabled])")];
  if (!items.length) return;
  const first = items[0], last = items[items.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
}

/** First-visit welcome: what ProofGate is, where to look, and the choice of a guided tour. */
export function Welcome({ onTour, onClose }: { onTour: () => void; onClose: () => void }) {
  const box = useRef<HTMLDivElement>(null);
  const primary = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const before = document.activeElement as HTMLElement | null;
    primary.current?.focus({ preventScroll: true });
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.preventDefault(); onClose(); }
      trapTab(e, box.current);
    };
    window.addEventListener("keydown", onKey);
    const html = document.documentElement, overflow = html.style.overflow;
    html.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      html.style.overflow = overflow;
      before?.focus?.({ preventScroll: true });
    };
  }, [onClose]);

  return (
    <div className={styles.backdrop} onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div ref={box} className={styles.welcome} role="dialog" aria-modal="true" aria-labelledby="pg-welcome-title"
        aria-describedby="pg-welcome-lead">
        <button className={styles.close} onClick={onClose} aria-label="Close the welcome">×</button>
        <p className="eyebrow">Welcome · Nebius x NVIDIA Global AI Hackathon</p>
        <h2 id="pg-welcome-title" className={styles.welcomeTitle}>
          Proof for every security report, before a maintainer reads it.
        </h2>
        <p id="pg-welcome-lead" className={styles.welcomeLead}>
          ProofGate checks AI-generated vulnerability reports against curl&apos;s real source code and full git history,
          then has an agent fix the real ones. Three places to start:
        </p>
        <ol className={styles.places}>
          {PLACES.map((p, i) => (
            <li key={p.href}>
              <Link href={p.href} onClick={onClose}>
                <span className={styles.placeN}>{i + 1}</span>
                <span className={styles.placeName}>{p.name}</span>
                <span className={styles.placeWhat}>{p.what}</span>
                <span className={styles.placeGo} aria-hidden>→</span>
              </Link>
            </li>
          ))}
        </ol>
        <p className={styles.demoNote}>
          <span className="dot" aria-hidden />
          This public demo replays real runs recorded on NVIDIA Nemotron through Nebius Token Factory, in your
          browser. Nothing to install, no sign-in, no keys.
        </p>
        <div className={styles.welcomeActions}>
          <button ref={primary} className="btn btn-primary" onClick={onTour}>Take the 2-minute tour →</button>
          <a className="btn" href={VIDEO_URL} target="_blank" rel="noreferrer">Watch the 2:46 video ↗</a>
          <button className={styles.textBtn} onClick={onClose}>Explore on my own</button>
        </div>
        <p className={styles.reopen}>You can reopen this and the tour any time from <b>Guide</b>, bottom right.</p>
      </div>
    </div>
  );
}
