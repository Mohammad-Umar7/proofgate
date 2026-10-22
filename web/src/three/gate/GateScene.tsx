"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Bloom, ChromaticAberration, EffectComposer, Noise, Vignette } from "@react-three/postprocessing";
import { BlendFunction } from "postprocessing";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { Beam, Dust, Floor } from "./Atmosphere";
import { Embers } from "./Embers";
import { Gate } from "./Gate";
import { makeShards } from "./data";
import { Shards } from "./Shards";

// Scroll choreography: hero framing -> approach -> membrane fills the view -> through the ring
// -> cruising toward the maintainer beacon. Positions and look targets are splines, so any
// scroll position is a smooth, deterministic shot.
const PATH = new THREE.CatmullRomCurve3([
  new THREE.Vector3(-34, 5, 30),
  new THREE.Vector3(-25, 3.2, 15),
  new THREE.Vector3(-13, 1.4, 4.5),
  new THREE.Vector3(-2.5, 0.5, 1.2),
  new THREE.Vector3(12, 1.0, 2.6),
  new THREE.Vector3(34, 2.6, 5.5),
], false, "centripetal");
const LOOK = new THREE.CatmullRomCurve3([
  new THREE.Vector3(-9, 1, -10),
  new THREE.Vector3(-3, 0.6, -3),
  new THREE.Vector3(0, 0, 0),
  new THREE.Vector3(18, 0, 0),
  new THREE.Vector3(70, 0, 0),
  new THREE.Vector3(78, 0, 0),
], false, "centripetal");

function CameraRig({ scroll }: { scroll: React.RefObject<number> }) {
  const { camera, pointer } = useThree();
  const target = useMemo(() => new THREE.Vector3(), []);
  const look = useMemo(() => new THREE.Vector3(-9, 1, -10), []);
  const lookGoal = useMemo(() => new THREE.Vector3(), []);
  useFrame((state, dt) => {
    const t = state.clock.elapsedTime;
    const s = Math.min(1, Math.max(0, scroll.current ?? 0));
    const e = s * s * (3 - 2 * s);
    const calm = 1 - e; // drift and pointer parallax fade out as we fly in
    PATH.getPointAt(e, target);
    LOOK.getPointAt(e, lookGoal);
    target.x += (Math.sin(t * 0.07) * 2.2 + pointer.x * 3) * calm;
    target.y += (Math.sin(t * 0.11) * 1.0 + pointer.y * 2) * calm;
    target.z += Math.cos(t * 0.05) * 1.5 * calm;
    camera.position.lerp(target, 1 - Math.exp(-dt * 3.2));
    look.lerp(lookGoal, 1 - Math.exp(-dt * 3.2));
    camera.lookAt(look);
  });
  return null;
}

export default function GateScene({ quality = "high", progress }: {
  quality?: "high" | "low";
  /** 0..1 scroll progress through the pinned hero, owned by the page */
  progress?: React.RefObject<number>;
}) {
  const fallback = useRef(0);
  const scroll = progress ?? fallback;
  const [reduced, setReduced] = useState(false);
  const data = useMemo(() => makeShards(quality === "high" ? 1500 : 700), [quality]);

  useEffect(() => {
    setReduced(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }, []);

  const timeScale = reduced ? 0.25 : 1;
  return (
    <Canvas
      dpr={[1, 1.75]}
      gl={{ antialias: false, powerPreference: "high-performance", alpha: false }}
      camera={{ position: [-34, 5, 30], fov: 42, near: 0.1, far: 600 }}
      onCreated={({ gl, scene }) => {
        gl.setClearColor("#05060a");
        scene.fog = new THREE.FogExp2("#05060a", 0.0065);
      }}
    >
      <CameraRig scroll={scroll} />
      <Dust count={quality === "high" ? 7000 : 3000} />
      <Floor />
      <Beam />
      <Gate data={data} timeScale={timeScale} />
      <Shards data={data} timeScale={timeScale} />
      <Embers data={data} timeScale={timeScale} perShard={quality === "high" ? 14 : 6} />
      <EffectComposer multisampling={0}>
        <Bloom mipmapBlur intensity={1.25} luminanceThreshold={0.12} luminanceSmoothing={0.25} radius={0.78} />
        <ChromaticAberration
          blendFunction={BlendFunction.NORMAL}
          offset={new THREE.Vector2(0.0009, 0.0006)}
          radialModulation
          modulationOffset={0.35}
        />
        <Noise opacity={0.035} premultiply />
        <Vignette eskil={false} offset={0.18} darkness={0.85} />
      </EffectComposer>
    </Canvas>
  );
}
