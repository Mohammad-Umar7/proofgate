"use client";

import { Component, type ReactNode, useEffect, useState } from "react";
import { hasWebGL } from "@/lib/webgl";
import styles from "./Guard3D.module.css";

type Reason = "off" | "crashed";

class Boundary extends Component<{ fallback: (r: Reason) => ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error: unknown) { console.warn("[proofgate] 3D view stopped:", error); }
  render() { return this.state.failed ? this.props.fallback("crashed") : this.props.children; }
}

/** The explanation shown where a 3D view would be. */
export function No3D({ what, reason, className }: { what: string; reason: Reason; className?: string }) {
  return (
    <div className={`${styles.note} ${className ?? ""}`} role="note">
      <b>{reason === "off" ? `The 3D ${what} needs WebGL, which is turned off in this browser.`
        : `The 3D ${what} could not start in this browser.`}</b>
      <span>Everything else on this page works. To see it, turn on hardware acceleration, or open the page in a
        current Chrome, Edge or Firefox.</span>
    </div>
  );
}

/** Mount a three.js view only where WebGL works. Without WebGL, or if the view throws, show a short
 *  explanation in its place instead of a blank canvas or a page that fails to render. */
export function Guard3D({ what, children, fallback, className }: {
  what: string; children: ReactNode; fallback?: (r: Reason) => ReactNode; className?: string;
}) {
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => setOk(hasWebGL()), []);
  const fb = fallback ?? ((r: Reason) => <No3D what={what} reason={r} className={className} />);
  if (ok === null) return null;
  if (!ok) return <>{fb("off")}</>;
  return <Boundary fallback={fb}>{children}</Boundary>;
}
