"use client";

import { useEffect, useRef } from "react";
import type { StageEvent } from "@/lib/types";
import styles from "./console.module.css";

const TONE: Record<string, string> = {
  verified: styles.tOk, contradicted: styles.tBad, partial: styles.tWarn, unverifiable: styles.tDim,
};

export function EventLog({ events }: { events: StageEvent[] }) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => { box.current?.scrollTo({ top: box.current.scrollHeight, behavior: "smooth" }); }, [events.length]);
  const t0 = events[0]?.t ?? 0;
  return (
    <div ref={box} className={styles.log}>
      {events.map((e, i) => {
        const verdict = (e.data?.verdict as string) || "";
        return (
          <div key={i} className={`${styles.logRow} ${TONE[verdict] ?? ""} ${e.status === "done" ? styles.logDone : ""}`}>
            <span className={styles.logT}>+{(e.t - t0).toFixed(2)}s</span>
            <span className={styles.logStage}>{e.stage}</span>
            <span className={styles.logMsg}>{verdict && <i>{verdict}</i>}{e.message}</span>
          </div>
        );
      })}
      {!events.length && <div className={styles.logEmpty}>Pick a report to start. Events stream here as each stage runs.</div>}
    </div>
  );
}
