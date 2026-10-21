# Demo video script (under 3:00)

Rules: public YouTube, under 3 minutes, no copyrighted music, say "Nebius Token Factory" and
"NVIDIA Nemotron" out loud. Record at 1920x1080; use the hosted demo plus one live run.

| Time | Screen | Voice-over |
|---|---|---|
| 0:00–0:15 | Landing hero, slow push toward the gate | "In January 2026, curl ended its bug bounty. AI made fake vulnerability reports free to produce, and every one costs a volunteer an hour to disprove." |
| 0:15–0:30 | Scroll: problem section, the curl slop list | "ProofGate makes proving them cheap. It checks every claim in a report against the real code, at the exact version, before a human spends time on it." |
| 0:30–1:10 | Console: invented-function sample plays; stages light up | "Claims are extracted by NVIDIA Nemotron Nano on Nebius Token Factory. Then grounding: this function has never existed — not in this release, not in any of forty thousand commits. Line 3987? The file has 3,086 lines. The quoted code never existed either." |
| 1:10–1:30 | Galaxy panel: ghost node adrift | "Every real curl function is a star here. The one this report cites floats outside, connected to nothing." |
| 1:30–1:50 | Evidence card: ledger, diff, reply draft | "The maintainer gets line-linked proof and a polite reply ready to send. Nemotron Ultra writes it, then argues the reporter's side to make sure we are not dismissing a real bug." |
| 1:50–2:10 | Known-CVE sample: DUPLICATE; prompt-injection sample: flagged | "Duplicates of published advisories are caught. Reports that try to talk to the AI are treated as data and flagged." |
| 2:10–2:30 | Arena: 10–0 scoreboard; SlopBench page | "A red-team agent writes sneakier fakes every level. And on SlopBench — curl's own public record — we measure the one number that matters most: real vulnerabilities wrongly dismissed." |
| 2:30–2:50 | Architecture: Nemotron roles, OpenShell sandbox, fix loop | "Nano, Nano Omni, Super and Ultra each have one job, all on Token Factory. Reproduced bugs run in an NVIDIA OpenShell sandbox with no network, and go to a tested patch." |
| 2:50–3:00 | GitHub Action snippet, repo URL | "Open source, one line to install. A human always makes the final call." |

Shot list to capture beforehand: hero (10 s loop), console run (record at 1x), galaxy ghost,
evidence card scroll, arena, bench, a live run once `NEBIUS_API_KEY` is set (shows real Token
Factory cost in the counter).
