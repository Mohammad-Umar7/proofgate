"use client";

import { Html } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

/** A function the report cites that does not exist: a flickering wireframe adrift outside the
 *  galaxy, connected to nothing. A dashed tether points at the real name it imitates. */
export function Ghost({ name, position, anchor, near, note = "never existed in curl" }: {
  name: string; position: THREE.Vector3; anchor: THREE.Vector3 | null; near: string[]; note?: string;
}) {
  const group = useRef<THREE.Group>(null!);
  const uniforms = useMemo(() => ({ uTime: { value: 0 } }), []);
  const tether = useMemo(() => {
    if (!anchor) return null;
    const geo = new THREE.BufferGeometry().setFromPoints([position, anchor]);
    const line = new THREE.Line(geo, new THREE.LineDashedMaterial({
      color: new THREE.Color(1.0, 0.32, 0.38), dashSize: 2, gapSize: 2.5, transparent: true, opacity: 0.55,
    }));
    line.computeLineDistances();
    return line;
  }, [position, anchor]);

  useFrame((s) => {
    const t = s.clock.elapsedTime;
    uniforms.uTime.value = t;
    if (group.current) {
      group.current.rotation.y = t * 0.4;
      group.current.rotation.x = Math.sin(t * 0.7) * 0.3;
      group.current.position.y = position.y + Math.sin(t * 0.9) * 1.2;
    }
  });

  return (
    <>
      {tether && <primitive object={tether} />}
      <group ref={group} position={position}>
        <mesh>
          <icosahedronGeometry args={[3.2, 1]} />
          <shaderMaterial
            uniforms={uniforms}
            wireframe
            transparent
            depthWrite={false}
            blending={THREE.AdditiveBlending}
            vertexShader={/* glsl */ `
              uniform float uTime; varying float vGlitch; varying float vY;
              float h(float n) { return fract(sin(n) * 43758.5453); }
              void main() {
                vec3 p = position;
                float band = floor((p.y + uTime * 3.0) * 2.0);
                float g = step(0.9, h(band + floor(uTime * 12.0)));
                p.x += g * (h(band) - 0.5) * 2.2;
                vGlitch = g; vY = p.y;
                gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
              }
            `}
            fragmentShader={/* glsl */ `
              uniform float uTime; varying float vGlitch; varying float vY;
              void main() {
                float scan = 0.55 + 0.45 * step(0.5, fract(vY * 3.0 - uTime * 4.0));
                float flicker = 0.75 + 0.25 * sin(uTime * 31.0) * sin(uTime * 17.0);
                vec3 col = mix(vec3(1.0, 0.3, 0.37), vec3(0.6, 0.9, 1.0), vGlitch) * 2.2 * scan * flicker;
                gl_FragColor = vec4(col, 0.85);
              }
            `}
          />
        </mesh>
        <mesh>
          <icosahedronGeometry args={[1.4, 0]} />
          <meshBasicMaterial color={[1.6, 0.35, 0.42]} wireframe toneMapped={false} />
        </mesh>
      </group>
      <Html position={[position.x, position.y + 6.5, position.z]} center style={{ pointerEvents: "none" }}>
        <div className="galaxy-ghost">
          <b>{name}()</b>
          <span>{note}</span>
          {near[0] && <em>closest real name: {near[0]}()</em>}
        </div>
      </Html>
    </>
  );
}
