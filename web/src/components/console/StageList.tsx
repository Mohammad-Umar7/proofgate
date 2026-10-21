"use client";

import { motion } from "motion/react";
import { STAGES, type Stage, type StageEvent } from "@/lib/types";
import styles from "./console.module.css";

export type StageState = { status: "idle" | "running" | "done" | "skipped" | "error"; message: string; ms: number; bad?: boolean };

export function reduceStages(events: StageEvent[]): Record<Stage, StageState> {
  const out = Object.fromEntries(STAGES.map((s) => [s.id, { status: "idle", message: "", ms: 0 }])) as Record<Stage, StageState>;
  for (const e of events) {
    const cur = out[e.stage];
    if (e.status === "start") out[e.stage] = { ...cur, status: "running", message: e.message };
    else if (e.status === "progress") out[e.stage] = { ...cur, status: "running", message: e.message, ms: e.elapsed_ms };
    else if (e.status === "done") {
      const bad = e.stage === "grounding" && /[1-9]\d* contradicted/.test(e.message);
      out[e.stage] = { status: "done", message: e.message, ms: e.elapsed_ms, bad };
    } else out[e.stage] = { status: e.status, message: e.message, ms: e.elapsed_ms };
  }
  return out;
}

function Icon({ s }: { s: StageState }) {
  if (s.status === "running") return <span className={styles.spin} />;
  if (s.status === "done") return <span className={`${styles.ico} ${s.bad ? styles.icoBad : styles.icoOk}`}>{s.bad ? "!" : "✓"}</span>;
  if (s.status === "skipped") return <span className={`${styles.ico} ${styles.icoSkip}`}>–</span>;
  if (s.status === "error") return <span className={`${styles.ico} ${styles.icoBad}`}>×</span>;
  return <span className={`${styles.ico} ${styles.icoIdle}`} />;
}

export function StageList({ events }: { events: StageEvent[] }) {
  const states = reduceStages(events);
  return (
    <ol className={styles.stages}>
      {STAGES.map((s, i) => {
        const st = states[s.id];
        return (
          <motion.li
            key={s.id}
            className={`${styles.stage} ${styles[st.status]}`}
            initial={false}
            animate={{ opacity: st.status === "idle" ? 0.45 : 1 }}
            transition={{ duration: 0.3 }}
          >
            <Icon s={st} />
            <div className={styles.stageBody}>
              <div className={styles.stageTop}>
                <span className={styles.stageNum}>{String(i + 1).padStart(2, "0")}</span>
                <b>{s.label}</b>
                {s.model && <span className={styles.model}>{s.model}</span>}
                {st.ms > 0 && <span className={styles.ms}>{st.ms < 1000 ? `${st.ms} ms` : `${(st.ms / 1000).toFixed(1)} s`}</span>}
              </div>
              <div className={styles.stageMsg}>{st.message || s.what}</div>
            </div>
          </motion.li>
        );
      })}
    </ol>
  );
}
