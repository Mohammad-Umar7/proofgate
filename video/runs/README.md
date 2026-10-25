# The live runs filmed for the demo (Oct 25, 2026)

Both ran on the engine (`proofgate serve`) on the recording laptop, against real Nebius Token
Factory and Tavily keys, through the site built with `NEXT_PUBLIC_API_URL` pointing at it.

| File | What it is |
|---|---|
| `engine-live-triage.log` | The engine's INFO log: one line per Token Factory call (stage, model, tokens, cost, latency), per Tavily search, and per outbound HTTP request. 14:02 is a check run; 14:03:24-14:03:46 is the run in the film. |
| `live.marks.json` | Where the recorder found each highlighted element on screen, with the recording's wall-clock start. |
| `fixlive.events.txt` | The SSE stream of the filmed FixBench run (`POST /api/fix`, CVE-2026-6276, Nemotron 3 Super): every status line, every agent step with its tool output, and the graded result. |
| `fixlive.marks.json`, `galaxy.marks.json` | Element marks for the fix and galaxy shots. |

Triage: https://hackerone.com/reports/3418528, UNGROUNDED in 21.6 s, $0.0084.
Fix: resolved, all 30 tests pass, checksrc clean, 61 s, $0.034 (an earlier take: resolved, 68 s, $0.043).
