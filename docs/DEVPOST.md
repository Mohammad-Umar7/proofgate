# Devpost submission text (copy-paste ready)

## Step 1: Project overview

**Project name** (≤60): `ProofGate`

**Elevator pitch** (≤200):
> AI made fake security reports free to produce. ProofGate makes proving them cheap: every claim is checked against the real code and git history, on NVIDIA Nemotron via Nebius Token Factory.

Thumbnail: crop `docs/img/hero.jpg` to 3:2.

## Step 2: Project details

**Built with** (tags): `nvidia-nemotron`, `nebius-token-factory`, `nebius-ai-cloud`, `tavily`,
`nvidia-openshell`, `python`, `fastapi`, `tree-sitter`, `git`, `sqlite`, `next.js`, `react`,
`three.js`, `react-three-fiber`, `glsl`, `typescript`, `docker`, `github-actions`, `osv`

**Try it out links**: https://proofgate-ten.vercel.app · https://github.com/Mohammad-Umar7/proofgate

**Image gallery**: `docs/img/hero.jpg`, `console.jpg`, `evidence.jpg`, `galaxy.jpg`, `arena.jpg`

**About the project** (Markdown):

```markdown
## Inspiration
In January 2026 curl ended its bug bounty. Its maintainer keeps a public list of AI-generated
"slop" reports: functions that never existed, line numbers past the end of the file, code nobody
wrote. Each one costs a volunteer real time to disprove, and the flood buries real vulnerabilities.
We wanted the proof to be as cheap as the fake.

## What it does
ProofGate checks every claim in a vulnerability report against the real repository, at the exact
version, before a maintainer reads it. Nine stages, cheapest first: intake (Nemotron Nano Omni reads
screenshots), claim extraction (Nemotron Nano), grounding (git + tree-sitter over the full history,
then Nemotron Super over the real functions), prior art (curl's advisories, OSV and Tavily), the
project's own security policy, a network-less sandbox for the reporter's reproduction (NVIDIA
OpenShell), a verdict from a rule table that Nemotron Ultra explains and then argues against, a fix
loop for reproduced bugs, and a line-linked evidence card with a reply draft.

Two guarantees: only deterministic proof can dismiss a report, and every report is checked against
the code as it was on the day it was filed, so renamed or removed code is never called invented.

## How we built it
Python 3.11 engine (FastAPI, tree-sitter, git plumbing, SQLite), every model call through Nebius
Token Factory with the OpenAI SDK and four Nemotron sizes routed by job, with live cost accounting
and a per-report budget. Next.js + React Three Fiber front end with custom GLSL: a GPU-driven gate
where slop dissolves, a 3D galaxy of curl's 4,291 functions where invented ones float as ghost
nodes, and a helix of 40,000 commits swept by the pickaxe search.

## SlopBench
197 disclosed curl reports: every entry on curl's public slop list and every curl CVE whose
advisory links the original HackerOne report, with leakage control so ProofGate cannot look up
the answer. We report how much slop is closed with proof and, most importantly, how many real
vulnerabilities would have been wrongly dismissed.

## Challenges
Our first benchmark run dismissed 39 real CVEs. The causes were instructive: we were checking 2021
reports against 2026 code, reading reporters' own PoC helpers as claims about curl, and treating
removed files as invented. Time-travel grounding and reporter-code detection brought that down to
a handful, which taught us that "don't dismiss real bugs" has to be measured, not assumed.

## What we learned
Most slop can be disproved without asking a model anything. Models are most valuable where we put
them: reading real code, applying policy, explaining, and attacking our own verdicts.

## What's next
Plausibility ranking of the NEEDS INFO queue, more projects through the GitHub Action, and a hosted
service maintainers can point their security inbox at.
```

**Demo video URL**: YouTube link (public, under 3:00).

## Step 3: Additional info

- Track: **Coding and agentic engineering** · New project: **New**
- Repo: https://github.com/Mohammad-Umar7/proofgate · Demo: https://proofgate-ten.vercel.app
- Tavily used: **Yes** (runtime prior-art search, `engine/proofgate/tavily.py`)
- Feedback answers: see `docs/FEEDBACK.md` (personalize the ✍️ items)
- AI tools used: list the AI coding tools the team used (for example Claude Code)
