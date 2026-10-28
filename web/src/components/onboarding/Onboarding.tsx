"use client";

import { useCallback, useEffect, useState } from "react";
import { EVENT, KEYS, type OnboardingCommand, read, write } from "@/lib/onboarding";
import { STEPS } from "./steps";
import { Tour } from "./Tour";
import { Welcome } from "./Welcome";

type Phase = { kind: "idle" } | { kind: "welcome" } | { kind: "tour"; step: number };

/** The onboarding layer, mounted once for every page. A first visit gets the welcome; a tour in
 *  progress survives page changes and reloads; anything on the page can open either one. */
export function Onboarding() {
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });

  useEffect(() => {
    const saved = Number(read(KEYS.tourStep, "session"));
    if (read(KEYS.tourStep, "session") !== null && saved >= 0 && saved < STEPS.length) {
      setPhase({ kind: "tour", step: saved });
      return;
    }
    if (read(KEYS.welcomed)) return;
    // let the page paint first, so the welcome lands on a site that is already there
    const id = window.setTimeout(() => setPhase((p) => (p.kind === "idle" ? { kind: "welcome" } : p)), 700);
    return () => clearTimeout(id);
  }, []);

  const go = useCallback((step: number) => {
    write(KEYS.tourStep, String(step), "session");
    setPhase({ kind: "tour", step });
  }, []);
  const end = useCallback(() => {
    write(KEYS.tourStep, null, "session");
    write(KEYS.welcomed, "1");
    setPhase({ kind: "idle" });
  }, []);
  const startTour = useCallback(() => { write(KEYS.welcomed, "1"); go(0); }, [go]);

  useEffect(() => {
    const on = (e: Event) => {
      const c = (e as CustomEvent<OnboardingCommand>).detail;
      if (c === "tour") startTour();
      else if (c === "welcome") setPhase({ kind: "welcome" });
    };
    window.addEventListener(EVENT, on);
    return () => window.removeEventListener(EVENT, on);
  }, [startTour]);

  if (phase.kind === "welcome") return <Welcome onTour={startTour} onClose={end} />;
  if (phase.kind === "tour") return <Tour index={phase.step} onGo={go} onClose={end} />;
  return null;
}
