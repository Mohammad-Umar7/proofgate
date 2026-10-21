/** GLSL shared by the gate scene: hashing and the analytic path every report shard follows.
 *  Shards, debris and membrane impacts all evaluate the same function, so a slop shard's embers
 *  burst from exactly where it hit the gate, with no CPU simulation. */
export const GLSL_COMMON = /* glsl */ `
float hash(float n) { return fract(sin(n) * 43758.5453123); }

const float GATE_P = 0.62;     // fraction of a shard's life spent approaching the gate
const float START_X = -95.0;

vec3 aperture(float seed) {
  float ra = mix(0.6, 7.6, sqrt(hash(seed * 5.1)));
  float aA = hash(seed * 1.3) * 6.2831 + 2.2 + hash(seed * 7.7) * 1.5;
  return vec3(0.0, sin(aA) * ra, cos(aA) * ra);
}

vec3 shardPath(float p, float seed, float fate, out float scale, out float flash) {
  float a0 = hash(seed * 1.3) * 6.2831;
  float r0 = mix(16.0, 44.0, hash(seed * 2.7));
  vec3 at = aperture(seed);
  float aA = atan(at.y, at.z);
  float ra = length(at.yz);
  scale = 1.0;
  flash = 0.0;
  if (p < GATE_P) {
    float q = p / GATE_P;
    float e = q * q * (3.0 - 2.0 * q);
    float x = mix(START_X, 0.0, q);
    float ang = mix(a0, aA, e);
    float r = mix(r0, ra, pow(e, 0.75));
    float wob = sin(q * 11.0 + seed * 10.0) * 0.8 * (1.0 - q);
    scale = smoothstep(0.0, 0.06, q);
    return vec3(x, sin(ang) * r + wob, cos(ang) * r);
  }
  float q = (p - GATE_P) / (1.0 - GATE_P);
  flash = exp(-q * 14.0);
  if (fate < 0.5) {
    scale = 1.0 - smoothstep(0.0, 0.07, q);
    return at + vec3(-q * 1.2, 0.0, 0.0);
  } else if (fate < 1.5) {
    vec3 c = vec3(16.0, 9.5, -7.0);
    float e = smoothstep(0.0, 0.45, q);
    float oa = q * 8.0 + seed * 6.2831;
    vec3 orbit = c + vec3(cos(oa) * 2.6, sin(oa * 1.7) * 1.3, sin(oa) * 2.6);
    scale = 1.0 - smoothstep(0.86, 1.0, q);
    vec3 mid = mix(at, c, 0.5) + vec3(0.0, 5.0, 0.0);
    vec3 a = mix(at, mid, e);
    vec3 b = mix(mid, orbit, e);
    return mix(a, b, e);
  }
  float e = q * q;
  vec3 pos = mix(at, vec3(78.0, 0.0, 0.0), e);
  pos.yz *= 1.0 - e * 0.92;
  scale = 1.0 - smoothstep(0.92, 1.0, q);
  return pos;
}
`;

export const FATE_COLORS = /* glsl */ `
const vec3 C_NEUTRAL = vec3(0.80, 0.84, 0.95);
const vec3 C_RED = vec3(1.00, 0.30, 0.37);
const vec3 C_BLUE = vec3(0.30, 0.64, 1.00);
const vec3 C_GREEN = vec3(0.24, 0.86, 0.59);
vec3 fateColor(float fate) {
  return fate < 0.5 ? C_RED : (fate < 1.5 ? C_BLUE : C_GREEN);
}
`;
