#!/usr/bin/env python3
"""Normalize raw takes into game-ready WAVs with ffmpeg.

audio/raw/<lang>/<id>.{wav,mp3,ogg,flac}  ->  audio/final/<lang>/<id>.wav
(48 kHz, mono, 16-bit PCM, silence trimmed, loudness -16 LUFS, peak -1.5 dBTP)

Only files whose name matches a line id from lines.csv are processed, so
alternative takes (<id>__t2.wav) are ignored: rename the best take to <id>.wav.

Usage:
  python3 tools/postprocess.py --lang ru
  python3 tools/postprocess.py --lang ru --radio      # ship-intercom colouring
  python3 tools/postprocess.py --lang ru --force      # re-process everything
"""
import argparse
import shutil
import subprocess

from common import LANGS, ROOT, load_lines

EXTS = (".wav", ".mp3", ".ogg", ".flac")
TRIM = ("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,"
        "areverse,"
        "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.08,"
        "areverse")
BASE = ("highpass=f=70,"
        "acompressor=threshold=-18dB:ratio=3:attack=5:release=120:makeup=2,"
        "loudnorm=I=-16:TP=-1.5:LRA=7")
RADIO = "highpass=f=250,lowpass=f=4200,acrusher=bits=12:mix=0.15,"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lang", choices=LANGS, default="ru")
    ap.add_argument("--radio", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg not found in PATH (https://ffmpeg.org/download.html)")

    ids = {r["id"] for r in load_lines()}
    src_dir = ROOT / "audio" / "raw" / args.lang
    dst_dir = ROOT / "audio" / "final" / args.lang
    dst_dir.mkdir(parents=True, exist_ok=True)
    chain = TRIM + "," + (RADIO if args.radio else "") + BASE

    sources = sorted(p for p in src_dir.glob("*") if p.suffix.lower() in EXTS)
    for src in sources:
        if src.stem not in ids:
            continue
        dst = dst_dir / f"{src.stem}.wav"
        if dst.exists() and not args.force:
            continue
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                        "-i", str(src), "-af", chain,
                        "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(dst)],
                       check=True)
        print(dst.relative_to(ROOT))


if __name__ == "__main__":
    main()
