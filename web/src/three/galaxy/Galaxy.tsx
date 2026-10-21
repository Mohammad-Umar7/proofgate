"use client";

import { CameraControls, Html } from "@react-three/drei";
import { Canvas, type ThreeEvent, useFrame } from "@react-three/fiber";
import { Bloom, EffectComposer, Vignette } from "@react-three/postprocessing";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { GraphData } from "@/lib/types";
import { Ghost } from "./Ghost";
import { nodeColor } from "./palette";
import { PathBeam } from "./PathBeam";

export interface GalaxyFocus {
  path?: string[]; // entry -> ... -> target (function names; "table:X" allowed first)
  target?: string;
  ghosts?: { name: string; near: string[]; note?: string }[];
}

function Nodes({ graph, lit, dim, onHover }: {
  graph: GraphData; lit: Set<number>; dim: boolean; onHover: (i: number | null) => void;
}) {
  const mesh = useRef<THREE.InstancedMesh>(null!);
  const count = graph.nodes.length;
  const { colors, lights } = useMemo(() => {
    const colors = new Float32Array(count * 3);
    const lights = new Float32Array(count);
    graph.nodes.forEach((n, i) => {
      const c = nodeColor(n.file);
      colors.set([c.r, c.g, c.b], i * 3);
    });
    return { colors, lights };
  }, [graph, count]);

  useEffect(() => {
    const m = new THREE.Matrix4();
    graph.nodes.forEach((n, i) => {
      const s = 0.22 + Math.sqrt(n.loc) * 0.05 + (n.entry ? 0.6 : 0);
      m.makeScale(s, s, s).setPosition(n.pos[0], n.pos[1], n.pos[2]);
      mesh.current.setMatrixAt(i, m);
    });
    mesh.current.instanceMatrix.needsUpdate = true;
    mesh.current.computeBoundingSphere();
  }, [graph]);

  useEffect(() => {
    lights.fill(0);
    lit.forEach((i) => (lights[i] = 1));
    const attr = mesh.current.geometry.getAttribute("aLit") as THREE.InstancedBufferAttribute;
    if (attr) attr.needsUpdate = true;
  }, [lit, lights]);

  const uniforms = useMemo(() => ({ uTime: { value: 0 }, uFocus: { value: 0 } }), []);
  useFrame((s, dt) => {
    uniforms.uTime.value = s.clock.elapsedTime;
    uniforms.uFocus.value += ((dim ? 1 : 0) - uniforms.uFocus.value) * Math.min(1, dt * 3);
  });

  return (
    <instancedMesh
      ref={mesh}
      args={[undefined, undefined, count]}
      onPointerMove={(e: ThreeEvent<PointerEvent>) => { e.stopPropagation(); onHover(e.instanceId ?? null); }}
      onPointerOut={() => onHover(null)}
    >
      <icosahedronGeometry args={[1, 1]}>
        <instancedBufferAttribute attach="attributes-aColor" args={[colors, 3]} />
        <instancedBufferAttribute attach="attributes-aLit" args={[lights, 1]} />
      </icosahedronGeometry>
      <shaderMaterial
        uniforms={uniforms}
        vertexShader={/* glsl */ `
          attribute vec3 aColor; attribute float aLit;
          uniform float uTime; uniform float uFocus;
          varying vec3 vColor; varying float vLit; varying vec3 vN; varying vec3 vView;
          void main() {
            vec4 wp = modelMatrix * instanceMatrix * vec4(position * (1.0 + aLit * (0.6 + 0.25 * sin(uTime * 4.0))), 1.0);
            vN = normalize(mat3(modelMatrix * instanceMatrix) * normal);
            vView = normalize(cameraPosition - wp.xyz);
            vColor = aColor; vLit = aLit;
            gl_Position = projectionMatrix * viewMatrix * wp;
          }
        `}
        fragmentShader={/* glsl */ `
          uniform float uFocus;
          varying vec3 vColor; varying float vLit; varying vec3 vN; varying vec3 vView;
          void main() {
            float fres = pow(1.0 - max(dot(vN, vView), 0.0), 2.0);
            vec3 base = vColor * (0.55 + fres * 0.9);
            base *= mix(1.0, 0.14, uFocus);            // dim the galaxy when a path is shown
            vec3 lit = vec3(0.35, 1.0, 0.68) * (2.4 + fres * 2.0);
            gl_FragColor = vec4(mix(base, lit, vLit), 1.0);
          }
        `}
      />
    </instancedMesh>
  );
}

