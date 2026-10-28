# Build progress (updated 2026-10-28)

## Done and pushed (~277 commits on main)
- **Engine** (`engine/proofgate`): nine-stage triage pipeline, FastAPI + SSE, CLI, SQLite store,
  arena, SlopBench, export for the static demo, draft-PR publisher, Docker + OpenShell sandboxes.
- **FixBench** (`engine/proofgate/fixbench`): instances from curl's advisory feed, sandboxed
  build-and-test harness (curl's own runtests.pl, valgrind on regression tests, stunnel/sshd, NTLM,
  checksrc reported separately), native tool-calling Nemotron agent, strict grading, cascade metric.
  Methodology: `docs/FIXBENCH.md`. CI reproduces one instance end to end on every push.
- **Web** (`web/`): landing (gate hero, helix, FixBench headline), console, code galaxy, arena,
  SlopBench, FixBench (per-CVE replay, test lights, agent patch vs maintainers' patch). Vercel.
- **Live mode** (engine + site with `NEXT_PUBLIC_API_URL`): the console takes a disclosed HackerOne
  link (fetched at run time); FixBench has Run live (localhost only), streaming steps, test lights,
  live clock and spend. The galaxy now rotates freely over the poles and frames itself beside panels.
- **Onboarding (Oct 28)** (`web/src/components/onboarding`): first-visit welcome, a 15-stop guided
  tour across all six pages that plays the 3D views (gate flight, commit helix, a lit call path and a
  floating invented function in the galaxy, a fixed CVE), a glowing tour button until it is taken (spotlight, keyboard, phone bottom sheet, pauses if you wander off),
  idle hints with a one-click next step, a Guide button (`?`), a Play button for the scroll-driven
  hero, WebGL fallbacks and loading/retry states on every page. The galaxy now opens face-on, with
  the subsystem clusters ringed around the core.
- **Engine fixes from live runs (Oct 25):** Nemotron 3 ignores `/no_think`; reasoning is now switched
  with `chat_template_kwargs.enable_thinking` (live triage 38-60 s -> 17-22 s); failed JSON attempts
  now count in the run's cost; the adversarial challenge runs without reasoning so it completes.

## Results (all live on Token Factory)
- SlopBench, 197 curl reports: full pipeline 0/148 CVEs wrongly dismissed, $0.007/report, $1.39 total.
  Ablation without grounding: 0/49 slop closed, ranking AUC 0.53 (vs 0.67 with grounding).
- FixBench, 27 validated curl CVEs (2 dropped, listed): Super 8/27 ($0.62/fix), Ultra 9/27
  ($1.98/fix), Super-then-Ultra cascade 11/27 (41%, $1.62/fix), 0 fixes broke a nearby test.
- Nano 2/27 ($0.05 per CVE). All three sizes are on the site and in the README.
- Live runs filmed Oct 25 (`video/runs/`): HackerOne #3418528 UNGROUNDED in 21.6 s, $0.0084;
  CVE-2026-6276 fixed live by Nemotron 3 Super twice (61 s / $0.034, 68 s / $0.043).
- Demo film v2: `video/film` (HyperFrames), 2:46, built from the live runs, with subtitles, highlights
  and the engine log; rendered and mastered to `video/film/renders/ProofGate-demo.mp4` (git-ignored;
  rebuild steps in `docs/VIDEO.md`). Public on YouTube: https://youtu.be/d4L-x6sTMmI
- SlopBench predates the reasoning-switch fix; a rerun (about $1.6) is pending a decision.

## Credits
Token Factory: $25 promo redeemed 2026-10-25; balance read $3.70 on Oct 25 afternoon (usage posts
with a delay). The public site makes no model calls, so judging costs nothing. FixBench Ultra is the expensive part (~$0.66/CVE); Super ~$0.18/CVE, Nano ~$0.04/CVE.

## Submission
Submitted on Devpost on Oct 28, 2026: https://devpost.com/software/proofgate-ik0f95 (editable until
the deadline, Oct 30 10:00 AM PT). Video: https://youtu.be/d4L-x6sTMmI. The site redeploys from `main`.

## Waiting on the team
1. Personalize the ✍️ items in `docs/FEEDBACK.md`.
2. Optional: join the Nebius Builders Program for +$25 Token Factory credits.

## Local setup notes (Windows)
- Python venv: `%USERPROFILE%\.cache\proofgate\venv` (session folder path too long for tree-sitter).
- curl clone + caches: `%USERPROFILE%\.cache\proofgate\`. FixBench configure cache: `...\fixbench\`.
- Docker Desktop must be running for FixBench (image `proofgate/curl-test:3`, volume `proofgate-ccache`).
  If it fails to start with a secrets-engine socket error, move
  `%LOCALAPPDATA%\docker-secrets-engine` aside and start it again.
- Web: `cd web && npm run dev`. Engine: `proofgate serve`.
