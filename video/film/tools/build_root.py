"""Write index.html (scene hosts, overlays, audio) and compositions/captions.html from
timeline.json and the narration transcript (assets/vo/transcript.json, Parakeet word times)."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
tl = json.loads((ROOT / "timeline.json").read_text())
words = json.loads((ROOT / "assets" / "vo" / "transcript.json").read_text(encoding="utf-8"))
S = {s["id"]: s for s in tl["scenes"]}
TOTAL = tl["total"]

# ASR spellings -> the words actually spoken (the script)
FIX = {
    "Curl": "curl", "Curl's": "curl's", "Curl,": "curl,", "Hacker1": "HackerOne", "Nemitron,": "Nemotron,",
    "Nemitron": "Nemotron", "Nemetron": "Nemotron", "TreeSitter": "tree-sitter", "Tavili": "Tavily",
    "Tavili,": "Tavily,", "Proofgate": "ProofGate", "Galaxy,": "galaxy:", "size": "sized", "styker": "style checker",
    "everyone": "every one", "Slop": "slop", "super": "Super", "Nvidia": "NVIDIA", "maintainers": "maintainers'",
    "job,": "job.", "again,": "again:", "pars": "parsed", "Nematron": "Nemotron",
}


def fixed(ws: list[dict]) -> list[dict]:
    out = []
    for i, w in enumerate(ws):
        text = FIX.get(w["text"], w["text"])
        if text == "test," and i and ws[i - 1]["text"] == "TreeSitter":
            text = "test"
        if text == "eight," and out and out[-1]["text"] == "forty":
            out[-1] = {**out[-1], "text": "forty-eight,", "end": w["end"]}
            continue
        if out and re.search(r"[.!?]$", out[-1]["text"]):
            text = text[:1].upper() + text[1:]
        out.append({**w, "text": text})
    # names that must stay on one line
    merged: list[dict] = []
    for w in out:
        prev = merged[-1]["text"] if merged else ""
        if (prev == "NVIDIA" and w["text"].startswith("Nemotron")) or (prev == "Nebius" and w["text"] == "Token")                 or (prev == "Nebius Token" and w["text"].startswith("Factory")):
            merged[-1] = {**merged[-1], "text": f"{prev} {w['text']}", "end": w["end"]}
        else:
            merged.append(w)
    return merged


STOP = {"a", "an", "the", "in", "of", "to", "and", "with", "from", "for", "its", "by", "on", "is", "it", "that"}


def groups(ws: list[dict], max_words: int = 7, max_chars: int = 44) -> list[dict]:
    out, cur = [], []

    def emit(items: list[dict]) -> None:
        out.append({"text": " ".join(x["text"] for x in items), "start": items[0]["start"], "end": items[-1]["end"]})

    for i, w in enumerate(ws):
        cur.append(w)
        nxt = ws[i + 1] if i + 1 < len(ws) else None
        text = " ".join(x["text"] for x in cur)
        natural = (nxt is None or re.search(r"[.:!?]$", w["text"])
                   or re.search(r"[,;]$", w["text"]) and len(cur) >= 2
                   or nxt["start"] - w["end"] > 0.45)
        full = nxt is not None and (len(cur) >= max_words or len(text) + 1 + len(nxt["text"]) > max_chars)
        if natural:
            emit(cur)
            cur = []
        elif full:
            # never leave "a", "the", "of"... dangling at the end of a line
            carry = []
            while len(cur) > 2 and cur[-1]["text"].lower() in STOP:
                carry.insert(0, cur.pop())
            emit(cur)
            cur = carry
    return out


ws = fixed(words)
caps = groups(ws)
for g in caps:
    g["text"] = g["text"].replace("Real bug need", "Real bugs need")
# each group holds until the next starts (or 0.4 s after its last word), never overlapping
for i, g in enumerate(caps):
    nxt = caps[i + 1]["start"] if i + 1 < len(caps) else TOTAL
    g["show"] = max(0.1, g["start"] - 0.06)
    g["hide"] = min(nxt - 0.02, g["end"] + 0.45)

cap_html = "\n".join(
    f'    <div data-hf-id="hf-cap{i}" id="cap{i}" class="cap"><span>{g["text"]}</span></div>' for i, g in enumerate(caps))
cap_js = "\n".join(
    f'    tl.fromTo("#cap{i}", {{ opacity: 0, y: 8 }}, {{ opacity: 1, y: 0, duration: 0.12, ease: "power2.out" }}, {g["show"]:.3f});\n'
    f'    tl.to("#cap{i}", {{ opacity: 0, duration: 0.1, ease: "power2.in" }}, {g["hide"] - 0.1:.3f});\n'
    f'    tl.set("#cap{i}", {{ visibility: "hidden" }}, {g["hide"]:.3f});' for i, g in enumerate(caps))
(ROOT / "compositions" / "captions.html").write_text(f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; pointer-events: none; }}
    .cap {{ position: absolute; left: 0; right: 0; bottom: 58px; text-align: center; opacity: 0; overflow: visible; }}
    .cap span {{ display: inline-block; max-width: 1500px; padding: 10px 22px 12px; border-radius: 14px;
      background: rgba(5, 6, 10, 0.78); color: #f3f4f6; font-family: "Inter", sans-serif; font-weight: 600;
      font-size: 44px; line-height: 1.2; letter-spacing: -0.01em; }}
  </style>
  <div data-hf-id="hf-capr" id="root" data-composition-id="captions" data-width="1920" data-height="1080">
    <!-- the narration, word-timed by Parakeet (assets/vo/transcript.json), spellings from SCRIPT.md -->
{cap_html}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{cap_js}
    window.__timelines["captions"] = tl;
  </script>
</template>
""", encoding="utf-8")

