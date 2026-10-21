"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import { aperture, GATE_P, type ShardData } from "./data";

const IMPACTS = 24;
const RADIUS = 9.4;

/** The gate: machined outer ring, scanning arcs, tick ring, and a membrane that ripples red
 *  wherever a slop shard hits it (impacts computed from the same analytic paths as the shards). */
export function Gate({ data, timeScale = 1 }: { data: ShardData; timeScale?: number }) {
  const scanA = useRef<THREE.Mesh>(null!);
  const scanB = useRef<THREE.Mesh>(null!);
  const ticks = useRef<THREE.InstancedMesh>(null!);

  const ring = useMemo(() => ({ uTime: { value: 0 } }), []);
  const membrane = useMemo(() => ({
    uTime: { value: 0 },
    uImpacts: { value: Array.from({ length: IMPACTS }, () => new THREE.Vector3(0, 0, -100)) },
  }), []);
  const cursor = useRef(0);
  const lastT = useRef(0);

  const slop = useMemo(() => {
    const idx: number[] = [];
    for (let i = 0; i < data.count; i++) if (data.fate[i] === 0) idx.push(i);
    return idx;
  }, [data]);

  const tickMatrices = useMemo(() => {
    const out: THREE.Matrix4[] = [];
    const n = 120;
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2;
      const long = i % 10 === 0;
      const m = new THREE.Matrix4();
      const r = RADIUS + 3.4;
      m.compose(
        new THREE.Vector3(0, Math.sin(a) * r, Math.cos(a) * r),
        new THREE.Quaternion().setFromEuler(new THREE.Euler(Math.PI / 2 - a, 0, 0)),
        new THREE.Vector3(0.08, long ? 1.1 : 0.45, 0.08),
      );
      out.push(m);
    }
    return out;
  }, []);

  useFrame((state) => {
    const t = state.clock.elapsedTime * timeScale;
    ring.uTime.value = t;
    membrane.uTime.value = t;
    if (scanA.current) scanA.current.rotation.z = t * 0.35;
    if (scanB.current) scanB.current.rotation.z = -t * 0.22 + 1.3;
    if (ticks.current && !ticks.current.userData.ready) {
      tickMatrices.forEach((m, i) => ticks.current.setMatrixAt(i, m));
      ticks.current.instanceMatrix.needsUpdate = true;
      ticks.current.userData.ready = true;
    }
    if (ticks.current) ticks.current.rotation.x = t * 0.03;
    // membrane impacts: which slop shards crossed the gate since the last frame?
    const prev = lastT.current;
    lastT.current = t;
    if (prev === 0) return;
    for (const i of slop) {
      const p0 = (prev * data.speed[i] + data.offset[i]) % 1;
      const p1 = (t * data.speed[i] + data.offset[i]) % 1;
      if (p0 < GATE_P && p1 >= GATE_P) {
        const [y, z] = aperture(data.seed[i]);
        membrane.uImpacts.value[cursor.current % IMPACTS].set(y, z, t);
        cursor.current++;
      }
    }
  });

  return (
    <group>
      {/* outer machined ring */}
      <mesh rotation={[0, Math.PI / 2, 0]}>
        <torusGeometry args={[RADIUS + 1.6, 0.55, 48, 360]} />
        <shaderMaterial
          uniforms={ring}
          vertexShader={/* glsl */ `
            varying vec2 vUv; varying vec3 vN; varying vec3 vView;
            void main() {
              vUv = uv;
              vec4 wp = modelMatrix * vec4(position, 1.0);
              vN = normalize(mat3(modelMatrix) * normal);
              vView = normalize(cameraPosition - wp.xyz);
              gl_Position = projectionMatrix * viewMatrix * wp;
            }
          `}
          fragmentShader={/* glsl */ `
            uniform float uTime; varying vec2 vUv; varying vec3 vN; varying vec3 vView;
            void main() {
              float fres = pow(1.0 - abs(dot(vN, vView)), 2.2);
              float ticks = step(0.93, fract(vUv.x * 72.0));
              float sweep = exp(-pow((fract(vUv.x - uTime * 0.07) - 0.5) * 7.0, 2.0) * 6.0);
              float sweep2 = exp(-pow((fract(vUv.x + uTime * 0.045 + 0.33) - 0.5) * 9.0, 2.0) * 6.0);
              vec3 steel = vec3(0.045, 0.05, 0.065) + vec3(0.25, 0.3, 0.38) * fres;
              vec3 glow = vec3(0.55, 0.75, 1.0) * (ticks * 0.35 + sweep * 2.2) + vec3(1.0, 0.35, 0.4) * sweep2 * 0.9;
              gl_FragColor = vec4(steel + glow * (0.35 + fres), 1.0);
            }
          `}
        />
      </mesh>

      {/* inner bright lip */}
      <mesh rotation={[0, Math.PI / 2, 0]}>
        <torusGeometry args={[RADIUS, 0.07, 16, 360]} />
        <meshBasicMaterial color={[2.2, 2.6, 3.2]} toneMapped={false} />
      </mesh>

      {/* rotating scanner arcs (in the gate plane, spinning about the gate axis) */}
      <group rotation={[0, Math.PI / 2, 0]}>
        <mesh ref={scanA}>
          <torusGeometry args={[RADIUS + 2.6, 0.06, 8, 200, Math.PI * 0.55]} />
          <meshBasicMaterial color={[0.6, 1.4, 2.6]} toneMapped={false} />
        </mesh>
        <mesh ref={scanB}>
          <torusGeometry args={[RADIUS + 2.9, 0.035, 8, 200, Math.PI * 0.3]} />
          <meshBasicMaterial color={[2.4, 0.7, 0.8]} toneMapped={false} />
        </mesh>
      </group>

      {/* tick ring */}
      <instancedMesh ref={ticks} args={[undefined, undefined, tickMatrices.length]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshBasicMaterial color={[0.5, 0.6, 0.8]} toneMapped={false} />
      </instancedMesh>

      {/* membrane */}
      <mesh rotation={[0, Math.PI / 2, 0]}>
        <circleGeometry args={[RADIUS, 128]} />
        <shaderMaterial
          uniforms={membrane}
          transparent
          depthWrite={false}
          side={THREE.DoubleSide}
          blending={THREE.AdditiveBlending}
          vertexShader={/* glsl */ `
            varying vec2 vLocal;
            void main() { vLocal = position.xy; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
          `}
          fragmentShader={/* glsl */ `
            uniform float uTime; uniform vec3 uImpacts[${IMPACTS}]; varying vec2 vLocal;
            void main() {
              float r = length(vLocal) / ${RADIUS.toFixed(1)};
              float rim = smoothstep(0.82, 1.0, r) * 0.55;
              float waves = (sin(r * 46.0 - uTime * 1.6) * 0.5 + 0.5) * 0.05 * (1.0 - r);
              float scan = exp(-pow(fract(vLocal.y * 0.06 + uTime * 0.11) - 0.5, 2.0) * 900.0) * 0.12;
              vec3 col = vec3(0.35, 0.55, 1.0) * (rim + waves + scan + 0.025);
              for (int i = 0; i < ${IMPACTS}; i++) {
                vec3 im = uImpacts[i]; // (world y, world z, time)
                float age = uTime - im.z;
                if (age < 0.0 || age > 2.5) continue;
                // the circle is rotated +90deg about Y: local x = -world z, local y = world y
                float d = distance(vLocal, vec2(-im.y, im.x));
                float ring = exp(-pow(d - age * 5.5, 2.0) * 2.2) * exp(-age * 1.6);
                float core = exp(-d * d * 1.2) * exp(-age * 5.0);
                col += vec3(1.0, 0.3, 0.36) * (ring * 0.9 + core * 2.2);
              }
              gl_FragColor = vec4(col, 1.0);
            }
          `}
        />
      </mesh>
    </group>
  );
}
