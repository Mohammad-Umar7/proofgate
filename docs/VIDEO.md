# Demo video script (under 3:00)

Rules: public YouTube, under 3 minutes, no copyrighted music, say "Nebius Token Factory" and
"NVIDIA Nemotron" out loud. Record at 1920x1080 on the hosted demo (https://proofgate-ten.vercel.app).
Good CVE to replay on FixBench: CVE-2026-92390 (Ultra, 24 replies, first test run passes, checksrc clean).

| Time | Screen | Voice-over |
|---|---|---|
| 0:00–0:12 | Landing hero, slow push toward the gate | "In January 2026, curl ended its bug bounty. AI made fake vulnerability reports free to produce, and every one costs a volunteer an hour to disprove." |
| 0:12–0:22 | Scroll: problem section, facts | "ProofGate makes proving them cheap, and for the real bugs it goes all the way to a tested patch." |
| 0:22–0:55 | Console: invented-function sample plays; stages light up | "Claims are extracted by NVIDIA Nemotron Nano on Nebius Token Factory. Then grounding: this function has never existed, not in this release, not in any of forty thousand commits. Line 3987? The file has 3,086 lines." |
| 0:55–1:08 | Evidence card: ledger, diff, Ultra's challenge | "The maintainer gets line-linked proof and a reply draft. Nemotron Ultra writes it, then argues the reporter's side, so we never dismiss a real bug on a model's word." |
| 1:08–1:22 | SlopBench page | "On curl's own public record, 197 real reports, ProofGate wrongly dismissed zero of 148 real CVEs, for under a cent per report." |
| 1:22–1:35 | FixBench hero: KPIs and the flow strip | "Triage is half the job. FixBench asks: can an open model fix real curl security bugs? 27 published CVEs, each with the regression test curl's maintainers wrote." |
| 1:35–2:15 | FixBench: open a fixed CVE, press Replay; transcript streams (reproduce in red, edits, build + test in green) | "The agent gets only the public advisory and the vulnerable code. It reproduces the failure in a sandbox with no network, reads the code, edits C, then compiles curl and runs curl's own tests, and when they fail, it reads the output and tries again. Every step is a real Nemotron tool call on Token Factory." |
| 2:15–2:32 | The agent's diff next to the maintainers' diff | "Here is its patch next to the one curl actually shipped. A fix only counts if a fresh build passes the regression test and every nearby test." |
| 2:32–2:47 | Cascade panel and the model table | "Super and Ultra fix different bugs, so we route by job: Super first, Ultra only when Super fails. Eleven of twenty-seven real CVEs fixed, a dollar sixty-two per verified fix, and not one fix broke another test." |
| 2:47–3:00 | Repo URL, "Built on" strip | "Nemotron on Nebius Token Factory, Tavily, NVIDIA OpenShell. Open source. A human always makes the final call." |

Shot list to capture beforehand: hero (10 s loop), console replay at 1x, evidence card scroll,
SlopBench page, FixBench page (KPIs, a Replay of a fixed CVE, the two diffs, the model table).
