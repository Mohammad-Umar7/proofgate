"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import styles from "@/components/console/console.module.css";
import { EventLog } from "@/components/console/EventLog";
import { EvidenceCard } from "@/components/console/EvidenceCard";
import { StageList } from "@/components/console/StageList";
import { Guard3D } from "@/components/Guard3D";
import { LoadError, Loading } from "@/components/Status";
import { API, card as fetchCard, health, loadGraph, loadReplays, replay, stream, submit } from "@/lib/api";
import type { Card, GraphData, Replay, StageEvent } from "@/lib/types";
import type { GalaxyFocus } from "@/three/galaxy/Galaxy";

const Galaxy = dynamic(() => import("@/three/galaxy/Galaxy"), {
  ssr: false, loading: () => <Loading label="Starting the 3D view…" fill />,
});

function focusFrom(card: Card | null): GalaxyFocus {
  if (!card) return {};
  // a report can cite the same invented function several times: one ghost per name
  const ghosts = (card.ghosts ?? []).filter((g, i, all) => all.findIndex((x) => x.name === g.name) === i);
  if (ghosts.length) return { ghosts: ghosts.slice(0, 2).map((g) => ({ ...g, note: "never existed in curl" })) };
  const p = card.paths?.find((x) => x.chain?.length);
  if (p) return { path: p.chain.filter((n) => !n.startsWith("table:")), target: p.function };
  return {};
}

