"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { LoadError, Loading } from "@/components/Status";
import { API, card as fetchCard, data, stream } from "@/lib/api";
import { VERDICT_META, type Card, type StageEvent, type Verdict } from "@/lib/types";
import styles from "./arena.module.css";

interface Round {
  seed: number; level: number; strategy: string; author: string;
  report: { title: string; body: string }; verdict: Verdict; caught: boolean; card: Card;
}

const LEVEL_NAMES = ["", "Invented file + function", "Real file, invented function", "Real function, wrong lines",
  "Real code, check already exists", "Real code + talks to the AI"];

export default function ArenaPage() {
  const [rounds, setRounds] = useState<Round[]>([]);
  const [open, setOpen] = useState<number | null>(null);
  const [liveLevel, setLiveLevel] = useState(4);
  const [liveState, setLiveState] = useState<string>("");
  const [load, setLoad] = useState<"loading" | "ok" | "failed">("loading");

  useEffect(() => {
    fetch(data("arena.json")).then((r) => r.json()).then((r) => { setRounds(r); setLoad("ok"); })
      .catch(() => setLoad("failed"));
  }, []);

  const caught = rounds.filter((r) => r.caught).length;
  const fooled = rounds.length - caught;

  async function liveRound() {
    setLiveState("Nemotron Super is writing a fake report…");
    try {
      const res = await fetch(`${API}/api/arena/round?level=${liveLevel}`, { method: "POST" });
      if (!res.ok) throw new Error((await res.json()).detail);
      const { run_id, title, body, level } = await res.json();
      setLiveState("ProofGate is checking it against the real code…");
      stream(run_id, (_e: StageEvent) => {}, async () => {
        const card = await fetchCard(run_id);
        const verdict = card.verdict as Verdict;
        setRounds((xs) => [{ seed: Date.now(), level, strategy: "", author: "Nemotron Super (live)",
          report: { title, body }, verdict, caught: verdict === "UNGROUNDED" || verdict === "NEEDS_INFO", card }, ...xs]);
        setLiveState("");
        setOpen(0);
      });
    } catch (e) {
      setLiveState(String((e as Error).message));
    }
  }

  return (
    <main className={`container ${styles.page}`}>
      <p className="eyebrow">Adversarial arena</p>
      <h1 className={styles.h1}>A red-team agent writes fake reports. Each level gets closer to the truth.</h1>
      <p className={styles.lead}>
        Level 1 invents everything. Level 5 quotes real curl code accurately, claims a check is missing when it is
        not, and adds a line addressed to the AI triager. ProofGate&apos;s job: never let one through as real, and only
        dismiss when it can prove a contradiction.
      </p>

      <div className={styles.score}>
        <motion.div className={styles.scoreSide} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <span>ProofGate</span><b className={styles.green}>{caught}</b>
        </motion.div>
        <div className={styles.vs}>vs</div>
        <motion.div className={styles.scoreSide} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <span>Red team</span><b className={styles.red}>{fooled}</b>
        </motion.div>
      </div>

      <div className={styles.ladder}>
        {[1, 2, 3, 4, 5].map((lvl) => {
          const rs = rounds.filter((r) => r.level === lvl);
          return (
            <div key={lvl} className={`panel ${styles.rung}`}>
              <span className={styles.lvl}>Level {lvl}</span>
              <b>{LEVEL_NAMES[lvl]}</b>
              <div className={styles.pips}>
                {rs.map((r, i) => <i key={i} style={{ background: VERDICT_META[r.verdict].color }} title={r.verdict} />)}
              </div>
            </div>
          );
        })}
      </div>

      {API && (
        <div className={`panel ${styles.live}`}>
          <div>
            <b>Play a live round</b>
            <p>Nemotron Super writes a new fake at the level you pick, from real curl code. ProofGate checks it live.</p>
          </div>
          <div className={styles.liveCtl}>
            <select value={liveLevel} onChange={(e) => setLiveLevel(Number(e.target.value))}>
              {[1, 2, 3, 4, 5].map((l) => <option key={l} value={l}>Level {l}</option>)}
            </select>
            <button className="btn btn-primary" onClick={liveRound} disabled={!!liveState}>Run round</button>
            <Link className="btn" href="/console/">Paste your own fake →</Link>
          </div>
          {liveState && <p className={styles.liveState}>{liveState}</p>}
        </div>
      )}

      {load !== "ok" && <div className={`panel ${styles.status}`}>
        {load === "failed" ? <LoadError what="The arena rounds" /> : <Loading label="Loading the red-team rounds…" />}
      </div>}

      <div className={styles.rounds}>
        {rounds.map((r, i) => {
          const meta = VERDICT_META[r.verdict];
          const top = r.card.ledger.find((l) => l.status === "contradicted") ?? r.card.ledger[0];
          return (
            <div key={`${r.seed}-${r.level}-${i}`} className={`panel ${styles.round}`}>
              <button className={styles.roundHead} onClick={() => setOpen(open === i ? null : i)}>
                <span className={styles.lvl}>L{r.level}</span>
                <span className={styles.roundTitle}>{r.report.title}</span>
                {r.card.flags.includes("prompt-injection") && <span className="chip amber">injection flagged</span>}
                <span className={`chip ${meta.css}`}>{meta.label}</span>
                <span className={`${styles.res} ${r.caught ? styles.green : styles.red}`}>{r.caught ? "caught" : "fooled"}</span>
              </button>
              {top && <p className={styles.why}>{top.detail}</p>}
              {open === i && (
                <div className={styles.detail}>
                  <div>
                    <h4>Red team ({r.author})</h4>
                    <pre>{r.report.body}</pre>
                  </div>
                  <div>
                    <h4>ProofGate evidence</h4>
                    {r.card.ledger.map((l, k) => (
                      <div key={k} className={styles.ev}>
                        <span className={`chip ${l.status === "verified" ? "green" : l.status === "contradicted" ? "red" : l.status === "partial" ? "amber" : ""}`}>{l.status}</span>
                        <span>{l.detail}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </main>
  );
}
