#!/usr/bin/env python3
"""
Find the file the Summit workbook downloaded, without asking the person where it is.

The workbook saves one file, named per BRAIN-FILE-CONTRACT.md. Browsers do not
keep that name exactly: a second download becomes "summit-ai-brain (1).md", and
Safari sometimes adds ".txt". So this looks for the name loosely, in the places
a download actually lands.

Takes the best name match (the contracted name beats a loose one), newest first
within the same match. Prints one JSON object:
  {"found": true,  "path": "...", "modified": "...", "others": [...]}   others excludes path
  {"found": false, "searched": [...], "blocked": [...]}                 blocked = macOS said no

Read-only. Runs on the Python that ships with macOS (3.9), so no newer syntax.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

# The contracted name first, then looser shapes of it, most specific first.
PATTERNS = [
    re.compile(r"^summit-ai-brain", re.I),
    re.compile(r"ai[-_ ]?brain", re.I),
    re.compile(r"summit.*(brain|workbook)", re.I),
    re.compile(r"(brain|workbook).*summit", re.I),
]
EXTENSIONS = {".md", ".txt", ".json", ".pdf", ".docx", ".markdown"}
MAX_AGE_DAYS = 120


def places() -> list[Path]:
    home = Path.home()
    out = [home / "Downloads", home / "Desktop", home / "Documents"]
    # Windows can move Downloads; OneDrive is the usual new home.
    profile = os.environ.get("USERPROFILE")
    if profile:
        p = Path(profile)
        out += [p / "Downloads", p / "OneDrive" / "Downloads", p / "OneDrive" / "Desktop"]
    seen, uniq = set(), []
    for p in out:
        if p.exists() and str(p) not in seen:
            seen.add(str(p))
            uniq.append(p)
    return uniq


def rank(name: str) -> int | None:
    for i, pat in enumerate(PATTERNS):
        if pat.search(name):
            return i
    return None


def main() -> int:
    cutoff = time.time() - MAX_AGE_DAYS * 86400
    hits = []
    searched = []
    blocked = []
    for folder in places():
        searched.append(str(folder))
        try:
            entries = list(folder.iterdir())
        except (PermissionError, OSError):
            # macOS asks before letting anything read Downloads. A refusal lands here,
            # and must be reported: "not found" would send them to re-download for nothing.
            blocked.append(str(folder))
            continue
        for f in entries:
            if not f.is_file() or f.suffix.lower() not in EXTENSIONS:
                continue
            r = rank(f.name)
            if r is None:
                continue
            mtime = f.stat().st_mtime
            if mtime < cutoff:
                continue
            hits.append((r, -mtime, f))

    if not hits:
        print(json.dumps({"found": False, "searched": searched, "blocked": blocked}, indent=2))
        return 1

    hits.sort()
    best = hits[0][2]
    print(json.dumps({
        "found": True,
        "path": str(best),
        "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(best.stat().st_mtime)),
        "others": [str(h[2]) for h in hits[1:6]],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