export default function ConsolePage() {
  const [replays, setReplays] = useState<Replay[]>([]);
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [live, setLive] = useState<Record<string, unknown> | null>(null);
  const [active, setActive] = useState<string | null>(null);
  const [events, setEvents] = useState<StageEvent[]>([]);
  const [card, setCard] = useState<Card | null>(null);
  const [focus, setFocus] = useState<GalaxyFocus>({});
  const [running, setRunning] = useState(false);
  const [draft, setDraft] = useState({ url: "", title: "", body: "" });
  const [liveTitle, setLiveTitle] = useState("");
  const [error, setError] = useState("");
  const [failed, setFailed] = useState({ replays: false, graph: false });
  const [now, setNow] = useState(0);
  const stop = useRef<() => void>(() => {});

  useEffect(() => {
    loadReplays().then((r) => { setReplays(r); if (r[0]) start(r[0]); })
      .catch(() => setFailed((f) => ({ ...f, replays: true })));
    loadGraph().then(setGraph).catch(() => setFailed((f) => ({ ...f, graph: true })));
    health().then(setLive);
    return () => stop.current();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => setNow(Date.now() / 1000), 100);
    return () => clearInterval(id);
  }, [running]);

  const start = useCallback((rec: Replay) => {
    stop.current();
    setActive(rec.id);
    setEvents([]);
    setCard(null);
    setFocus({});
    setRunning(true);
    setNow(Date.now() / 1000);
    stop.current = replay(rec, (e) => {
      setEvents((xs) => [...xs, { ...e, t: Date.now() / 1000 }]);
      if (e.stage === "grounding" && e.status === "done") setFocus(focusFrom(rec.card));
    }, () => { setCard(rec.card); setRunning(false); });
  }, []);

  async function runLive() {
    setError("");
    stop.current();
    setActive("live");
    setEvents([]);
    setCard(null);
    setFocus({});
    setRunning(true);
    setLiveTitle("");
    try {
      const pasted = draft.body.trim().length >= 20;
      const { run_id: id, title } = await submit(draft.title, pasted ? draft.body : "", pasted ? undefined : draft.url.trim());
      setLiveTitle(title);
      stop.current = stream(id, (e) => setEvents((xs) => [...xs, e]), async () => {
        const c = await fetchCard(id);
        setCard(c);
        setFocus(focusFrom(c));
        setRunning(false);
      });
    } catch (e) {
      setError(String((e as Error).message));
      setRunning(false);
    }
  }

  const rec = replays.find((r) => r.id === active);
  const t0 = events[0]?.t;
  const elapsed = t0 ? ((running ? now : events[events.length - 1].t) - t0) : 0;
  const cost = events.length ? events[events.length - 1].cost_usd : 0;
  const claims = useMemo(() => {
    const ev = events.find((e) => e.stage === "claims" && e.status === "done");
    return (ev?.data?.claims as { kind: string; text: string }[]) ?? [];
  }, [events]);
  const linkOk = /^https:\/\/hackerone\.com\/reports\/\d+\/?$/.test(draft.url.trim());
  const pasteOk = draft.title.trim().length >= 3 && draft.body.trim().length >= 20;
  const stagesDone = new Set(events.filter((e) => ["done", "skipped"].includes(e.status)).map((e) => e.stage)).size;

  return (
    <main className={`container ${styles.page}`}>
      <div className={styles.head}>
        <div>
          <p className="eyebrow">Triage console</p>
          <h1 className={styles.h1}>Watch a report get proven, claim by claim.</h1>
        </div>
        <div className={styles.mode}>
          <span className={`chip ${live ? "green" : ""}`}><span className="dot" />
            {live ? `Live · Token Factory ${live.token_factory ? "connected" : "off"}` : "Replay of recorded runs"}
          </span>
        </div>
      </div>

      <div className={styles.picker}>
        {API && (
          <button className={`${styles.pick} ${active === "live" ? styles.pickOn : ""}`} onClick={() => setActive("live")}>
            <span className={styles.pickLabel}>Live · your report</span>
            <b>Paste a link or a report and run the real pipeline</b>
          </button>
        )}
        {!replays.length && (failed.replays ? <LoadError what="The recorded runs" className={styles.pickerStatus} />
          : <Loading label="Loading recorded runs…" className={styles.pickerStatus} />)}
        {replays.map((r) => (
          <button key={r.id} className={`${styles.pick} ${active === r.id ? styles.pickOn : ""}`} onClick={() => start(r)}>
            <span className={styles.pickLabel}>{r.label}</span>
            <b>{r.report.title}</b>
          </button>
        ))}
      </div>

      <div className={styles.work}>
        <section className={`panel ${styles.col}`}>
          <p className={styles.colTitle}><span>Report</span><span>untrusted input</span></p>
          {active === "live" ? (
            <div className={styles.paste}>
              <input placeholder="Link to a disclosed HackerOne report" value={draft.url} spellCheck={false}
                aria-label="HackerOne report link" onChange={(e) => setDraft({ ...draft, url: e.target.value })} />
              <span className={styles.or}>or paste a report</span>
              <input placeholder="Title" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
              <textarea rows={liveTitle ? 3 : 9} placeholder="Report body (markdown)…" value={draft.body}
                onChange={(e) => setDraft({ ...draft, body: e.target.value })} />
              <button className="btn btn-primary" disabled={running || !(linkOk || pasteOk)} onClick={runLive}>
                {running ? "Running live…" : "Run ProofGate live"}
              </button>
              {error && <div className={styles.error}>{error}</div>}
              {liveTitle && (
                <>
                  <h2 className={styles.reportTitle}>{liveTitle}</h2>
                  {!pasteOk && linkOk && <p className={styles.galaxyNote}>Fetched live from {draft.url.trim().replace("https://", "")}</p>}
                  <div className={styles.claims}>
                    {claims.map((c, i) => <div key={i} className={styles.claimRow}><span>{c.kind}</span>{c.text}</div>)}
                  </div>
                </>
              )}
            </div>
          ) : rec ? (
            <>
              <h2 className={styles.reportTitle}>{rec.report.title}</h2>
              {rec.report.body ? <pre className={styles.reportBody}>{rec.report.body}</pre> : (
                <>
                  <a className="btn" href={rec.report.source_url ?? "#"} target="_blank" rel="noreferrer">Read the original on HackerOne ↗</a>
                  <p className={styles.galaxyNote}>Claims ProofGate extracted from it:</p>
                  <div className={styles.claims}>
                    {claims.map((c, i) => <div key={i} className={styles.claimRow}><span>{c.kind}</span>{c.text}</div>)}
                  </div>
                </>
              )}
            </>
          ) : null}
        </section>

        <section className={`panel ${styles.col}`}>
          <p className={styles.colTitle}><span>Pipeline</span><span>{stagesDone}/9 stages</span></p>
          <div className={styles.counters}>
            <div className={styles.counter}><b>{elapsed.toFixed(1)}s</b><span>elapsed</span></div>
            <div className={styles.counter}><b>${cost.toFixed(4)}</b><span>Token Factory spend</span></div>
            <div className={styles.counter}><b>{events.length}</b><span>events</span></div>
          </div>
          <StageList events={events} />
          <EventLog events={events} />
        </section>

        <section className={`panel ${styles.col}`}>
          <p className={styles.colTitle}><span>Code galaxy</span><span>curl {graph?.version}</span></p>
          <div className={styles.galaxy}>
            {graph ? <Guard3D what="code galaxy"><Galaxy graph={graph} focus={focus} autoRotate compact /></Guard3D>
              : failed.graph ? <LoadError what="The code galaxy" fill /> : <Loading label="Loading curl's functions…" fill />}
          </div>
          <p className={styles.galaxyNote}>
            {focus.ghosts?.length ? `${focus.ghosts.length} cited function(s) do not exist: shown adrift, connected to nothing.`
              : focus.path?.length ? "Reachable path from a public entry point to the cited function."
                : "Lights up once grounding finishes."}
          </p>
        </section>
      </div>

      {card && <EvidenceCard card={card} />}
    </main>
  );
}
