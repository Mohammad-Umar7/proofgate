import { PLAY_HERO, samePage, scrollBehavior } from "@/lib/onboarding";
import { selector } from "./useTarget";

/** One hint for a page that has sat idle: what to do next, pointed at the element to do it on,
 *  with a button that does it. Built when it is shown, so it can describe the page as it is. */
export interface Hint {
  text: string;
  target?: string;
  actions: { label: string; run: () => void }[];
}
interface PageHints { after: number; build: (go: (href: string) => void) => Hint | null }

const el = (target: string) => document.querySelector<HTMLElement>(selector(target));
const inView = (e: HTMLElement) => {
  const r = e.getBoundingClientRect();
  return r.bottom > 64 && r.top < window.innerHeight;
};
const show = (target: string) => {
  const e = el(target);
  if (!e) return;
  const top = window.scrollY + e.getBoundingClientRect().top - 84;
  window.scrollTo({ top: Math.max(0, top), behavior: scrollBehavior() });
};
const click = (target: string) => el(target)?.click();

const PAGES: [route: string, hints: PageHints][] = [
  ["/", {
    after: 6000,
    build: (go) => window.scrollY > 40 ? null : {
      text: "The 3D scene moves as you scroll. Play the flight through the gate, or go straight to a real report being triaged.",
      target: "hero-hint",
      actions: [
        { label: "▶ Play the flight", run: () => window.dispatchEvent(new Event(PLAY_HERO)) },
        { label: "Open the console", run: () => go("/console/") },
      ],
    },
  }],
  ["/console/", {
    after: 11000,
    build: () => {
      const card = el("evidence");
      if (card && !inView(card)) return {
        text: "The run has finished. Its evidence card, with the verdict and a reply draft, is below the console.",
        actions: [{ label: "Show the evidence ↓", run: () => show("evidence") }],
      };
      const cards = [...document.querySelectorAll<HTMLElement>(`${selector("picker")} button`)];
      const on = cards.findIndex((c) => c.getAttribute("aria-pressed") === "true");
      const nextCard = cards[(on + 1) % Math.max(1, cards.length)];
      return {
        text: "Each card above is a recorded run. Click one to replay it, with its real timings and Token Factory spend.",
        target: "picker",
        actions: nextCard ? [{ label: "Replay the next report", run: () => { nextCard.click(); show("picker"); } }] : [],
      };
    },
  }],
  ["/galaxy/", {
    after: 7000,
    build: () => ({
      text: "Drag the galaxy to turn it and scroll to zoom. Or look up a function: invented ones float outside, connected to nothing.",
      target: "galaxy-ghost",
      actions: [{ label: "Show a hallucinated function", run: () => click("galaxy-ghost") }],
    }),
  }],
  ["/arena/", {
    after: 8000,
    build: () => el("arena-hardest") ? {
      text: "Open a round to read the red team's fake beside the evidence ProofGate found against it.",
      target: "arena-hardest",
      actions: [{ label: "Open the hardest round", run: () => { click("arena-hardest"); show("arena-hardest"); } }],
    } : null,
  }],
  ["/bench/", {
    after: 9000,
    build: () => el("bench-rows") ? {
      text: "All 197 reports are listed further down, each with its verdict and a link to the original report.",
      actions: [{ label: "Show the reports ↓", run: () => show("bench-rows") }],
    } : null,
  }],
  ["/fixbench/", {
    after: 8000,
    build: () => el("fixbench-fixed") ? {
      text: "Each green tile is a CVE Nemotron fixed. Click one for the agent's full transcript and its patch beside curl's.",
      target: "fixbench-fixed",
      actions: [{ label: "Show a fix", run: () => { click("fixbench-fixed"); window.setTimeout(() => show("fixbench-detail"), 120); } }],
    } : null,
  }],
];

export function hintsFor(path: string | null): PageHints | null {
  return PAGES.find(([route]) => samePage(path, route))?.[1] ?? null;
}
