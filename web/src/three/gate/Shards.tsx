"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo } from "react";
import * as THREE from "three";
import { FATE_COLORS, GLSL_COMMON } from "../shaders/common";
import type { ShardData } from "./data";

/** Report shards: one instanced quad per report, animated entirely in the vertex shader. */
export function Shards({ data, timeScale = 1 }: { data: ShardData; timeScale?: number }) {
  const geometry = useMemo(() => {
    const base = new THREE.PlaneGeometry(0.62, 0.82);
    const geo = new THREE.InstancedBufferGeometry();
    geo.index = base.index;
    geo.setAttribute("position", base.getAttribute("position"));
    geo.setAttribute("uv", base.getAttribute("uv"));
    geo.setAttribute("aSeed", new THREE.InstancedBufferAttribute(data.seed, 1));
    geo.setAttribute("aFate", new THREE.InstancedBufferAttribute(data.fate, 1));
    geo.setAttribute("aSpeed", new THREE.InstancedBufferAttribute(data.speed, 1));
    geo.setAttribute("aOffset", new THREE.InstancedBufferAttribute(data.offset, 1));
    geo.instanceCount = data.count;
    return geo;
  }, [data]);

  const uniforms = useMemo(() => ({ uTime: { value: 0 } }), []);
  useFrame((state) => {
    uniforms.uTime.value = state.clock.elapsedTime * timeScale;
  });

  return (
    <mesh geometry={geometry} frustumCulled={false}>
      <shaderMaterial
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        side={THREE.DoubleSide}
        vertexShader={/* glsl */ `
          uniform float uTime;
          attribute float aSeed; attribute float aFate; attribute float aSpeed; attribute float aOffset;
          varying vec2 vUv; varying vec3 vColor; varying float vAlpha;
          ${GLSL_COMMON}
          ${FATE_COLORS}
          mat3 rot(vec3 axis, float a) {
            axis = normalize(axis); float s = sin(a), c = cos(a), oc = 1.0 - c;
            return mat3(oc*axis.x*axis.x + c, oc*axis.x*axis.y - axis.z*s, oc*axis.z*axis.x + axis.y*s,
                        oc*axis.x*axis.y + axis.z*s, oc*axis.y*axis.y + c, oc*axis.y*axis.z - axis.x*s,
                        oc*axis.z*axis.x - axis.y*s, oc*axis.y*axis.z + axis.x*s, oc*axis.z*axis.z + c);
          }
          void main() {
            float p = fract(uTime * aSpeed + aOffset);
            float scale, flash;
            vec3 center = shardPath(p, aSeed, aFate, scale, flash);
            vec3 axis = vec3(hash(aSeed*3.1)-0.5, hash(aSeed*4.3)-0.5, hash(aSeed*6.7)-0.5);
            float size = 0.75 + hash(aSeed*9.0) * 0.6;
            vec3 local = rot(axis, uTime * (0.4 + hash(aSeed)) + aSeed) * (position * scale * size);
            gl_Position = projectionMatrix * modelViewMatrix * vec4(center + local, 1.0);
            vUv = uv;
            bool past = p >= GATE_P;
            vec3 col = past ? fateColor(aFate) : C_NEUTRAL * 0.55;
            vColor = mix(col, vec3(1.0), flash * 0.85) * (past ? 1.7 : 1.0);
            vAlpha = smoothstep(-95.0, -55.0, center.x) * (past ? 1.0 : 0.75);
          }
        `}
        fragmentShader={/* glsl */ `
          varying vec2 vUv; varying vec3 vColor; varying float vAlpha;
          float box(vec2 p, vec2 b, float r) { vec2 d = abs(p) - b + r; return length(max(d, 0.0)) - r; }
          void main() {
            vec2 p = vUv - 0.5;
            float d = box(p, vec2(0.46), 0.08);
            float edge = smoothstep(0.025, 0.0, abs(d));
            float fill = smoothstep(0.0, -0.02, d) * 0.16;
            float lines = step(0.55, fract(vUv.y * 7.0)) * step(abs(p.x), 0.3) * step(abs(p.y), 0.33) * 0.24;
            float a = (edge + fill + lines) * vAlpha;
            if (a < 0.01) discard;
            gl_FragColor = vec4(vColor * a, a);
          }
        `}
      />
    </mesh>
  );
}
