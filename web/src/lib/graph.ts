import type { GraphData } from "./types";

/** Shortest caller chain from a public entry point (or a dispatch table) to `target`,
 *  mirroring the engine's CodeIndex.path_from_entry. */
export function pathFromEntry(graph: GraphData, target: string, maxDepth = 12): string[] | null {
  const idx = graph.nodes.findIndex((n) => n.name === target);
  if (idx < 0) return null;
  const callers = new Map<number, number[]>();
  for (const [a, b] of graph.edges) {
    if (!callers.has(b)) callers.set(b, []);
    callers.get(b)!.push(a);
  }
  if (graph.nodes[idx].entry) return [target];
  const seen = new Set([idx]);
  let frontier: number[][] = [[idx]];
  let fallback: string[] | null = null;
  for (let depth = 0; depth < maxDepth && frontier.length; depth++) {
    const next: number[][] = [];
    for (const chain of frontier) {
      const head = chain[chain.length - 1];
      const table = graph.nodes[head].table;
      if (!fallback && table) fallback = [`table:${table}`, ...chain.slice().reverse().map((i) => graph.nodes[i].name)];
      for (const c of callers.get(head) ?? []) {
        if (seen.has(c)) continue;
        if (graph.nodes[c].entry) return [c, ...chain.slice().reverse()].map((i) => graph.nodes[i].name);
        seen.add(c);
        next.push([...chain, c]);
      }
    }
    frontier = next;
  }
  return fallback;
}

/** Closest real names for a name that does not exist (simple ratio like difflib). */
export function nearNames(graph: GraphData, name: string, limit = 3): string[] {
  const score = (a: string, b: string) => {
    const A = a.toLowerCase(), B = b.toLowerCase();
    const grams = (s: string) => new Set(Array.from({ length: Math.max(0, s.length - 2) }, (_, i) => s.slice(i, i + 3)));
    const ga = grams(A), gb = grams(B);
    let inter = 0;
    ga.forEach((g) => gb.has(g) && inter++);
    return (2 * inter) / (ga.size + gb.size || 1);
  };
  const uniq = Array.from(new Set(graph.nodes.map((n) => n.name)));
  return uniq
    .map((n) => [n, score(name, n)] as const)
    .filter(([, s]) => s > 0.35)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([n]) => n);
}
