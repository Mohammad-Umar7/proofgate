# Build progress (updated 2026-10-21, late)

## Done and pushed (~100 commits on main)
- **Engine** (`engine/proofgate`): all nine stages, pipeline, FastAPI server with SSE, CLI,
  SQLite store, arena, SlopBench (dataset + runner + metrics), export for the static demo,
  draft-PR publisher, sandbox backends (Docker + NVIDIA OpenShell SDK), sanitizer attribution.
- **Grounding** is time-travel aware (release at the report date + master on that date), treats
  removed/renamed code as partial, ignores the reporter's own files/functions, whole-history pickaxe
  cached per needle. Works for any git project via `PG_REPO_URL` etc.
- **Web** (`web/`): landing with GPU gate hero + history helix, triage console (replay + live),
  code galaxy explorer (ghost nodes, path beams), arena (10–0 offline), SlopBench dashboard.
  Static export builds; `NEXT_PUBLIC_BASE_PATH` supports GitHub Pages.
- **Shipping**: docker-compose one-command setup, engine/web Dockerfiles, CI workflow, Pages workflow
  (manual trigger), GitHub Action (`action/`), README, architecture, video script, feedback draft.

## Status (2026-10-24)
- Keys are in `engine/.env` (git-ignored). Live Nemotron + Tavily verified; replays and arena are
  recorded from live calls (~$0.007 per report). Demo: https://proofgate-ten.vercel.app (Vercel,
  auto-deploys from main).
- Token Factory account is on the $1 trial; the $25 promo code (NEBIUS-DEVPOST-GLOBAL26 form) is
  pending by email. Redeem it under Billing, then run the full benchmark (~$2):
  `proofgate bench run --config full` (+ `single-model`, `no-grounding`), then `proofgate bench table`
  and `proofgate export-web --only bench`.

## Waiting on the team
1. Promo code email → redeem in Token Factory Billing.
2. Record the video (`docs/VIDEO.md`), personalize `docs/FEEDBACK.md`, fill the Devpost form.

## Known gaps / next
- REPRODUCED path: engine + sandbox image are built, but no recorded demo run yet.
- Fix loop needs a live key and a sanitizer image (`proofgate image <tag>`) to demo.
- Optional: plausibility ranking of the NEEDS_INFO queue from Nemotron Super's assessment.

## Local setup notes (Windows)
- Python venv: `%USERPROFILE%\.cache\proofgate\venv` (session folder path too long for tree-sitter).
- curl clone + caches: `%USERPROFILE%\.cache\proofgate\`.
- Web: `cd web && npm run dev` (port 3000). Engine: `proofgate serve` (port 8000).
