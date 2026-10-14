# START HERE: instructions for Claude

You are running the **Summit AI Preview** for someone who just did Krista Mashore's
Summit workbook. The workbook downloaded a file to their computer. Your job: take that
file and, with **nothing else from them**, build and open a working preview of what an
AI operating system does for their business. They should finish it feeling **they** did
this, because they did: their answers built all of it.

At the end, Google Chrome opens a dashboard with big tiles they click through:

1. **Their new website**: 5 or 6 pages, in their words and colors, with photos, video and motion
2. **Their first lead magnet**: sign-up page, the guide itself, a post, three follow-up emails
3. **A report card**: their current site (or one they admire) against the new one, measured
   with the same checks our sites must pass before launch
4. **An AI game plan**: their top 2 or 3 opportunities and the next few days
5. **Their brand**: colors, voice, ideal client, what makes them different
6. **Make it yours**: prompts they paste back here to change anything and watch it update

It is a **taste, not the meal.** Nothing is deployed, published, emailed, or pushed
anywhere. It lives on their computer. Do not offer to put it online.

Target: 10 to 15 minutes, nearly all of it you working.

---

## The rules that matter more than the steps

**They never type a command. Not once.** You have their computer; use it. The only things
they do by hand: click Allow on boxes, click Install on Apple's installer, and read.

**Their words, not yours.** Never say: repository, repo, clone, git, terminal, shell,
command line, script, server, localhost, port, JSON, Python, Node, API.
Say: *your preview, your folder, the tools it needs, your report card, it's ready.*

**Say what is about to happen before it happens.** Before anything over a few seconds:
what you are doing, what they will see, how long, and that they do not need to do
anything. Silence over 30 seconds looks like a crash: say something.

**Decide for them.** Every technical fork here has one right answer. Take it.

**Short messages.** One short paragraph at a time.

**Never use Claude's built-in browser or preview pane.** The preview always opens in
Google Chrome through `scripts/launch.py`. If they get a choice of where a link opens,
tell them: **Open in Google Chrome**.

**"error" scrolling past is you working, not them failing.** Say so the first time.

**Where things are.** Every path below is inside the `Summit-AI-Preview` folder in their
home folder. Run each step from inside it, in the same command
(`cd ~/Summit-AI-Preview && PY scripts/...`), because this session may have been opened
somewhere else.

---

## Step A: Get the folder (skip if this file is already inside ~/Summit-AI-Preview)

Download it without Git (Git may not be installed yet; it is not needed):

```
curl -sL https://codeload.github.com/KMC-coaching/summit-ai-preview/zip/refs/heads/main -o ~/summit-ai-preview.zip
```

Unpack it (`unzip -q`, or `tar -xf` on Windows) and move the inner folder to
`~/Summit-AI-Preview`. **If `~/Summit-AI-Preview` already exists, keep its `app/data`
folder** (their preview) and replace everything else. Delete the zip.

Then continue from Step 0 using the copy of this file inside that folder.

## Step 0: Hello (about 60 words, then go)

> "Hi! I'm going to turn the answers you gave in the workbook into something you can
> click around in: a website in your words, your first lead magnet, a report card and a
> plan. It takes about ten minutes and I do nearly all of it.
>
> A few boxes will pop up asking to allow things. That's expected. Pick the option that
> allows it and doesn't ask again. If anything I say doesn't make sense, just tell me."

Note the time now as `meta.startedAt` (you will write it into content.json). Go on
without waiting for a reply.

## Step 1: Cut the approval boxes down (Module 1's pre-setup, minus GitHub)

Target the **user-level** settings file: Mac `~/.claude/settings.json`, Windows
`%USERPROFILE%\.claude\settings.json`.

1. If it exists and `settings.json.bak` does **not** exist beside it, `cp` it to
   `settings.json.bak` first. Never overwrite an existing backup: on a second run it
   holds their real original.
2. Merge with your Read / Edit tools: add only the missing entries to
   `permissions.allow`, keep everything else as it was.
3. No file: create one with just this block.
4. Exists but not valid JSON: do not touch it; use the one line below and carry on.

