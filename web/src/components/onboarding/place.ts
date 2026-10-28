export interface Box { top: number; left: number; width: number; height: number }
export type Side = "bottom" | "top" | "right" | "left" | "center";

const GAP = 14;     // between the highlighted element and the card
const EDGE = 12;    // keep the card this far inside the viewport
const NAV = 64;     // the fixed nav covers the top of every page

/** Where the tour card goes for a highlighted element: below it if it fits, then above, then
 *  beside it, else over the middle of the screen (an element taller than the viewport). The card
 *  is clamped inside the viewport and never under the nav. */
export function place(target: Box | null, card: { width: number; height: number },
  view: { width: number; height: number }): { top: number; left: number; side: Side } {
  const clampX = (x: number) => Math.min(Math.max(EDGE, x), view.width - card.width - EDGE);
  const clampY = (y: number) => Math.min(Math.max(NAV + EDGE, y), view.height - card.height - EDGE);
  const centered = { top: clampY((view.height - card.height) / 2), left: clampX((view.width - card.width) / 2), side: "center" as Side };
  if (!target) return centered;

  const midX = target.left + target.width / 2 - card.width / 2;
  const midY = target.top + target.height / 2 - card.height / 2;
  const below = target.top + target.height + GAP, above = target.top - GAP - card.height;
  const right = target.left + target.width + GAP, left = target.left - GAP - card.width;

  if (below + card.height <= view.height - EDGE) return { top: below, left: clampX(midX), side: "bottom" };
  if (above >= NAV + EDGE) return { top: above, left: clampX(midX), side: "top" };
  if (right + card.width <= view.width - EDGE) return { top: clampY(midY), left: right, side: "right" };
  if (left >= EDGE) return { top: clampY(midY), left, side: "left" };
  // the element fills the screen: dock the card in the bottom-right corner, where it covers the least
  return { top: clampY(view.height - card.height - EDGE * 2), left: clampX(view.width - card.width - EDGE * 2), side: "center" };
}
