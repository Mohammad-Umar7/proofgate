"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

/** Drifting dust that flows toward the gate, for depth and a sense of current. */
export function Dust({ count = 7000 }: { count?: number }) {
  const geometry = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const seed = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      pos[i * 3] = Math.random() * 200 - 110;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 80;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 120;
      seed[i] = Math.random();
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("aSeed", new THREE.BufferAttribute(seed, 1));
    return geo;
  }, [count]);
  const uniforms = useMemo(() => ({ uTime: { value: 0 }, uPixel: { value: 1 } }), []);
  useFrame((s) => {
    uniforms.uTime.value = s.clock.elapsedTime;
    uniforms.uPixel.value = s.gl.getPixelRatio();
  });
  return (
    <points geometry={geometry} frustumCulled={false}>
      <shaderMaterial
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        vertexShader={/* glsl */ `
          uniform float uTime; uniform float uPixel; attribute float aSeed; varying float vA;
          void main() {
            vec3 p = position;
            p.x = mod(p.x + uTime * (1.5 + aSeed * 2.5) + 110.0, 200.0) - 110.0;
            p.y += sin(uTime * 0.3 + aSeed * 30.0) * 0.6;
            vec4 mv = modelViewMatrix * vec4(p, 1.0);
            gl_Position = projectionMatrix * mv;
            vA = 0.25 + aSeed * 0.5;
            gl_PointSize = (0.6 + aSeed * 1.4) * uPixel * (40.0 / -mv.z);
          }
        `}
        fragmentShader={/* glsl */ `
          varying float vA;
          void main() {
            float d = length(gl_PointCoord - 0.5);
            if (d > 0.5) discard;
            gl_FragColor = vec4(vec3(0.55, 0.65, 0.9) * vA * (1.0 - d * 2.0), 1.0);
          }
        `}
      />
    </points>
  );
}

/** Infinite-feeling floor grid that fades into the dark. */
export function Floor() {
  const uniforms = useMemo(() => ({ uTime: { value: 0 } }), []);
  useFrame((s) => { uniforms.uTime.value = s.clock.elapsedTime; });
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -17, 0]}>
      <planeGeometry args={[420, 420, 1, 1]} />
      <shaderMaterial
        uniforms={uniforms}
        transparent
        depthWrite={false}
        vertexShader={/* glsl */ `
          varying vec2 vXY;
          void main() { vXY = position.xy; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
        `}
        fragmentShader={/* glsl */ `
          uniform float uTime; varying vec2 vXY;
          float grid(vec2 p, float s) {
            vec2 g = abs(fract(p / s - 0.5) - 0.5) / fwidth(p / s);
            return 1.0 - min(min(g.x, g.y), 1.0);
          }
          void main() {
            vec2 p = vXY + vec2(uTime * 2.0, 0.0);
            float g = grid(p, 4.0) * 0.5 + grid(p, 20.0) * 0.8;
            float fade = exp(-length(vXY) * 0.012);
            float glow = exp(-pow(vXY.y, 2.0) * 0.004) * exp(-abs(vXY.x) * 0.01);
            vec3 col = vec3(0.3, 0.42, 0.7) * g * fade * 0.55 + vec3(0.2, 0.35, 0.7) * glow * 0.05;
            gl_FragColor = vec4(col, g * fade * 0.8 + glow * 0.05);
          }
        `}
      />
    </mesh>
  );
}

/** The beam through the gate and the maintainer beacon real bugs fly to. */
export function Beam() {
  const beacon = useRef<THREE.Mesh>(null!);
  useFrame((s) => {
    const k = 1 + Math.sin(s.clock.elapsedTime * 2.2) * 0.12;
    beacon.current?.scale.setScalar(k);
  });
  return (
    <group>
      <mesh rotation={[0, 0, Math.PI / 2]} position={[30, 0, 0]}>
        <cylinderGeometry args={[0.06, 0.06, 140, 8, 1, true]} />
        <meshBasicMaterial color={[0.4, 0.9, 0.7]} transparent opacity={0.12} toneMapped={false} />
      </mesh>
      <mesh ref={beacon} position={[78, 0, 0]}>
        <icosahedronGeometry args={[1.1, 2]} />
        <meshBasicMaterial color={[0.6, 3.2, 1.9]} toneMapped={false} />
      </mesh>
      <mesh position={[78, 0, 0]}>
        <sphereGeometry args={[3.2, 32, 16]} />
        <meshBasicMaterial color={[0.2, 0.9, 0.55]} transparent opacity={0.08} toneMapped={false} />
      </mesh>
      {/* duplicate cluster nucleus */}
      <mesh position={[16, 9.5, -7]}>
        <icosahedronGeometry args={[0.7, 1]} />
        <meshBasicMaterial color={[0.6, 1.4, 3.2]} wireframe toneMapped={false} />
      </mesh>
    </group>
  );
}
