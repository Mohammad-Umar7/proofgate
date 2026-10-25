# SPEC: ProofGate demo film, v2 (live runs, subtitles, highlights)

GOAL:    a judge finishes certain the product is real: a report triaged live by NVIDIA Nemotron on
         Nebius Token Factory, a real curl CVE fixed live, and knows why it matters and how it works.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps, MP4 for YouTube. 166.2 s (under 3:00).
CLOCK:   the narration (13 Kokoro clips, tools/build_vo.py lays them 0.3 s into each scene).
FOOTAGE: video/tools/record.mjs against the site built with NEXT_PUBLIC_API_URL on a live engine:
         live.mp4 (HackerOne link triage), fixlive.mp4 (Run live on CVE-2026-6276), galaxy.mp4
         (drags through full turns), plus hero, bench, fixbench from the public site. The recorder
         saves element marks; every highlight box is placed from a mark or a frame read.
HONESTY: every live scene carries a "LIVE RECORDING" badge with its speed (1.6x, real time, 1.4x,
         sped up 5-8x); the sped-up fix keeps the page's own real clock and spend in frame.
         The engine log panel is the run's real log (proofgate.llm, proofgate.tavily, httpx at INFO),
         each line placed at its timestamp mapped onto the footage.
LOOK:    product world = the site's own dark UI, punched in 1.15-1.35x; number world = #f3f4f6 with
         one accent (s01, s07, s08, s12). Highlights: 3 px #8bd3ff ring with glow, the rest of the
         frame dimmed to 50%, a short tag in the same blue (green for passes, red for failures);
         each appears on the word that names it and leaves before the next. Subtitles: Inter 600 44 px
         on a 78% dark pill, 58 px from the bottom, 2-7 words per group, broken at sentence ends.
SCENES:  s01 hook (curl ended its bounty) · s02 the gate (benefit) · s03-s05 LIVE triage + log ·
         s06 code galaxy · s07 the nine stages and three guarantees · s08 0 / 148 · s09-s11 LIVE fix ·
         s12 11 / 27 · s13 end card.
QA:      `npx hyperframes check` passes; snapshots at every highlight; narration says "NVIDIA
         Nemotron" and "Nebius Token Factory" (s03, s13) and names Tavily (s04, s13).
