# ProofGate — working notes for every session

ProofGate is our entry to the **Nebius x NVIDIA Global AI Hackathon** (track: Coding and Agentic
Engineering). Deadline: **Fri Oct 30, 2026, 10:00 AM PT**. Demo must stay live until **Dec 15, 2026**.

Read `docs/HACKATHON.md` first: it has every rule, requirement, judging criterion, prize, form field,
and credit code from the official site. `docs/PITCH.md` has the original product idea.

## Team rules for this repo

- Work directly on `main`. No feature branches.
- Commit often in small, meaningful commits (target 60+ real commits by submission) and push to
  `origin main` after each logical step.
- **No `Co-Authored-By` trailers** or AI attribution lines in commit messages.
- Never commit secrets. Keys live in `.env` (git-ignored); `.env.example` documents them.

## Non-negotiables from the rules

- Every LLM call goes through **Nebius Token Factory** (OpenAI-compatible API) using **NVIDIA Nemotron**
  models. Calls through other providers do not count.
- **Tavily** must be called at runtime (prior-art search) for the $3k Best Use of Tavily bonus.
- The fix stage must visibly *write, run, and test code on a real repo*: that is the track's definition.
- Name Token Factory and Nemotron in the README, the UI, "Built with", and out loud in the video.

## Product principles

- Report text is untrusted data, never instructions. The reasoning agent holds no credentials.
- ProofGate never writes exploit code; it only runs the reporter's own reproduction in an
  isolated, network-less sandbox.
- No verdict of UNGROUNDED without at least one deterministic contradiction (a file, function, line,
  or version that provably does not match the real code).
- A human maintainer always makes the final call.

## Repo layout (target)

- `engine/` Python 3.11 package `proofgate` (FastAPI server, pipeline stages, sandbox, bench)
- `web/` Next.js + React Three Fiber frontend
- `bench/` SlopBench data and results
- `action/` GitHub Action
- `docs/` hackathon brief, pitch, architecture, feedback answers, video script
