# AI Preview

The VIP / fast-action piece for Krista's three-day events, from the Oct 13 strategy call (Jerry, Chelsea,
Hailey, Krista).

**One set of answers in, a working preview out.** The person fills in Krista's
workbook, which downloads one file. They paste a three-line prompt into the Claude app's
Code tab. Claude prepares their computer (Module 1's pre-setup, minus GitHub), finds that
file on its own, and about ten minutes later Google Chrome opens a dashboard where they
choose where to go:

| Tile | What it is |
|---|---|
| **Your new website** | 5-6 real pages in their words and colors, in the seeds' Turnberry style: hero slideshow with Ken Burns drift, video band, photo marquee, scroll reveals, count-up stats. Shown as large live thumbnails. |
| **Your lead magnet** | Sign-up page, the guide itself, the post that promotes it, 3 follow-up emails |
| **Report card** | Their site (or a competitor's) against the new one, on the seed gate's checks, side by side |
| **Game plan** | AI opportunity audit: 2-3 opportunities and the next few days, on one screen |
| **Your brand** | Colors, voice, ideal client, differentiator |
| **Make it yours** | Prompts to paste back into Claude; each change rebuilds the site |

It is a taste, not the meal: nothing deploys, nothing is published, no accounts are
connected. It runs only on their computer.

## Real estate first, everyone else too

`profiles/real-estate.json` and `profiles/general.json` hold everything that differs by
profession (pages, schema type, photos, compliance). The engine is shared. Real estate
gets Sell and Buy pages, license + brokerage + Equal Housing in every footer, and Fair
Housing enforced on every word. Adding a profession is one profile file.

## The audit is the seed's gate

`scripts/grade_site.py` runs the realtor-site-seed launch checks against any live site:

- **Lighthouse floors** (perf 85, a11y 100, best practices 95, SEO 100), with the
  accessibility failures listed by name. This is axe-core, as in the seed's browser audit.
- **Structured data**, as in `validate:schema`: on every page, parses, `@type` present,
  `@id` references resolve, the business type is declared, FAQ markup matches the page.
- **Launch-check rules**: canonical, share preview, titles, descriptions, one H1,
  sitemap, robots, llms.txt, alt text, links home and to contact, 5+ internal links.
- **The content scrub**: leftover template text, unfilled blanks, near-duplicate pages,
  FTC claims, em-dashes and stock AI phrases.
- **Real estate**: Fair Housing, steering phrases, commission wording, and license,
  brokerage and Equal Housing on every page.
- **Privacy**: a policy page, and tracking tools named in it.
- **Not measured, said out loud**: dark-mode contrast, overlap and focus rings need a
  scripted browser.

Tested against a real third-party agent site (reidprice.com, read-only): 58 (F), with
real findings verified by hand: lorem ipsum on a live page, no Equal Housing statement,
javascript: links. The preview built for the test agent: 97 (A), Lighthouse 92/100/96/100.

`scripts/check_preview.py` runs the same rule lists over content.json **before** anything
is built, so a Fair Housing or FTC problem never reaches a page.

## Files

| Piece | What it does |
|---|---|
| `STUDENT-GUIDE.md` | The student-facing steps and the prompt they paste |
| `START-HERE.md` | The runbook Claude follows in the student's session |
| `BRAIN-FILE-CONTRACT.md` | **For Krista's workbook:** the download's name and contents |
| `CONTENT-SPEC.md` | The shape of `app/data/content.json`, which Claude writes |
| `profiles/*.json` | Per-profession pages, photos, schema, compliance |
| `scripts/find_brain_file.py` | Finds the newest workbook download |
| `scripts/get_node.py` | Private Node in `~/.ai-preview/node` for Lighthouse (no admin) |
| `scripts/grade_site.py` | The audit (above) |
| `scripts/check_preview.py` | Completeness + rule gate on content.json |
| `scripts/build_site.py` | Builds the real HTML site, sitemap, robots.txt, llms.txt |
| `scripts/launch.py` | Check, build, serve, open Chrome, measure the new site |
| `scripts/serve.py` | The local server (127.0.0.1 only) and the Chrome opener |
| `app/` | Dashboard, site styles and motion, fonts, the photo library |
| `app/config/settings.json` | Ours: example student sites, what's-next video and link |

Per-person output (`app/data/*`, `app/site/*`, `app/robots.txt`, `app/llms.txt`) is
git-ignored.

## Photos and video

53 Unsplash photos in `app/assets/img/library/`, each screened at full size for faces,
logos, brand names, signs, house numbers and artwork (two rejected on the second pass),
with source and license in `library.json`. Three sizes each (640, 960, 1280, WebP).
The video band is a Mixkit aerial (Mixkit Free License), screened for faces and signs, and
hotlinked rather than bundled.

## Run it locally (team)

```bash
cp examples/ai-brain-realtor.md ~/Downloads/ai-brain.md
```

Then open a Claude Code session in this folder and say "build my preview".

## External services

- **Google Lighthouse** runs locally in headless Chrome via `npx lighthouse@12.8.2`.
  Google PageSpeed Insights is only a fallback (anonymous calls are rate-limited; an
  optional `PAGESPEED_API_KEY` env var is honoured; never commit one, this repo is public).
- **nodejs.org / npm**: downloaded once into the user's home folder.
- **Mixkit** video CDN; **Unsplash** photos are bundled.

No secrets live in this repo, and none are needed.

## Still open

- Krista's workbook must download `ai-brain.md` per `BRAIN-FILE-CONTRACT.md`.
- Example student sites in `app/config/settings.json` (Ronnie, Doug, Alisha Collins,
  Chris Vanette): URLs to confirm and grade first.
- What's-next video and call-to-action link in `app/config/settings.json`.
- Real lead magnet examples from Jerry to model the generated one on.
