"""Lay the per-scene narration clips on the film timeline and write timeline.json.

Each scene lasts its clip plus padding; the clip starts LEAD seconds into its scene.
Output: assets/vo/narration.wav (48 kHz mono, loudness-normalised) and timeline.json.
"""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VO = ROOT / "assets" / "vo"
LEAD = 0.3
# scene -> total duration (seconds); chosen so every clip ends 0.3-1.5 s before its cut
DUR = {
    "s01": 11.6, "s02": 11.5, "s03": 14.0, "s04": 11.5, "s05": 13.0, "s06": 14.4, "s07": 18.6,
    "s08": 11.3, "s09": 14.3, "s10": 10.5, "s11": 8.6, "s12": 12.9, "s13": 14.0,
}


def length(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(path)], capture_output=True, text=True, check=True).stdout
    return float(out)


def main() -> None:
    t = 0.0
    scenes = []
    for sid, dur in DUR.items():
        clip = VO / f"{sid}.wav"
        n = length(clip)
        assert n + LEAD < dur, f"{sid}: clip {n:.2f}s does not fit {dur}s"
        scenes.append({"id": sid, "start": round(t, 3), "duration": dur, "vo_at": round(t + LEAD, 3),
                       "vo_len": round(n, 3)})
        t += dur
    total = round(t, 3)
    inputs, filters = [], []
    for i, s in enumerate(scenes):
        inputs += ["-i", str(VO / f"{s['id']}.wav")]
        ms = int(s["vo_at"] * 1000)
        filters.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=mono,adelay={ms}[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(len(scenes)))
    graph = ";".join(filters) + f";{mix}amix=inputs={len(scenes)}:normalize=0,atrim=0:{total},apad=whole_dur={total}[m]"
    raw = VO / "narration.raw.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-map", "[m]",
                    "-ar", "48000", "-ac", "1", str(raw)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af",
                    "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "1", str(VO / "narration.wav")],
                   check=True)
    (ROOT / "timeline.json").write_text(json.dumps({"total": total, "scenes": scenes}, indent=1))
    print(f"total {total}s")
    for s in scenes:
        print(f"  {s['id']}  {s['start']:7.2f}  {s['duration']:5.1f}  vo {s['vo_len']:.2f}")


if __name__ == "__main__":
    main()