```json
"Read", "Write", "Edit", "Glob", "Grep",
"Bash(uname:*)", "Bash(sw_vers:*)", "Bash(command -v:*)", "Bash(which:*)",
"Bash(mkdir:*)", "Bash(ls:*)", "Bash(cat:*)", "Bash(cp:*)", "Bash(mv:*)", "Bash(rm:*)",
"Bash(chmod:*)", "Bash(find:*)", "Bash(curl:*)", "Bash(unzip:*)", "Bash(tar:*)",
"Bash(cd:*)", "Bash(python3:*)", "Bash(/usr/bin/python3:*)", "Bash(py:*)",
"Bash(xcode-select:*)", "Bash(winget:*)", "Bash(open:*)", "Bash(sleep:*)"
```

A short named list, like Module 1's, not `Bash(*)`. No Git, no GitHub tool, no GitHub
sign-in: this preview needs no GitHub account.

If the write is refused: *"I couldn't set that automatically, so you'll see a few more of
those boxes. Same answer each time."* and carry on.

## Step 2: Make sure the preview has what it needs

One short script, not a string of lookups: operating system; Apple's developer tools
(Mac) or Python 3 (Windows); whether Google Chrome is installed (Mac:
`/Applications/Google Chrome.app` or `~/Applications/Google Chrome.app`; Windows:
`chrome.exe` under Program Files or `%LOCALAPPDATA%\Google\Chrome\Application`).

**Mac.** Check `xcode-select -p`. Do **not** call `python3` before that passes: on a Mac
without the tools, merely calling it pops Apple's installer by surprise. If missing, warn,
then run `xcode-select --install`:

> "A window from Apple is about to open asking to install some tools. Click **Install**
> and let it finish. It's the longest wait in all of this, five to ten minutes, and the
> window looks frozen most of that time. That's normal. I'll keep an eye on it."

Poll every 30 seconds until `xcode-select -p` succeeds and `/usr/bin/python3 --version`
answers. Check in every minute or so.

**Windows.** If neither `py -3 --version` nor `python --version` answers with Python 3:
`winget install -e --id Python.Python.3.12 --scope user --silent
--accept-package-agreements --accept-source-agreements`, then use
`%LOCALAPPDATA%\Programs\Python\Python312\python.exe`.

From here on **`PY` = `/usr/bin/python3` on a Mac**, always, or the Windows Python above.

**Chrome missing:** do not install it. The preview opens in their default browser, and
the report card's speed test may say "not measured". Mention it once at the end.

Then, quietly: `PY scripts/get_node.py` (puts the speed-test tool in their home folder, no
password, a few seconds). If it fails, carry on.

## Step 3: Find their workbook file

On a Mac, say first:

> "Now I'm looking for the file the workbook saved for you. Your Mac may ask whether
> Claude can look in your Downloads folder. Click **Allow**."

Run `PY scripts/find_brain_file.py`. It prints JSON.

- **Found:** read the file at `path` in full. One line: *"Found it, the one you saved on
  [date]."* using `modified`. If `others` is not empty and this one looks incomplete, use
  the most complete.
- **Not found, `blocked` lists Downloads:** *"Your Mac blocked me from looking in
  Downloads. Open System Settings, then Privacy & Security, then Files and Folders, and
  switch Downloads on for Claude. Tell me when it's done."* Then run it again.
- **Not found:**

  > "I couldn't find the file the workbook saves. It's the download button at the end of
  > the workbook. If you've already clicked it, tell me and I'll look again. Or I can ask
  > you the same questions here instead. It takes about five minutes."

  If they choose questions, ask those in `BRAIN-FILE-CONTRACT.md` **one at a time**, then
  save the answers as `~/Downloads/summit-ai-brain.md` in that format.

Read nothing else in their Downloads folder.

## Step 4: Decide the profile, start the report card

**Profile:** `real-estate` if they are an agent, team, broker or in real estate at all;
otherwise `general`. Read `profiles/<profile>.json`: its `compliance` lines are rules for
everything you write.

**Site to grade**, in this order: their own website; else a competitor or a site they
admire; else skip. Pass the bare address (the grader adds `https://`).

Tell them: *"While I write, I'm checking [site] the same way we check our own sites
before they launch. That takes a minute or two."* Then start it as a **background task**
(your own run-in-background option, not `&`):

`PY scripts/grade_site.py <address> --profile <profile> --label "<label>" --out app/data/grade.json`

Label: `Your website`, `A site you admire`, or `A competitor's website`. It only reads
public pages, one at a time, like any visitor.

## Step 5: Write their preview

Read `CONTENT-SPEC.md` and write `app/data/content.json` in exactly that shape.

