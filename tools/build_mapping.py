#!/usr/bin/env python3
"""Check final audio against lines.csv and build the SoundModCreator mapping.

Reads audio/final/<lang>/*.wav and writes:
  build/smc_mapping_<lang>.csv   one row per file: event, SMC trigger hint, file
  build/smc_mapping_<lang>.md    same, grouped by event, for manual entry in SMC
  build/Duke_Fleet/              staged WAVs, copy target for SoundModCreator

Reports missing/unknown files and lines that are too long for their trigger
frequency. Exit code 1 if anything is missing (use --allow-missing to build a
partial mapping while recording is still in progress).

Usage: python3 tools/build_mapping.py --lang ru [--allow-missing]
"""
import argparse
import csv
import shutil
import sys
import wave

from common import BUILD, LANGS, ROOT, events, load_lines, plain_text

# Soft length limits, seconds: frequent events must stay short.
MAX_LEN = {"high": 2.5, "medium": 3.5, "low": 5.0}


def duration(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lang", choices=LANGS, default="ru")
    ap.add_argument("--allow-missing", action="store_true")
    args = ap.parse_args()

    rows = load_lines()
    src = ROOT / "audio" / "final" / args.lang
    files = {p.stem: p for p in src.glob("*.wav")} if src.exists() else {}
    ids = {r["id"] for r in rows}

    missing = [r["id"] for r in rows if r["id"] not in files]
    unknown = sorted(set(files) - ids)
    long_lines = []
    for r in rows:
        if r["id"] in files:
            d = duration(files[r["id"]])
            r["duration"] = f"{d:.2f}"
            if d > MAX_LEN[r["frequency"]]:
                long_lines.append(f"{r['id']} {d:.2f}s > {MAX_LEN[r['frequency']]}s")

    stage = BUILD / "Duke_Fleet"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    present = [r for r in rows if r["id"] in files]
    for r in present:
        shutil.copy2(files[r["id"]], stage / f"{r['id']}.wav")

    fields = ["event_key", "event_ru", "trigger_check", "file", "duration", "subtitle"]
    with open(BUILD / f"smc_mapping_{args.lang}.csv", "w", encoding="utf-8-sig",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for r in present:
            w.writerow([r["event_key"], r["event_ru"], r["trigger_check"],
                        f"{r['id']}.wav", r["duration"],
                        plain_text(r[f"text_{args.lang}"])])

    md = [f"# Duke Fleet: таблица для SoundModCreator ({args.lang.upper()})", "",
          "В SoundModCreator для каждого события выберите соответствующий "
          "игровой триггер и добавьте все файлы группы: при нескольких файлах "
          "игра выбирает случайный. Пометка «проверить» означает, что "
          "отдельного голосового триггера для события может не быть. "
          "Если в списке SMC его нет, событие пропустите.", ""]
    for key, group in events(present).items():
        g0 = group[0]
        md.append(f"## {g0['event_ru']} (`{key}`, {g0['trigger_check']})")
        md += [f"- `{r['id']}.wav` ({r['duration']} с): "
               f"{plain_text(r[f'text_{args.lang}'])}" for r in group]
        md.append("")
    (BUILD / f"smc_mapping_{args.lang}.md").write_text("\n".join(md), encoding="utf-8")

    print(f"{len(present)}/{len(rows)} lines ready, staged in {stage}")
    for title, items in (("MISSING", missing), ("UNKNOWN (not in lines.csv)", unknown),
                         ("TOO LONG", long_lines)):
        if items:
            print(f"{title}: {len(items)}")
            for i in items:
                print("  ", i)
    if missing and not args.allow_missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
