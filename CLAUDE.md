# Summit AI Preview

This folder is someone's **Summit AI Preview**. They are not technical and they never
type commands.

- **First run, or "build my preview":** follow `START-HERE.md` exactly, top to bottom.
- **"Open my preview"** (or anything like it): run `/usr/bin/python3 scripts/serve.py`
  on a Mac (Windows: the Python from START-HERE Step 2), from this folder. It reuses or restarts the preview and
  opens it in Google Chrome.
- **A prompt starting "In my Summit AI Preview,"**: they copied it from their dashboard.
  Do what it asks by editing `app/data/content.json` (shape in `CONTENT-SPEC.md`), or by
  running `scripts/grade_site.py` for a website. Then run `scripts/check_preview.py`,
  make sure the preview is running (`scripts/serve.py --no-open`), and tell them to
  refresh the Chrome tab.

## Always

- Plain words. No repository, terminal, script, server, JSON, port, localhost.
- Never open anything in Claude's built-in browser or preview pane. Chrome only, via
  `scripts/serve.py`. If they get a choice of where a link opens: **Open in Google Chrome**.
- Never invent facts about them: no stats, reviews, testimonials, awards or years they
  did not give. Use a visible `[placeholder]`.
- Never publish, deploy, push, email, or connect accounts. This is a local preview.
- Only read their workbook file (found by `scripts/find_brain_file.py`) and this folder.
