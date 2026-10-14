# Summit AI Preview

This folder is someone's **Summit AI Preview**. They are not technical and they never
type commands. `PY` below is `/usr/bin/python3` on a Mac (Windows: see START-HERE Step 2).

- **First run, or "build my preview":** follow `START-HERE.md` exactly, top to bottom.
- **"Open my preview"** (or anything like it): `PY scripts/launch.py` from this folder.
  It rebuilds, starts the preview if needed, and opens it in Google Chrome.
- **A prompt starting "In my Summit AI Preview,"**: they copied it from their dashboard.
  1. Do what it asks by editing `app/data/content.json` (shape in `CONTENT-SPEC.md`).
     - Another lead magnet: add it to `moreMagnets` (never replace the first).
     - Posts: add them to `posts`.
     - Grading their OWN site: `--out app/data/grade.json`. Any OTHER site (a competitor,
       one they admire): `--out app/data/grades/<domain>.json`, so their own report card
       is never overwritten. (The first build is the exception: with no working site of
       their own, START-HERE puts the competitor in `grade.json`.) Use `--profile` from content.json and a plain `--label`.
     - "My sample site" means the new preview site this folder built.
     - Colors: the first color they name is `primary`, the second is `accent`. If the
       accent they name is white or near-white, keep it out of the accent slot (it would
       vanish on the page): use a deeper shade of their main color, and say so.
     - Anything the file cannot hold (reviews, a quiz, a booking system, publishing): say
       plainly that the preview does not do that, and what the full system does instead.
     - Reviews, stats or stories they did not give: never write them; add a `[blank]`.
  2. `PY scripts/check_preview.py`, fix anything it lists.
  3. `PY scripts/launch.py --no-open`, then tell them to refresh their Chrome tab. If
     `app/data/site.json` has `colorNotes`, tell them in one line (e.g. their yellow was
     deepened so text stays readable).
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
