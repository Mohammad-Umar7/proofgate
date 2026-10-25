# Build progress (updated 2026-10-25)

## Done and pushed (~185 commits on main)
- **Engine** (`engine/proofgate`): nine-stage triage pipeline, FastAPI + SSE, CLI, SQLite store,
  arena, SlopBench, export for the static demo, draft-PR publisher, Docker + OpenShell sandboxes.
- **FixBench** (`engine/proofgate/fixbench`): instances from curl's advisory feed, sandboxed
  build-and-test harness (curl's own runtests.pl, valgrind on regression tests, stunnel/sshd, NTLM,
  checksrc reported separately), native tool-calling Nemotron agent, strict grading, cascade metric.
  Methodology: `docs/FIXBENCH.md`. CI reproduces one instance end to end on every push.
- **Web** (`web/`): landing (gate hero, helix, FixBench headline), console, code galaxy, arena,
  SlopBench, FixBench (per-CVE replay, test lights, agent patch vs maintainers' patch). Vercel.

## Results (all live on Token Factory)
- SlopBench, 197 curl reports: full pipeline 0/148 CVEs wrongly dismissed, $0.007/report, $1.39 total.
  Ablation without grounding: 0/49 slop closed, ranking AUC 0.53 (vs 0.67 with grounding).
- FixBench, 27 validated curl CVEs (2 dropped, listed): Super 8/27 ($0.62/fix), Ultra 9/27
  ($1.98/fix), Super-then-Ultra cascade 11/27 (41%, $1.62/fix), 0 fixes broke a nearby test.
- Nano run in progress (2026-10-25); add it with `proofgate fixbench table` +
  `proofgate export-web --only fixbench`.

## Credits
Token Factory: $25 promo redeemed 2026-10-25 (balance read $9.19 after the FixBench runs; usage posts
with a delay). FixBench Ultra is the expensive part (~$0.66/CVE); Super ~$0.18/CVE, Nano ~$0.04/CVE.

## Waiting on the team
1. Record the video (`docs/VIDEO.md`), personalize the ✍️ items in `docs/FEEDBACK.md`.
2. Fill the Devpost form from `docs/DEVPOST.md` (pitch, About, Built with, gallery incl. fixbench.jpg).
3. Optional: join the Nebius Builders Program for +$25 Token Factory credits.

## Local setup notes (Windows)
- Python venv: `%USERPROFILE%\.cache\proofgate\venv` (session folder path too long for tree-sitter).
- curl clone + caches: `%USERPROFILE%\.cache\proofgate\`. FixBench configure cache: `...\fixbench\`.
- Docker Desktop must be running for FixBench (image `proofgate/curl-test:3`, volume `proofgate-ccache`).
  If it fails to start with a secrets-engine socket error, move
  `%LOCALAPPDATA%\docker-secrets-engine` aside and start it again.
- Web: `cd web && npm run dev`. Engine: `proofgate serve`.
