"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Nav.module.css";

const LINKS = [
  { href: "/console/", label: "Console" },
  { href: "/galaxy/", label: "Code galaxy" },
  { href: "/arena/", label: "Arena" },
  { href: "/bench/", label: "SlopBench" },
];

export function Nav() {
  const path = usePathname();
  return (
    <header className={styles.nav}>
      <div className={styles.inner}>
        <Link href="/" className={styles.brand} aria-label="ProofGate home">
          <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden>
            <defs>
              <linearGradient id="pg" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#e8eaf0" />
                <stop offset="1" stopColor="#7d8496" />
              </linearGradient>
            </defs>
            <circle cx="16" cy="16" r="12.5" fill="none" stroke="url(#pg)" strokeWidth="2.4" />
            <circle cx="16" cy="16" r="6.5" fill="none" stroke="url(#pg)" strokeWidth="2.4" opacity=".55" />
            <rect x="15" y="1" width="2" height="30" fill="#05060a" />
            <circle cx="16" cy="16" r="2.2" fill="#3ddc97" />
          </svg>
          <span>ProofGate</span>
        </Link>
        <nav className={styles.links}>
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} className={path?.startsWith(l.href) ? styles.active : undefined}>
              {l.label}
            </Link>
          ))}
        </nav>
        <a className={styles.gh} href="https://github.com/Mohammad-Umar7/proofgate" target="_blank" rel="noreferrer">
          GitHub
        </a>
      </div>
    </header>
  );
}
