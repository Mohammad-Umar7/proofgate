"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { API, health, loadFixBench, loadFixBenchDetail, stream, submitFix } from "@/lib/api";
import type { FbDetail, FbRow, FbStep, FixBench, FixEvent } from "@/lib/types";
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

/** A live agent run streamed from the engine (POST /api/fix): same shape as a recorded row. */
interface LiveFix {
  cve: string; role: string; model: string; started: number; ended?: number;
  steps: FbStep[]; status: string; result?: FbRow; error?: string; done: boolean;
}

function advance(l: LiveFix, e: FixEvent): LiveFix {
  const now = Date.now() / 1000;
  switch (e.kind) {
    case "start": return { ...l, model: e.model, started: e.started };
    case "status": return { ...l, status: e.text };
    case "step": return { ...l, steps: [...l.steps, e.step] };
    case "result": return { ...l, result: e.row, done: true, ended: now };
    case "error": return { ...l, error: e.error, done: true, ended: now };
  }
}

function LiveBar({ live }: { live: LiveFix }) {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    if (live.done) return;
    const id = setInterval(() => setNow(Date.now() / 1000), 250);
    return () => clearInterval(id);
  }, [live.done]);
  const secs = Math.max(0, (live.ended ?? now) - live.started);
  const cost = live.result?.cost_usd ?? live.steps.reduce((a, s) => a + (s.cost_usd || 0), 0);
  const state = live.error ? "red" : !live.done ? "blue" : live.result?.resolved ? "green" : "red";
  return (
    <div className={styles.liveBar}>
      <span className={`chip ${state} ${live.done ? "" : styles.pulse}`}><span className="dot" />
        {live.error ? "live run failed" : !live.done ? "LIVE" : live.result?.resolved ? "live run: fixed" : "live run: not fixed"}
      </span>
      <span className="mono">{live.model || "…"}</span>
      <span className={styles.dim}>started {new Date(live.started * 1000).toLocaleTimeString()}</span>
      <b className="mono">{Math.floor(secs / 60)}:{String(Math.floor(secs % 60)).padStart(2, "0")}</b>
      <b className="mono">${cost.toFixed(4)}</b>
      <span className={styles.liveStatus}>{live.error ?? (live.done ? "Graded on a fresh build of the final patch." : live.status)}</span>
    </div>
  );
}

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
  if (s.observation.startsWith("ALL TESTS PASS")) return "pass";
  return /^(FAILING|BUILD FAILED|PATCH DID NOT APPLY|SANDBOX ERROR)/.test(s.observation) ? "fail" : null;
}

/** Per-test results parsed from a sandbox run's first line: "Build OK. test1629 ok, test61 ok, ..." */
function testStatuses(obs: string | undefined): [string, string][] {
  if (!obs) return [];
  const head = obs.split("\n").find((l) => l.startsWith("Build OK.")) ?? "";
  return [...head.matchAll(/test(\d+) (ok|fail|skip|missing)/g)].map((m) => [m[1], m[2]]);
}

function TestLights({ row }: { row: FbRow }) {
  const before = testStatuses(row.steps.find((s) => s.tool === "reproduce")?.observation);
  const runs = row.steps.filter((s) => s.tool === "run_tests" && s.observation.includes("Build OK."));
  const after = testStatuses(runs[runs.length - 1]?.observation);
  if (!before.length && !after.length) return null;
  const own = new Set(row.fail_to_pass);
  const line = (label: string, items: [string, string][]) => (
    <div className={styles.lightRow}>
      <span>{label}</span>
      <div className={styles.lights}>
        {items.map(([t, s]) => (
          <i key={t} title={`test${t}: ${s}`}
            className={`${s === "ok" ? styles.lOk : s === "fail" ? styles.lFail : styles.lOff} ${own.has(t) ? styles.lOwn : ""}`} />
        ))}
      </div>
    </div>
  );
  return (
    <div className={styles.testLights}>
      {line("vulnerable build", before)}
      {after.length > 0 && line("after the agent's last test run", after)}
      <p>Larger lights are curl&apos;s regression test{row.fail_to_pass.length > 1 ? "s" : ""} for this CVE; the rest are nearby tests that must keep passing.</p>
    </div>
  );
}

