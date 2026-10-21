"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import { memo, useMemo, useRef } from "react";
import * as THREE from "three";

export interface History { months: [string, number][]; total: number; first: string; last: string }

const LENGTH = 150;
const RADIUS = 7;
const TURNS = 11;
const SCAN_SECONDS = 9;

function helixPos(t: number, strand: number, jitter = 0): THREE.Vector3 {
  const a = t * Math.PI * 2 * TURNS + strand * Math.PI;
  const r = RADIUS + jitter;
  return new THREE.Vector3((t - 0.5) * LENGTH, Math.cos(a) * r, Math.sin(a) * r);
}

/** Every commit in the project's history as a point on a double helix, oldest on the left.
 *  A scan ring sweeps the whole history the way a pickaxe search does. */
function Strands({ history, onProgress }: { history: History; onProgress: (t: number) => void }) {
  const { geometry, cumulative } = useMemo(() => {
    const months = history.months;
    const per = Math.max(1, Math.round(history.total / 9000)); // ~9k points on screen
    const pos: number[] = [];
    const tt: number[] = [];
    const seed: number[] = [];
    let i = 0;
    const cumulative: number[] = [];
    let acc = 0;
    months.forEach(([, count], m) => {
      acc += count;
      cumulative.push(acc);
      const n = Math.max(1, Math.round(count / per));
      for (let k = 0; k < n; k++, i++) {
        const t = (m + Math.random()) / months.length;
        const strand = i % 2;
        const p = helixPos(t, strand, (Math.random() - 0.5) * 1.6);
        pos.push(p.x, p.y + (Math.random() - 0.5) * 0.6, p.z);
        tt.push(t);
        seed.push(Math.random());
      }
    });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute("aT", new THREE.Float32BufferAttribute(tt, 1));
    geo.setAttribute("aSeed", new THREE.Float32BufferAttribute(seed, 1));
    return { geometry: geo, cumulative };
  }, [history]);

  const uniforms = useMemo(() => ({ uScan: { value: 0 }, uTime: { value: 0 }, uPixel: { value: 1 } }), []);
  const ring = useRef<THREE.Mesh>(null!);
  const last = useRef(-1);

  useFrame((s) => {
    const t = s.clock.elapsedTime;
    const cycle = (t % (SCAN_SECONDS + 3)) / SCAN_SECONDS; // scan, then hold 3 s
    const scan = Math.min(1, cycle);
    uniforms.uScan.value = scan;
    uniforms.uTime.value = t;
    uniforms.uPixel.value = s.gl.getPixelRatio();
    if (ring.current) {
      ring.current.position.x = (scan - 0.5) * LENGTH;
      ring.current.visible = scan < 1;
    }
    const idx = Math.min(history.months.length - 1, Math.floor(scan * history.months.length));
    if (idx !== last.current) {
      last.current = idx;
      onProgress(scan >= 1 ? history.total : cumulative[idx]);
    }
  });

  return (
    <>
      <points geometry={geometry}>
        <shaderMaterial
          uniforms={uniforms}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          vertexShader={/* glsl */ `
            uniform float uScan; uniform float uTime; uniform float uPixel;
            attribute float aT; attribute float aSeed;
            varying vec3 vColor; varying float vA;
            void main() {
              vec3 old = vec3(0.25, 0.35, 0.95), mid = vec3(0.3, 0.8, 1.0), now = vec3(0.3, 1.0, 0.65);
              vec3 c = aT < 0.5 ? mix(old, mid, aT * 2.0) : mix(mid, now, (aT - 0.5) * 2.0);
              float scanned = step(aT, uScan);
              float front = exp(-pow((aT - uScan) * 90.0, 2.0));
              vColor = mix(c * 0.55, c * 1.6, scanned) + vec3(1.0) * front * 1.8;
              vA = 0.5 + scanned * 0.6 + front;
              vec4 mv = modelViewMatrix * vec4(position, 1.0);
              gl_Position = projectionMatrix * mv;
              gl_PointSize = (2.0 + aSeed * 2.2 + front * 4.0) * uPixel * (70.0 / -mv.z);
            }
          `}
          fragmentShader={/* glsl */ `
            varying vec3 vColor; varying float vA;
            void main() {
              float d = length(gl_PointCoord - 0.5);
              if (d > 0.5) discard;
              gl_FragColor = vec4(vColor * vA * (1.0 - d * 2.0), 1.0);
            }
          `}
        />
      </points>
      <mesh ref={ring} rotation={[0, Math.PI / 2, 0]}>
        <torusGeometry args={[RADIUS + 2.4, 0.09, 12, 160]} />
        <meshBasicMaterial color={[1.6, 2.4, 3.2]} toneMapped={false} />
      </mesh>
    </>
  );
}

function Rig() {
  useFrame((s) => {
    const t = s.clock.elapsedTime;
    s.camera.position.set(Math.sin(t * 0.08) * 8, 7 + Math.sin(t * 0.13) * 2, 92);
    s.camera.lookAt(0, 1, 0);
  });
  return null;
}

function HistoryHelix({ history, onProgress }: { history: History; onProgress: (n: number) => void }) {
  return (
    <Canvas dpr={[1, 1.75]} gl={{ antialias: false, alpha: true }} camera={{ position: [0, 7, 92], fov: 40 }}>
      <Rig />
      <Strands history={history} onProgress={onProgress} />
      <EffectComposer multisampling={0}>
        <Bloom mipmapBlur intensity={1.25} luminanceThreshold={0.1} radius={0.65} />
      </EffectComposer>
    </Canvas>
  );
}

export default memo(HistoryHelix);
