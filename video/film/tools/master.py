"""Master the rendered film's audio to -15 LUFS integrated (two-pass loudnorm), video copied.

  python tools/master.py renders/film-raw.mp4 renders/film-master.mp4
"""

import json
import os
import re
import subprocess
import sys

TARGET = {"I": -15.0, "TP": -1.5, "LRA": 11}


def main(src: str, dst: str) -> None:
    # Windows paths are case-insensitive: "ProofGate-demo.mp4" IS "proofgate-demo.mp4"
    if os.path.normcase(os.path.abspath(src)) == os.path.normcase(os.path.abspath(dst)):
        raise SystemExit("output would overwrite the input; pick another name")
    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", src, "-af",
         f"loudnorm=I={TARGET['I']}:TP={TARGET['TP']}:LRA={TARGET['LRA']}:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=True).stderr
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", probe, re.S).group(0))
    filt = (f"loudnorm=I={TARGET['I']}:TP={TARGET['TP']}:LRA={TARGET['LRA']}:measured_I={m['input_i']}:"
            f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
            f"offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-c:v", "copy", "-af", filt,
                    "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst], check=True)
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", dst, "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summary = out[out.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", summary)
    peak = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary)
    print(f"input {m['input_i']} LUFS -> {i.group(1) if i else '?'} LUFS, true peak {peak.group(1) if peak else '?'} dBFS")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
