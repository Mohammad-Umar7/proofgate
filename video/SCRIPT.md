# ProofGate demo film: narration

One line per scene, spoken by Kokoro (`af_heart`). Every number is from a real run: the two live
runs filmed for scenes 3-5 and 9-11, or the published SlopBench and FixBench results. Spoken
spellings are written out for the TTS. Subtitles are the same words, timed from the narration
with Parakeet.

| id | Footage | Voiceover |
|---|---|---|
| s01 | terminal: curl's commit ending the bug bounty, real slop titles | In January twenty twenty-six, curl ended its bug bounty. AI made fake security reports free to write, and every one costs a volunteer hours to disprove. |
| s02 | landing page | ProofGate is a gate in front of the inbox. It checks every claim in a report against the real code, closes the fake ones with proof, and turns real ones into tested patches. |
| s03 | LIVE: console on this laptop, HackerOne link pasted, run starts; engine log beside it | This is live, not a replay. I paste a link to a real report from curl's HackerOne program. ProofGate fetches it, and NVIDIA Nemotron, on Nebius Token Factory, pulls out every claim it can check. |
| s04 | LIVE (real time): grounding, prior art; log fills with Token Factory and Tavily calls | Git and tree-sitter test each claim against curl's real source and its full history, while Tavily searches the web for earlier disclosures. Every request in that log is real. |
| s05 | LIVE result: 21.6 s, $0.0084, the ghost in the galaxy, the evidence card | Twenty-two seconds, under one cent. The function this report is built on has never existed in curl, in any of forty thousand commits. That is proof, not opinion, so the verdict is ungrounded. |
| s06 | code galaxy: free rotation, a real call path, an invented function | This is the code galaxy: every function in curl and every call between them, parsed from the source. A real function lights up with its path from a public entry point. An invented one floats outside, connected to nothing. |
| s07 | drawn: the nine stages and the three guarantees | Under the hood are nine stages, each with a model sized to its job. Nano extracts the claims, Super reads the code, and Ultra writes the verdict, then argues against it. The report is untrusted data, the model holds no credentials, and a rule table decides. |
| s08 | SlopBench, then "0 / 148" | On a hundred and ninety-seven real curl reports with known outcomes, it never dismissed a real vulnerability. Zero of a hundred and forty-eight, for under a cent each. |
| s09 | LIVE: FixBench, Run live on CVE-2026-6276, reproduce, red light | Disproving slop is half the job. Real bugs need fixing. Live again: Nemotron Super gets a published curl CVE and the vulnerable code, and first reproduces the bug. The regression test fails. |
| s10 | LIVE (sped up, real clock on screen): reads, edit, build, 30 tests | It reads the code, writes a patch, then builds curl and runs curl's own tests, in a sandbox with no network. The whole run took about a minute, and three cents. |
| s11 | LIVE result: all green, checksrc clean, the two patches | Every test passes, the regression test included, and curl's style checker is clean. The agent never saw the maintainers' fix. |
| s12 | FixBench cascade and the three sizes, then "11 / 27" | Across twenty-seven real curl CVEs, Super and Ultra fix different bugs, so ProofGate routes by job: eleven fixed, all verified by curl's own tests, and none broke another. |
| s13 | end card | ProofGate never closes a report on a guess, and a maintainer makes the final call. Built on NVIDIA Nemotron through Nebius Token Factory, with Tavily. Open source, and live now. |

## The two live runs (Oct 25, 2026, on the engine running on this laptop)

- **Triage:** https://hackerone.com/reports/3418528 (on curl's public AI-slop list), fetched at run
  time. UNGROUNDED in 21.6 s for $0.0084: `Curl_ldap_err2string()` never existed in any of 40,192
  commits. Calls in the engine log: Nemotron 3 Nano (claims), Tavily (prior art), Nemotron 3 Super
  (rules), Nemotron 3 Ultra (verdict, then the adversarial pass, which upheld it).
- **Fix:** CVE-2026-6276 (stale custom cookie host causes cookie leak) with Nemotron 3 Super.
  Reproduced test2504 failing, 11 replies, one edit to `lib/http.c`, one sandbox build and test run:
  all 30 tests pass, checksrc clean, 61 s, $0.034. An earlier take the same day also fixed it
  (68 s, $0.043); the film uses the second take, which keeps the live bar fully in frame.
