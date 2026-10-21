# ProofGate — the original pitch

**Pitch:** AI made fake security reports free to produce. ProofGate makes proving them cheap.
**Track:** Coding & Agentic Engineering

## The problem

Open-source projects like curl run on billions of devices and are maintained by volunteers.
AI-generated fake vulnerability reports cite code that doesn't exist and bugs that can't happen, and
each one costs a volunteer an hour to disprove. Projects have started shutting down bug bounties and
pausing reports entirely, so real vulnerabilities go unreported.

## What it does

ProofGate is an open-source agent that checks every incoming vulnerability report against the real
code, and for confirmed bugs it goes all the way to a tested fix. A human always makes the final call,
and ProofGate never writes exploit code.

Pipeline (cheap checks first, expensive reasoning last):

1. **Intake** — reads report text, screenshots, and terminal output in images (Nemotron Nano Omni / VL).
2. **Claim extraction** — JSON of every checkable claim: file, function, line, version, quoted code,
   CVE IDs (Nemotron Nano).
3. **Grounding** — checks out the repo at the claimed version, verifies claims with ripgrep and
   tree-sitter, then reasons over the real code: is the path reachable or already guarded?
   (Nemotron Super, long context).
4. **Prior art** — advisories, mailing lists, issues: duplicates or already-fixed bugs (Tavily + OSV).
5. **Project rules** — a rulebook auto-built from the project's SECURITY.md and past advisories.
6. **Reproduction** — runs the reporter's own PoC in an NVIDIA OpenShell sandbox, no network, no secrets.
7. **Adjudication** — forms a verdict, then an adversarial second pass challenges it (Nemotron Ultra).
8. **Triage to fix** — for reproduced bugs: regression test from the PoC, draft patch, run the test
   suite to prove it, open a draft PR for the maintainer.
9. **Evidence card** — verdict, line-linked evidence, duplicates, cost, reproduction log.

Verdicts: **UNGROUNDED** (red), **DUPLICATE** (blue), **NEEDS INFO** (amber), **REPRODUCED** (green).

## Extra features

- **Adversarial arena** — a red-team agent writes increasingly sneaky fake reports to try to fool
  ProofGate, with a round-by-round scoreboard. Judges can paste their own fake report.
- **SlopBench** — a labeled benchmark from curl's publicly disclosed reports (real CVEs vs slop):
  agreement with the curl team, valid reports wrongly dismissed (target zero), cost and time per report,
  ablations (grounding on/off, single-model vs routed models). Published in the repo.
- **Full history replay** — run curl's public report history through ProofGate.
- **GitHub Action** — any project installs it in one line.

## Visual design

- Dark, clean security-tool aesthetic (GitHub dark / Linear), monospace for code, color only for meaning.
- Live pipeline view: stages light up green or red with live time and cost counters.
- Evidence card: claimed code vs actual code side by side, mismatches highlighted red.
- 3D codebase map (Three.js): functions as nodes, calls as edges; the claimed path glows if reachable;
  hallucinated functions appear as a floating, disconnected ghost node.
- 3D landing hero (Three.js): reports stream as particles through glowing gates; slop dissolves,
  duplicates merge, real bugs pass through.
- Live sandbox terminal with sanitizer output highlighted.
- Duplicate cluster graph (2D). Benchmark dashboard with clean 2D charts.

## Sponsor tech

- Every LLM call through **Nebius Token Factory** (OpenAI-compatible client), Nemotron models with
  distinct jobs per size.
- Sandbox and jobs on Nebius AI Cloud compute (optional per FAQ).
- NVIDIA OpenShell for untrusted PoC execution.
- **Tavily** at runtime for prior-art search ($3k bonus).

## Security rules for the system itself

- Report text is treated strictly as data.
- The reasoning agent holds no credentials and can't post, push, or merge.
- A separate orchestrator posts results.
- The sandbox is ephemeral and denies network access by default.

## Stack

Python + FastAPI, Next.js + Three.js, SQLite, tree-sitter, ripgrep, GitHub API.

## Submission must-haves

- Public GitHub repo, Apache-2.0 license visible in the About panel.
- README: one-command setup, "Built on Nebius + NVIDIA" section with cost table and SlopBench results.
- Hosted demo, sample reports preloaded, no login, live until Dec 15.
- Public YouTube video under 3:00, no copyrighted music.
- Detailed feedback section (eligible for the $100 feedback prize).
