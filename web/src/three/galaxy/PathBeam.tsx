"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo } from "react";
import * as THREE from "three";

/** A reachable call path drawn as a tube with energy pulses flowing entry -> target. */
export function PathBeam({ points }: { points: [number, number, number][] }) {
  const geometry = useMemo(() => {
    const pts = points.map((p) => new THREE.Vector3(...p));
    // lift intermediate control points so the beam arcs instead of cutting through clusters
    const ctrl: THREE.Vector3[] = [];
    pts.forEach((p, i) => {
      ctrl.push(p);
      if (i < pts.length - 1) {
        const mid = p.clone().lerp(pts[i + 1], 0.5);
        ctrl.push(mid.add(mid.clone().normalize().multiplyScalar(p.distanceTo(pts[i + 1]) * 0.18)));
      }
    });
    const curve = new THREE.CatmullRomCurve3(ctrl, false, "centripetal");
    return new THREE.TubeGeometry(curve, Math.max(64, ctrl.length * 40), 0.32, 10, false);
  }, [points]);

  const uniforms = useMemo(() => ({ uTime: { value: 0 } }), []);
  useFrame((s) => { uniforms.uTime.value = s.clock.elapsedTime; });

  return (
    <mesh geometry={geometry}>
      <shaderMaterial
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        vertexShader={/* glsl */ `
          varying vec2 vUv;
          void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
        `}
        fragmentShader={/* glsl */ `
          uniform float uTime; varying vec2 vUv;
          void main() {
            float pulse = pow(fract(vUv.x * 3.0 - uTime * 0.55), 6.0);
            float core = 0.35 + pulse * 2.6;
            float edge = 1.0 - abs(vUv.y - 0.5) * 2.0;
            vec3 col = vec3(0.3, 1.0, 0.66) * core * (0.4 + edge);
            gl_FragColor = vec4(col, 0.65 * (0.3 + pulse));
          }
        `}
      />
    </mesh>
  );
}
