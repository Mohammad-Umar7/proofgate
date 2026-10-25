# Feedback on Nebius Token Factory, AI Cloud and NVIDIA models (draft)

> Draft for the Devpost "Additional info" questions. **The team must edit this with its own
> experience after running ProofGate with a real Token Factory key** — judges reward specific,
> first-hand detail. Items marked ✍️ need your numbers or opinions.

## Which models, and why that size/variant
- **Nemotron 3 Nano** for claim extraction: high-volume, short structured JSON, latency matters.
- **Nemotron 3.5 Super VL** for screenshots and terminal captures attached to reports (the vision model on Token Factory).
- **Nemotron 3 Super** for reading real source code (long context), reachability and guard
  analysis, applying the project's policy, and drafting patches in the fix loop.
- **Nemotron 3 Ultra** for the final explanation and the adversarial challenge, called twice per
  report: the only place we pay for the largest model.

## First-hand observations from building ProofGate (facts, use them in the answers)

- **Native tool calling works and matters.** Through Token Factory's OpenAI-compatible `tools`
  parameter, Nemotron 3 Super returns `finish_reason: "tool_calls"` with clean JSON arguments, and
  its reasoning separately in `reasoning_content` (also `reasoning`), with `reasoning_tokens` in usage.
  Our first FixBench agent used a text protocol (tags in the reply) instead: Super wrote one tool call
  and then **invented the tool's output** (fake file contents, fake grep hits) for 4,000 tokens.
  Switching to native tool calling removed that failure mode completely. Worth a line in the docs.
- **Super as a coding agent.** It localizes well from a real test failure (it read the protocol
  diff in the reproduction log and went straight to the right function), but it explores in small
  slices (20–40 lines per read) and can circle without editing; a "commit to an edit and run the
  tests" nudge after 12 replies made the difference. A full agent run on a real curl CVE (reproduce,
  explore, edit, build curl, run 31 tests, iterate, pass) cost about **$0.08 and 3 minutes**.
- **Ultra** reads larger chunks and commits sooner, at roughly 5x the tokens of Super on the same
  CVE (about $0.50 vs $0.08 in our first comparison).
- **Measured on FixBench (27 real curl CVEs, same agent, same budget of 40 replies and 4 test runs):**
  Nano 3 30B 2/27 fixed ($0.05 per CVE, right file 30% of the time), Super 3 120B 8/27 ($0.18 per CVE,
  right file 85%), Ultra 3 550B 9/27 ($0.66 per CVE, every fix passed on its first test run). Super and
  Ultra fix different CVEs: Super first and Ultra on its failures fixes 11/27 at $1.62 per verified fix.
  No fix from any size broke a nearby test. Total FixBench spend about $24 across the three sizes.
- **Agent failure modes we saw:** Super loops on repeated identical searches and small reads (a guard
  that flags repeated calls helped); Ultra sometimes spends its budget searching for a dependency's
  constants (libssh2) that are not in the repository; Nano rarely commits to an edit at all.
- **Triage at scale.** The full SlopBench run (197 real curl reports, four Nemotron sizes routed
  by job plus Tavily) cost **$1.39 in total**, $0.007 per report.
- **Billing UX.** The promo code lives in "Top up balance", where the default tab is "By card" with
  the saved card preselected, so one wrong click charges the card. A separate "Redeem code" entry
  would be safer. After about $2 of usage the account balance had not changed yet; real-time usage
  would help when running benchmarks against a fixed credit.
- **Model ids** mix casing styles (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`,
  `nvidia/nemotron-3-super-120b-a12b`, `nvidia/Nemotron-3-Ultra-550b-a55b`); we resolve them at
  runtime from `GET /v1/models` to stay robust.

## Output quality (1–10) ✍️
What to cover: JSON reliability (how often the retry-with-error path was needed), whether Super
cited real line numbers from the excerpts, whether Ultra's challenge found real gaps or invented
ones, multilingual reports if any.

## Approach
Prompt-engineered, out of the box. No fine-tuning. Key techniques: fencing untrusted report text in
a randomized tag; requiring citations only from provided excerpts; a deterministic rule table decides,
the model explains; an adversarial second pass with an explicit "credible" flag.

## Compared with other models ✍️

## Most valuable Nebius capabilities
- OpenAI-compatible API: the official `openai` SDK works with only `base_url` changed.
- `GET /v1/models` lets the app resolve exact model ids at runtime instead of hard-coding them.
- One provider for four model sizes made per-stage routing and cost accounting simple.

## Likelihood to recommend (1–10) ✍️  · Experience vs. previous environments (1–10) ✍️

## What would have made it better (specific, from building ProofGate)
1. **Model id discoverability.** Third-party catalogs list the same Nemotron models with different
   casing; a canonical, documented id list (and stable aliases like `nemotron-3-super-latest`) would
   remove a class of runtime errors.
2. **Reasoning toggle docs.** A single documented switch for Nemotron reasoning on/off (and whether
   reasoning tokens are billed and returned separately) per model.
3. **Structured outputs.** Guaranteed JSON-schema mode for every Nemotron size would remove our
   retry path.
4. **Pricing in the API.** Per-model prices from an endpoint, so live cost counters do not need a
   manually maintained table.
5. **Budget guardrails.** Per-key spend caps and rate limits configurable in the console, for public
   demos.

## What we hope to see from the Nemotron team next ✍️
Ideas: a small code-specialised Nemotron for repository-grounded tasks; first-class tool-calling
parity across sizes; long-context retrieval over git history.
