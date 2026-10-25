"""Pre-render every speed-changed clip at its exact speed, and point the scenes at the result.

The renderer's frame extraction failed for every <video> with data-playback-rate != 1 on this
machine, so each such clip is cut and retimed here with ffmpeg (setpts) into assets/clips/<id>.mp4,
and the scene plays it at 1x from 0. The footage and the timing are the same.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "clips"
VIDEO = re.compile(r'<video([^>]*?)id="([^"]+)"([^>]*?)src="assets/rec/([^"]+)"([^>]*?)>')


def attr(tag: str, name: str, default: str | None = None) -> str | None:
    m = re.search(rf'{name}="([^"]+)"', tag)
    return m.group(1) if m else default


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for comp in sorted((ROOT / "compositions").glob("s*.html")):
        html = comp.read_text(encoding="utf-8")
        changed = False
        for m in list(VIDEO.finditer(html)):
            tag = m.group(0)
            rate = float(attr(tag, "data-playback-rate", "1"))
            if rate == 1:
                continue
            vid, src = m.group(2), m.group(4)
            start = float(attr(tag, "data-media-start", "0"))
            dur = float(attr(tag, "data-duration"))
            out = OUT / f"{vid}.mp4"
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start}", "-t", f"{dur * rate + 0.2:.3f}",
                "-i", str(ROOT / "assets" / "rec" / src),
                "-vf", f"setpts=(PTS-STARTPTS)/{rate},fps=30", "-an", "-t", f"{dur + 0.1:.3f}",
                "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuvj420p",
                "-color_range", "pc", "-colorspace", "bt470bg", "-g", "15", "-movflags", "+faststart", str(out),
            ], check=True)
            new = (tag.replace(f'src="assets/rec/{src}"', f'src="assets/clips/{vid}.mp4"')
                   .replace(f'data-media-start="{attr(tag, "data-media-start")}"', 'data-media-start="0"')
                   .replace(f' data-playback-rate="{attr(tag, "data-playback-rate")}"', ""))
            new = new.replace("<video", f"<video data-retimed=\"{src} from {start}s at {rate}x\"", 1)
            html = html.replace(tag, new)
            changed = True
            print(f"{comp.name}: {vid} <- {src} {start}s x{rate} for {dur}s")
        if changed:
            comp.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
