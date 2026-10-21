"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo } from "react";
import * as THREE from "three";
import { GLSL_COMMON } from "../shaders/common";
import type { ShardData } from "./data";

/** Slop dissolving: each slop shard bursts into embers exactly where it hit the membrane. */
export function Embers({ data, perShard = 14, timeScale = 1 }: {
  data: ShardData; perShard?: number; timeScale?: number;
}) {
  const geometry = useMemo(() => {
    const slop = [] as number[];
    for (let i = 0; i < data.count; i++) if (data.fate[i] === 0) slop.push(i);
    const n = slop.length * perShard;
    const seed = new Float32Array(n);
    const speed = new Float32Array(n);
    const offset = new Float32Array(n);
    const k = new Float32Array(n);
    let j = 0;
    for (const i of slop) {
      for (let e = 0; e < perShard; e++, j++) {
        seed[j] = data.seed[i];
        speed[j] = data.speed[i];
        offset[j] = data.offset[i];
        k[j] = e;
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    geo.setAttribute("aSeed", new THREE.BufferAttribute(seed, 1));
    geo.setAttribute("aSpeed", new THREE.BufferAttribute(speed, 1));
    geo.setAttribute("aOffset", new THREE.BufferAttribute(offset, 1));
    geo.setAttribute("aK", new THREE.BufferAttribute(k, 1));
    return geo;
  }, [data, perShard]);

  const uniforms = useMemo(() => ({ uTime: { value: 0 }, uPixel: { value: 1 } }), []);
  useFrame((state) => {
    uniforms.uTime.value = state.clock.elapsedTime * timeScale;
    uniforms.uPixel.value = state.gl.getPixelRatio();
  });

  return (
    <points geometry={geometry} frustumCulled={false}>
      <shaderMaterial
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        vertexShader={/* glsl */ `
          uniform float uTime; uniform float uPixel;
          attribute float aSeed; attribute float aSpeed; attribute float aOffset; attribute float aK;
          varying float vLife; varying float vHeat;
          ${GLSL_COMMON}
          void main() {
            float p = fract(uTime * aSpeed + aOffset);
            float q = (p - GATE_P) / (1.0 - GATE_P);
            float t = clamp(q / 0.55, 0.0, 1.0);
            float alive = step(GATE_P, p) * step(t, 0.999);
            vec3 at = aperture(aSeed);
            float s = aSeed * 13.1 + aK * 7.3;
            vec3 dir = normalize(vec3(-0.6 - hash(s), hash(s + 1.0) - 0.5, hash(s + 2.0) - 0.5));
            float burst = 1.0 - exp(-t * 5.0);
            vec3 pos = at + dir * burst * (2.0 + hash(s + 3.0) * 4.0);
            pos += vec3(-t * 3.0, -t * t * 2.5, 0.0);
            pos.y += sin(t * 9.0 + s) * 0.25 * t;
            pos.z += cos(t * 7.0 + s) * 0.25 * t;
            vec4 mv = modelViewMatrix * vec4(pos, 1.0);
            gl_Position = projectionMatrix * mv;
            vLife = 1.0 - t;
            vHeat = hash(s + 4.0);
            gl_PointSize = alive * (1.0 - t * 0.7) * (3.5 + vHeat * 5.0) * uPixel * (60.0 / -mv.z);
          }
        `}
        fragmentShader={/* glsl */ `
          varying float vLife; varying float vHeat;
          void main() {
            vec2 c = gl_PointCoord - 0.5;
            float d = length(c);
            if (d > 0.5) discard;
            float glow = pow(1.0 - d * 2.0, 2.0);
            vec3 ember = mix(vec3(1.0, 0.28, 0.35), vec3(1.0, 0.62, 0.30), vHeat);
            vec3 col = mix(ember, vec3(1.0), pow(vLife, 6.0));
            gl_FragColor = vec4(col * glow * vLife * 2.6, glow * vLife);
          }
        `}
      />
    </points>
  );
}
