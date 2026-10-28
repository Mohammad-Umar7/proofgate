import styles from "./Status.module.css";

/** What a view shows while its data or 3D code is still on the way, so it never reads as broken. */
export function Loading({ label, className }: { label: string; className?: string }) {
  return (
    <div className={`${styles.box} ${className ?? ""}`} role="status" aria-live="polite">
      <i className={styles.spin} aria-hidden />
      <span>{label}</span>
    </div>
  );
}

/** A failed fetch: say what is missing and offer the one fix a visitor has, which is to retry. */
export function LoadError({ what, className }: { what: string; className?: string }) {
  return (
    <div className={`${styles.box} ${styles.error} ${className ?? ""}`} role="alert">
      <b>{what} did not load.</b>
      <span>Check your connection, then try again.</span>
      <button className="btn" onClick={() => window.location.reload()}>Retry</button>
    </div>
  );
}
