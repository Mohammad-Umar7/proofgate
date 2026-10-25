# Demo video

The submission video is produced from this repository, not recorded by hand:

- **Footage** is the live site (https://proofgate-ten.vercel.app), filmed by
  [`video/tools/record.mjs`](../video/tools/record.mjs): its own Chrome profile at 1920x1080, scripted
  steps (navigate, scroll, click Replay), DevTools screencast frames, encoded to constant-frame-rate MP4.
- **Narration** is [`video/SCRIPT.md`](../video/SCRIPT.md), spoken by Kokoro (`af_heart`, on device,
  free) through `npx hyperframes tts`, one clip per scene. It says "NVIDIA Nemotron" and
  "Nebius Token Factory" out loud in scenes 3 and 12, and names Nemotron Ultra and Super in 5 and 11.
- **Edit** is a HyperFrames project, [`video/film`](../video/film): twelve scenes timed to the narration,
  punch-ins on the panel the voice names, two number payoffs ("0 / 148", "11 / 27"), the end card.
  `SPEC.md`, `STORYLINES.md` and `REVIEW.md` there record the decisions.
- **Sound**: narration plus bundled effects (credits in `video/film/SFX-CREDITS.md`). No music, so no
  copyright question.

Length: 1:56 (rules: under 3:00). Output: 1920x1080, 30 fps, H.264 MP4.

## Rebuild

```
node video/tools/record.mjs                      # re-film the site (needs Chrome)
cd video/film && npx hyperframes check            # lint, layout, timing
npx hyperframes render --quality delivery -o renders/proofgate-demo.mp4
```

On Windows, run the HyperFrames commands from a short path (copy `video/film` to e.g. `%USERPROFILE%\pgfilm`
with its `assets/`): deep paths exceed MAX_PATH inside the renderer's temp folders.

## Upload checklist

- YouTube, **Public** (or Unlisted), title "ProofGate: proving AI-generated security reports, then fixing
  the real ones (Nemotron on Nebius Token Factory)".
- Description: the Devpost elevator pitch, the demo URL, the repo URL.
- Paste the link into Devpost (Demo video) and into README.md (Video section).
