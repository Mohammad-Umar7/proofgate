/** First-visit state for the welcome, the guided tour and the page hints. Storage can be missing or
 *  throw (private windows, blocked site data, embedded previews): every access is wrapped, and the
 *  site simply behaves as on a first visit when it cannot remember. */

export const KEYS = {
  /** localStorage: set once the visitor has answered the welcome, so it is not shown again */
  welcomed: "pg.onboarding.welcomed.v1",
  /** localStorage: set once the visitor has started the tour, so its button stops calling for them */
  toured: "pg.onboarding.toured.v1",
  /** sessionStorage: index of the tour step in progress, so a reload resumes the tour */
  tourStep: "pg.onboarding.tour",
  /** sessionStorage: the step a visitor was on when they left the tour's page on their own */
  tourPaused: "pg.onboarding.tour.paused",
  /** sessionStorage: pages whose hint was already shown in this visit */
  hinted: "pg.onboarding.hinted",
} as const;

type Area = "local" | "session";
const area = (a: Area): Storage | null => {
  try { return a === "local" ? window.localStorage : window.sessionStorage; } catch { return null; }
};

export function read(key: string, a: Area = "local"): string | null {
  try { return area(a)?.getItem(key) ?? null; } catch { return null; }
}

export function write(key: string, value: string | null, a: Area = "local"): void {
  try {
    const s = area(a);
    if (!s) return;
    if (value === null) s.removeItem(key);
    else s.setItem(key, value);
  } catch { /* storage full or blocked: forget it */ }
}

/** Pages are compared without the trailing slash the static export adds. */
export const samePage = (a: string | null | undefined, b: string) =>
  (a ?? "").replace(/\/+$/, "") === b.replace(/\/+$/, "");

/** Ask the onboarding layer to do something from anywhere on the page (a call to action, the nav). */
export type OnboardingCommand = "tour" | "resume" | "welcome" | "hint";
export const EVENT = "pg:onboarding";
export function command(c: OnboardingCommand) {
  window.dispatchEvent(new CustomEvent<OnboardingCommand>(EVENT, { detail: c }));
}

/** Ask the landing hero to play its scroll-driven flight through the gate. */
export const PLAY_HERO = "pg:play-hero";

/** Respect a visitor's reduced-motion setting for scrolling the page on their behalf. */
export const scrollBehavior = (): ScrollBehavior =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
