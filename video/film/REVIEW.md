# REVIEW: ProofGate demo film

## Creative calls
- Storyline A, "the proof is cheaper than the fake" (STORYLINES.md). Not built: B (one CVE's journey as
  one continuous take) and C (numbers cut on the beat).
- Every product shot is the live site, recorded with `video/tools/record.mjs` (its own Chrome profile,
  DevTools screencast, constant-frame-rate MP4), punched in 1.25-2.2x on the panel the voice names.
- Two worlds: the dark product UI and a light number world for the two payoffs ("0 / 148", "11 / 27"),
  entered by a colour flood from below. The opening is a real `git log` line from curl's repository
  and real titles from curl's public slop list.
- Voice: Kokoro `af_heart` (free, on device), one clip per scene, mixed into `assets/vo/narration.wav`.
  The spoken "forty thousand commits" was dropped after the transcript heard "4,000"; the screen shows
  the real count instead.
- No music: no music source here (no HeyGen sign-in, no local MusicGen). Six bundled effects only
  (two whoosh takes on world changes, pops on the three numbers, one impact on the mark).

## Measured vs looked at
- `hyperframes check`: passes, no errors. Snapshots and the review sheets (beats, seams) were read.
- Word timings come from a Parakeet transcript of the final narration; numbers land on their words
  (49 at 8.4 s, 0 at 56.7 s, 11 at 99.4 s).
- The sound was measured, not heard: nobody has listened to the mix.

## Weakest shot
s09 (79.7-87.7 s): the test lights are the hero but share the frame with the CVE header and cost
cards. With more time: re-record that region at 2x device scale and crop to the lights alone.

## Warnings kept on purpose
- `line_unread` on the slop titles in s01: they are a flood meant to be glanced, not read.
- `line_unread` on the git output line (3.2 s for 16 words): the highlighted phrase is what must read.
- `dead_stretch` on the two number payoffs: deliberate holds, marked `data-hold`.
