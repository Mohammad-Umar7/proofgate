import type { CSSProperties } from "react";
import styles from "./Status.module.css";

type Place = { className?: string; style?: CSSProperties; /** cover the parent, e.g. a canvas area */ fill?: boolean };
const cls = (extra: string, { className, fill }: Place) =>
  [styles.box, extra, fill ? styles.fill : "", className ?? ""].filter(Boolean).join(" ");

/** What a view shows while its data or 3D code is still on the way, so it never reads as broken. */
export function Loading({ label, ...place }: { label: string } & Place) {
  return (
    <div className={cls("", place)} style={place.style} role="status" aria-live="polite">
      <i className={styles.spin} aria-hidden />
      <span>{label}</span>
    </div>
  );
}

/** A failed fetch: say what is missing and offer the one fix a visitor has, which is to retry. */
export function LoadError({ what, ...place }: { what: string } & Place) {
  return (
    <div className={cls(styles.error, place)} style={place.style} role="alert">
      <b>{what} did not load.</b>
      <span>Check your connection, then try again.</span>
      <button className="btn" onClick={() => window.location.reload()}>Retry</button>
    </div>
  );
}
