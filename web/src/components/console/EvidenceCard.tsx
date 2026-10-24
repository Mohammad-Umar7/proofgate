"use client";

import { motion } from "motion/react";
import { useState } from "react";
import { VERDICT_META, type Card } from "@/lib/types";
import styles from "./card.module.css";

const STATUS = {
  verified: { label: "verified", css: "green" },
  contradicted: { label: "contradicted", css: "red" },
  partial: { label: "partial", css: "amber" },
  unverifiable: { label: "unverifiable", css: "" },
} as const;

function norm(s: string) {
  return s.replace(/\/\*.*?\*\/|\/\/.*$/g, "").replace(/\s+/g, " ").trim();
}

function Diff({ claimed, actual, missing, file, line, url }: Card["diffs"][number]) {
  const miss = new Set((missing ?? []).map(norm));
  return (
    <div className={styles.diff}>
      <div className={styles.diffCol}>
        <div className={styles.diffHead}><span className="chip red">reporter claims</span></div>
        <pre>
          {(claimed ?? "").split("\n").map((l, i) => (
            <div key={i} className={miss.has(norm(l)) ? styles.lineBad : styles.line}>{l || " "}</div>
          ))}
        </pre>
      </div>
      <div className={styles.diffCol}>
        <div className={styles.diffHead}>
          <span className="chip green">real code</span>
          {file && <a href={url ?? "#"} target="_blank" rel="noreferrer" className={styles.loc}>{file}{line ? `:${line}` : ""} ↗</a>}
        </div>
        <pre>
          {actual ? actual.split("\n").map((l, i) => <div key={i} className={styles.line}>{l || " "}</div>)
            : <div className={styles.none}>No matching code at this version, and the distinctive lines never appear in git history.</div>}
        </pre>
      </div>
    </div>
  );
}

export function EvidenceCard({ card }: { card: Card }) {
  const meta = VERDICT_META[card.verdict];
  const [copied, setCopied] = useState(false);
  const models = Object.entries(card.cost_by_model ?? {});
  return (
    <motion.section
      className={`panel ${styles.card}`}
      style={{ ["--v" as string]: meta.color }}
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.2, 0.8, 0.2, 1] }}
    >
      <header className={styles.banner}>
        <div className={styles.verdict}>
          <span className={`chip ${meta.css}`}><span className="dot" />{meta.label}</span>
          <span className={styles.conf}>confidence {(card.confidence * 100).toFixed(0)}%</span>
        </div>
        <h2>{card.headline}</h2>
        <div className={styles.metaRow}>
          <span>curl {card.version}</span>
          <span>{card.seconds}s</span>
          <span>${card.cost_usd.toFixed(4)} on Token Factory</span>
          {card.commits_searched ? <span>{card.commits_searched.toLocaleString()} commits searched</span> : null}
          {card.report.source_url && <a href={card.report.source_url} target="_blank" rel="noreferrer">original report ↗</a>}
        </div>
      </header>

      {card.flags.includes("prompt-injection") && (
        <div className={styles.alert}>
          <b>Prompt injection detected.</b> The report tries to instruct the triage model. It was treated as data:
          {card.injection.slice(0, 2).map((h, i) => <code key={i}>“{h.excerpt}”</code>)}
        </div>
      )}

      <div className={styles.grid}>
        <div>
          <h3>Why</h3>
          <ul className={styles.reasons}>{card.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
          {card.verdict === "NEEDS_INFO" && card.credibility != null && (
            <div className={styles.cred}>
              <div className={styles.credTop}>
                <span>Queue priority (credibility)</span><b>{card.credibility}</b>
              </div>
              <span className={styles.credBar}><i style={{ width: `${card.credibility}%` }} /></span>
              <ul>{(card.credibility_why ?? []).map((w, i) => <li key={i}>{w}</li>)}</ul>
            </div>
          )}
          {card.challenge && (
            <div className={styles.challenge}>
              <h4>Adversarial pass · Nemotron Ultra argued the reporter&apos;s side</h4>
              <p>{card.challenge}</p>
              <span className={`chip ${card.challenge_changed ? "amber" : card.challenge_upheld ? "green" : ""}`}>
                {card.challenge_changed ? "objection holds: dismissal downgraded to needs info"
                  : card.challenge_upheld ? "verdict stands" : "objection noted for the maintainer"}
              </span>
            </div>
          )}
        </div>
        <div>
          <h3>Reply draft for the maintainer</h3>
          <pre className={styles.reply}>{card.reply_draft}</pre>
          <button className="btn" onClick={() => { navigator.clipboard.writeText(card.reply_draft ?? ""); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>
            {copied ? "Copied" : "Copy reply"}
          </button>
        </div>
      </div>

      <h3>Evidence ledger</h3>
      <div className={styles.ledger}>
        {card.ledger.map((row, i) => {
          const st = STATUS[row.status];
          return (
            <div key={i} className={styles.row}>
              <span className={`chip ${st.css}`}>{st.label}</span>
              <span className={styles.claim}><code>{row.kind}</code> {row.claim}</span>
              <span className={styles.detail}>
                {row.detail}
                {row.url && <a href={row.url} target="_blank" rel="noreferrer"> ↗</a>}
              </span>
              <span className={styles.method}>{row.method}{row.deterministic ? "" : " · model"}</span>
            </div>
          );
        })}
      </div>

      {card.diffs.length > 0 && (<><h3>Claimed code vs real code</h3>{card.diffs.slice(0, 2).map((d, i) => <Diff key={i} {...d} />)}</>)}

      {card.prior_art.length > 0 && (
        <>
          <h3>Prior art</h3>
          <div className={styles.prior}>
            {card.prior_art.slice(0, 5).map((p) => (
              <a key={p.id + p.url} href={p.url} target="_blank" rel="noreferrer" className={styles.priorRow}>
                <span className={styles.bar}><i style={{ width: `${Math.round(p.score * 100)}%` }} /></span>
                <span className="mono">{p.id}</span>
                <span className={styles.priorTitle}>{p.title}</span>
                <span className={styles.method}>{p.source}{p.fixed_in ? ` · fixed in ${p.fixed_in}` : ""}</span>
              </a>
            ))}
          </div>
        </>
      )}

      {card.rules.length > 0 && (
        <>
          <h3>Project policy</h3>
          {card.rules.map((r) => (
            <div key={r.rule} className={styles.rule}><b>{r.title}</b> — {r.reason}</div>
          ))}
        </>
      )}

      {card.sandbox?.ran && (
        <>
          <h3>Sandbox · {card.sandbox.backend} · network {card.sandbox.network}</h3>
          <pre className={styles.term}>{card.sandbox.log.slice(-3000)}</pre>
        </>
      )}

      {models.length > 0 && (
        <>
          <h3>Nemotron on Nebius Token Factory</h3>
          <div className={styles.models}>
            {models.map(([role, m]) => (
              <div key={role}>
                <b>{role}</b><span className="mono">{m.model}</span>
                <span>{m.calls} call{m.calls > 1 ? "s" : ""} · {m.tokens.toLocaleString()} tok · ${m.cost_usd.toFixed(4)} · {(m.ms / 1000).toFixed(1)}s</span>
              </div>
            ))}
          </div>
        </>
      )}
      {models.length === 0 && (
        <p className={styles.offline}>This run used only the deterministic stages (git, tree-sitter, advisories): $0.00.</p>
      )}
    </motion.section>
  );
}