hosts = "\n".join(
    f'      <div data-hf-id="hf-h{s["id"]}" id="{s["id"]}" data-composition-id="{s["id"]}" data-composition-src="compositions/{s["id"]}.html" '
    f'data-start="{s["start"]}" data-duration="{s["duration"]}" data-track-index="1" data-track-kind="graphics" data-width="1920" data-height="1080"></div>'
    for s in tl["scenes"])
log_start = S["s03"]["start"]
log_end = S["s05"]["start"] + 6.3  # the evidence card takes the frame
cut = {k: S[k]["start"] for k in S}


def fx(i: str, src: str, at: float, dur: float, vol: float, track: int) -> str:
    return (f'      <audio data-hf-id="hf-{i}" id="{i}" class="clip" src="assets/sfx/{src}" data-start="{at:.2f}" '
            f'data-duration="{dur}" data-track-index="{track}" data-volume="{vol}"></audio>')


effects = "\n".join([
    fx("fx-whip1", "whoosh-short.mp3", cut["s02"] - 0.12, 0.57, 0.6, 3),
    fx("fx-click1", "click-soft.mp3", cut["s03"] + 5.9, 0.4, 0.7, 4),
    fx("fx-whip2", "whoosh-short.mp3", cut["s06"] - 0.12, 0.57, 0.55, 3),
    fx("fx-whip3", "whoosh-short.mp3", cut["s07"] - 0.12, 0.57, 0.55, 3),
    fx("fx-flood1", "whoosh.mp3", cut["s08"] + 6.55, 0.57, 0.55, 3),
    fx("fx-pop0", "pop.mp3", cut["s08"] + 7.25, 0.72, 0.8, 4),
    fx("fx-whip4", "whoosh-short.mp3", cut["s09"] - 0.12, 0.57, 0.55, 3),
    fx("fx-click2", "click-soft.mp3", cut["s09"] + 4.27, 0.4, 0.7, 4),
    fx("fx-flood2", "whoosh.mp3", cut["s12"] + 6.85, 0.57, 0.55, 3),
    fx("fx-pop11", "pop.mp3", cut["s12"] + 7.55, 0.72, 0.8, 4),
    fx("fx-mark", "impact-bass-1.mp3", cut["s13"] + 1.15, 2, 0.75, 4),
])

(ROOT / "index.html").write_text(f"""<!doctype html>
<html lang="en" data-resolution="landscape">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: #05060a; }}
      #root {{ position: relative; width: 100%; height: 100%; font-family: "Inter", sans-serif; }}
      #bg {{ position: absolute; inset: 0; background: #05060a; }}
    </style>
  </head>
  <body>
    <div data-hf-id="hf-root" id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="1920" data-height="1080">
      <div data-hf-id="hf-bg" id="bg"></div>

      <!-- scenes, timed to the narration (timeline.json, tools/build_vo.py) -->
{hosts}

      <!-- the engine's real log for the live triage run, beside the console (s03-s05) -->
      <div data-hf-id="hf-hlog" id="logpanel" data-composition-id="logpanel" data-composition-src="compositions/logpanel.html" data-start="{log_start}" data-duration="{round(log_end - log_start, 3)}" data-track-index="5" data-track-kind="graphics" data-width="1920" data-height="1080"></div>

      <!-- subtitles for every line of narration -->
      <div data-hf-id="hf-hcap" id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{TOTAL}" data-track-index="6" data-track-kind="captions" data-width="1920" data-height="1080"></div>

      <!-- narration: Kokoro af_heart, one clip per scene laid on the timeline (assets/vo, SCRIPT.md) -->
      <audio data-hf-id="hf-vo" id="vo" class="clip" src="assets/vo/narration.wav" data-start="0" data-duration="{TOTAL}" data-track-index="2" data-volume="1"></audio>

      <!-- effects, each on a visible cause -->
{effects}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
""", encoding="utf-8")
print(len(caps), "caption groups")
for g in caps[:12]:
    print(f'{g["show"]:7.2f}-{g["hide"]:7.2f}  {g["text"]}')
