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

    # Krista's Workbook Hub downloads, made by her real page (examples/hub/).
    want = {"AIDR-Workbook_jordan-avery_20261018.json": ("real-estate", True),
            "AIDR-Workbook_priya-natarajan_20261018.json": ("lender", True),
            "AIDR-Workbook_sam-ortiz_20261018.json": ("real-estate", False),
            "AIDR-Workbook_taylor-brooks_20261018.json": ("real-estate", False)}
    bad = []
    for name, (prof, done) in want.items():
        code, out = run(["scripts/read_brain_file.py", str(ROOT / "examples" / "hub" / name)], env)
        try:
            r = json.loads(out)
            enough_want = name != "AIDR-Workbook_taylor-brooks_20261018.json"
            if r["answers"]["profile"] != prof or r["complete"] != done or not r.get("made_by_hub") or r.get("enough") != enough_want:
                bad.append("%s: %s %s" % (name, r["answers"]["profile"], r["complete"]))
        except Exception as e:
            bad.append("%s: %s" % (name, e))
    step("reads Workbook Hub files (profile, partial or complete)", not bad, "; ".join(bad))

    # Half-done workbooks (real downloads, 2026-10-19). First half: builds, banner on, and the
    # client FAQ and AI audit questions are offered. Skipped Day 1: not enough until asked.
    def hub(name, extra):
        code, out = run(["scripts/read_brain_file.py", str(ROOT / "examples" / "hub" / name), "--extra", str(extra)], env)
        return json.loads(out)
    none = home / "no-extra.json"
    half = hub("AIDR-Workbook_jordan-avery-first-half_20261019.json", none)
    asks = [a["id"] for a in half["ask"]]
    step("first half: builds, shows the banner, offers the missing questions",
         half["enough"] and half["partial"] and asks == ["P4.1", "P4.2", "P2.1", "P5.1"] and all(a["question"] for a in half["ask"]),
         "%s %s %s" % (half["enough"], half["partial"], asks))
    skip = hub("AIDR-Workbook_unnamed_20261019.json", none)
    extra = home / "extra-answers.json"
    extra.write_text(json.dumps({"B.name": "Jordan Avery", "D.1": "I write the plan down first.", "B.t3": "",
                                 "8.1": "Long-time owners a year out.", "P1.7": "should never replace the file"}))
    fixed = hub("AIDR-Workbook_unnamed_20261019.json", extra)
    step("skipped Day 1: asks only the Day 1 questions, in plain words, then builds from the answers",
         # The name is in My Profile (P1.1), so it is not asked again.
         not skip["enough"] and [a["id"] for a in skip["ask"]][:3] == ["D.1", "B.t3", "8.1"]
         and not any(w in a["question"] for a in skip["ask"] for w in ("Paste", "six colors"))
         and fixed["enough"] and sorted(fixed["added_here"]) == ["8.1", "B.name", "D.1"]
         and fixed["by_id"]["P1.7"] != "should never replace the file",
         "%s %s" % ([a["id"] for a in skip["ask"]], fixed.get("added_here")))
    full = hub("AIDR-Workbook_jordan-avery_20261018.json", none)
    step("finished workbook: no banner, nothing to ask", not full["partial"] and full["ask"] == [],
         "%s %s" % (full["partial"], full["ask"]))
    # The .md twin is saved 0.6 s after the .json; a re-download gets " (1)". The newest .json wins.
    dl = home / "Downloads"
    for f in ("AIDR-Workbook_sam-ortiz_20261018.json", "AIDR-Workbook_sam-ortiz_20261018.md"):
        shutil.copy(ROOT / "examples" / "hub" / f, dl / f)
    time.sleep(1.1)
    shutil.copy(ROOT / "examples" / "hub" / "AIDR-Workbook_jordan-avery_20261018.json", dl / "AIDR-Workbook_jordan-avery_20261018 (1).json")
    time.sleep(1.1)
    shutil.copy(ROOT / "examples" / "hub" / "AIDR-Workbook_jordan-avery_20261018.md", dl / "AIDR-Workbook_jordan-avery_20261018 (1).md")
    code, out = run(["scripts/find_brain_file.py"], env)
    try:
        picked = Path(json.loads(out)["path"]).name
    except Exception:
        picked = out[-200:]
    step("finder picks the newest Hub .json, never its .md twin", picked == "AIDR-Workbook_jordan-avery_20261018 (1).json", picked)
    for f in dl.glob("AIDR-*"):
        f.unlink()

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
    # A student's own story, word for word, once reached the site this way (2026-10-19).
    bad["site"]["home"]["statement"] = "A widow in Land Park, selling the house she raised her kids in."
    (data / "content.json").write_text(json.dumps(bad), encoding="utf-8")
    code, out = run(["scripts/check_preview.py"], env)
    step("checker blocks a client story about family or marital status",
         code != 0 and "widow" in out and "raised her kids" in out, out[-300:])
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

    # The broker's required line, word for word, replaces "License #" and the brokerage blank,
    # and still counts as license + brokerage on every page.
    c = json.loads((data / "content.json").read_text(encoding="utf-8"))
    c["business"]["licenseLine"] = "Jordan Avery, REALTOR® | DRE #01234567 | Avery Home Group"
    (data / "content.json").write_text(json.dumps(c, indent=1), encoding="utf-8")
    code, out = run(["scripts/build_site.py", "--base", "http://127.0.0.1:9/"], env)
    page = (ROOT / "app" / "site" / "index.html").read_text(encoding="utf-8")
    step("broker's license line shows word for word, no blanks beside it",
         code == 0 and "DRE #01234567 | Avery Home Group" in page and "[Your brokerage]" not in page and "License # " not in page,
         out[-300:])
    return finish()


def finish():
    print("\n%d failure(s)%s" % (len(FAILS), (": " + "; ".join(FAILS)) if FAILS else ""), flush=True)
    return len(FAILS)


if __name__ == "__main__":
    sys.exit(main())
