# Build progress (paused 2026-10-21)

## Done and pushed
- Public repo, Apache-2.0, `docs/HACKATHON.md` (all rules/fields/credits), `docs/PITCH.md`, `CLAUDE.md`.
- Engine (`engine/proofgate`): settings, data model, Token Factory client (Nemotron role routing,
  live model-id resolution, JSON mode, cost tracking, budget cap), git layer over curl's full
  history (40,188 commits, 215 releases), tree-sitter code index + call graph + reachability
  (incl. dispatch tables), prompt-injection guard.
- Stages done: intake, claims, grounding, prior_art (curl OSV feed with 239 advisories, OSV.dev,
  Tavily), rules (19 categories auto-built from curl's VULN-DISCLOSURE-POLICY.md).
- Sandbox: Docker backend (no network, read-only, caps dropped, limits) + sanitizer parser with
  crash attribution (project code vs reporter's own code).
- Tests: `engine/tests/test_grounding.py` passes (fabricated report contradicted, real verified).

## Next steps (in order)
1. `sandbox/openshell.py` — OpenShell backend via its Python SDK (`SandboxClient.create/exec/delete`,
   docs: github.com/NVIDIA/OpenShell docs/sdk/python.mdx). Needs Linux/WSL2 + Docker.
2. Stages: `repro.py` (run reporter's PoC only), `adjudicate.py` (Ultra verdict + adversarial
   challenge; UNGROUNDED requires a deterministic contradiction), `fix.py` (regression test, patch,
   test loop, draft PR), `card.py` (evidence card + reply draft).
3. `pipeline.py` orchestrator + `server.py` (FastAPI, SSE event stream) + `cli.py`.
4. SlopBench: slop list (bagder gist, 2025-26) + real CVEs (vuln.json `issue` -> HackerOne), runner,
   metrics, ablations.
5. Frontend `web/`: Next.js + React Three Fiber — gate hero, code galaxy with ghost nodes,
   history helix, live pipeline, evidence card, sandbox terminal, arena, bench dashboard.
6. README with Built on Nebius + NVIDIA section, cost table, bench results; GitHub Action; deploy.

## Needed from the team
- `engine/.env` with `NEBIUS_API_KEY` (credits code NEBIUS-DEVPOST-GLOBAL26) and `TAVILY_API_KEY`
  (promo BBDEVPOST). Copy from `engine/.env.example`.

## Local setup notes (Windows)
- Python venv lives at `%USERPROFILE%\.cache\proofgate\venv` (session folder path is too long for
  tree-sitter DLLs). Run: `& "$HOME\.cache\proofgate\venv\Scripts\python.exe" -m pytest -q` in `engine/`.
- curl clone cache: `%USERPROFILE%\.cache\proofgate\repos\curl`.
