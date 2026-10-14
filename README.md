# Summit AI Preview

The VIP / fast-action piece for Summit, from the Oct 13 strategy call (Jerry, Chelsea,
Hailey, Krista).

**One set of answers in, a working preview out.** The person fills in Krista's Summit
workbook, which downloads one file. They paste one prompt into Claude. Claude finds that
file on its own, and ten minutes later Google Chrome opens a dashboard with:

1. Their brand, ideal client and differentiator, from their answers
2. A measured report card on their website (or one they admire), against the bar our sites launch at
3. A five-page sample website in their words and colors, with structured data on every page
4. Their first lead magnet: sign-up page, the guide, a social post, three follow-up emails
5. An AI opportunity audit: top 2-3 opportunities and the next few days
6. Prompts to paste that change any of it live
7. What's next (video slot + call to action)

It is a taste, not the meal: nothing deploys, nothing is published, no accounts are
connected. It runs only on their computer.

## How a student gets it

`STUDENT-GUIDE.md` is the whole student-facing flow: finish the workbook, open the Claude
app's Code tab, paste one prompt. No GitHub account (it is a public repo, downloaded as a
zip), no terminal, no Obsidian.

The setup part of Module 1's pre-setup runs inside it (`START-HERE.md` steps 1-2): the
approval allow-list, Apple's developer tools for Python, a private Node for the speed
test. The GitHub tool and GitHub sign-in are deliberately left out.

## How it works

| Piece | What it does |
|---|---|
| `START-HERE.md` | The runbook Claude follows in the student's session. Voice rules from `boss-pre-setup`. |
| `BRAIN-FILE-CONTRACT.md` | **For Krista's workbook:** the download's file name and what it must contain. |
| `scripts/find_brain_file.py` | Finds the workbook download (newest `summit-ai-brain*` in Downloads/Desktop/Documents). |
| `scripts/grade_site.py` | Website grader: Lighthouse (local headless Chrome, Google PageSpeed fallback), structured data per page, broken pages and links, search basics, AI-readiness. Lifted from `realtor-site-seed`'s `audit:compare`, rebuilt on stdlib Python 3.9. |
| `scripts/get_node.py` | Private Node in `~/.summit-preview/node` for Lighthouse. No admin, no password. |
| `CONTENT-SPEC.md` | The shape of `app/data/content.json`, which Claude writes from the workbook file. |
| `scripts/check_preview.py` | Refuses to launch an unfinished preview (missing fields, unreadable colors). |
| `scripts/serve.py` | Starts the preview on 127.0.0.1 in the background and opens **Google Chrome**. |
| `app/` | The pre-built dashboard and sample site. Everything reads `app/data/*.json`. |
| `app/config/settings.json` | Ours: example student sites and the what's-next video. |

Per-person output lands in `app/data/` and is git-ignored.

## Run it locally (team)

```bash
cp examples/summit-ai-brain.md ~/Downloads/summit-ai-brain.md
```

Then open a Claude Code session in this folder and say "build my preview".

Grader on its own:

```bash
python3 scripts/grade_site.py https://example.com --out app/data/grade.json
```

## External services

- **Google PageSpeed Insights** (fallback only, no key): runs Lighthouse remotely when
  local Chrome can't. Anonymous calls are rate-limited (measured: HTTP 429), which is why
  local Lighthouse is primary. An optional `PAGESPEED_API_KEY` env var is honoured; never
  commit one, this repo is public.
- **nodejs.org** and **npm** (`lighthouse@12.8.2`): downloaded once into the user's home folder.
- **Google Fonts**: loaded by the preview pages.

No secrets live in this repo, and none are needed.

## Still open

- Krista's workbook must download `summit-ai-brain.md` per `BRAIN-FILE-CONTRACT.md`.
- Example student sites in `app/config/settings.json` (Ronnie, Doug, Alisha Collins,
  Chris Vanette): URLs to confirm and grade first.
- What's-next video URL and call-to-action link in `app/config/settings.json`.
