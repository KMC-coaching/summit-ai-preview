#!/usr/bin/env python3
"""
Refuse to launch a preview that is not finished.

    python3 scripts/check_preview.py      -> exit 0 and "OK", or a list of what is missing

A half-filled page in front of someone who just spent ten minutes answering
questions is worse than a thirty-second delay, so every field the pages read is
checked here, in CONTENT-SPEC.md's shape.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "app" / "data" / "content.json"
GRADE = ROOT / "app" / "data" / "grade.json"

REQUIRED = [
    "business.name", "business.person", "business.profession", "business.oneLiner", "business.market",
    "brand.colors.primary", "brand.colors.accent", "brand.colors.ink", "brand.colors.paper",
    "brand.tagline", "brand.voice",
    "avatar.name", "avatar.snapshot", "avatar.pains", "avatar.wants",
    "differentiator.methodName", "differentiator.statement", "differentiator.pillars",
    "site.home.heroHeadline", "site.home.heroSub", "site.home.primaryCta", "site.home.whoItsFor",
    "site.home.steps", "site.home.closingHeadline", "site.home.closingText",
    "site.about.headline", "site.about.story", "site.about.values",
    "site.services.headline", "site.services.intro", "site.services.items",
    "site.faq", "site.contact.headline", "site.contact.text",
    "leadMagnet.title", "leadMagnet.subtitle", "leadMagnet.format", "leadMagnet.hook", "leadMagnet.bullets",
    "leadMagnet.formHeadline", "leadMagnet.buttonText", "leadMagnet.sections", "leadMagnet.closing",
    "leadMagnet.socialPost", "leadMagnet.emails",
    "audit.summary", "audit.opportunities", "audit.plan",
    "prompts",
]
COUNTS = {
    "differentiator.pillars": (3, 3), "site.home.steps": (3, 3), "leadMagnet.emails": (3, 3),
    "site.faq": (3, 8), "audit.opportunities": (2, 3), "audit.plan": (3, 5), "prompts": (4, 10),
    "leadMagnet.sections": (3, 8), "site.services.items": (2, 6),
}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def dig(obj, path):
    for k in path.split("."):
        if not isinstance(obj, dict) or k not in obj:
            return None
        obj = obj[k]
    return obj


def luminance(h):
    rgb = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = sorted([luminance(a), luminance(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def main() -> int:
    if not CONTENT.exists():
        print("MISSING: app/data/content.json has not been written yet.")
        return 1
    try:
        c = json.loads(CONTENT.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print("BROKEN: content.json is not valid JSON (%s)." % e)
        return 1

    problems = []
    for p in REQUIRED:
        v = dig(c, p)
        if v in (None, "", [], {}):
            problems.append("empty: " + p)
    for p, (lo, hi) in COUNTS.items():
        v = dig(c, p)
        if isinstance(v, list) and not (lo <= len(v) <= hi):
            problems.append("%s has %d items, needs %d-%d" % (p, len(v), lo, hi))

    colors = dig(c, "brand.colors") or {}
    for k in ("primary", "accent", "ink", "paper"):
        if k in colors and not HEX.match(str(colors[k])):
            problems.append("brand.colors.%s must be a 6-digit hex like #1F4E79" % k)
    if all(HEX.match(str(colors.get(k, ""))) for k in ("ink", "paper", "primary")):
        if contrast(colors["ink"], colors["paper"]) < 7:
            problems.append("ink on paper is hard to read (contrast %.1f, needs 7+)" % contrast(colors["ink"], colors["paper"]))
        if contrast("#FFFFFF", colors["primary"]) < 4.5:
            problems.append("white text on primary is hard to read (contrast %.1f, needs 4.5+): darken primary" % contrast("#FFFFFF", colors["primary"]))

    for i, e in enumerate(dig(c, "leadMagnet.emails") or []):
        for k in ("day", "subject", "body"):
            if e.get(k) in (None, ""):
                problems.append("leadMagnet.emails[%d].%s is empty" % (i, k))
    for i, o in enumerate(dig(c, "audit.opportunities") or []):
        for k in ("title", "why", "evidence", "whatChanges", "bossDoes"):
            if not o.get(k):
                problems.append("audit.opportunities[%d].%s is empty" % (i, k))

    if GRADE.exists():
        try:
            json.loads(GRADE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            problems.append("grade.json is not valid JSON: run the grader again")

    if problems:
        print("NOT READY:")
        for p in problems:
            print("  - " + p)
        return 1
    print("OK: content is complete%s." % ("" if GRADE.exists() else " (no website was graded)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
