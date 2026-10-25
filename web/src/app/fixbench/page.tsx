"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { loadFixBench } from "@/lib/api";
import type { FbRow, FbStep, FixBench } from "@/lib/types";
import styles from "./fixbench.module.css";

const ROLE_LABEL: Record<string, string> = {
  nano: "Nemotron 3 Nano 30B",
  super: "Nemotron 3 Super 120B",
  ultra: "Nemotron 3 Ultra 550B",
};
const TOOL_CSS: Record<string, string> = {
  grep: "", ls: "", read: "", outline: "", function: "", edit: "amber", run_tests: "blue", reproduce: "red",
  finish: "green", none: "",
};
const TOOL_LABEL: Record<string, string> = { run_tests: "build + test", reproduce: "reproduce", none: "thinking" };

function DiffView({ diff, empty }: { diff: string; empty: string }) {
  if (!diff.trim()) return <div className={styles.none}>{empty}</div>;
  return (
    <pre className={styles.diff}>
      {diff.split("\n").map((l, i) => {
        const cls = l.startsWith("+++") || l.startsWith("---") || l.startsWith("diff ") || l.startsWith("index ")
          ? styles.dh : l.startsWith("@@") ? styles.dhunk : l.startsWith("+") ? styles.dadd : l.startsWith("-") ? styles.ddel : "";
        return <div key={i} className={cls}>{l || " "}</div>;
      })}
    </pre>
  );
}

function argLine(s: FbStep) {
  const a = s.args ?? {};
  if (s.tool === "grep") return `${a.pattern ?? ""}  in ${a.path ?? "lib/"}`;
  if (s.tool === "read") return `${a.file ?? a.path ?? ""}:${a.start ?? 1}-${a.end ?? ""}`;
  if (s.tool === "edit") return a.file ?? a.path ?? "";
  if (s.tool === "function") return a.name ?? "";
  if (s.tool === "outline" || s.tool === "ls") return a.file ?? a.path ?? "";
  if (s.tool === "finish") return (a.summary ?? "").slice(0, 140);
  if (s.tool === "reproduce") return "regression test on the vulnerable build";
  if (s.tool === "run_tests") return s.observation.split("\n")[0];
  return "";
}

function testState(s: FbStep): "pass" | "fail" | null {
  if (s.tool === "reproduce") return "fail";
  if (s.tool !== "run_tests") return null;
  return s.observation.startsWith("ALL TESTS PASS") ? "pass" : s.observation.startsWith("FAILING") ? "fail" : null;
}