function Edges({ graph, dim }: { graph: GraphData; dim: boolean }) {
  const geometry = useMemo(() => {
    // utility hubs (logging, allocation wrappers) are called from everywhere and would draw
    // bright fans across the galaxy; leave their incoming edges out of the backdrop
    const indeg = new Map<number, number>();
    graph.edges.forEach(([, b]) => indeg.set(b, (indeg.get(b) ?? 0) + 1));
    const edges = graph.edges.filter(([, b]) => (indeg.get(b) ?? 0) <= 40);
    const pos = new Float32Array(edges.length * 6);
    const col = new Float32Array(edges.length * 6);
    edges.forEach(([a, b], i) => {
      const A = graph.nodes[a].pos, B = graph.nodes[b].pos;
      pos.set([A[0], A[1], A[2], B[0], B[1], B[2]], i * 6);
      const ca = nodeColor(graph.nodes[a].file), cb = nodeColor(graph.nodes[b].file);
      col.set([ca.r, ca.g, ca.b, cb.r, cb.g, cb.b], i * 6);
    });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
    return geo;
  }, [graph]);
  const mat = useRef<THREE.LineBasicMaterial>(null!);
  useFrame((_, dt) => {
    const target = dim ? 0.035 : 0.11;
    mat.current.opacity += (target - mat.current.opacity) * Math.min(1, dt * 3);
  });
  return (
    <lineSegments geometry={geometry} frustumCulled={false}>
      <lineBasicMaterial ref={mat} vertexColors transparent opacity={0.11} depthWrite={false}
        blending={THREE.AdditiveBlending} />
    </lineSegments>
  );
}

function Stars() {
  const geo = useMemo(() => {
    const n = 4000;
    const p = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const r = 260 + Math.random() * 300;
      const t = Math.random() * Math.PI * 2, u = Math.acos(2 * Math.random() - 1);
      p.set([r * Math.sin(u) * Math.cos(t), r * Math.cos(u), r * Math.sin(u) * Math.sin(t)], i * 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(p, 3));
    return g;
  }, []);
  return (
    <points geometry={geo}>
      <pointsMaterial size={1.1} sizeAttenuation={false} color="#8b93a8" transparent opacity={0.55} />
    </points>
  );
}

