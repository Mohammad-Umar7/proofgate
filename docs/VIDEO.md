# Demo video

The submission video is produced from this repository, not edited by hand. It is 2:46, 1920x1080,
30 fps, H.264, and it is built around **two live runs** filmed on Oct 25, 2026 (evidence in
[`video/runs/`](../video/runs/)):

- **Live triage.** A real report from curl's HackerOne program (#3418528, on curl's public AI-slop
  list) is pasted as a link into the console; the engine fetches it and runs all nine stages on
  Nebius Token Factory and Tavily. UNGROUNDED in 21.6 s for $0.0084. The engine's real log runs in a
  panel beside the console, each line appearing when it was written.
- **Live fix.** On the FixBench page, **Run live now** sends CVE-2026-6276 to Nemotron 3 Super: it
  reproduces the failing regression test, reads the code, edits `lib/http.c`, builds curl and runs 30
  of curl's tests in a network-less Docker sandbox. All pass, checksrc clean, 61 s, $0.034.

## How it is made

- **Footage**: [`video/tools/record.mjs`](../video/tools/record.mjs) drives its own Chrome (separate
  profile) with real mouse drags, clicks and typing, captures DevTools screencast frames, encodes a
  constant-frame-rate MP4 per shot, and saves *marks*: where each element the narration will name
  sits on screen, with the recording's wall-clock start. Live shots run against the site built with
  `NEXT_PUBLIC_API_URL` pointing at `proofgate serve`; the others against the public site.
- **Narration**: [`video/SCRIPT.md`](../video/SCRIPT.md), 13 lines spoken by Kokoro (`af_heart`, on
  device) through `npx hyperframes tts`. It says "NVIDIA Nemotron" and "Nebius Token Factory" in
  scenes 3 and 13 and names Tavily in 4 and 13.
- **Edit**: a HyperFrames project, [`video/film`](../video/film).
  `tools/build_vo.py` lays the clips on the timeline (`timeline.json`); `tools/build_root.py`
  writes `index.html` and the subtitles from the narration's word times (Parakeet), with the
  script's spellings; `tools/make_clips.py` pre-renders every sped-up or slowed clip with ffmpeg.
- **Subtitles** on every line; **highlights**: a ring on the exact area each line names, the rest of
  the frame dimmed, and a short tag, placed from the recorder's marks and timed to the word.
- **Honesty**: every live scene carries a LIVE RECORDING badge with its playback speed; the sped-up
  fix keeps the page's own real clock and spend in frame.
- **Sound**: narration plus bundled effects on visible actions (credits in
  `video/film/SFX-CREDITS.md`). No music, so no copyright question.

## Rebuild

```
proofgate serve                                              # engine with keys, on :8000
cd web && NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npx next build && (cd out && python -m http.server 3100)
PG_SITE=http://localhost:3100 node video/tools/record.mjs galaxy live fixlive
node video/tools/record.mjs hero bench fixbench              # public site
cd video/film                                                # copy to a short path on Windows
npx hyperframes tts ... (one clip per line of narration.json into assets/vo)
python tools/build_vo.py && npx hyperframes transcribe assets/vo/narration.wav --engine parakeet
python tools/build_root.py && python tools/make_clips.py
npx hyperframes check && npx hyperframes render --quality delivery -o renders/film-raw.mp4
python tools/master.py renders/film-raw.mp4 renders/film-master.mp4   # -15 LUFS, video copied
```

On Windows, run the HyperFrames commands from a short path (e.g. `%USERPROFILE%\pgfilm2`): deep
paths exceed MAX_PATH inside the renderer's temp folders. Give Node a larger heap for the render
(`NODE_OPTIONS=--max-old-space-size=6144`).

## Published

**https://youtu.be/d4L-x6sTMmI** (public, 1080p, uploaded Oct 28, 2026), linked from README and Devpost.

## Upload checklist

- YouTube, **Public** (or Unlisted), title "ProofGate: proving AI-generated security reports, then fixing
  the real ones (Nemotron on Nebius Token Factory)".
- Description: the Devpost elevator pitch, the demo URL, the repo URL, and the two live runs.
- Paste the link into Devpost (Demo video) and into README.md (Video section).
