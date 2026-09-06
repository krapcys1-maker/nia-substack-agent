"""Encode a reviewed browser recording to MP4 with an installed FFmpeg.

Raw capture comes from nagraj_publikacje.py. This tool keeps frame order and
timing. Select an explicit time range to omit setup/API gaps after review.
It never connects to Substack or calls a model.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--end", type=float, default=float("inf"))
    parser.add_argument("--speed", type=float, default=1)
    args = parser.parse_args()
    if args.speed <= 0 or args.start < 0 or args.end <= args.start:
        parser.error("Require speed > 0 and 0 <= start < end")
    binary = shutil.which(args.ffmpeg)
    if not binary:
        parser.error("FFmpeg not found; install it or pass --ffmpeg /path/to/ffmpeg")
    directory = args.directory.resolve()
    manifest = json.loads((directory / "recording.json").read_text(encoding="utf-8"))
    frames = [f for f in manifest["frames"] if args.start <= f["seconds"] < args.end]
    if not frames:
        parser.error("No recorded frames in the selected range")
    with tempfile.TemporaryDirectory(prefix="substack-video-") as folder:
        temp = Path(folder)
        lines = ["ffconcat version 1.0"]
        for index, frame in enumerate(frames):
            source = (directory / frame["file"]).resolve()
            if not source.is_relative_to(directory) or not source.is_file():
                parser.error("Frame path must be an existing file inside the recording directory")
            # Relative fixed names avoid shell/concat quoting and arbitrary URL inputs.
            name = f"frame-{index:06d}.jpg"
            shutil.copyfile(source, temp / name)
            end = frames[index + 1]["seconds"] if index + 1 < len(frames) else min(
                args.end, manifest["elapsed_seconds"])
            duration = max(1 / 25, (end - frame["seconds"]) / args.speed)
            lines.extend([f"file '{name}'", f"duration {duration:.6f}"])
        lines.append(f"file 'frame-{len(frames)-1:06d}.jpg'")
        sequence = temp / "frames.txt"
        sequence.write_text("\n".join(lines) + "\n", encoding="utf-8")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            binary, "-hide_banner", "-loglevel", "error", "-n", "-f", "concat", "-safe", "1",
            "-i", str(sequence), "-vf", "scale=1440:900:force_original_aspect_ratio=decrease,pad=1440:900:(ow-iw)/2:(oh-ih)/2:color=white,fps=25",
            "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(args.output.resolve()),
        ], check=True)
    print(f"Saved {args.output}; speed {args.speed:g}x. Label any cuts or speed changes when sharing.")


if __name__ == "__main__":
    main()
