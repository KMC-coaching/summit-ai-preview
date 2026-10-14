#!/usr/bin/env python3
"""
Check, build, serve, open, measure. The one thing Claude runs to show the preview.

    python3 scripts/launch.py            first launch, "open my preview", and after every change
    python3 scripts/launch.py --no-open  rebuild and re-measure, leave the browser alone

  1. check_preview.py   refuses an unfinished content.json
  2. serve.py           starts (or reuses) the local server, so the address is known
  3. build_site.py      builds every page with that address in its canonical links
  4. opens Google Chrome on the dashboard (never Claude's built-in browser)
  5. starts grade_site.py --local on the new site, in the background; the
     dashboard picks the result up by itself when it lands (about a minute)

Prints one JSON line: {"url": ..., "openedIn": ..., "measuring": true}
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
sys.path.insert(0, str(ROOT / "scripts"))
import serve  # noqa: E402  (same folder; keeps one copy of the browser logic)


def run(args):
    p = subprocess.run([PY] + args, cwd=str(ROOT), capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def main() -> int:
    code, out = run(["scripts/check_preview.py"])
    if code != 0:
        print(out)
        return 1

    port = serve.start()
    base = "http://localhost:%d" % port
    code, out = run(["scripts/build_site.py", "--base", base])
    if code != 0:
        print("BUILD FAILED:\n" + out)
        return 1

    content = json.loads((ROOT / "app" / "data" / "content.json").read_text(encoding="utf-8"))
    profile = content.get("profile") or "general"

    # The new site is measured the same way their old one was. Detached, so the
    # dashboard opens now and the result appears on it within a minute.
    stale = ROOT / "app" / "data" / "grade-preview.json"
    if stale.exists():
        stale.unlink()
    kwargs = {"creationflags": 0x00000008} if os.name == "nt" else {"start_new_session": True}
    with open(ROOT / ".preview-audit.log", "w") as log:
        subprocess.Popen([PY, "scripts/grade_site.py", base + "/site/", "--local", "--profile", profile,
                          "--label", "Your new site", "--out", "app/data/grade-preview.json"],
                         cwd=str(ROOT), stdout=log, stderr=log, stdin=subprocess.DEVNULL, **kwargs)

    url = base + "/"
    where = None if "--no-open" in sys.argv else serve.open_in_chrome(url)
    print(json.dumps({"url": url, "openedIn": where, "measuring": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
