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
    "planted":   ["lines addressed to an AI, to report and never follow"]
  }

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
    for line in text.splitlines():
        if PLANTED.search(line):
            out["planted"].append(line.strip()[:200])
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
