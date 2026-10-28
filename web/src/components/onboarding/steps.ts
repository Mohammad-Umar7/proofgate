/** The guided tour: one stop per idea, in the order a maintainer would meet them. Each step points
 *  at an element marked `data-tour="<target>"` on its page; a step without a target is a centred
 *  card. Copy states only what the recorded data shows. */

export interface TourStep {
  route: string;
  target?: string;
  title: string;
  body: string;
  /** scroll the page to the top first (the landing hero is pinned and fades as you scroll) */
  top?: boolean;
  /** shown while the target is not on the page yet, e.g. a card that appears when a run ends */
  waiting?: string;
  /** leave the page undimmed: the step is about a full-screen 3D scene, which should be seen whole */
  clear?: boolean;
  /** keep the card in this bottom corner, out of the way of what the step shows */
  dock?: "left" | "right";
  /** what the tour does on arrival, so the visitor sees it happen instead of reading about it */
  run?: StepAction;
}

export interface StepAction {
  /** click the element marked `data-tour=<click>` (left alone if it is already open or pressed) */
  click?: string;
  /** or send this event to the window */
  event?: string;
  /** wait for the element marked `data-tour=<when>` first: a view that only works once its data loaded */
  when?: string;
  /** then wait this long (ms), so the page has settled before it moves */
  delay?: number;
}

export const VIDEO_URL = "https://youtu.be/d4L-x6sTMmI";
export const REPO_URL = "https://github.com/Mohammad-Umar7/proofgate";

export const STEPS: TourStep[] = [
  {
    route: "/", target: "hero-copy", top: true,
    title: "Prove the report before anyone reads it",
    body: "AI made fake vulnerability reports free to write. ProofGate checks every claim in a report against the real source code and its git history, so a volunteer maintainer only spends time on what holds up.",
  },
  {
    route: "/", target: "hero-legend", top: true,
    title: "The gate, driven by your scroll",
    body: "Each shard flying in is a report. Scroll to fly through: slop dissolves on the gate, duplicates of published advisories merge, and real bugs pass through to the maintainer.",
  },
  {
    route: "/console/", target: "picker",
    title: "Pick a report to replay",
    body: "Ten recorded runs: four synthetic reports that each test one check, four real reports from curl's public AI-slop list, and two real reports that became CVEs. Click any card to replay it with its real timings.",
  },
  {
    route: "/console/", target: "pipeline",
    title: "Nine stages, cheapest first",
    body: "Each stage shows what it found, how long it took and what it cost on Nebius Token Factory. git and tree-sitter do the grounding at no model cost; NVIDIA Nemotron Nano, Super and Ultra only get the jobs that need a model.",
  },
  {
    route: "/console/", target: "console-galaxy",
    title: "Invented code has nowhere to attach",
    body: "Once grounding finishes, a function the report cites that never existed in curl appears here, adrift outside the galaxy, labelled with the closest real names.",
  },
  {
    route: "/console/", target: "evidence",
    waiting: "The evidence card appears below the console when the run finishes, in a few seconds.",
    title: "What the maintainer receives",
    body: "The verdict with its evidence: every claim checked against a file, a line and git history at the report's version, and a reply draft ready to send. ProofGate only dismisses a report on a deterministic contradiction, and a human makes the final call.",
  },
  {
    route: "/galaxy/", target: "galaxy-presets",
    title: "Look up any function",
    body: "All 4,291 functions of curl 8.23.0 and the 9,747 calls between them. Click a real function to light up its call path from a public entry point, then a hallucinated one to see it float outside. Drag the galaxy to turn it, scroll to zoom.",
  },
  {
    route: "/arena/", target: "arena-ladder",
    title: "A red team tries to fool it",
    body: "An agent writes fake reports at five levels of realism, up to real curl code with a line addressed to the AI triager. Open any round below to read the fake beside ProofGate's evidence.",
  },
  {
    route: "/bench/", target: "bench-kpis",
    title: "Measured on curl's public record",
    body: "SlopBench: 197 disclosed curl reports, every entry on curl's AI-slop list and every CVE whose advisory links its HackerOne report. The number that matters most: 0 of 148 real CVEs wrongly dismissed.",
  },
  {
    route: "/fixbench/", target: "fixbench-grid",
    title: "From a proven bug to a tested patch",
    body: "Each tile is a real curl CVE. Nemotron reads the public advisory, edits curl's C code, builds it and runs curl's own tests in a sandbox with no network. Click a tile for the full transcript and the patch beside the one curl shipped.",
  },
  {
    route: "/fixbench/",
    title: "That's ProofGate",
    body: "Every model call you saw ran on NVIDIA Nemotron through Nebius Token Factory. This public site replays those recorded runs so it stays up for free; with the engine running, the same pages run live on a link you paste.",
  },
];
