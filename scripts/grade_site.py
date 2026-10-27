#!/usr/bin/env python3
"""
Audit a website the way our launch gate does, and say plainly what it found.

    python3 scripts/grade_site.py <url> [--label "Your website"] [--profile real-estate|lender|general]
                                        [--local] [--out app/data/grade.json]

ONE ENGINE, EVERYWHERE (owner decision, 2026-10-26)
  This file is a front door, not a grader. The checks, the rules and the grade are the
  website-health engine: grader.py, packs.py and security.py next to this file, byte-identical
  with KMC-coaching/website-health-ci (engine/), the website-health skill in both student kits,
  and ranker.kristamashore.com. The same site gets the same grade from all four. Never edit
  those three files here: fix them in website-health-ci and copy them over.

  --profile real-estate and --profile lender set the trade rules (Fair Housing, licence and
  Equal Housing; fair lending, NMLS and Equal Housing Lender). --profile general lets the
  engine read the trade from the site, as the web checker does.

--local
  For the new preview site on this computer. HTTPS and "can Google crawl it" cannot pass on a
  site that is not published, so they are marked "after launch" rather than failed.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grader  # noqa: E402
# check_preview.py reads the site with the engine's own rule lists: one list of rules, not two.
from grader import CLAIMS, COMMISSION, FAIR_LENDING, FH_FAIL, FH_WARN, INVENTED, LENDING, SLOP  # noqa: E402,F401

PROFILE_INDUSTRY = {"general": "auto", "real-estate": "real-estate", "lender": "lender"}


def audit(url, label="Your website", profile="general", local=False):
    home = grader.normalize_url(url)
    if not home:
        return grader.unreachable(url, label, "That does not look like a website address. Check it and try again.")
    try:
        return grader.audit(home, label, PROFILE_INDUSTRY[profile], "", local, lighthouse=True)
    except Exception as e:  # a site that breaks the check still gets a plain answer, never a traceback
        return grader.unreachable(home, label, "Something on this site stopped the check (%s). Nothing of yours is affected." % type(e).__name__)


def main():
    ap = argparse.ArgumentParser(description="Audit a website the way the seed's launch gate does.")
    ap.add_argument("url")
    ap.add_argument("--label", default="Your website")
    ap.add_argument("--profile", default="general", choices=sorted(PROFILE_INDUSTRY))
    ap.add_argument("--local", action="store_true", help="the preview site on this computer")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    report = audit(a.url.strip(), a.label, a.profile, a.local)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        tmp = a.out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
        os.replace(tmp, a.out)  # never leave a half-written file for the dashboard to read
    if not report.get("reachable"):
        print(report["message"])
        return 2
    t = report["totals"]
    print("\n%s  %s" % (report["label"], report["url"]))
    print("Overall: %s (%s)   %d passed, %d to fix, %d warnings, %d not measured"
          % (report["overall"], report["letter"], t["pass"], t["fail"], t["warn"], t["notMeasured"]))
    for c in report["categories"]:
        print("  %-52s %s" % (c["name"], "not measured" if c["score"] is None else c["score"]))
    if report.get("lighthouseError"):
        print("  (Lighthouse: %s)" % report["lighthouseError"])
    for c in report["checks"]:
        if c["status"] in ("fail", "todo"):
            print("  - [%s] %s: %s" % (c["status"], c["name"], (c.get("detail") or "")[:110]))
    if a.out:
        print("\nSaved to %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