function Scene({ graph, focus, autoRotate }: { graph: GraphData; focus: GalaxyFocus; autoRotate: boolean }) {
  const controls = useRef<CameraControls>(null!);
  const [hover, setHover] = useState<number | null>(null);
  const byName = useMemo(() => {
    const m = new Map<string, number>();
    graph.nodes.forEach((n, i) => { if (!m.has(n.name)) m.set(n.name, i); });
    return m;
  }, [graph]);

  const pathIdx = useMemo(
    () => (focus.path ?? []).map((n) => byName.get(n)).filter((i): i is number => i !== undefined),
    [focus.path, byName],
  );
  const lit = useMemo(() => {
    const s = new Set(pathIdx);
    const t = focus.target ? byName.get(focus.target) : undefined;
    if (t !== undefined) s.add(t);
    return s;
  }, [pathIdx, focus.target, byName]);

  const ghosts = focus.ghosts ?? [];
  const ghostAnchors = ghosts.map((g, k) => {
    const near = g.near.map((n) => byName.get(n)).find((i) => i !== undefined);
    const anchor = near !== undefined ? new THREE.Vector3(...graph.nodes[near].pos) : new THREE.Vector3(0, 0, 0);
    const dir = anchor.clone().normalize();
    if (dir.lengthSq() < 0.1) dir.set(1, 0.3, 0.2).normalize();
    const pos = dir.multiplyScalar(118 + k * 14).add(new THREE.Vector3(0, 10 + k * 8, 0));
    return { ...g, pos, anchor: near !== undefined ? anchor : null };
  });

  useEffect(() => {
    const c = controls.current;
    if (!c) return;
    if (ghostAnchors.length && !pathIdx.length) {
      // side view: galaxy on one side, the ghost adrift on the other, tether between them
      const g = ghostAnchors[0].pos;
      const mid = g.clone().multiplyScalar(0.5);
      const perp = new THREE.Vector3().crossVectors(g, new THREE.Vector3(0, 1, 0)).normalize();
      const eye = mid.clone().add(perp.multiplyScalar(g.length() * 1.55)).add(new THREE.Vector3(0, 30, 0));
      c.setLookAt(eye.x, eye.y, eye.z, mid.x, mid.y, mid.z, true);
      return;
    }
    const pts = pathIdx.map((i) => new THREE.Vector3(...graph.nodes[i].pos));
    ghostAnchors.forEach((g) => pts.push(g.pos.clone()));
    if (focus.target && byName.has(focus.target)) pts.push(new THREE.Vector3(...graph.nodes[byName.get(focus.target)!].pos));
    if (!pts.length) {
      c.setLookAt(-48, 70, 285, -48, 0, 0, true);
      return;
    }
    const box = new THREE.Box3().setFromPoints(pts);
    const center = box.getCenter(new THREE.Vector3());
    const size = Math.max(95, box.getSize(new THREE.Vector3()).length());
    const dir = center.clone().normalize();
    if (dir.lengthSq() < 0.1) dir.set(0, 0.3, 1);
    const eye = center.clone().add(dir.multiplyScalar(size * 1.25)).add(new THREE.Vector3(0, size * 0.25, 0));
    c.setLookAt(eye.x, eye.y, eye.z, center.x, center.y, center.z, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathIdx.join(","), ghosts.map((g) => g.name).join(","), focus.target]);

  useFrame((_, dt) => {
    if (autoRotate && controls.current && !lit.size && !ghosts.length) controls.current.azimuthAngle += dt * 0.04;
  });

  const hovered = hover !== null ? graph.nodes[hover] : null;
  return (
    <>
      <CameraControls ref={controls} minDistance={20} maxDistance={420} smoothTime={0.9} />
      <Stars />
      <Edges graph={graph} dim={lit.size > 0 || ghosts.length > 0} />
      <Nodes graph={graph} lit={lit} dim={lit.size > 0 || ghosts.length > 0} onHover={setHover} />
      {pathIdx.length > 1 && <PathBeam points={pathIdx.map((i) => graph.nodes[i].pos)} />}
      {ghostAnchors.map((g) => (
        <Ghost key={g.name} name={g.name} position={g.pos} anchor={g.anchor} near={g.near} note={g.note} />
      ))}
      {hovered && (
        <Html position={hovered.pos} center style={{ pointerEvents: "none" }}>
          <div className="galaxy-tip">
            <b>{hovered.name}()</b>
            <span>{hovered.file}:{hovered.line}</span>
          </div>
        </Html>
      )}
      {pathIdx.length > 0 && pathIdx.map((i, k) => (
        <Html key={`lbl-${i}`} position={graph.nodes[i].pos} style={{ pointerEvents: "none" }}>
          <div className={`galaxy-label ${k === pathIdx.length - 1 ? "target" : ""}`}>{graph.nodes[i].name}</div>
        </Html>
      ))}
      <EffectComposer multisampling={0}>
        <Bloom mipmapBlur intensity={1.1} luminanceThreshold={0.2} radius={0.7} />
        <Vignette offset={0.2} darkness={0.8} />
      </EffectComposer>
    </>
  );
}

export default function Galaxy({ graph, focus = {}, autoRotate = true }: {
  graph: GraphData; focus?: GalaxyFocus; autoRotate?: boolean;
}) {
  return (
    <Canvas
      dpr={[1, 1.75]}
      gl={{ antialias: false, powerPreference: "high-performance" }}
      camera={{ position: [-48, 70, 285], fov: 45, near: 0.5, far: 2000 }}
      onCreated={({ gl }) => gl.setClearColor("#05060a")}
    >
      <Scene graph={graph} focus={focus} autoRotate={autoRotate} />
    </Canvas>
  );
}
