# Summit AI Preview

This folder is someone's **Summit AI Preview**. They are not technical and they never
type commands. `PY` below is `/usr/bin/python3` on a Mac (Windows: see START-HERE Step 2).

- **First run, or "build my preview":** follow `START-HERE.md` exactly, top to bottom.
- **"Open my preview"** (or anything like it): `PY scripts/launch.py` from this folder.
  It rebuilds, starts the preview if needed, and opens it in Google Chrome.
- **A prompt starting "In my Summit AI Preview,"**: they copied it from their dashboard.
  1. Do what it asks by editing `app/data/content.json` (shape in `CONTENT-SPEC.md`), or
     `scripts/grade_site.py <site> --profile <profile> --label "..." --out app/data/grade.json`
     for a website.
  2. `PY scripts/check_preview.py`, fix anything it lists.
  3. `PY scripts/launch.py --no-open`, then tell them to refresh their Chrome tab.
  4. One honest line of credit naming what they did: *"Nice. You just added a second lead
     magnet by asking for it. That's how the full system works."*

## Always

- Plain words. No repository, terminal, script, server, JSON, port, localhost.
- Never open anything in Claude's built-in browser or preview pane. Chrome only, via
  `scripts/launch.py`. If they get a choice of where a link opens: **Open in Google Chrome**.
- Never invent facts about them: no stats, reviews, testimonials, awards, license numbers
  or years they did not give. Use a visible `[placeholder]`.
- Real estate: Fair Housing applies to every word. `check_preview.py` enforces it.
- Never publish, deploy, push, email, or connect accounts. This is a local preview.
- Only read their workbook file (found by `scripts/find_brain_file.py`) and this folder.
