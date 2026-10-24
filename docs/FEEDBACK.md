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
