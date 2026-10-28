"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { Guard3D } from "@/components/Guard3D";
import { loadHistory } from "@/lib/api";
import type { History } from "@/three/helix/HistoryHelix";
import styles from "./HelixSection.module.css";

const HistoryHelix = dynamic(() => import("@/three/helix/HistoryHelix"), { ssr: false });

export function HelixSection() {
  const [history, setHistory] = useState<History | null>(null);
  const [scanned, setScanned] = useState(0);
  useEffect(() => { loadHistory().then((h) => setHistory(h as History)).catch(() => {}); }, []);
  const done = history && scanned >= history.total;

  return (
    <section className={styles.wrap}>
      <div className={`container ${styles.head}`}>
        <p className="eyebrow">Grounding, visualized</p>
        <h2>Every claim is checked against every commit since {history?.first.slice(0, 4) ?? "1998"}.</h2>
        <p>
          When a report cites a function, ProofGate looks for it at the claimed release, on the branch as of the
          day the report was filed, and across the project&apos;s entire history with git&apos;s pickaxe. For curl
          that is the whole helix below, searched in about four seconds, at no model cost.
        </p>
      </div>
      <div className={styles.canvas}>
        {history && <Guard3D what="commit helix"><HistoryHelix history={history} onProgress={setScanned} /></Guard3D>}
        {history && (
          <div className={styles.years}>
            {history.months.filter(([ym]) => ym.endsWith("-01") && Number(ym.slice(0, 4)) % 3 === 0).map(([ym]) => (
              <span key={ym}>{ym.slice(0, 4)}</span>
            ))}
          </div>
        )}
        <div className={styles.hud}>
          <code>git log -S&quot;Curl_cookie_parse_header(&quot;</code>
          <div className={styles.count}><b>{scanned.toLocaleString()}</b><span>commits searched</span></div>
          <div className={`${styles.result} ${done ? styles.show : ""}`}>0 matches · this function has never existed</div>
        </div>
      </div>
    </section>
  );
}
