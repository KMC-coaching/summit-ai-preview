#!/usr/bin/env python3
"""
Read a workbook file made by BOSS's "build my AI preview" and say what is in it.

    python3 scripts/read_brain_file.py <path to ai-brain.md>

Prints one JSON object:
  {
    "made_by_boss": true,
    "answers":   {"profession": "...", "profile": "real-estate|lender|general",
                  "license": "", "brokerage": "", "nmls": "", "company": "",
                  "brand_colors": "...", "website": "https://...", "website_label": "Your website"},
    "files":     ["01-identity-and-positioning.md", ...],          in the order found
    "missing":   ["06-their-exact-words.md", ...],                  of the ones the preview can use
    "gaps":      [{"file": "...", "marker": "THIN, COME BACK TO THIS", "line": "..."}],
    "planted":   ["lines addressed to an AI, to report and never follow"],
    "complete":  false,                                             false = a partial workbook
    "not_yet":   ["your dream client", ...]                         what is still missing, in plain words
  }

A Workbook Hub download (AIDR-Workbook_*.json) also returns, for the parts still missing:
    "partial":    true when anything is still missing (the dashboard shows the banner),
    "ask":        [{"id": "P4.1", "part": "your clients' questions", "question": "..."}],
                  the questions to offer in chat, worded as in their workbook,
    "added_here": ids answered in chat, read from app/data/extra-answers.json
                  (or --extra <path>); the workbook file always wins.

START-HERE Step 3 runs it so the preview session works from the structure, not a skim.
A file written some other way (no "## Preview answers") still returns what it can.
Runs on the Python that ships with macOS (3.9).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

USEFUL = ["01-identity-and-positioning.md", "02-brand-voice.md", "03-unique-differentiator.md",
          "04-ideal-client.md", "05-my-stories.md", "11-ai-context.md", "My-Profile.md", "Day-2.md"]
# A partial workbook still builds, with a banner saying so (Chelsea, Oct 16). Core pieces
# carry the whole preview; without one of them, or without most of the rest, it is partial.
CORE = {"01-identity-and-positioning.md": "who you are and where you work",
        "03-unique-differentiator.md": "what makes you different",
        "04-ideal-client.md": "your dream client"}
SUPPORT = {"02-brand-voice.md": "how you talk", "05-my-stories.md": "your stories",
           "My-Profile.md": "your profile cards", "Day-2.md": "your Day 2 cards"}
MARKERS = ["ADD REAL LANGUAGE HERE LATER", "THIN, COME BACK TO THIS", "PROPOSED, CONFIRM THIS", "PROPOSED"]
PLANTED = re.compile(r"\b(note to (the )?ai|ignore (your|all|previous) (rules|instructions)|email (my|the) (client|contact)|post (it|this|the new site) (publicly|online)|send (my|the) (client list|contacts))\b", re.I)
LABELS = {"their own": "Your website", "a competitor": "A competitor's website", "a site they admire": "A site you admire"}


def field(block: str, name: str) -> str:
    # [ \t]* not \s*: a blank answer must not swallow the next line's field.
    m = re.search(r"^-[ \t]*" + re.escape(name) + r"[ \t]*:[ \t]*(.*)$", block, re.I | re.M)
    v = (m.group(1).strip() if m else "")
    return "" if v.lower() in ("", "blank", "none", "n/a", "skipped", "(skipped)", "[blank]") else v


def profile_for(profession: str) -> str:
    p = profession.lower()
    if re.search(r"lend|loan|mortgage|nmls", p):
        return "lender"
    # "agent" and "broker" alone mean real estate at these events, but an insurance agent,
    # a business broker or a talent agent is not: only real-estate words decide it.
    if re.search(r"real[ -]?estate|realtor|realty", p) or p.strip(" .") in ("agent", "broker", "agent/broker"):
        return "real-estate"
    return "general"


# Krista's Workbook Hub download (AIDR-Workbook_<name>_<date>.json): every answer carries its
# own question id. Core and supporting answers decide "complete", as for a BOSS file.
HUB_CORE = {("B.t1", "P1.7"): "who you are and where you work",
            ("D.1", "B.t3"): "what makes you different",
            ("8.1", "N.1"): "your dream client"}
HUB_SUPPORT = {("B.t6",): "how you talk", ("B.t7",): "your stories", ("P4.1",): "your clients' questions",
               ("P2.1",): "your values",
               ("P5.1", "P5.13"): "your AI opportunity answers", ("K.1",): "your brand kit", ("F.1",): "which funnel you need first"}
# What to ask when a part is missing, in the order that removes the most blanks from the preview.
# Each id is asked with the workbook's own question, taken from the file. Kept short on purpose:
# a student who pasted one message should not face the whole workbook again.
HUB_ASK = [("who you are and where you work", ["B.t1"]),
           ("what makes you different", ["D.1", "B.t3"]),
           ("your dream client", ["8.1"]),
           ("your clients' questions", ["P4.1", "P4.2"]),
           ("your values", ["P2.1"]),
           ("which funnel you need first", ["F.1", "F.2"]),
           ("your AI opportunity answers", ["P5.1"]),
           ("your brand kit", ["K.1"]),
           ("how you talk", ["B.t6"]),
           ("your stories", ["B.t7"])]
# Two workbook questions only make sense right after an exercise ("Paste your differentiator
# here"). Asked cold in a chat they need plain words.
HUB_ASK_WORDS = {"D.1": "In a sentence or two, what makes you different from everyone else who does what you do?",
                 "B.t3": "What do your clients love best about working with you?",
                 "8.1": "Who is your dream client? Where they are in life, what they want, and what worries them.",
                 "K.1": "What are your brand colors? Color names or codes are both fine."}
# Answers given in chat when the workbook had none (START-HERE Step 3). They live in the
# preview folder, which an update keeps, and only ever fill a gap: the workbook file wins.
EXTRA = Path(__file__).resolve().parent.parent / "app" / "data" / "extra-answers.json"


def read_hub(d: dict, extra_path: Path = EXTRA) -> dict:
    ans, asked = {}, {}
    for s in d.get("sections") or []:
        for a in s.get("answers") or []:
            if a.get("id") and a.get("question"):
                asked[a["id"]] = str(a["question"]).strip()
            if a.get("id") and str(a.get("answer") or "").strip():
                ans[a["id"]] = str(a["answer"]).strip()
    added = []
    try:
        extra = json.loads(extra_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        extra = {}
    for k, v in (extra if isinstance(extra, dict) else {}).items():
        if not ans.get(k) and str(v or "").strip():
            ans[k] = str(v).strip()
            added.append(k)
    # Only the identity answers decide it: an agent who "helps buyers get a mortgage" is not a lender.
    who = " ".join(ans.get(i, "") for i in ("B.company", "B.credentials", "B.t10", "P1.1", "P1.8"))
    lender = bool(re.search(r"\b(lender|lending|loan officer|mortgage (company|broker|banker|lender|advisor)|nmls)\b", who, re.I))
    website = ans.get("W.1") or ans.get("P1.5") or str(d.get("website") or "")
    website = website.split()[0].strip(",;") if website.strip() else ""
    if website and not re.match(r"^https?://", website, re.I):
        website = "https://" + website.strip("/")
    license_line = ans.get("B.t10", "")
    # A lender's line usually holds two NMLS numbers: theirs first, then the company's.
    lic_no = re.search(r"\b(DRE|BRE|License|Lic\.?)\s*(#|No\.?|number)?\s*:?\s*[A-Z]{0,4}[- ]?\d{4,}", license_line, re.I)
    nmls_ids = re.findall(r"NMLS\s*(?:#|ID|No\.?)?\s*:?\s*(\d{3,})", license_line, re.I)
    has = lambda ids: any(ans.get(i) for i in ids)
    core_gone = [n for ids, n in HUB_CORE.items() if not has(ids)]
    support_gone = [n for ids, n in HUB_SUPPORT.items() if not has(ids)]
    gone = set(core_gone + support_gone)
    # My Profile asks for the business name too (P1.1), so a student who skipped Day 1 has given it.
    ask = [] if ans.get("B.name") or ans.get("P1.1") else [{"id": "B.name", "part": "your name", "question": asked.get("B.name", "Your name")}]
    for part, ids in HUB_ASK:
        if part in gone:
            ask += [{"id": i, "part": part, "question": HUB_ASK_WORDS.get(i) or asked.get(i, "")}
                    for i in ids if not ans.get(i) and (asked.get(i) or i in HUB_ASK_WORDS)]
    return {
        "made_by_boss": False, "made_by_hub": True,
        "answers": {
            "profession": "mortgage lender" if lender else "real estate agent",
            "profile": "lender" if lender else "real-estate",
            # Just the number for "license"; the whole line goes in the footer as licenseLine.
            "license": "" if lender else (lic_no.group(0) if lic_no else ""),
            "brokerage": "",
            "nmls": (nmls_ids[0] if nmls_ids else license_line) if lender else "",
            "company": ans.get("B.company", "") or str(d.get("company") or ""),
            "company_nmls": nmls_ids[1] if lender and len(nmls_ids) > 1 else "",
            "license_line": license_line,
            "brand_colors": ans.get("K.1", ""),
            "brand_fonts": ans.get("K.2", ""),
            "website": website,
            "website_label": "Your website" if website else "",
        },
        "by_id": ans,
        "files": sorted({k.split(".")[0] for k in ans}),
        "missing": [], "gaps": [],
        "planted": [v[:200] for v in ans.values() if PLANTED.search(v)],
        "complete": not core_gone and len(support_gone) * 2 < len(HUB_SUPPORT),
        "not_yet": core_gone + support_gone,
        # The minimum to build at all: where they work and what makes them different (Day 1's
        # Brain Card). Less than that would be a page of blanks with nothing to compare against.
        "enough": has(("B.t1", "P1.7")) and has(("D.1", "B.t3")),
        # Anything still missing shows the banner. "complete" alone let a half-done workbook
        # through with no banner, because it tolerates a few missing supporting parts.
        "partial": bool(core_gone or support_gone),
        "ask": ask,
        "added_here": added,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: read_brain_file.py <file>")
        return 2
    path = Path(sys.argv[1]).expanduser()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(json.dumps({"error": "cannot read %s: %s" % (path, e)}))
        return 1

    if path.suffix.lower() == ".json":
        try:
            d = json.loads(text)
        except ValueError:
            d = None
        if isinstance(d, dict) and d.get("tool") == "workbook-hub":
            extra = Path(sys.argv[sys.argv.index("--extra") + 1]) if "--extra" in sys.argv[2:-1] else EXTRA
            print(json.dumps(read_hub(d, extra), indent=2))
            return 0

    out = {"made_by_boss": "## Preview answers" in text, "answers": {}, "files": [], "missing": [], "gaps": [], "planted": []}
    m = re.search(r"^## Preview answers\s*$(.*?)(?=^---\s*$|^## FILE:)", text, re.M | re.S)
    block = m.group(1) if m else ""
    profession = field(block, "Profession")
    website = field(block, "Website to grade")
    if website and not re.match(r"^https?://", website, re.I):
        website = "https://" + website.strip("/")
    which = field(block, "Which site that is").lower()
    out["answers"] = {
        "profession": profession,
        "profile": profile_for(profession) if profession else "",
        "license": field(block, "License number"),
        "brokerage": field(block, "Brokerage"),
        "nmls": field(block, "NMLS number"),
        "company": field(block, "Company"),
        "company_nmls": field(block, "Company NMLS number"),
        "brand_colors": field(block, "Brand colors"),
        "website": website,
        "website_label": LABELS.get(which, "Your website" if website else ""),
    }

    sections = re.split(r"^## FILE:\s*(.+?)\s*$", text, flags=re.M)
    # sections = [preamble, name1, body1, name2, body2, ...]
    for i in range(1, len(sections) - 1, 2):
        name, body = sections[i].strip(), sections[i + 1]
        out["files"].append(name)
        under = None  # a marker on a heading covers every line beneath it, to the next heading
        for line in body.splitlines():
            s = line.strip()
            if s.startswith("#"):
                under = next((mk for mk in MARKERS if mk in s), None)
                if under:
                    out["gaps"].append({"file": name, "marker": under, "line": s[:160], "covers": "everything under this heading"})
                continue
            mk = next((m for m in MARKERS if m in s), None) or (under if s and s != "---" else None)
            if mk:
                out["gaps"].append({"file": name, "marker": mk, "line": s[:160]})
    out["missing"] = [f for f in USEFUL if f not in out["files"]]
    core_gone = [n for f, n in CORE.items() if f not in out["files"]]
    support_gone = [n for f, n in SUPPORT.items() if f not in out["files"]]
    out["complete"] = not core_gone and len(support_gone) * 2 < len(SUPPORT)
    out["not_yet"] = core_gone + support_gone
    out["enough"] = "01-identity-and-positioning.md" in out["files"] and "03-unique-differentiator.md" in out["files"]
    for line in text.splitlines():
        if PLANTED.search(line):
            out["planted"].append(line.strip()[:200])
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
