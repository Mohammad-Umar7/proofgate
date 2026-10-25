import type { Card, FbDetail, FixBench, GraphData, Replay, StageEvent } from "./types";

/** Live mode talks to a running engine; replay mode plays recorded real runs from /data. */
export const API = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
/** Static data path, aware of the deploy sub-path (e.g. GitHub Pages /proofgate). */
export const data = (name: string) => `${process.env.NEXT_PUBLIC_BASE_PATH || ""}/data/${name}`;

export async function health(): Promise<Record<string, unknown> | null> {
  if (!API) return null;
  try {
    const res = await fetch(`${API}/api/health`, { cache: "no-store" });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}

export async function loadReplays(): Promise<Replay[]> {
  const res = await fetch(data("replays.json"));
  return res.ok ? res.json() : [];
}

export async function loadGraph(): Promise<GraphData> {
  const res = await fetch(data("graph.json"));
  return res.json();
}

export async function loadBench(): Promise<any> {
  const res = await fetch(data("bench.json"));
  return res.ok ? res.json() : null;
}

export async function loadFixBench(): Promise<FixBench | null> {
  const res = await fetch(data("fixbench.json"));
  return res.ok ? res.json() : null;
}

export async function loadFixBenchDetail(role: string): Promise<FbDetail | null> {
  const res = await fetch(data(`fixbench-${role}.json`));
  return res.ok ? res.json() : null;
}

export async function loadHistory(): Promise<{ months: [string, number][]; total: number }> {
  const res = await fetch(data("history.json"));
  return res.json();
}

/** Submit a report: either title + body, or a disclosed HackerOne link the engine fetches itself. */
export async function submit(title: string, body: string, sourceUrl?: string): Promise<{ run_id: string; title: string }> {
  const res = await fetch(`${API}/api/runs`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ title, body, source_url: sourceUrl || null }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.json();
}

/** Start a live FixBench agent run (only accepted by an engine on this machine). */
export async function submitFix(cve: string, role: string): Promise<string> {
  const res = await fetch(`${API}/api/fix`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ cve, role }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return (await res.json()).run_id;
}

export function stream<T = StageEvent>(runId: string, onEvent: (e: T) => void, onEnd: () => void): () => void {
  const source = new EventSource(`${API}/api/runs/${runId}/events`);
  source.onmessage = (msg) => onEvent(JSON.parse(msg.data));
  source.addEventListener("end", () => {
    source.close();
    onEnd();
  });
  source.onerror = () => {
    source.close();
    onEnd();
  };
  return () => source.close();
}

export async function card(runId: string): Promise<Card> {
  const res = await fetch(`${API}/api/runs/${runId}`);
  return res.json();
}

/** Plays a recorded run with its real relative timing, compressed so a run takes ~speed x. */
export function replay(rec: Replay, onEvent: (e: StageEvent) => void, onEnd: () => void, speed = 1): () => void {
  const events = rec.events;
  if (!events.length) {
    onEnd();
    return () => {};
  }
  const t0 = events[0].t;
  const timers: number[] = [];
  events.forEach((e, i) => {
    const raw = (e.t - t0) * 1000;
    const delay = Math.min(raw, 600 + i * 260) / speed; // keep slow stages watchable
    timers.push(window.setTimeout(() => onEvent(e), delay));
  });
  const last = Math.min((events[events.length - 1].t - t0) * 1000, 600 + events.length * 260) / speed;
  timers.push(window.setTimeout(onEnd, last + 400));
  return () => timers.forEach((t) => clearTimeout(t));
}
