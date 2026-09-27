#!/usr/bin/env python3
"""Generate raw WAV files via the ElevenLabs text-to-speech API.

Reads build/tts/<lang>/elevenlabs_<v2|v3>.jsonl (run make_tts_package.py first)
and writes audio/raw/<lang>/<id>.wav (44.1 kHz mono PCM). Existing files are
skipped, so the script can be re-run after a failure or after deleting takes
you did not like.

Environment:
  ELEVENLABS_API_KEY   required (not needed for --dry-run)
  ELEVENLABS_VOICE_ID  required unless --voice-id is given

Examples:
  python3 tools/tts_generate.py --lang ru --dry-run
  python3 tools/tts_generate.py --lang ru --only DF_battle_start_01,DF_torps_detected_01
  python3 tools/tts_generate.py --lang ru --takes 3     # 3 variants per line
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import wave

from common import BUILD, LANGS, ROOT

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=pcm_44100"
MODELS = {"v2": "eleven_multilingual_v2", "v3": "eleven_v3"}
RATE = 44100


def synth(text, settings, voice, model, key, retries=4):
    body = json.dumps({"text": text, "model_id": model,
                       "voice_settings": settings}).encode()
    req = urllib.request.Request(
        API.format(voice=voice), data=body, method="POST",
        headers={"xi-api-key": key, "Content-Type": "application/json",
                 "Accept": "audio/pcm"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503) or attempt == retries:
                raise SystemExit(f"HTTP {e.code}: {e.read()[:500]!r}")
        except urllib.error.URLError:
            if attempt == retries:
                raise
        time.sleep(2 ** (attempt + 1))


def write_wav(path, pcm):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lang", choices=LANGS, default="ru")
    ap.add_argument("--model", choices=MODELS, default="v2")
    ap.add_argument("--voice-id", default=os.environ.get("ELEVENLABS_VOICE_ID"))
    ap.add_argument("--only", help="comma-separated line ids")
    ap.add_argument("--takes", type=int, default=1,
                    help="variants per line; takes >1 are saved as <id>__tN.wav")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = BUILD / "tts" / args.lang / f"elevenlabs_{args.model}.jsonl"
    if not src.exists():
        raise SystemExit(f"{src} not found: run tools/make_tts_package.py first")
    items = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l]
    if args.only:
        wanted = set(args.only.split(","))
        items = [i for i in items if i["id"] in wanted]
        missing = wanted - {i["id"] for i in items}
        if missing:
            raise SystemExit(f"Unknown ids: {sorted(missing)}")

    key = os.environ.get("ELEVENLABS_API_KEY")
    if not args.dry_run and not (key and args.voice_id):
        raise SystemExit("Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID (or --voice-id)")

    out_dir = ROOT / "audio" / "raw" / args.lang
    done = 0
    for item in items:
        for t in range(1, args.takes + 1):
            name = item["id"] + (f"__t{t}" if args.takes > 1 else "") + ".wav"
            path = out_dir / name
            if path.exists():
                continue
            print(f"{name}: {item['text']}")
            if args.dry_run:
                continue
            write_wav(path, synth(item["text"], item["voice_settings"],
                                  args.voice_id, MODELS[args.model], key))
            done += 1
    print(f"generated {done} file(s) into {out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
