export type Verdict = "UNGROUNDED" | "DUPLICATE" | "NEEDS_INFO" | "REPRODUCED";
export type Stage =
  | "intake" | "claims" | "grounding" | "prior_art" | "rules"
  | "repro" | "adjudicate" | "fix" | "card";

export const STAGES: { id: Stage; label: string; model?: string; what: string }[] = [
  { id: "intake", label: "Intake", model: "Nemotron Nano Omni", what: "Reads text, screenshots and terminal captures" },
  { id: "claims", label: "Claims", model: "Nemotron Nano", what: "Every checkable claim as JSON" },
  { id: "grounding", label: "Grounding", model: "Nemotron Super", what: "git + tree-sitter at the claimed version" },
  { id: "prior_art", label: "Prior art", model: "Tavily + OSV", what: "Advisories, disclosures, duplicates" },
  { id: "rules", label: "Policy", model: "Nemotron Super", what: "The project's own SECURITY rules" },
  { id: "repro", label: "Reproduce", model: "OpenShell sandbox", what: "Reporter's steps, no network" },
  { id: "adjudicate", label: "Verdict", model: "Nemotron Ultra", what: "Verdict + adversarial challenge" },
  { id: "fix", label: "Fix", model: "Nemotron Super", what: "Patch, rebuild, test, draft PR" },
  { id: "card", label: "Evidence", what: "Line-linked evidence card" },
];

export const VERDICT_META: Record<Verdict, { color: string; label: string; css: string }> = {
  UNGROUNDED: { color: "#ff4d5e", label: "Ungrounded", css: "red" },
  DUPLICATE: { color: "#4da3ff", label: "Duplicate", css: "blue" },
  NEEDS_INFO: { color: "#ffb547", label: "Needs info", css: "amber" },
  REPRODUCED: { color: "#3ddc97", label: "Reproduced", css: "green" },
};

export interface StageEvent {
  run_id: string;
  stage: Stage;
  status: "start" | "progress" | "done" | "skipped" | "error";
  message: string;
  t: number;
  elapsed_ms: number;
  cost_usd: number;
  data: Record<string, unknown>;
}

export interface LedgerRow {
  claim: string;
  kind: string;
  status: "verified" | "contradicted" | "partial" | "unverifiable";
  method: string;
  deterministic: boolean;
  detail: string;
  url?: string | null;
  file?: string | null;
  line?: number | null;
}

export interface Card {
  run_id: string;
  report: { id: string; title: string; source_url?: string | null; project: string };
  verdict: Verdict;
  color: string;
  confidence: number;
  credibility?: number;
  credibility_why?: string[];
  headline: string;
  reasons: string[];
  challenge?: string | null;
  challenge_upheld?: boolean | null;
  reply_draft?: string | null;
  version?: string;
  rev?: string;
  ledger: LedgerRow[];
  diffs: { claimed?: string | null; actual?: string | null; file?: string | null; line?: number | null; status: string; missing: string[]; url?: string | null }[];
  ghosts: { name: string; near: string[]; commits_searched?: number }[];
  paths: { function: string; chain: string[] }[];
  prior_art: { source: string; id: string; title: string; url: string; score: number; fixed_in?: string | null }[];
  rules: { rule: string; title: string; reason: string; deterministic: boolean; source: string }[];
  sandbox?: { backend: string; ran: boolean; exit_code?: number | null; network: string; duration_ms: number; log: string; attribution: string } | null;
  fix: { iteration: number; build_ok: boolean; repro_fixed: boolean; suite_passed: boolean; patch: string }[];
  flags: string[];
  injection: { kind: string; excerpt: string }[];
  cost_usd: number;
  cost_by_model: Record<string, { model: string; calls: number; tokens: number; cost_usd: number; ms: number }>;
  seconds: number;
  commits_searched?: number | null;
}

export interface Replay {
  id: string;
  label: string;
  kind: "slop" | "valid" | "synthetic" | "arena";
  report: { title: string; body: string; source_url?: string | null };
  events: StageEvent[];
  card: Card;
}

export interface GraphData {
  project: string;
  rev: string;
  version: string;
  files: { path: string; center: [number, number, number]; functions: number }[];
  nodes: { id: number; name: string; file: string; line: number; loc: number; pos: [number, number, number]; entry: boolean; table?: string | null }[];
  edges: [number, number][];
}
