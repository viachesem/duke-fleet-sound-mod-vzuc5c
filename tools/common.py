"""Shared helpers for the Duke Fleet tooling (stdlib only)."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINES_CSV = ROOT / "script" / "lines.csv"
BUILD = ROOT / "build"

PAUSE = "//"
LANGS = ("ru", "en")


def load_lines(path=LINES_CSV):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    ids = [r["id"] for r in rows]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise SystemExit(f"Duplicate ids in {path}: {sorted(dupes)}")
    return rows


def plain_text(text):
    """Subtitle-style text: pause markers collapsed to a space."""
    return " ".join(p.strip() for p in text.split(PAUSE))


def events(rows):
    """Ordered mapping event_key -> list of rows, preserving CSV order."""
    out = {}
    for r in rows:
        out.setdefault(r["event_key"], []).append(r)
    return out
