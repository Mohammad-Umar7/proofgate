"use client";

import { useEffect, useMemo, useState } from "react";
import { loadBench } from "@/lib/api";
import { VERDICT_META, type Verdict } from "@/lib/types";
import styles from "./bench.module.css";

type Metrics = {
  n: number; n_slop: number; n_valid: number; slop_closed: number; slop_ungrounded: number;
  valid_dismissed: number; valid_dismissed_ids: string[]; valid_closed?: number; agreement: number; cost_mean_usd: number;
  cost_total_usd: number; seconds_mean: number; seconds_p90: number;
  verdicts_slop: Partial<Record<Verdict, number>>; verdicts_valid: Partial<Record<Verdict, number>>;
};
type Row = { id: string; url: string; label: "slop" | "valid"; cve?: string; title: string; verdict: Verdict;
  confidence: number; cost_usd: number; seconds: number; contradictions: number; evidence: string[]; version?: string };

const CONFIG_LABEL: Record<string, string> = {
  deterministic: "Deterministic only (git + tree-sitter, $0)",
  full: "Full: routed Nemotron + Tavily",
  "no-grounding": "Ablation: no grounding",
  "single-model": "Ablation: Ultra for every role",
};
const ORDER: Verdict[] = ["UNGROUNDED", "DUPLICATE", "NEEDS_INFO", "REPRODUCED"];

function Stacked({ counts, total }: { counts: Partial<Record<Verdict, number>>; total: number }) {
  return (
    <div className={styles.stack}>
      {ORDER.map((v) => {
        const n = counts[v] ?? 0;
        if (!n) return null;
        return (
          <i key={v} style={{ width: `${(n / total) * 100}%`, background: VERDICT_META[v].color }}
            title={`${VERDICT_META[v].label}: ${n}`}><span>{n}</span></i>
        );
      })}
    </div>
  );
}

export default function BenchPage() {
  const [bench, setBench] = useState<{ configs: Record<string, Metrics>; rows: Row[]; rows_config: string; generated: string } | null>(null);
  const [filter, setFilter] = useState<"all" | "slop" | "valid">("all");
  useEffect(() => { loadBench().then(setBench).catch(() => {}); }, []);

  const configs = bench ? Object.entries(bench.configs) : [];
  const main = bench?.configs.full ?? bench?.configs.deterministic;
  const rows = useMemo(() => (bench?.rows ?? []).filter((r) => filter === "all" || r.label === filter), [bench, filter]);

  return (
    <main className={`container ${styles.page}`}>
      <p className="eyebrow">SlopBench</p>
      <h1 className={styles.h1}>Measured on curl&apos;s own public record, not on examples we wrote.</h1>
      <p className={styles.lead}>
        <b>Slop</b>: every report on the curl project&apos;s public list of AI slop submitted to its HackerOne
        program. <b>Valid</b>: every curl CVE whose advisory links the original HackerOne report. A report&apos;s
        own advisory, its own page and the public slop list are excluded from prior art, so ProofGate cannot look up
        the answer.
      </p>

      {!bench && <div className={`panel ${styles.empty}`}>Benchmark results are being generated.</div>}

      {main && (
        <div className={styles.kpis}>
          <div className="panel"><b>{Math.round(main.slop_closed * 100)}%</b><span>of known slop closed with evidence</span></div>
          <div className="panel"><b className={main.valid_dismissed ? styles.red : styles.green}>{main.valid_dismissed}</b><span>real CVEs wrongly dismissed (of {main.n_valid})</span></div>
          <div className="panel"><b>{Math.round(main.agreement * 100)}%</b><span>agreement with the curl team&apos;s outcome</span></div>
          <div className="panel"><b>${main.cost_mean_usd.toFixed(4)}</b><span>mean Token Factory cost per report</span></div>
          <div className="panel"><b>{main.seconds_mean.toFixed(1)}s</b><span>mean time per report (p90 {main.seconds_p90.toFixed(0)}s)</span></div>
        </div>
      )}

      {configs.length > 0 && (
        <section className={`panel ${styles.section}`}>
          <h2>Verdicts by class and configuration</h2>
          <div className={styles.legend}>
            {ORDER.map((v) => <span key={v}><i style={{ background: VERDICT_META[v].color }} />{VERDICT_META[v].label}</span>)}
          </div>
          {configs.map(([name, m]) => (
            <div key={name} className={styles.cfg}>
              <div className={styles.cfgName}>{CONFIG_LABEL[name] ?? name}</div>
              <div className={styles.cfgRow}><span>slop · {m.n_slop}</span><Stacked counts={m.verdicts_slop} total={m.n_slop} /></div>
              <div className={styles.cfgRow}><span>valid · {m.n_valid}</span><Stacked counts={m.verdicts_valid} total={m.n_valid} /></div>
            </div>
          ))}
          <table className={styles.table}>
            <thead><tr><th>Configuration</th><th>Slop closed</th><th>Valid dismissed</th><th>Valid closed as dup</th><th>Agreement</th><th>$ / report</th><th>s / report</th></tr></thead>
            <tbody>
              {configs.map(([name, m]) => (
                <tr key={name}>
                  <td>{CONFIG_LABEL[name] ?? name}</td>
                  <td>{(m.slop_closed * 100).toFixed(1)}%</td>
                  <td className={m.valid_dismissed ? styles.red : styles.green}>{m.valid_dismissed}</td>
                  <td>{(m.valid_closed ?? m.valid_dismissed) - m.valid_dismissed}</td>
                  <td>{(m.agreement * 100).toFixed(1)}%</td>
                  <td>${m.cost_mean_usd.toFixed(4)}</td>
                  <td>{m.seconds_mean.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {bench?.rows?.length ? (
        <section className={`panel ${styles.section}`}>
          <div className={styles.rowsHead}>
            <h2>Every report ({CONFIG_LABEL[bench.rows_config] ?? bench.rows_config})</h2>
            <div className={styles.filters}>
              {(["all", "slop", "valid"] as const).map((f) => (
                <button key={f} className={filter === f ? styles.on : ""} onClick={() => setFilter(f)}>{f}</button>
              ))}
            </div>
          </div>
          <div className={styles.rows}>
            {rows.map((r) => (
              <a key={r.id} href={r.url} target="_blank" rel="noreferrer" className={styles.row}>
                <span className={`chip ${r.label === "slop" ? "" : "blue"}`}>{r.label === "slop" ? "slop" : r.cve}</span>
                <span className={styles.title}>{r.title}</span>
                <span className={`chip ${VERDICT_META[r.verdict]?.css}`}>{VERDICT_META[r.verdict]?.label}</span>
                <span className={styles.ev}>{r.evidence[0] ?? ""}</span>
              </a>
            ))}
          </div>
          <p className={styles.note}>Generated {bench.generated}. Reproduce with <code>proofgate bench run --config full</code>.</p>
        </section>
      ) : null}
    </main>
  );
}
