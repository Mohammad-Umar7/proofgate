/** Per-shard parameters shared by the shards, their embers and the membrane impacts. */
export interface ShardData {
  count: number;
  seed: Float32Array;
  fate: Float32Array; // 0 slop, 1 duplicate, 2 real
  speed: Float32Array;
  offset: Float32Array;
}

export function makeShards(count: number, mix = { slop: 0.7, dup: 0.13 }): ShardData {
  const seed = new Float32Array(count);
  const fate = new Float32Array(count);
  const speed = new Float32Array(count);
  const offset = new Float32Array(count);
  let s = 1234567;
  const rand = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < count; i++) {
    seed[i] = i * 1.618 + 0.37;
    const r = rand();
    fate[i] = r < mix.slop ? 0 : r < mix.slop + mix.dup ? 1 : 2;
    speed[i] = 0.016 + rand() * 0.018;
    offset[i] = rand();
  }
  return { count, seed, fate, speed, offset };
}

/** JS mirror of the GLSL `hash` and `aperture`, for CPU-side impact bookkeeping. */
export function hash(n: number) {
  const x = Math.sin(n) * 43758.5453123;
  return x - Math.floor(x);
}

export function aperture(seed: number): [number, number] {
  const ra = 0.6 + (7.6 - 0.6) * Math.sqrt(hash(seed * 5.1));
  const a = hash(seed * 1.3) * 6.2831 + 2.2 + hash(seed * 7.7) * 1.5;
  return [Math.sin(a) * ra, Math.cos(a) * ra];
}

export const GATE_P = 0.62;
