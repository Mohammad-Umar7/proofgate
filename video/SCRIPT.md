# ProofGate demo film: narration

One line per scene. Every number is from the published results (README, SlopBench, FixBench).
Spoken spellings are written out for the TTS ("HTTP two", "eight point fourteen").

| id | Footage | Voiceover |
|---|---|---|
| s01 | hero: the gate | In January twenty twenty-six, curl ended its bug bounty. AI made fake security reports free to write, and each one costs a volunteer an hour to disprove. |
| s02 | hero: fly-through | ProofGate makes proving them cheap. Every claim in a report is checked against the real code, at the exact version, before a human reads it. |
| s03 | console: stages light up | This report cites an HTTP two function in curl eight point fourteen. NVIDIA Nemotron Nano, on Nebius Token Factory, pulls out every claim. Then git searches every commit in curl's history. |
| s04 | console: ghost in the galaxy | That function has never existed, not in this release and not in any commit. The quoted lines never appeared either. |
| s05 | card: evidence | Nemotron Ultra explains the verdict, argues the reporter's side, and drafts a polite reply for the maintainer. |
| s06 | bench | On SlopBench, a hundred and ninety-seven real curl reports, ProofGate wrongly dismissed zero of a hundred and forty-eight real CVEs, for under a cent each. |
| s07 | fixbench overview | Triage is half the job. FixBench asks whether an open model can fix real curl security bugs. |
| s08 | replay: reproduce, read, edit | The agent gets only the public advisory and the vulnerable code. It reproduces the failure in a sandbox with no network, reads the code, and edits it. |
| s09 | replay: test lights | Then it builds curl and runs curl's own tests. The regression test turns green, and every nearby test still passes. |
| s10 | replay: two patches | Here is its patch, next to the one curl's maintainers shipped. The agent never saw theirs. |
| s11 | fixbench: cascade | Nemotron Super and Ultra fix different bugs, so ProofGate routes by job: eleven of twenty-seven real CVEs fixed, and no fix broke another test. |
| s12 | end card | ProofGate. NVIDIA Nemotron on Nebius Token Factory, with Tavily. Open source, and a human always makes the final call. |