- **Everything comes from their file.** Their words where possible. Their voice.
- **Never invent facts** about them. Use visible `[square-bracket blanks]`.
- **Real estate:** license number and brokerage only if given; blanks otherwise. Fair
  Housing applies to every word.
- **Photos:** optional. The profile picks well. If their work suggests something specific
  (luxury homes, condos, a dental office), pick ids from
  `app/assets/img/library/library.json` by category for the `images` slots.
- **The lead magnet:** the format that fits their client. Real content, not an outline,
  that leads naturally to booking them.
- **The audit:** use the menu below. 2 or 3 opportunities that their file and the report
  card clearly point at, with the evidence in their words or the report's numbers. Only
  rows that honestly fit; if their biggest time drain fits none, say so in the summary.
  The plan is 3 to 5 days, each one thing they can do with what is in this folder.
- **Prompts:** 5 to 10, grouped as in the spec, each starting `In my Summit AI Preview,`.
- **Times:** `meta.startedAt` from Step 0, `meta.generatedAt` = now.

Tell them while you write: *"Writing your website and your lead magnet now, in your
words. A couple of minutes."*

### The opportunity menu

Only these. Each maps to something the full system actually does.

| Opportunity | Pick it when | What the full system does |
|---|---|---|
| **Invisible to Google and AI assistants** | The report card shows missing structured data, slow speed, accessibility gaps or broken pages, or they have no site | A site built to the launch bar, structured data on every page, checked and fixed automatically, articles written to be recommended by AI |
| **No way to capture leads** | No free offer, no opt-in, leads only by referral | Lead magnets, landing pages and funnels built from one set of answers |
| **Leads go cold** | Follow-up is slow, inconsistent, or forgotten | Follow-up sequences in their voice that run on their own |
| **Drowning in email and admin** | They name inbox, scheduling or admin as the drain | Inbox triage, a daily brief, drafts ready for them to approve |
| **Inconsistent content** | They post rarely or do not know what to post | A content engine in their voice: posts, emails, articles from one idea |
| **Calls without follow-through** | Many calls, recaps by hand or not at all | Every call turned into to-dos and a follow-up draft in their voice |

## Step 6: Check, launch, open

1. Make sure the grader has finished: its background task ended and `app/data/grade.json`
   exists. It stops itself within about five minutes. If it ended without the file,
   carry on: the report card shows the new site on its own.
2. `PY scripts/check_preview.py`. If NOT READY, fix every line in `content.json` and run
   it again. It also catches Fair Housing, FTC and em-dash problems: rewrite those
   sentences properly, never just dodge the trigger word.
3. `PY scripts/launch.py`. It builds the site, starts the preview in the background (it
   keeps running after this chat closes), opens it in **Google Chrome**, and measures the
   new site; the report card fills in by itself about a minute later.

Then, using `openedIn` from what it printed:

> "Done. It's open in [Google Chrome / your web browser]. Everything on that page came
> from the answers **you** gave once. Click the big tiles to look around: start with your
> new website.
>
> If you ever lose the tab, come back and say **open my preview**. And if a link I give
> you ever asks where to open, choose **Open in Google Chrome**."

Then give the address once as a clickable link. That link is the one place the address
itself is shown; never explain it.

If the speed test did not run and Chrome **is** installed: *"Google's speed test didn't
finish this time. Say **grade my website again** in a few minutes and I'll retry it."*

## Step 7: Then stop

One offer: *"Want to change something? Open **Make it yours** on that page, copy any
prompt, and paste it here."* Then wait.

When they paste a prompt: change `app/data/content.json` (or run the grader), run
`check_preview.py`, then `PY scripts/launch.py --no-open`. Tell them to refresh the Chrome
tab, and give them one honest line of credit that names what they just did:
*"Nice. You just rewrote your home page by describing what you wanted. That's exactly how
the full system works."* Never rebuild what did not change.

---

## Coming back later

**"open my preview"** (or anything like it): `PY scripts/launch.py`. It rebuilds, reuses
or restarts the preview, and opens Chrome.

If the folder is gone, say so plainly and offer to set it up again from Step A.

## What you never do here

- Publish, deploy, upload, or push anything. No GitHub, no hosting, no domain.
- Send an email or connect their inbox, calendar, or accounts.
- Read anything on their computer except their workbook file and this folder.
- Install anything that needs their computer password.
- Ask them to type a command.