function Transcript({ row }: { row: FbRow }) {
  const [shown, setShown] = useState(row.steps.length);
  const [open, setOpen] = useState<number | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => { setShown(row.steps.length); setOpen(null); return () => { if (timer.current) clearInterval(timer.current); }; }, [row]);
  const play = () => {
    if (timer.current) clearInterval(timer.current);
    setShown(0);
    timer.current = setInterval(() => {
      setShown((n) => {
        if (n >= row.steps.length) { if (timer.current) clearInterval(timer.current); return n; }
        return n + 1;
      });
    }, 420);
  };
  return (
    <div>
      <div className={styles.tHead}>
        <h3>Agent transcript · {row.turns} replies · {row.tests_run} sandbox test run{row.tests_run === 1 ? "" : "s"}</h3>
        <button className="btn" onClick={play}>Replay</button>
      </div>
      <ol className={styles.steps}>
        <AnimatePresence initial={false}>
          {row.steps.slice(0, shown).map((s, i) => {
            const st = testState(s);
            return (
              <motion.li key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.25 }}
                className={`${styles.step} ${st === "pass" ? styles.pass : st === "fail" ? styles.fail : ""}`}>
                <button className={styles.stepHead} onClick={() => setOpen(open === i ? null : i)}>
                  <span className={styles.turn}>{String(s.turn).padStart(2, "0")}</span>
                  <span className={`chip ${st === "pass" ? "green" : st === "fail" ? "red" : TOOL_CSS[s.tool] ?? ""}`}>{TOOL_LABEL[s.tool] ?? s.tool}</span>
                  <span className={styles.arg}>{argLine(s)}</span>
                  <span className={styles.t}>{s.t.toFixed(0)}s</span>
                </button>
                {s.thought && <p className={styles.thought}>{s.thought}</p>}
                {(open === i || st) && <pre className={styles.obs}>{s.observation}</pre>}
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ol>
    </div>
  );
}

function Detail({ row }: { row: FbRow }) {
  return (
    <motion.section key={row.id + row.role} className={`panel ${styles.detail}`} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
      <header className={styles.dHead}>
        <div>
          <div className={styles.dMeta}>
            <span className={`chip ${row.resolved ? "green" : "red"}`}><span className="dot" />{row.resolved ? "fixed: curl's tests pass" : "not fixed"}</span>
            {row.resolved && row.style_problems && (
              <span className={`chip ${row.style_problems.length ? "amber" : "green"}`}
                title={row.style_problems.slice(0, 5).join("\n")}>
                {row.style_problems.length ? `checksrc: ${row.style_problems.length} style notes` : "checksrc clean"}
              </span>
            )}
            <span className="mono">{row.id}</span>
            {row.severity && <span className={styles.dim}>{row.severity} severity</span>}
            <span className={styles.dim}>published {row.published}</span>
          </div>
          <h2>{row.summary}</h2>
          <div className={styles.links}>
            {row.advisory_url && <a href={row.advisory_url} target="_blank" rel="noreferrer">advisory ↗</a>}
            <a href={`https://github.com/curl/curl/commit/${row.fix_commit}`} target="_blank" rel="noreferrer">curl&apos;s fix ↗</a>
            <a href={`https://github.com/curl/curl/tree/${row.base}`} target="_blank" rel="noreferrer">vulnerable tree {row.base.slice(0, 10)} ↗</a>
          </div>
        </div>
        <div className={styles.dStats}>
          <div><b>{row.f2p_passed ? "pass" : "fail"}</b><span>regression test{row.fail_to_pass.length > 1 ? "s" : ""} {row.fail_to_pass.map((t) => `test${t}`).join(", ")}</span></div>
          <div><b>{row.p2p_broken.length ? `${row.p2p_broken.length} broke` : `${row.pass_to_pass} ok`}</b><span>nearby tests still passing</span></div>
          <div><b>${row.cost_usd.toFixed(3)}</b><span>{row.tokens.toLocaleString()} tokens on Token Factory</span></div>
          <div><b>{(row.seconds / 60).toFixed(1)} min</b><span>wall time, builds included</span></div>
        </div>
      </header>
      <div className={styles.dGrid}>
        <Transcript row={row} />
        <div>
          <h3>Patch written by {ROLE_LABEL[row.role] ?? row.model}</h3>
          <DiffView diff={row.diff} empty="The agent did not produce a patch." />
          {row.summary_agent && <p className={styles.agentSum}>{row.summary_agent}</p>}
          <h3>The curl maintainers&apos; fix (never shown to the agent)</h3>
          <DiffView diff={row.gold_diff} empty="" />
        </div>
      </div>
    </motion.section>
  );
}

export default function FixBenchPage() {
  const [fb, setFb] = useState<FixBench | null>(null);
  const [role, setRole] = useState<string>("super");
  const [sel, setSel] = useState<string | null>(null);
  useEffect(() => { loadFixBench().then((d) => { setFb(d); if (d && !d.models.super) setRole(Object.keys(d.models)[0] ?? "super"); }).catch(() => {}); }, []);

  const model = fb?.models[role];
  const m = model?.metrics;
  const rows = useMemo(() => model?.rows ?? [], [model]);
  const current = rows.find((r) => r.id === sel) ?? rows.find((r) => r.resolved) ?? rows[0];
  const dropped = (fb?.instances ?? []).filter((i) => i.validated === false);

  return (
    <main className={`container ${styles.page}`}>
      <p className="eyebrow">FixBench</p>
      <h1 className={styles.h1}>An open model fixing real curl security bugs, with curl&apos;s own test suite as the judge.</h1>
      <p className={styles.lead}>
        Every instance is a <b>published curl CVE</b> whose fix commit added a regression test. The agent gets the public
        advisory and the vulnerable checkout. It reads the code, edits it, and <b>builds curl and runs the tests itself</b> in a
        network-less sandbox, then iterates. It never sees the maintainers&apos; fix. A CVE counts as fixed only if a fresh build
        of the final patch passes the regression test <b>and</b> every nearby test that passed before. Every model call runs on
        Nebius Token Factory.
      </p>

      <div className={styles.flow}>
        {[
          ["Advisory", "public CVE text, fenced as untrusted"],
          ["Reproduce", "the regression test fails on the vulnerable build"],
          ["Explore", "grep · ls · read · tree-sitter functions"],
          ["Edit", "SEARCH/REPLACE on lib/ src/ include/"],
          ["Build + test", "Docker, --network none, curl's runtests.pl"],
          ["Grade", "fresh build: regression + nearby tests"],
        ].map(([a, b], i) => (
          <div key={a} className={styles.flowStep}><i>{i + 1}</i><b>{a}</b><span>{b}</span></div>
        ))}
      </div>

      {!fb && <div className={`panel ${styles.empty}`}>FixBench results are being generated.</div>}

      {fb && (
        <div className={styles.tabs}>
          {Object.keys(fb.models).map((r) => (
            <button key={r} className={r === role ? styles.on : ""} onClick={() => { setRole(r); setSel(null); }}>{ROLE_LABEL[r] ?? r}</button>
          ))}
        </div>
      )}

      {m && (
        <div className={styles.kpis}>
          <div className="panel"><b className={styles.green}>{m.resolved}<small>/{m.n}</small></b><span>real CVEs fixed, verified by curl&apos;s tests</span></div>
          <div className="panel"><b>{m.post_cutoff.resolved}<small>/{m.post_cutoff.n}</small></b><span>fixed CVEs whose fix landed after Feb 2026, past Nemotron 3 Super&apos;s training data</span></div>
          <div className="panel"><b>{m.cost_per_resolved_usd != null ? `$${m.cost_per_resolved_usd.toFixed(3)}` : "n/a"}</b><span>Token Factory cost per verified fix</span></div>
          <div className="panel"><b>{Math.round(m.localized * 100)}%</b><span>edited the same file as the maintainers</span></div>
          <div className="panel"><b className={m.broke_other_tests ? styles.red : ""}>{m.broke_other_tests}</b><span>fixes that broke another test</span></div>
        </div>
      )}

      {fb && Object.keys(fb.models).length > 1 && (
        <section className={`panel ${styles.section}`}>
          <h2>Same agent, three Nemotron sizes</h2>
          <table className={styles.table}>
            <thead><tr><th>Model</th><th>Fixed</th><th>Style-clean fixes</th><th>Right file</th><th>Passed on 1st test run</th><th>$ / CVE</th><th>$ / fix</th><th>Replies</th><th>Test runs</th></tr></thead>
            <tbody>
              {Object.entries(fb.models).map(([r, d]) => (
                <tr key={r}>
                  <td>{ROLE_LABEL[r] ?? r}<div className={styles.mid}>{d.model}</div></td>
                  <td><b>{d.metrics.resolved}</b> / {d.metrics.n}</td>
                  <td>{d.metrics.style_clean ?? "n/a"}</td>
                  <td>{Math.round(d.metrics.localized * 100)}%</td>
                  <td>{d.metrics.first_try}</td>
                  <td>${d.metrics.cost_mean_usd.toFixed(3)}</td>
                  <td>{d.metrics.cost_per_resolved_usd != null ? `$${d.metrics.cost_per_resolved_usd.toFixed(3)}` : "n/a"}</td>
                  <td>{d.metrics.turns_mean}</td>
                  <td>{d.metrics.tests_mean}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {rows.length > 0 && (
        <section className={styles.grid}>
          {rows.map((r) => (
            <button key={r.id} onClick={() => setSel(r.id)}
              className={`${styles.tile} ${r.resolved ? styles.tOk : styles.tNo} ${current?.id === r.id ? styles.tSel : ""}`}>
              <span className={styles.tId}>{r.id}</span>
              <span className={styles.tSum}>{r.summary}</span>
              <span className={styles.tFoot}>
                <span>{r.resolved ? "fixed" : r.f2p_passed ? "broke a test" : r.build_ok ? "test still fails" : "no build"}</span>
                <span>{r.tests_run} runs · ${r.cost_usd.toFixed(3)}</span>
              </span>
            </button>
          ))}
        </section>
      )}

      {current && <Detail row={current} />}

      {dropped.length > 0 && (
        <section className={`panel ${styles.section}`}>
          <h2>Instances left out, and why</h2>
          <p className={styles.note} style={{ marginTop: 0 }}>
            An instance is kept only if its regression test fails on the vulnerable commit and passes with the maintainers&apos;
            fix in our sandbox build. Everything else is listed here rather than silently dropped.
          </p>
          <div className={styles.dropped}>
            {dropped.map((d) => (
              <div key={d.id}><span className="mono">{d.id}</span><span>{d.summary}</span><span className={styles.dim}>{d.why}</span></div>
            ))}
          </div>
        </section>
      )}

      {model && <p className={styles.note}>Generated {model.generated}. Reproduce: <code>proofgate fixbench validate</code> then <code>proofgate fixbench run --model {role}</code>.</p>}
    </main>
  );
}
