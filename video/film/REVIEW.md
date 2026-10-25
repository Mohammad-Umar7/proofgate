# Review: ProofGate demo film v2

Checked with `npx hyperframes check` (0 errors) and snapshots at every highlight, then on the render.

## What changed from v1, and why
- **Live, not replayed** (the user's ask): both product demos are now live runs filmed on the engine
  running on the laptop, a real HackerOne report and a real curl CVE, with the engine's real log on
  screen and a LIVE RECORDING badge stating each scene's speed.
- **Subtitles** on every narrated word (Parakeet timings, script spellings).
- **Highlights**: whatever a line names is ringed, the rest dimmed, with a short tag, so a viewer
  always knows where to look.
- **Benefit and design**: s02 states what maintainers get; s07 shows the nine stages, which Nemotron
  does what, and the three guarantees.
- **Code galaxy** gets its own scene, dragged through full turns (the rotation bug is fixed in the
  site), then one real and one invented function.

## Fixed during review
- s03: the "engine on this laptop" tag ran under the log panel; the "fetches it" ring sat on the
  wrong spot because the form is taller before a run starts (measured from the frame).
- s07: the Grounding card's text overflowed; cards are taller.
- s09: the reproduce ring sat below its text (the page shifts once the test lights appear); the
  LIVE badge covered the page's own chip (fix scenes framed 1.15x so the badge sits in the margin).
- s11: a tag overlapped the subtitles.
- s12: re-filmed FixBench from the live site so it shows all three Nemotron sizes.
- Tags shortened where they left the screen before they could be read; badges and tags at 24-28 px.

## Known and accepted
- Log panel and stage-card detail text is small (14-20 px): it is evidence texture; the point of
  each is called out by a tag at reading size.
- The flood of slop titles in s01 moves faster than each title can be read, by design.
