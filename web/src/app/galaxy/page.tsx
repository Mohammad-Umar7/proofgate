"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { Guard3D } from "@/components/Guard3D";
import { LoadError, Loading } from "@/components/Status";
import { loadGraph } from "@/lib/api";
import { nearNames, pathFromEntry } from "@/lib/graph";
import type { GraphData } from "@/lib/types";
import type { GalaxyFocus } from "@/three/galaxy/Galaxy";
import { LEGEND } from "@/three/galaxy/palette";
import styles from "./galaxy.module.css";

const Galaxy = dynamic(() => import("@/three/galaxy/Galaxy"), {
  ssr: false, loading: () => <Loading label="Starting the 3D view…" fill />,
});

const PRESETS = [
  { q: "Curl_cookie_add", note: "real · reached via curl_easy_setopt" },
  { q: "socks5_connect", note: "real · reached via a dispatch table" },
  { q: "do_SOCKS5", note: "real in 8.5.0 · gone since a rework" },
  { q: "Curl_cookie_parse_header", note: "hallucinated" },
  { q: "Curl_http2_stream_reset_internal", note: "hallucinated" },
];
const FIRST_GHOST = PRESETS.find((p) => p.note === "hallucinated")?.q;

export default function GalaxyPage() {
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [query, setQuery] = useState("");
  const [focus, setFocus] = useState<GalaxyFocus>({});
  const [result, setResult] = useState<{ kind: "real" | "ghost"; text: string } | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => { loadGraph().then(setGraph).catch(() => setFailed(true)); }, []);

  // on wide screens the panel floats over the canvas: tell the galaxy how much it covers, so it
  // frames itself in the space beside the panel instead of underneath it
  const side = useRef<HTMLElement>(null);
  const canvas = useRef<HTMLDivElement>(null);
  const [inset, setInset] = useState(0);
  useEffect(() => {
    const measure = () => {
      const a = side.current?.getBoundingClientRect(), c = canvas.current?.getBoundingClientRect();
      if (!a || !c) return;
      const beside = a.right < c.left + c.width * 0.6 && a.bottom > c.top + c.height * 0.4;
      setInset(beside ? Math.round(a.right - c.left + 24) : 0);
    };
    measure();
    const ro = new ResizeObserver(measure);
    if (side.current) ro.observe(side.current);
    if (canvas.current) ro.observe(canvas.current);
    return () => ro.disconnect();
  }, []);

  const stats = useMemo(() => graph && {
    fns: graph.nodes.length, edges: graph.edges.length, files: graph.files.length, version: graph.version,
  }, [graph]);

  function look(name: string) {
    if (!graph) return;
    const q = name.trim().replace(/\(\)$/, "");
    setQuery(q);
    if (!q) { setFocus({}); setResult(null); return; }
    const node = graph.nodes.find((n) => n.name === q);
    if (node) {
      const chain = pathFromEntry(graph, q);
      setFocus({ path: chain?.filter((n) => !n.startsWith("table:")), target: q });
      const via = chain?.[0]?.startsWith("table:") ? `dispatch table ${chain[0].slice(6)}` : chain?.[0];
      setResult({
        kind: "real",
        text: `${q}() is defined at ${node.file}:${node.line}` +
          (chain ? ` · reachable from ${via} in ${chain.length - 1} call${chain.length > 2 ? "s" : ""}` : " · no caller path from a public entry point found"),
      });
    } else {
      const near = nearNames(graph, q);
      setFocus({ ghosts: [{ name: q, near, note: `not in curl ${graph.version}` }] });
      setResult({
        kind: "ghost",
        text: `No function named ${q}() exists in curl ${graph.version}. ProofGate also searches every ` +
          "commit in history, so a function that was renamed or removed is reported as such, not as invented.",
      });
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.canvas} ref={canvas}>
        {graph ? (
          <Guard3D what="code galaxy" className={styles.beside}>
            <Galaxy graph={graph} focus={focus} insetLeft={inset} />
          </Guard3D>
        ) : failed ? <LoadError what="The code galaxy" fill style={{ left: inset }} />
          : <Loading label="Loading every function in curl…" fill style={{ left: inset }} />}
      </div>
      <aside className={`panel ${styles.side}`} ref={side}>
        <p className="eyebrow">Code galaxy · curl {stats?.version ?? "…"}</p>
        <h1 className={styles.h1}>Every function in curl, every call between them.</h1>
        <p className={styles.p}>
          Parsed with tree-sitter from the real source. When a report names a function, ProofGate looks for it here
          and in all of git history. Real functions light up with their call path from a public entry point.
          Invented ones float outside the galaxy, connected to nothing.
        </p>
        {stats && (
          <div className={styles.stats}>
            <div><b>{stats.fns.toLocaleString()}</b><span>functions</span></div>
            <div><b>{stats.edges.toLocaleString()}</b><span>call edges</span></div>
            <div><b>{stats.files}</b><span>source files</span></div>
          </div>
        )}
        <div data-tour="galaxy-presets">
        <form onSubmit={(e) => { e.preventDefault(); look(query); }} className={styles.search}>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Type a function name…"
            spellCheck={false} aria-label="Function name" />
          <button className="btn btn-primary" type="submit">Find</button>
        </form>
        <div className={styles.presets}>
          {PRESETS.map((p) => (
            <button key={p.q} onClick={() => look(p.q)} className={styles.preset}
              data-tour={p.q === FIRST_GHOST ? "galaxy-ghost" : undefined}>
              <code>{p.q}()</code><span>{p.note}</span>
            </button>
          ))}
        </div>
        </div>
        {result && (
          <div className={`${styles.result} ${result.kind === "ghost" ? styles.ghost : styles.real}`}>{result.text}</div>
        )}
        <div className={styles.legend}>
          {LEGEND.map((l) => <span key={l.label}><i style={{ background: l.color }} />{l.label}</span>)}
        </div>
      </aside>
    </main>
  );
}
