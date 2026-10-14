#!/usr/bin/env python3
"""
Put a private copy of Node.js in the person's home folder, only if none is usable.

    python3 scripts/get_node.py        -> prints the path to a working `node`, or exits 1

Node is only here so Google Lighthouse can run on this computer, in Chrome,
instead of through Google's free web service, which turns away anonymous
requests when a room full of people use it at once (measured: HTTP 429).

No admin rights, no password, no installer: the official build from
nodejs.org is unpacked into ~/.ai-preview/node and nothing outside that
folder is touched. Deleting the folder undoes it completely.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

HOME_DIR = Path.home() / ".ai-preview" / "node"
MIN_MAJOR = 18


def works(node: str) -> bool:
    """node runs, is new enough, and has npx beside it (Lighthouse is fetched with npx)."""
    bindir = os.path.dirname(node)
    if not os.path.exists(os.path.join(bindir, "npx.cmd" if os.name == "nt" else "npx")):
        return False
    try:
        out = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=20).stdout.strip()
        return out.startswith("v") and int(out[1:].split(".")[0]) >= MIN_MAJOR
    except Exception:
        return False


def existing():
    # Same order as grade_site.find_node(): our private copy first, then whatever is on PATH.
    # AI_PREVIEW_FRESH_NODE=1 (the CI smoke test) ignores a system Node, so the download a
    # student's bare machine depends on is exercised on every operating system.
    system = None if os.environ.get("AI_PREVIEW_FRESH_NODE") else shutil.which("node")
    for cand in [str(HOME_DIR / "bin" / "node"), str(HOME_DIR / "node.exe"), system]:
        if cand and Path(cand).exists() and works(cand):
            return cand
    return None


def target():
    system = platform.system()
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
    if system == "Darwin":
        return "darwin-" + arch, ".tar.gz"
    if system == "Windows":
        return "win-" + arch, ".zip"
    return "linux-" + arch, ".tar.gz"


def main() -> int:
    found = existing()
    if found:
        print(found)
        return 0

    plat, ext = target()
    with urlopen(Request("https://nodejs.org/dist/index.json", headers={"User-Agent": "ai-preview"}), timeout=30) as r:
        releases = json.loads(r.read().decode())
    version = next(x["version"] for x in releases if x.get("lts"))
    name = "node-%s-%s" % (version, plat)
    url = "https://nodejs.org/dist/%s/%s%s" % (version, name, ext)
    print("Downloading %s ..." % url, file=sys.stderr, flush=True)

    tmp = Path(tempfile.mkdtemp())
    archive = tmp / (name + ext)
    with urlopen(Request(url, headers={"User-Agent": "ai-preview"}), timeout=300) as r, open(archive, "wb") as f:
        shutil.copyfileobj(r, f)

    if ext == ".zip":
        with zipfile.ZipFile(archive) as z:
            z.extractall(tmp)
    else:
        with tarfile.open(archive) as t:
            t.extractall(tmp)

    if HOME_DIR.exists():
        shutil.rmtree(HOME_DIR)
    HOME_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(tmp / name), str(HOME_DIR))
    shutil.rmtree(tmp, ignore_errors=True)

    node = str(HOME_DIR / ("node.exe" if ext == ".zip" else "bin/node"))
    if not works(node):
        print("Node was unpacked but does not run.", file=sys.stderr)
        return 1
    print(node)
    return 0


if __name__ == "__main__":
    sys.exit(main())
