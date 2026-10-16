#!/usr/bin/env python3
"""
The whole pipeline on a bare machine, without Claude: what CI runs on Windows, Mac and Linux.

    python tests/smoke.py

Every step a student's computer goes through, in order, in a throwaway home folder:
find the workbook download, put Node in place from nodejs.org, check the content,
build the site, start the local server, load every page, measure the new site with
Lighthouse, stop and restart on the same address. Each step prints PASS or FAIL;
the exit code is the number of failures.

What it cannot cover: the Claude conversation itself, the macOS/Windows permission
boxes, and opening Chrome on a desktop (CI has no screen).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
FAILS = []


def step(name, ok, detail=""):
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  -- " + detail) if detail else ""), flush=True)
    if not ok:
        FAILS.append(name)
    return ok


def run(args, env, timeout=600):
    p = subprocess.run([PY] + args, cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def get(url):
    with urlopen(url, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


def main():
    home = Path(tempfile.mkdtemp(prefix="aipreview-home-"))
    (home / "Downloads").mkdir()
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), AI_PREVIEW_FRESH_NODE="1")
    print("platform: %s, python %s, home %s" % (sys.platform, sys.version.split()[0], home), flush=True)

    # 1. The workbook file, as a browser saves a second download.
    shutil.copy(ROOT / "examples" / "ai-brain-realtor.md", home / "Downloads" / "ai-brain (1).md")
    code, out = run(["scripts/find_brain_file.py"], env)
    found = code == 0 and "ai-brain (1).md" in out
    step("finds the workbook download", found, "" if found else out[-300:])

    # 1b. The file BOSS writes ("build my AI preview"), read back into structure.
    code, out = run(["scripts/read_brain_file.py", str(ROOT / "examples" / "ai-brain-from-boss.md")], env)
    try:
        rb = json.loads(out)
        a = rb["answers"]
        ok = (rb["made_by_boss"] and a["profile"] == "real-estate" and a["license"] == "" and a["brokerage"] == ""
              and a["brand_colors"] == "deep green and brass" and a["website"].startswith("https://")
              and "My-Profile.md" in rb["files"] and not rb["planted"] and len(rb["gaps"]) > 0)
    except Exception as e:
        ok, a = False, str(e)
    step("reads the file BOSS makes (answers, files, gaps)", ok, "" if ok else str(a)[:300])
    sys.path.insert(0, str(ROOT / "scripts"))
    import read_brain_file as rbf
    cases = {"real estate agent": "real-estate", "Realtor": "real-estate", "agent": "real-estate", "loan officer": "lender",
             "mortgage broker": "lender", "independent life and health insurance agent": "general", "business broker": "general",
             "financial advisor": "general", "interior designer": "general", "online fitness and nutrition coach": "general"}
    wrong = {k: rbf.profile_for(k) for k, v in cases.items() if rbf.profile_for(k) != v}
    step("picks the right profile for each profession", not wrong, str(wrong))

    # 2. Node from nodejs.org into the home folder, no admin.
    t0 = time.time()
    code, out = run(["scripts/get_node.py"], env)
    node = next((l.strip() for l in out.splitlines() if l.strip().endswith(("node", "node.exe"))), "")
    step("downloads a private Node (%ds)" % (time.time() - t0), code == 0 and str(home) in node, out[-300:] if code else node)

    # 3. Content gate, on a real-estate fixture.
    data = ROOT / "app" / "data"
    data.mkdir(parents=True, exist_ok=True)
    for stale in ("grade-preview.json", ".measured", "grade.json"):
        if (data / stale).exists():
            (data / stale).unlink()
    shutil.copy(ROOT / "examples" / "content-realtor.json", data / "content.json")
    code, out = run(["scripts/check_preview.py"], env)
    step("content passes the checker", code == 0, out[-400:] if code else "")

    # 4. The gate catches a planted Fair Housing problem.
    c = json.loads((data / "content.json").read_text(encoding="utf-8"))
    bad = json.loads(json.dumps(c))
    bad["site"]["home"]["statement"] = "A safe neighborhood, perfect for families."
    (data / "content.json").write_text(json.dumps(bad), encoding="utf-8")
    code, out = run(["scripts/check_preview.py"], env)
    step("checker blocks Fair Housing language", code != 0 and "Fair Housing" in out, out[-300:])
    (data / "content.json").write_text(json.dumps(c, indent=1), encoding="utf-8")

    # 5. Build, serve, measure. Never opens a browser here.
    code, out = run(["scripts/launch.py", "--no-open"], env)
    url = ""
    try:
        url = json.loads(out.strip().splitlines()[-1])["url"]
    except Exception:
        pass
    if not step("launch builds and serves", code == 0 and url.startswith("http://127.0.0.1:"), out[-400:]):
        return finish()

    site = json.loads((data / "site.json").read_text(encoding="utf-8"))
    bad_pages = []
    for p in site["pages"]:
        try:
            s, body = get(url + "site/" + p["file"])
            if s != 200 or body.count("<h1") != 1 or "application/ld+json" not in body or 'rel="canonical"' not in body:
                bad_pages.append(p["file"])
        except Exception as e:
            bad_pages.append("%s (%s)" % (p["file"], e))
    step("every page loads with one h1, schema and canonical (%d pages)" % len(site["pages"]), not bad_pages, ", ".join(bad_pages))
    s, body = get(url)
    step("dashboard loads", s == 200 and "dashboard.js" in body)
    s, _ = get(url + "data/content.built.json")
    step("dashboard reads the checked snapshot", s == 200)
    s, footer = get(url + "site/index.html")
    step("real estate footer: Equal Housing + license blank", "Equal Housing Opportunity" in footer and "License #" in footer)
    import html as _html
    stmt = json.loads((ROOT / "examples" / "content-realtor.json").read_text())["site"]["home"]["statement"]
    m = re.search(r'<p class="statement[^"]*">(.*?)</p>', footer, re.S)
    step("home statement is the big quote, not a link", bool(m) and _html.unescape(re.sub("<[^>]+>", "", m.group(1))).strip()[:40] == stmt[:40],
         m.group(1)[:80] if m else "no statement found")

    # 6. The new site, measured by Lighthouse in this machine's Chrome.
    gp = data / "grade-preview.json"
    t0 = time.time()
    while time.time() - t0 < 360 and not gp.exists():
        time.sleep(5)
    if step("new site measured (%ds)" % (time.time() - t0), gp.exists(), (ROOT / ".preview-audit.log").read_text()[-500:] if (ROOT / ".preview-audit.log").exists() else ""):
        g = json.loads(gp.read_text(encoding="utf-8"))
        lh = g.get("lighthouse") or {}
        print("      overall %s %s, lighthouse %s, source %s" % (g.get("overall"), g.get("letter"), lh, g.get("lighthouseSource")), flush=True)
        if g.get("lighthouseLimit") == "windows" and lh.get("performance") is None:
            # Known Windows limit: the report card says so in plain words; check that it does.
            step("Windows: speed test shown as a Windows limit, not an error", "Windows limit" in (g.get("lighthouseError") or ""),
                 g.get("lighthouseError") or "")
        else:
            if not step("Lighthouse ran", lh.get("performance") is not None, g.get("lighthouseError") or ""):
                print("----- Lighthouse said -----\n%s\n---------------------------" % (g.get("lighthouseLog") or "(nothing)"), flush=True)
            step("accessibility 100", lh.get("accessibility") == 100, str(lh.get("accessibility")))
        step("structured data 100", any(c["name"].startswith("Structured") and c["score"] == 100 for c in g["categories"]))

    # 7. Stop and restart: same address.
    run(["scripts/serve.py", "--stop"], env)
    code, out = run(["scripts/launch.py", "--no-open"], env)
    try:
        again = json.loads(out.strip().splitlines()[-1])["url"]
    except Exception:
        again = ""
    step("restart keeps the same address", again == url, "%s -> %s" % (url, again))
    run(["scripts/serve.py", "--stop"], env)
    return finish()


def finish():
    print("\n%d failure(s)%s" % (len(FAILS), (": " + "; ".join(FAILS)) if FAILS else ""), flush=True)
    return len(FAILS)


if __name__ == "__main__":
    sys.exit(main())
