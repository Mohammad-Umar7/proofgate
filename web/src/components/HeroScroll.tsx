"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Guard3D } from "@/components/Guard3D";
import { PLAY_HERO } from "@/lib/onboarding";
import styles from "./HeroScroll.module.css";

const GateScene = dynamic(() => import("@/three/gate/GateScene"), { ssr: false });

const CAPTIONS = [
  // timed to the camera spline: approach, membrane fills the view, through the ring
  { from: 0.08, to: 0.34, eyebrow: "01 · intake", title: "Every report flies into the gate.", body: "Each shard is a report. Before a maintainer reads one, its claims are checked against the real code." },
  { from: 0.34, to: 0.55, eyebrow: "02 · grounding", title: "Slop dissolves on contact.", body: "A function that never existed, a line past the end of the file, code nobody wrote: proven false, in seconds, for free." },
  { from: 0.55, to: 0.98, eyebrow: "03 · verdict", title: "Real bugs pass through.", body: "What survives goes to the maintainer as an evidence card. Duplicates of published advisories merge into the blue cluster." },
];

/** The landing hero, pinned while the camera flies through the gate as you scroll. */
export function HeroScroll() {
  const wrap = useRef<HTMLElement>(null);
  const progress = useRef(0);
  const [step, setStep] = useState(-1);
  const [fade, setFade] = useState(0);

  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const el = wrap.current;
      if (!el) return;
      const total = el.offsetHeight - window.innerHeight;
      const p = Math.min(1, Math.max(0, -el.getBoundingClientRect().top / Math.max(1, total)));
      progress.current = p;
      setFade(Math.min(1, p / 0.14));
      setStep(CAPTIONS.findIndex((c) => p >= c.from && p < c.to));
    };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(update); };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      cancelAnimationFrame(frame);
    };
  }, []);

  // play the fly-through for a visitor who has not scrolled: an eased scroll to the end of the
  // hero, about 12 s for the whole flight, handed back the moment they scroll, tap or press a key
  const flight = useRef(0);
  const play = useCallback(() => {
    const el = wrap.current;
    if (!el || flight.current) return;
    const start = window.scrollY, end = el.offsetTop + el.offsetHeight - window.innerHeight;
    if (end - start < 8) return;
    const dur = 12000 * ((end - start) / Math.max(1, end - el.offsetTop));
    const t0 = performance.now();
    const stops = ["wheel", "touchstart", "keydown", "pointerdown"] as const;
    const stop = () => {
      cancelAnimationFrame(flight.current);
      flight.current = 0;
      stops.forEach((e) => window.removeEventListener(e, stop));
    };
    stops.forEach((e) => window.addEventListener(e, stop, { passive: true }));
    const tick = (now: number) => {
      const k = Math.min(1, (now - t0) / dur);
      const eased = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
      window.scrollTo(0, start + (end - start) * eased);
      if (k < 1) flight.current = requestAnimationFrame(tick);
      else stop();
    };
    flight.current = requestAnimationFrame(tick);
  }, []);
  useEffect(() => {
    window.addEventListener(PLAY_HERO, play);
    return () => { window.removeEventListener(PLAY_HERO, play); cancelAnimationFrame(flight.current); };
  }, [play]);
  const [still, setStill] = useState(false);
  useEffect(() => { setStill(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false); }, []);

  return (
    <section ref={wrap} className={styles.wrap}>
      <div className={styles.sticky}>
        <div className={styles.canvas}>
          {/* without WebGL, a still of the gate: the captions and calls to action work the same */}
          <Guard3D what="gate" fallback={() => <div className={styles.still} aria-hidden />}>
            <GateScene progress={progress} />
          </Guard3D>
        </div>
        <div className={styles.shade} style={{ opacity: 1 - fade * 0.85 }} />

        <div className={`container ${styles.inner}`} style={{ opacity: 1 - fade, transform: `translateY(${-fade * 40}px)`, pointerEvents: fade > 0.6 ? "none" : "auto" }}>
          <p className="eyebrow">Open-source security triage · NVIDIA Nemotron on Nebius Token Factory</p>
          <h1 className={styles.title} data-tour="hero-copy">
            AI made fake security reports <em>free to produce.</em>
            <br />
            ProofGate makes proving them <span>cheap.</span>
          </h1>
          <p className={styles.sub}>
            Every incoming vulnerability report is checked claim by claim against the real source code, at the exact
            version it names, before a volunteer maintainer spends an hour on it. Confirmed bugs go all the way to a
            tested patch. A human always makes the final call.
          </p>
          <div className={styles.ctas}>
            <Link href="/console/" className="btn btn-primary">Watch it triage a real report →</Link>
            <Link href="/arena/" className="btn">Try to fool it</Link>
          </div>
          <div className={styles.legend} data-tour="hero-legend">
            <span><i style={{ background: "var(--red)" }} /> slop dissolves on the gate</span>
            <span><i style={{ background: "var(--blue)" }} /> duplicates merge</span>
            <span><i style={{ background: "var(--green)" }} /> real bugs pass through</span>
          </div>
        </div>

        {CAPTIONS.map((c, i) => (
          <div key={c.title} className={`${styles.caption} ${step === i ? styles.on : ""}`} aria-hidden={step !== i}>
            <p className="eyebrow">{c.eyebrow}</p>
            <h2>{c.title}</h2>
            <p>{c.body}</p>
          </div>
        ))}

        <div className={styles.hint} style={{ opacity: 1 - fade }} data-tour="hero-hint">
          <span>Scroll to fly through the gate</span>
          {!still && (
            <button className={styles.play} onClick={play} style={{ pointerEvents: fade > 0.6 ? "none" : "auto" }}>
              <b aria-hidden>▶</b> or play the flight
            </button>
          )}
          <i />
        </div>
      </div>
    </section>
  );
}
