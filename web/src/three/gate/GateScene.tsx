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

function CameraRig({ scroll }: { scroll: React.RefObject<number> }) {
  const { camera, pointer } = useThree();
  const target = useMemo(() => new THREE.Vector3(), []);
  const look = useMemo(() => new THREE.Vector3(), []);
  useFrame((state, dt) => {
    const t = state.clock.elapsedTime;
    const s = scroll.current ?? 0;
    // slow cinematic drift + pointer parallax; scrolling dollies toward and through the gate
    // three-quarter view from the incoming side; scrolling flies through the gate
    target.set(
      -34 + s * 31 + Math.sin(t * 0.07) * 2.2 + pointer.x * 3,
      5 - s * 4 + Math.sin(t * 0.11) * 1.0 + pointer.y * 2,
      30 - s * 29 + Math.cos(t * 0.05) * 1.5,
    );
    camera.position.lerp(target, 1 - Math.exp(-dt * 1.6));
    look.lerp(new THREE.Vector3(-9 + s * 40, 1 - s, -10 + s * 10), 1 - Math.exp(-dt * 2));
    camera.lookAt(look);
  });
  return null;
}

export default function GateScene({ quality = "high" }: { quality?: "high" | "low" }) {
  const scroll = useRef(0);
  const [reduced, setReduced] = useState(false);
  const data = useMemo(() => makeShards(quality === "high" ? 1500 : 700), [quality]);

  useEffect(() => {
    setReduced(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    const onScroll = () => {
      scroll.current = Math.min(1, window.scrollY / (window.innerHeight * 1.2));
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
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
