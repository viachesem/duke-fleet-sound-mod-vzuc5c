#!/usr/bin/env python3
"""Build TTS / voice-actor packages from script/lines.csv.

Outputs per language into build/tts/<lang>/:
  elevenlabs_v2.jsonl  - text with <break/> tags + per-line voice_settings
  elevenlabs_v3.jsonl  - text with [audio tags] and "..." pauses
  plain.txt            - "filename<TAB>text" with "..." pauses, for any web TTS
  script_for_actor.md  - lines grouped by event with delivery notes

Usage: python3 tools/make_tts_package.py [--lang ru|en|all]
"""
import argparse
import json

from common import BUILD, LANGS, PAUSE, events, load_lines, plain_text

# Stability: lower = more expressive. Style: higher = more exaggerated.
VOICE_SETTINGS = {
    "smug":       {"stability": 0.45, "style": 0.45},
    "cocky":      {"stability": 0.40, "style": 0.55},
    "amused":     {"stability": 0.40, "style": 0.50},
    "deadpan":    {"stability": 0.65, "style": 0.20},
    "bored":      {"stability": 0.60, "style": 0.30},
    "grim":       {"stability": 0.55, "style": 0.35},
    "angry":      {"stability": 0.35, "style": 0.60},
    "alarmed":    {"stability": 0.30, "style": 0.65},
    "triumphant": {"stability": 0.40, "style": 0.60},
}
PAUSE_SEC = {"slow": 0.6, "medium": 0.45, "fast": 0.3}
V3_TAGS = {
    "smug": "[smug]", "cocky": "[confident]", "amused": "[amused]",
    "deadpan": "[deadpan]", "bored": "[bored]", "grim": "[serious]",
    "angry": "[annoyed]", "alarmed": "[shouting]", "triumphant": "[triumphant]",
}


def text_for(row, lang):
    return row[f"text_{lang}"].strip()


def v2_text(text, pace):
    brk = f' <break time="{PAUSE_SEC[pace]}s" /> '
    return brk.join(p.strip() for p in text.split(PAUSE))


def dotted(text):
    parts = [p.strip() for p in text.split(PAUSE)]
    head = [p[:-1] + "..." if p.endswith(".") else p + " ..." for p in parts[:-1]]
    return " ".join(head + parts[-1:])


def build(rows, lang):
    out = BUILD / "tts" / lang
    out.mkdir(parents=True, exist_ok=True)

    with open(out / "elevenlabs_v2.jsonl", "w", encoding="utf-8") as v2, \
         open(out / "elevenlabs_v3.jsonl", "w", encoding="utf-8") as v3, \
         open(out / "plain.txt", "w", encoding="utf-8") as plain:
        for r in rows:
            text, emo, pace = text_for(r, lang), r["emotion"], r["pace"]
            settings = {"similarity_boost": 0.8, "use_speaker_boost": True,
                        **VOICE_SETTINGS[emo]}
            v2.write(json.dumps({"id": r["id"], "text": v2_text(text, pace),
                                 "voice_settings": settings},
                                ensure_ascii=False) + "\n")
            v3.write(json.dumps({"id": r["id"],
                                 "text": f"{V3_TAGS[emo]} {dotted(text)}",
                                 "voice_settings": settings},
                                ensure_ascii=False) + "\n")
            plain.write(f"{r['id']}\t{dotted(text)}\n")

    md = [f"# Duke Fleet: сценарий озвучки ({lang.upper()})", "",
          f"Реплик: {len(rows)}. `//` — драматическая пауза. "
          "Имя файла = id + `.wav`.", ""]
    for key, group in events(rows).items():
        md += [f"## {group[0]['event_ru']} (`{key}`)", "",
               "| Файл | Реплика | Эмоция / темп | Указание |",
               "|---|---|---|---|"]
        for r in group:
            md.append(f"| `{r['id']}` | {text_for(r, lang)} | "
                      f"{r['emotion']} / {r['pace']} | {r['direction']} |")
        md.append("")
    (out / "script_for_actor.md").write_text("\n".join(md), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lang", choices=[*LANGS, "all"], default="all")
    args = ap.parse_args()
    rows = load_lines()
    bad = {r["emotion"] for r in rows} - VOICE_SETTINGS.keys()
    bad |= {r["pace"] for r in rows} - PAUSE_SEC.keys()
    if bad:
        raise SystemExit(f"Unknown emotion/pace values in lines.csv: {sorted(bad)}")
    for lang in (LANGS if args.lang == "all" else (args.lang,)):
        print(f"{lang}: {len(rows)} lines -> {build(rows, lang)}")
    print("subtitles example:", plain_text(rows[0]["text_ru"]))


if __name__ == "__main__":
    main()
