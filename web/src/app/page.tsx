"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useState } from "react";
import { HelixSection } from "@/components/HelixSection";
import { loadBench } from "@/lib/api";
import { STAGES } from "@/lib/types";
import styles from "./page.module.css";

const GateScene = dynamic(() => import("@/three/gate/GateScene"), { ssr: false });

const FACTS = [
  { k: "40,188", v: "curl commits searched per claim, in about 4 seconds" },
  { k: "215", v: "release tags resolved, so claims are checked at the version the reporter named" },
  { k: "239", v: "official curl advisories checked for duplicates" },
  { k: "0", v: "verdicts of UNGROUNDED without a deterministic contradiction" },
];

export default function Home() {
  const [bench, setBench] = useState<any>(null);
  useEffect(() => { loadBench().then(setBench).catch(() => {}); }, []);
  const full = bench?.configs?.full ?? bench?.configs?.deterministic;

  return (
    <main>
      <section className={styles.hero}>
        <div className={styles.canvas}><GateScene /></div>
        <div className={styles.heroShade} />
        <div className={`container ${styles.heroInner}`}>
          <p className="eyebrow">Open-source security triage · NVIDIA Nemotron on Nebius Token Factory</p>
          <h1 className={styles.title}>
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
          <div className={styles.legend}>
            <span><i style={{ background: "var(--red)" }} /> slop dissolves on the gate</span>
            <span><i style={{ background: "var(--blue)" }} /> duplicates merge</span>
            <span><i style={{ background: "var(--green)" }} /> real bugs pass through</span>
          </div>
        </div>
      </section>

      <section className={`container ${styles.section}`}>
        <p className="eyebrow">The problem</p>
        <h2 className={styles.h2}>A fake report costs seconds to generate and an hour to disprove.</h2>
        <p className={styles.lead}>
          Open-source projects like curl run on billions of devices and are maintained by volunteers. AI-generated
          reports cite functions that never existed, line numbers past the end of the file, and code nobody wrote.
          The curl project keeps a public list of them. ProofGate turns that hour into seconds by checking the claims
          against git history, not by trusting another model&apos;s opinion.
        </p>
        <div className={styles.facts}>
          {FACTS.map((f) => (
            <div key={f.v} className={`panel ${styles.fact}`}>
              <div className={styles.factK}>{f.k}</div>
              <div className={styles.factV}>{f.v}</div>
            </div>
          ))}
        </div>
        {full && (
          <div className={`panel ${styles.bench}`}>
            <div>
              <p className="eyebrow">SlopBench · {full.n} real curl reports</p>
              <p className={styles.benchLine}>
                Closes <b>{Math.round(full.slop_closed * 100)}%</b> of known slop · wrongly dismisses{" "}
                <b>{full.valid_dismissed}</b> of {full.n_valid} real CVEs · <b>${full.cost_mean_usd.toFixed(4)}</b> per report
              </p>
            </div>
            <Link className="btn" href="/bench/">See the benchmark</Link>
          </div>
        )}
      </section>

      <HelixSection />

      <section className={`container ${styles.section}`}>
        <p className="eyebrow">How it works</p>
        <h2 className={styles.h2}>Nine stages. Cheap checks first, expensive reasoning last.</h2>
        <ol className={styles.stages}>
          {STAGES.map((s, i) => (
            <li key={s.id} className="panel">
              <span className={styles.stageN}>{String(i + 1).padStart(2, "0")}</span>
              <span className={styles.stageL}>{s.label}</span>
              <span className={styles.stageW}>{s.what}</span>
              {s.model && <span className="chip">{s.model}</span>}
            </li>
          ))}
        </ol>
      </section>

      <section className={`container ${styles.section}`}>
        <p className="eyebrow">Built on</p>
        <div className={styles.stack}>
          <div className="panel">
            <b>Nebius Token Factory</b>
            <p>Every model call, through the OpenAI-compatible API. Four Nemotron sizes, each with one job, with live cost accounting and a hard per-report budget.</p>
          </div>
          <div className="panel">
            <b>NVIDIA Nemotron 3</b>
            <p>Nano Omni reads screenshots, Nano extracts claims, Super reasons over real source and writes patches, Ultra decides and then argues the other side.</p>
          </div>
          <div className="panel">
            <b>Tavily</b>
            <p>Runtime prior-art search across disclosed reports, advisories, issues and mailing lists, to catch duplicates and already-fixed bugs.</p>
          </div>
          <div className="panel">
            <b>NVIDIA OpenShell</b>
            <p>The reporter&apos;s own reproduction runs in an ephemeral sandbox with network denied, no credentials, and resource limits.</p>
          </div>
        </div>
      </section>

      <footer className={`container ${styles.footer}`}>
        <span>ProofGate · Apache-2.0 · Nebius x NVIDIA Global AI Hackathon 2026</span>
        <a href="https://github.com/Mohammad-Umar7/proofgate">github.com/Mohammad-Umar7/proofgate</a>
      </footer>
    </main>
  );
}
