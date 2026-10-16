#!/usr/bin/env python3
"""
Refuse to build a preview that is not finished, or that breaks a rule.

    python3 scripts/check_preview.py      -> "OK: ..." (exit 0), or a list of what to fix (exit 1)

Checks app/data/content.json against CONTENT-SPEC.md, then scans every word in
it with the SAME lists the audit uses (scripts/grade_site.py): Fair Housing for
real estate, FTC claims for everyone, em-dashes and stock AI phrases. Catching
them here costs nothing; catching them on the report card is embarrassing.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import grade_site as G  # noqa: E402  one list of rules, not two

CONTENT = ROOT / "app" / "data" / "content.json"
LIB = ROOT / "app" / "assets" / "img" / "library" / "library.json"
PREFIX = "In my AI Preview,"

COMMON = [
    "profile", "business.name", "business.person", "business.profession", "business.oneLiner", "business.market",
    "brand.colors.primary", "brand.colors.accent", "brand.tagline", "brand.voice",
    "avatar.name", "avatar.snapshot", "avatar.pains", "avatar.wants",
    "differentiator.methodName", "differentiator.statement", "differentiator.pillars",
    "site.home.heroLead", "site.home.heroSub", "site.home.primaryCta", "site.home.statement",
    "site.home.differenceHeadline", "site.home.differenceBody", "site.home.tickerHeadline", "site.home.tickerCaptions",
    "site.home.splitHeadline", "site.home.splitBody", "site.home.closingHeadline", "site.home.closingText",
    "site.about.headline", "site.about.story", "site.about.values", "site.faq", "site.contact.headline", "site.contact.text",
    "leadMagnet.title", "leadMagnet.subtitle", "leadMagnet.format", "leadMagnet.hook", "leadMagnet.bullets",
    "leadMagnet.formHeadline", "leadMagnet.buttonText", "leadMagnet.sections", "leadMagnet.closing",
    "leadMagnet.socialPost", "leadMagnet.emails", "audit.summary", "audit.opportunities", "audit.plan", "prompts",
]
BY_PROFILE = {
    "real-estate": ["business.areas", "site.sell.headline", "site.sell.intro", "site.sell.steps", "site.buy.headline", "site.buy.intro", "site.buy.steps"],
    "general": ["site.services.headline", "site.services.intro", "site.services.items"],
    "lender": ["business.areas", "site.loans.headline", "site.loans.intro", "site.loans.items", "site.buy.headline", "site.buy.intro", "site.buy.steps"],
}
COUNTS = {
    "differentiator.pillars": (3, 4), "site.home.tickerCaptions": (6, 6), "leadMagnet.emails": (3, 3),
    "site.faq": (4, 6), "audit.opportunities": (2, 3), "audit.plan": (3, 5), "prompts": (5, 10),
    "leadMagnet.sections": (4, 7), "site.services.items": (2, 6), "site.loans.items": (2, 6), "site.sell.steps": (3, 5), "site.buy.steps": (3, 5),
    "site.about.values": (3, 3), "leadMagnet.bullets": (3, 5),
}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def dig(obj, path):
    for k in path.split("."):
        if not isinstance(obj, dict) or k not in obj:
            return None
        obj = obj[k]
    return obj


def strings(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("wordsTheyAvoid",):  # the list of words they never use, quoted on purpose
                continue
            yield from strings(v, path + "." + k if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from strings(v, "%s[%d]" % (path, i))


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
    profile = c.get("profile")
    if profile not in BY_PROFILE:
        problems.append('profile must be "real-estate", "lender" or "general"')
    for p in COMMON + BY_PROFILE.get(profile, []):
        if dig(c, p) in (None, "", [], {}):
            problems.append("empty: " + p)
    for p, (lo, hi) in COUNTS.items():
        v = dig(c, p)
        if isinstance(v, list) and not (lo <= len(v) <= hi):
            problems.append("%s has %d items, needs %d-%d" % (p, len(v), lo, hi))

    for k in ("primary", "accent"):
        v = dig(c, "brand.colors." + k)
        if v and not HEX.match(str(v)):
            problems.append("brand.colors.%s must be a 6-digit hex like #1F4E79" % k)

    for i, e in enumerate(dig(c, "leadMagnet.emails") or []):
        for k in ("day", "subject", "body"):
            if e.get(k) in (None, ""):
                problems.append("leadMagnet.emails[%d].%s is empty" % (i, k))
    for i, o in enumerate(dig(c, "audit.opportunities") or []):
        for k in ("title", "why", "evidence", "whatChanges", "bossDoes"):
            if not o.get(k):
                problems.append("audit.opportunities[%d].%s is empty" % (i, k))
    for i, p in enumerate(dig(c, "prompts") or []):
        if not str(p.get("prompt", "")).startswith(PREFIX):
            problems.append('prompts[%d].prompt must start with "%s"' % (i, PREFIX))
        if not p.get("group") or not p.get("label"):
            problems.append("prompts[%d] needs a group and a label" % i)
    for i, d in enumerate(dig(c, "audit.plan") or []):
        if d.get("prompt") and not str(d["prompt"]).startswith(PREFIX):
            problems.append('audit.plan[%d].prompt must start with "%s"' % (i, PREFIX))
    for i, s in enumerate(dig(c, "business.stats") or []):
        if not isinstance(s.get("value"), (int, float)) or not s.get("label"):
            problems.append("business.stats[%d] needs a numeric value and a label (and only real numbers from their file)" % i)

    # A second (third...) lead magnet: same required fields as the first, its own pages.
    MAG = ["title", "subtitle", "format", "hook", "bullets", "formHeadline", "buttonText", "sections", "closing", "socialPost", "emails"]
    for i, m in enumerate([c.get("leadMagnet") or {}] + list(c.get("moreMagnets") or [])):
        where = "leadMagnet" if i == 0 else "moreMagnets[%d]" % (i - 1)
        if i:
            for k in MAG + ["slug"]:
                if m.get(k) in (None, "", []):
                    problems.append("empty: %s.%s" % (where, k))
        if m.get("format") and m["format"] not in ("checklist", "guide", "book", "companion"):
            problems.append('%s.format must be "checklist", "guide", "book" or "companion" (quizzes and scorecards are not built yet)' % where)
        if m.get("format") == "companion" and not str(m.get("prompt") or "").strip():
            problems.append("%s.prompt: an AI companion needs the prompt the visitor pastes into ChatGPT or Claude" % where)
    slugs = [m.get("slug") for m in (c.get("moreMagnets") or [])]
    if len(slugs) != len(set(slugs)):
        problems.append("moreMagnets: every slug must be different")
    for i, p in enumerate(c.get("posts") or []):
        if not p.get("text") or not p.get("platform"):
            problems.append("posts[%d] needs a platform and text" % i)

    # Numbers shown as stats must come from their own file, never from us.
    brain = (c.get("meta") or {}).get("brainFilePath")
    stats = dig(c, "business.stats") or []
    if stats:
        try:
            raw = Path(brain).expanduser().read_text(encoding="utf-8", errors="replace") if brain else ""
        except OSError:
            raw = ""
        digits = re.sub(r"[^0-9]", " ", raw)
        for i, st in enumerate(stats):
            v = str(int(st["value"])) if isinstance(st.get("value"), (int, float)) and float(st["value"]).is_integer() else str(st.get("value"))
            if not raw:
                problems.append("business.stats: set meta.brainFilePath so each number can be checked against their file")
                break
            if v not in digits.split():
                problems.append("business.stats[%d]: %s is not in their workbook file. Only their own numbers." % (i, v))

    known = {"profile", "meta", "business", "brand", "avatar", "differentiator", "images", "site", "leadMagnet", "moreMagnets", "posts", "audit", "prompts", "coach"}
    unknown = sorted(set(c) - known)
    if unknown:
        problems.append("unknown top-level keys %s: nothing reads them, so they would never show. See CONTENT-SPEC.md." % unknown)

    if LIB.exists():
        ids = {x["id"] for x in json.loads(LIB.read_text(encoding="utf-8"))}
        for slot, v in (c.get("images") or {}).items():
            for x in ([v] if isinstance(v, str) else (v or [])):
                if x not in ids:
                    problems.append('images.%s: "%s" is not in the photo library' % (slot, x))

    # The audit's own rules, run on every word before anything is built.
    rules = [(G.CLAIMS, "FTC claim"), (G.INVENTED, "invented proof"), (G.SLOP, "reads like AI")]
    if profile == "lender":
        rules += [(G.FH_FAIL + G.FAIR_LENDING, "Fair lending"), (G.LENDING, "Lending claim")]
    if profile == "real-estate":
        rules += [(G.FH_FAIL, "Fair Housing"), (G.FH_WARN, "Fair Housing risk"), (G.COMMISSION, "commission wording")]
    for path, text in strings(c):
        if path.startswith("prompts") or path.startswith("meta"):
            continue
        for patterns, kind in rules:
            for pat, why in patterns:
                m = re.search(pat, text, re.I)
                if m:
                    problems.append('%s: "%s" in %s (%s)' % (kind, m.group(0), path, why))

    warnings = []
    for path, text in strings(c):
        low = text.lower()
        for m in ("example.com", ".example", "@example", "555-01", "(555)", "lorem ipsum", "yourdomain"):
            if m in low:
                warnings.append('"%s" in %s looks like template text; the report card will flag it. Fine only if it is truly theirs.' % (m, path))
                break

    if problems:
        for w in warnings:
            problems.append("note: " + w)
        print("NOT READY:")
        for p in problems:
            print("  - " + p)
        return 1
    print("OK: content is complete and passes the %s rules." % {"real-estate": "real estate", "lender": "lending"}.get(profile, "general"))
    for w in warnings:
        print("  note: " + w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