function Transcript({ row, live }: { row: FbRow; live: boolean }) {
  const [shown, setShown] = useState(row.steps.length);
  const [open, setOpen] = useState<number | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const list = useRef<HTMLOListElement>(null);
  useEffect(() => { setShown(row.steps.length); if (!live) setOpen(null); return () => { if (timer.current) clearInterval(timer.current); }; }, [row, live]);
  useEffect(() => {
    if (live && list.current) list.current.scrollTo({ top: list.current.scrollHeight, behavior: "smooth" });
  }, [live, row.steps.length]);
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
        {!live && <button className="btn" onClick={play}>Replay</button>}
      </div>
      {row.steps.length === 0 && <div className={styles.none}>{live ? "Reproducing the bug first: the regression test runs on the vulnerable build…" : "Loading the transcript…"}</div>}
      <ol className={styles.steps} ref={list}>
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
                {(open === i || st || (live && s.tool === "edit")) && <pre className={styles.obs}>{s.observation}</pre>}
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ol>
    </div>
  );
}

function Detail({ row, live, onRun }: { row: FbRow; live: LiveFix | null; onRun?: () => void }) {
  const pending = live !== null && !live.done;
  return (
    <motion.section key={row.id + row.role} className={`panel ${styles.detail}`} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
      {live && <LiveBar live={live} />}
      <header className={styles.dHead}>
        <div>
          <div className={styles.dMeta}>
            {pending ? <span className="chip blue"><span className="dot" />agent working</span> : (
              <span className={`chip ${row.resolved ? "green" : "red"}`}><span className="dot" />{row.resolved ? "fixed: curl's tests pass" : "not fixed"}</span>
            )}
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
          {onRun && (
            <button className={`btn btn-primary ${styles.runLive}`} onClick={onRun} disabled={pending}>
              {pending ? "Running live…" : `Run live now: ${ROLE_LABEL[row.role] ?? row.role}`}
            </button>
          )}
        </div>
        <div className={styles.dStats}>
          <div><b>{pending ? "…" : row.f2p_passed ? "pass" : "fail"}</b><span>regression test{row.fail_to_pass.length > 1 ? "s" : ""} {row.fail_to_pass.map((t) => `test${t}`).join(", ")}</span></div>
          <div><b>{pending ? "…" : row.p2p_broken.length ? `${row.p2p_broken.length} broke` : `${row.pass_to_pass} ok`}</b><span>nearby tests still passing</span></div>
          <div><b>${row.cost_usd.toFixed(pending ? 4 : 3)}</b><span>{pending ? "spent so far" : `${row.tokens.toLocaleString()} tokens`} on Token Factory</span></div>
          <div><b>{pending ? `${row.turns} / 40` : `${(row.seconds / 60).toFixed(1)} min`}</b><span>{pending ? "model replies so far" : "wall time, builds included"}</span></div>
        </div>
      </header>
      <TestLights row={row} />
      <div className={styles.dGrid}>
        <Transcript row={row} live={live !== null} />
        <div>
          <h3>Patch written by {ROLE_LABEL[row.role] ?? row.model}</h3>
          <DiffView diff={row.diff} empty={pending ? "The final patch appears here when the agent finishes; its edits show in the transcript as they happen." : "The agent did not produce a patch."} />
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
  const [role, setRole] = useState<string>("ultra");
  const [sel, setSel] = useState<string | null>(null);
  const [details, setDetails] = useState<Record<string, FbDetail>>({});
  const [engine, setEngine] = useState<Record<string, unknown> | null>(null);
  const [live, setLive] = useState<LiveFix | null>(null);
  const stopLive = useRef<() => void>(() => {});
  useEffect(() => { health().then(setEngine); return () => stopLive.current(); }, []);
  useEffect(() => {
    loadFixBench().then((d) => {
      setFb(d);
      // open on the model that fixed the most CVEs
      const best = d ? Object.entries(d.models).sort((a, b) => b[1].metrics.resolved - a[1].metrics.resolved)[0] : null;
      if (best) setRole(best[0]);
    }).catch(() => {});
  }, []);
  useEffect(() => {
    if (!fb?.models[role] || details[role]) return;
    loadFixBenchDetail(role).then((d) => { if (d) setDetails((prev) => ({ ...prev, [role]: d })); }).catch(() => {});
  }, [fb, role, details]);

  const model = fb?.models[role];
  const m = model?.metrics;
  const rows = useMemo(() => {
    const byId = new Map((details[role]?.rows ?? []).map((r) => [r.id, r]));
    return (model?.rows ?? []).map((r): FbRow => {
      const d = byId.get(r.id);
      return { ...r, steps: d?.steps ?? [], diff: d?.diff ?? "", gold_diff: d?.gold_diff ?? "", summary_agent: d?.summary_agent ?? "" };
    });
  }, [model, details, role]);
  const cascade = fb?.cascade;
  const current = rows.find((r) => r.id === sel) ?? rows.find((r) => r.resolved) ?? rows[0];
  const canRun = Boolean(API && engine?.token_factory && engine?.sandbox_ready);
  const liveHere = live && current && live.cve === current.id && live.role === role ? live : null;
  const shown: FbRow | undefined = !current || !liveHere ? current : liveHere.result ?? {
    ...current, model: liveHere.model || current.model, resolved: false, f2p_passed: false, p2p_broken: [],
    build_ok: false, style_problems: undefined, first_test_passed: null, stop: "", tokens: 0, seconds: 0,
    tests_run: liveHere.steps.filter((s) => s.tool === "run_tests").length,
    turns: liveHere.steps.reduce((a, s) => Math.max(a, s.turn), 0),
    cost_usd: liveHere.steps.reduce((a, s) => a + (s.cost_usd || 0), 0),
    files_edited: [], diff: "", summary_agent: "", steps: liveHere.steps,
  };

  async function runLive(row: FbRow) {
    stopLive.current();
    const base: LiveFix = { cve: row.id, role, model: "", started: Date.now() / 1000, steps: [], status: "Starting the run…", done: false };
    setLive(base);
    try {
      const id = await submitFix(row.id, role);
      stopLive.current = stream<FixEvent>(id, (e) => setLive((l) => (l ? advance(l, e) : l)),
        () => setLive((l) => (l && !l.done ? { ...l, done: true, ended: Date.now() / 1000, error: "the stream closed before a result" } : l)));
    } catch (e) {
      setLive({ ...base, error: String((e as Error).message), done: true, ended: Date.now() / 1000 });
    }
  }
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
          <div className="panel"><b>{m.post_cutoff.resolved}<small>/{m.post_cutoff.n}</small></b><span>of the CVEs fixed upstream after Feb 2026, past Nemotron 3 Super&apos;s documented training data</span></div>
          <div className="panel"><b>{m.cost_per_resolved_usd != null ? `$${m.cost_per_resolved_usd.toFixed(3)}` : "n/a"}</b><span>Token Factory cost per verified fix</span></div>
          <div className="panel"><b>{Math.round(m.localized * 100)}%</b><span>edited the same file as the maintainers</span></div>
          <div className="panel"><b className={m.broke_other_tests ? styles.red : ""}>{m.broke_other_tests}</b><span>fixes that broke another test</span></div>
        </div>
      )}

      {cascade && (
        <section className={`panel ${styles.section} ${styles.cascade}`}>
          <div>
            <p className="eyebrow">Route by job</p>
            <h2>Super first, Ultra only when Super fails: <span className={styles.green}>{cascade.resolved} of {cascade.n}</span> fixed</h2>
            <p className={styles.note} style={{ marginTop: 0 }}>
              The two models fix different CVEs. Running Nemotron 3 Super on every CVE and sending only its {cascade.escalated} failures
              to Nemotron 3 Ultra fixes {cascade.resolved} ({Math.round(cascade.resolved_rate * 100)}%) for
              ${cascade.cost_total_usd.toFixed(2)} in total, {cascade.cost_per_resolved_usd != null ? `$${cascade.cost_per_resolved_usd.toFixed(2)}` : "n/a"} per
              verified fix. Computed from the two full runs above; no extra calls.
            </p>
          </div>
          <div className={styles.cascadeK}>
            <div><b>{Object.values(cascade.fixed_by).filter((v) => v === "both").length}</b><span>fixed by both</span></div>
            <div><b>{Object.values(cascade.fixed_by).filter((v) => v === cascade.roles[0]).length}</b><span>only Super</span></div>
            <div><b>{Object.values(cascade.fixed_by).filter((v) => v === cascade.roles[1]).length}</b><span>only Ultra</span></div>
          </div>
        </section>
      )}

      {fb && Object.keys(fb.models).length > 1 && (
        <section className={`panel ${styles.section}`}>
          <h2>Same agent, {Object.keys(fb.models).length} Nemotron sizes</h2>
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
                <span>{r.resolved ? "fixed" : !r.files_edited.length ? "no patch" : r.f2p_passed ? "broke a test"
                  : r.build_ok ? "test still fails" : "does not build"}</span>
                <span>{r.tests_run} runs · ${r.cost_usd.toFixed(3)}</span>
              </span>
            </button>
          ))}
        </section>
      )}

      {shown && <Detail row={shown} live={liveHere} onRun={canRun && current ? () => runLive(current) : undefined} />}

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
