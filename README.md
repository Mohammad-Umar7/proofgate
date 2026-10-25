<div align="center">

# ProofGate

**AI made fake security reports free to produce. ProofGate makes proving them cheap.**

Evidence-first triage for vulnerability reports: every claim is checked against the real code,
at the exact version, before a volunteer maintainer spends an hour on it.

Built on **NVIDIA Nemotron 3** via **Nebius Token Factory** · **Tavily** · **NVIDIA OpenShell**

**[▶ Live demo: proofgate-ten.vercel.app](https://proofgate-ten.vercel.app)** · [Video](#video) · [SlopBench](#slopbench-measured-on-curls-own-record) · [FixBench](#fixbench-nemotron-fixing-real-curl-cves-judged-by-curls-own-tests) · [Architecture](docs/ARCHITECTURE.md)

![ProofGate: reports stream through the gate; slop dissolves, duplicates merge, real bugs pass](docs/img/hero.jpg)

</div>

## The problem

curl runs on billions of devices and is maintained by volunteers. On 2026-01-26 the project
committed [`BUG-BOUNTY.md: we stop the bug-bounty end of Jan 2026`](https://github.com/curl/curl/commit/ca7ef4b817):
its HackerOne bounty had been flooded with AI-generated reports. The file now says a bounty gives
people incentives to make up "problems" in bad faith. curl's maintainer keeps a
[public list of AI slop reports](https://gist.github.com/bagder/07f7581f6e3d78ef37dfbfc81fd1d1cd):
49 entries as of October 2026, each one cost a volunteer real time to disprove.

These reports cite functions that never existed, line numbers past the end of the file, and code
nobody wrote. Disproving them does not need another model's opinion. It needs the git history.

## What ProofGate does

ProofGate is an open-source agent that checks every incoming report against the real repository,
and for reproduced bugs goes all the way to a tested patch. **A human always makes the final call,
and ProofGate never writes exploit code.**

| | Stage | How | Model / tool |
|---|---|---|---|
| 1 | **Intake** | Splits prose, quoted code, the reporter's own PoC and logs; reads screenshots | Nemotron 3.5 Super VL |
| 2 | **Claims** | Every checkable claim as JSON: file, function, line, version, code, CVE | regex + Nemotron 3 Nano |
| 3 | **Grounding** | `git show/grep/ls-tree` at the claimed version, full-history pickaxe, tree-sitter call graph; then reasoning over the real functions | git, tree-sitter, Nemotron 3 Super |
| 4 | **Prior art** | curl's 239 official advisories, OSV.dev, and a live web search of disclosures and issues | Tavily, OSV |
| 5 | **Policy** | A rulebook built at runtime from the project's own "not a security issue" policy (19 rules for curl) | Nemotron 3 Super |
| 6 | **Reproduce** | Runs only the reporter's steps, in an ephemeral sandbox with no network and no secrets; attributes any crash to project code or reporter code | NVIDIA OpenShell / Docker |
| 7 | **Verdict** | A rule table decides; Ultra explains, then argues the reporter's side | Nemotron 3 Ultra |
| 8 | **Fix** | For reproduced bugs: patch, `git apply --check`, rebuild, rerun, run the area's tests, iterate; draft PR on a fork | Nemotron 3 Super |
| 9 | **Evidence card** | Verdict, line-linked ledger, claimed-vs-real diff, duplicates, cost, reply draft | |

Verdicts: 🔴 **UNGROUNDED** · 🔵 **DUPLICATE** · 🟠 **NEEDS INFO** · 🟢 **REPRODUCED**

### The two guarantees

1. **Only proof can dismiss.** `UNGROUNDED` requires deterministic contradictions (a function that
   never existed in any commit, a line past the end of the file, quoted code that never appeared)
   that outweigh what checks out. Model output can explain, challenge or downgrade a verdict, never
   create a dismissal.
2. **Time-travel grounding.** A report is checked against the release it names, or the newest release
   on the day it was filed, and against the default branch as of that date. Renamed or removed code is
   reported as such ("`lib/vtls/nss.c` existed until 2023-07-29"), never as invented.

![Evidence ledger and claimed-vs-real diff](docs/img/evidence.jpg)

## What it looks like

| Triage console | Code galaxy |
|---|---|
| ![console](docs/img/console.jpg) | ![galaxy](docs/img/galaxy.jpg) |
| Nine stages light up live with time and Token Factory spend; the 3D galaxy reacts. | All 4,291 functions and 9,747 calls of curl 8.23.0 (tree-sitter). Real paths glow; invented functions float outside, connected to nothing. |

| Adversarial arena |
|---|
| ![arena](docs/img/arena.jpg) |
| A red-team agent writes fakes that get closer to the truth each level (real file, real function, real quoted code, then text aimed at the AI). Offline rounds: **ProofGate 10, red team 0.** |

## SlopBench: measured on curl's own record

[`bench/slopbench.jsonl`](bench/slopbench.jsonl) indexes **197 disclosed curl reports**:
**49 slop** (every entry on the public slop list) and **148 valid** (every curl CVE whose
advisory links the original HackerOne report). Report text is fetched from HackerOne's public JSON
into a local cache and is not redistributed. A report's own advisory, its own page and the slop
list itself are excluded from prior art, so ProofGate cannot look up the answer.

<!-- BENCH:START -->
| Configuration | Slop closed with proof | Real CVEs wrongly dismissed | Real CVEs closed as duplicate | Agreement with curl | Cost / report | Time / report |
|---|---|---|---|---|---|---|
| Deterministic only (git + tree-sitter + advisories) | 12% (6/49) | **0** / 148 | 2 | 77% | $0.0000 | 8.0s |
| Full pipeline (routed Nemotron + Tavily) | 8% (4/49) | **0** / 148 | 2 | 76% | $0.0071 | 56.9s |

_Not yet run: Ablation: Nemotron Ultra for every role, Ablation: no grounding._

_Generated 2026-10-25T03:55:58Z by `proofgate bench table`._
<!-- BENCH:END -->

**How to read this.** "Slop closed with proof" counts reports ProofGate would close with a
deterministic contradiction or a matching published advisory. Everything else gets **NEEDS INFO**:
real code is cited but nothing proves the bug, so the maintainer receives the evidence ledger and
a reply draft asking for a reproduction instead of an hour of investigation. "Real CVEs wrongly
dismissed" is the number that must stay at or near zero: those were genuine vulnerabilities.

Reproduce: `proofgate bench build && proofgate bench fetch && proofgate bench run --config deterministic`
(or `--config full` with Token Factory and Tavily keys).

## FixBench: Nemotron fixing real curl CVEs, judged by curl's own tests

Triage is half the job. For a real bug, ProofGate's fix agent writes the patch, and FixBench measures
whether it actually works, the same way coding agents are measured on SWE-bench, but on security bugs
in a 30-year-old C codebase.

**Instances** ([`bench/fixbench.jsonl`](bench/fixbench.jsonl)) come from curl's official advisory feed:
every CVE since 2023 whose fix commit added a regression test (29 candidates, most of them published
in 2026). For each one:

- **base** = the parent of curl's fix commit, i.e. the vulnerable code;
- **fail-to-pass** = the regression test the curl maintainers wrote with the fix;
- **pass-to-pass** = up to 30 existing tests in the same area (shared test keywords);
- **gold patch** = the maintainers' fix, used only to validate the instance, **never shown to the agent**.

An instance is kept only if, in our sandbox build, its regression test **fails on the vulnerable commit
and passes with the maintainers' fix**. Dropped instances are listed with the reason, not hidden.

**The agent** ([`engine/proofgate/fixbench/agent.py`](engine/proofgate/fixbench/agent.py)) is a
native tool-calling loop on Token Factory. It gets the public advisory (fenced as untrusted text)
and the vulnerable checkout:

1. **Reproduce.** It runs the regression test on the untouched build and sees the real failure.
2. **Explore.** `grep`, `ls`, `read`, tree-sitter `outline`/`function`, plus a deterministic first pass
   that locates the identifiers the advisory names.
3. **Edit.** Exact search/replace edits, limited to `.c/.h` files under `lib/`, `src/`, `include/`.
   Edits to tests or build files are refused.
4. **Build and test.** `run_tests` compiles curl (debug build, ccache) and runs curl's own `runtests.pl`
   in a Docker sandbox with `--network none`, a read-only root, no capabilities and hard limits. The
   regression test runs under valgrind, as in curl's CI, so memory errors fail it too. curl's own
   `checksrc.pl` style checker runs on the changed files. Failures (compiler errors, protocol diffs,
   valgrind reports, style warnings) go back to the model, and it iterates, up to 4 test runs and
   40 replies. If a later edit breaks a passing patch, the agent falls back to its last green one.

**Grading is strict.** A CVE counts as fixed only if a fresh build of the agent's final diff passes every
fail-to-pass test **and** every pass-to-pass test. Style is reported separately ("style-clean"), so
an indentation slip is never counted as a broken build.

<!-- FIXBENCH:START -->
<!-- FIXBENCH:END -->

Every transcript, the agent's diff and the maintainers' diff are on the
[FixBench page](https://proofgate-ten.vercel.app/fixbench/). Methodology, dropped instances and threats
to validity: [docs/FIXBENCH.md](docs/FIXBENCH.md). Reproduce (Docker required):
`proofgate fixbench validate && proofgate fixbench run --model super && proofgate fixbench table`.

## Built on Nebius + NVIDIA

**Every model call goes through Nebius Token Factory** with the official `openai` SDK
(`base_url=https://api.tokenfactory.nebius.com/v1/`). Model ids are resolved at startup from
`GET /v1/models`, so the app keeps working as ids evolve. Each Nemotron size has exactly one job:

| Role | Token Factory model id | Job | Why this size | $ / 1M tokens (in / out) |
|---|---|---|---|---|
| nano | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | claims as JSON | high volume, latency-sensitive | 0.06 / 0.24 |
| super | `nvidia/nemotron-3-super-120b-a12b` | real-source reasoning, policy, patches, red team | long context over real code | 0.30 / 0.90 |
| ultra | `nvidia/Nemotron-3-Ultra-550b-a55b` | verdict explanation + adversarial challenge | strongest reasoning, two calls per report | 1.00 / 3.00 |
| omni | `nvidia/Nemotron-3.5-Super-VL` | screenshots, terminal captures | the vision model on Token Factory | 0.30 / 0.90 |

Measured on a live run (one fabricated report, every stage on, Tavily included): **about $0.01 and
40 seconds**, most of it the git history search. Prices are the Token Factory list prices used by
the live cost counter.

- **Cost is a product feature.** Every call records tokens, latency and USD; the console shows live
  spend; `PG_MAX_COST_PER_REPORT` (default $0.25) aborts a run over budget; the public server caps
  daily spend. The deterministic stages handle the bulk of the work for $0.
- **NVIDIA OpenShell** runs reproductions through its Python SDK (`SandboxClient.create_session`
  → `exec` → `delete`) under OpenShell's default-deny network policy with no providers attached.
  A Docker backend (`--network none`, read-only root, dropped capabilities, PID/memory/CPU limits)
  is the fallback.
- **Nebius AI Cloud**: the engine ships as a container (`engine/Dockerfile`) for a Nebius VM or
  Serverless Endpoint; the demo front end is static.
- **Tavily** is called at runtime in the prior-art stage, scoped to disclosure and advisory domains.

## Quick start

**One command** (engine on :8000, web on :3000):

```bash
docker compose up --build
```

Add keys for live mode: copy `engine/.env.example` to `engine/.env` and set `NEBIUS_API_KEY`
(hackathon credits code `NEBIUS-DEVPOST-GLOBAL26`) and `TAVILY_API_KEY`.
Without keys the deterministic stages, the replays, the galaxy and the arena all still work.

Local development:

```bash
pip install -e "./engine[dev]"      # Python 3.11
proofgate check bench/samples/01-ghost-function.json --offline
proofgate arena --offline
proofgate serve                     # API on :8000
cd web && npm ci && npm run dev     # UI on :3000 (NEXT_PUBLIC_API_URL=http://localhost:8000 for live)
```

## GitHub Action

Any project can run ProofGate on issues labeled `security-report`; see
[`action/example-workflow.yml`](action/example-workflow.yml):

```yaml
- uses: Mohammad-Umar7/proofgate/action@main
  with:
    nebius-api-key: ${{ secrets.NEBIUS_API_KEY }}
    tavily-api-key: ${{ secrets.TAVILY_API_KEY }}
```

The triage step receives model keys but **no GitHub token**; a separate posting step comments the
evidence card. It works on any C repository with release tags (`tag-prefix`, `source-dirs` inputs).

## Security of ProofGate itself

- Report text is untrusted data: fenced in a randomized tag on every model call, and scanned for
  text that addresses the triage model (flagged on the card, never obeyed).
- The reasoning stages hold no credentials and cannot post, push or merge. Only the orchestrator
  (`publish.py`) holds a token, and it only opens **draft** PRs on a fork, never upstream.
- Sandboxes are ephemeral, network-less, credential-less and resource-limited.

## Hosted demo

**https://proofgate-ten.vercel.app**: no login, no backend required, so it stays up through
judging. It is a static export of `web/` on Vercel (root directory `web`, redeployed on every push
to `main`): recorded runs of real curl reports in the console, the code galaxy, the arena and
SlopBench. Set `NEXT_PUBLIC_API_URL` to a running engine to switch the console into live mode.

## Video

See [`docs/VIDEO.md`](docs/VIDEO.md) for the script.

## Repository

```
engine/   Python 3.11 package `proofgate`: pipeline stages, sandbox, bench, FastAPI server, CLI
web/      Next.js + React Three Fiber: gate hero, console, code galaxy, arena, SlopBench
bench/    SlopBench index, synthetic samples, results
action/   GitHub Action
docs/     architecture, hackathon brief, video script, feedback
```

Feedback on Token Factory, AI Cloud and Nemotron: [`docs/FEEDBACK.md`](docs/FEEDBACK.md).

Apache-2.0. Built for the Nebius x NVIDIA Global AI Hackathon 2026 (Coding and Agentic Engineering).
