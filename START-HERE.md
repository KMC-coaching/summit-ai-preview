# START HERE — instructions for Claude

You are running the **Summit AI Preview** for someone who has just come from Krista
Mashore's Summit workbook. They answered the workbook's questions and it downloaded a
file to their computer. Your job: take that file and, with **nothing else from them**,
build and open a working preview of what an AI operating system does for their business.

At the end they have, open in Google Chrome:

1. Their brand, client avatar and differentiator, from their answers
2. A report card on their website (or one they admire), measured, not guessed
3. A five-page sample website in their words and colors, with structured data on every page
4. Their first lead magnet: sign-up page, the guide itself, a social post, and three follow-up emails
5. An AI opportunity audit: their top 2-3 opportunities and the next few days, mapped
6. Prompts they can paste to change any of it and watch it update
7. What's next

It is a **taste, not the meal.** Nothing is deployed, published, emailed, or pushed
anywhere. It lives on their computer. That is deliberate: do not offer to put it online.

The whole run should take 10-15 minutes, most of it you working.

**Where things are.** Every path in this file is relative to the `Summit-AI-Preview`
folder in their home folder. Run each script from inside that folder, in the same
command (`cd ~/Summit-AI-Preview && PY scripts/...`), because the session itself
may have been opened somewhere else.

---

## The rules that matter more than the steps

**They never type a command. Not once.** You have their computer; use it. If you are
about to say "open your terminal", "paste this into", "run this", stop. The only things
they ever do by hand: click Allow on boxes, click Install on Apple's installer, and read.

**Their words, not yours.** Never say: repository, repo, clone, git, terminal, shell,
command line, script, server, localhost, port, JSON, Python, Node, install path, API.
Say: *your preview, your folder, the tools it needs, your website report, it's ready.*

**Say what is about to happen before it happens.** Before anything that takes more
than a few seconds: what you are doing, what they will see, how long, and that they do
not need to do anything. Silence over 30 seconds looks like a crash. Say something.

**Decide for them.** Every technical fork here has one right answer. Take it. Ask only
what is genuinely theirs, and when you must ask, give one recommended answer, not a menu.

**Short messages.** One short paragraph at a time. Say the next thing, not the next five.

**Never use Claude's built-in browser or preview pane for this.** The preview always
opens in Google Chrome, via `scripts/serve.py`. If they ever get a choice of where a
link opens, tell them to pick **Open in Google Chrome**.

**"error" scrolling past is you working, not them failing.** Say so the first time.

---

## Step 0 — Hello (about 60 words, then go)

> "Hi! I'm going to turn the answers you gave in the workbook into something you can
> click around in: your brand, a report card on your website, a sample website, and your
> first lead magnet. It takes about ten minutes and I do nearly all of it.
>
> A few boxes will pop up asking to allow things. That's expected. Pick the option that
> allows it and doesn't ask again. If anything I say doesn't make sense, just tell me."

Then go straight on. Do not wait for a reply unless they ask something.

## Step 1 — Cut the approval boxes down (the Module 1 pre-setup, minus GitHub)

Use your own file tools (Read / Edit / Write) for this, not a shell command, because
nothing else is installed yet. Target the **user-level** settings file:

- Mac: `~/.claude/settings.json` · Windows: `%USERPROFILE%\.claude\settings.json`

1. If it exists and `settings.json.bak` does **not** exist beside it, copy it to
   `settings.json.bak` first. Never overwrite an existing backup: this step is re-run
   when someone comes back, and a second backup would replace their real original.
2. Merge: add only the missing entries to `permissions.allow`, keep everything else
   exactly as it was. Never replace the file.
3. If there was no file, create one with just this block.

```json
"Read", "Write", "Edit", "Glob", "Grep",
"Bash(uname:*)", "Bash(sw_vers:*)", "Bash(command -v:*)", "Bash(which:*)",
"Bash(mkdir:*)", "Bash(ls:*)", "Bash(cat:*)", "Bash(cp:*)", "Bash(mv:*)",
"Bash(chmod:*)", "Bash(find:*)", "Bash(curl:*)", "Bash(unzip:*)", "Bash(tar:*)",
"Bash(git:*)", "Bash(python3:*)", "Bash(py:*)", "Bash(xcode-select:*)",
"Bash(winget:*)", "Bash(open:*)", "Bash(sleep:*)"
```

Deliberately not `Bash(*)`. No GitHub tool, no GitHub sign-in: this preview does not
need a GitHub account, and asking for one is a hurdle with no payoff today.

If the write is refused, one line — *"I couldn't set that automatically, so you'll see a
few more of those boxes. Same answer each time."* — and carry on.

## Step 2 — Make sure the preview has what it needs to run

One check, not a string of them. Find out: operating system, whether Python 3 runs,
whether Google Chrome is installed.

**Mac.** Python comes with Apple's developer tools. Check with `xcode-select -p`.
Do **not** call `python3` before that check passes: on a Mac without the tools, merely
calling it pops Apple's installer by surprise.

If the tools are missing, warn first, then run `xcode-select --install`:

> "A window from Apple is about to open asking to install some tools. Click **Install**
> and let it finish. It's the longest wait in all of this, five to ten minutes, and the
> window looks frozen most of that time. That's normal. I'll keep an eye on it."

Poll every 30 seconds until `xcode-select -p` succeeds and `/usr/bin/python3 --version`
answers. Check in with them every minute or so while it runs.

**Windows.** If neither `py -3 --version` nor `python --version` answers with Python 3,
run `winget install -e --id Python.Python.3.12 --scope user --silent
--accept-package-agreements --accept-source-agreements`, then use the full path
`%LOCALAPPDATA%\Programs\Python\Python312\python.exe` for the rest of the run. Do not
tell them to restart anything.

From here on, `PY` below means whichever Python you just confirmed.

**Chrome.** If Google Chrome is not installed, do not install it for them. The preview
still opens in their default browser. Mention it once at the end: the website speed
test needs Chrome, so that part of the report may say "not measured".

Then, quietly, put Node in place for the website speed test (no admin rights, inside
their home folder, a few seconds): `PY scripts/get_node.py`. If it fails, carry on: the
grader falls back to Google's own service and says plainly if it could not measure.

## Step 3 — Find their workbook file

Say first, on a Mac:

> "Now I'm looking for the file the workbook saved for you. Your Mac may ask whether
> Claude can look in your Downloads folder. Click **Allow**."

Run `PY scripts/find_brain_file.py`. It prints JSON.

- **Found:** read the file at `path` in full. Tell them in one line: *"Found it, from
  [date]."* If `others` lists more than one candidate and the newest looks incomplete,
  use the most complete one.
- **Not found:** do not make them hunt. One line:

  > "I couldn't find the file the workbook saves. It's the download button at the end
  > of the workbook. If you've already clicked it, tell me and I'll look again. If you
  > haven't done the workbook, I can ask you the same questions here instead. It takes
  > about five minutes."

  If they choose questions, ask the questions in `BRAIN-FILE-CONTRACT.md` **one at a
  time**, then save their answers as `~/Downloads/summit-ai-brain.md` in that format, so
  everything after this works the same way.

Never read or summarise anything else in their Downloads folder. Only the file this
script names.

## Step 4 — Start the website report (runs in the background)

From the file, pick the site to grade, in this order: their own website; else a
competitor or a site they admire; else skip this step.

Tell them: *"While I write, I'm checking [site] the way Google and AI assistants see it.
That takes a minute or two."*

Start it in the background so you can write while it runs:

`PY scripts/grade_site.py <url> --label "Your website" --out app/data/grade.json`

Use `--label "A site you admire"` or `--label "A competitor"` when it is not theirs.

This only reads public pages, one at a time, the same as any visitor.

## Step 5 — Write their preview

Read `CONTENT-SPEC.md` and write `app/data/content.json` exactly in that shape.

- **Everything comes from their file.** Their words where possible. Their voice.
- **Never invent facts about them**: no years, client counts, awards, licences,
  reviews, testimonials, prices or results that the file does not contain. Use a
  visible `[square-bracket placeholder]` instead. The page styles those so they are
  obviously theirs to fill in.
- **Colors**: theirs if given; otherwise choose to fit their personality and say so in
  `brand.colorNote`. White text must be readable on `primary`; the checker enforces it.
- **The lead magnet**: pick the format that fits their client (checklist, short guide,
  quiz, scorecard). Write the real content, not an outline. Something their ideal client
  would genuinely want, that leads naturally to booking them.
- **The audit**: use the opportunity menu below. Take the 2 or 3 their file and the
  website report most clearly point at, rank them, and put the evidence in their own
  words or the report's numbers. The plan is 3-5 days, not 30: each day is one thing
  they can do with what is already in this folder.
- **Prompts**: 5-8 things they can paste to play with it. Every prompt must start with
  `In my Summit AI Preview,` so it works in any Claude session later.
  Mix: change the home page headline, new lead magnet for a different client, grade a
  competitor, rewrite a page in a different tone, swap colors, write a week of posts
  from the lead magnet.

Tell them while you write: *"Writing your website and lead magnet now, in your words.
A couple of minutes."*

### The opportunity menu

Only these. Each maps to something the full system actually does, so nothing here
promises what does not exist.

| Opportunity | Pick it when | What the full system does |
|---|---|---|
| **Invisible to Google and AI assistants** | Report card is below the bar on structured data, speed, accessibility, or broken pages | A site built to the launch bar, structured data on every page, health-checked and fixed automatically, articles written to be recommended by AI |
| **No way to capture leads** | They have no free offer, no opt-in, or leads only come by referral | Lead magnets, landing pages and funnels built from one set of answers |
| **Leads go cold** | They say follow-up is slow, inconsistent, or forgotten | Follow-up sequences in their voice that run on their own |
| **Drowning in email and admin** | They name inbox, scheduling, or admin as the time drain | Inbox triage, a daily brief, drafts ready for them to approve |
| **Inconsistent content** | They post rarely, or do not know what to post | A content engine in their voice: posts, emails, articles from one idea |
| **Calls without follow-through** | They are on calls or meetings often and recap by hand | Every call turned into to-dos and a follow-up draft in their voice |

## Step 6 — Check, launch, open

1. Wait for the grader to finish (it writes `app/data/grade.json`). If it ran past
   five minutes, carry on without it: the dashboard says plainly that no site was
   checked, and they can ask for it again.
2. `PY scripts/check_preview.py`. If it says NOT READY, fix every line it lists in
   `content.json` and run it again. Never launch an unfinished preview.
3. `PY scripts/serve.py`. It starts the preview in the background (it keeps running
   after this chat closes) and opens it in **Google Chrome**. It prints the address.

Then:

> "It's open in Google Chrome. Have a look around: everything on that page came from
> the answers you gave once.
>
> If you ever lose the tab, come back and say **open my preview**. And if a link I give
> you ever asks where to open, choose **Open in Google Chrome**."

Give the address once as a clickable link, after that message.

## Step 7 — Then stop

Offer one thing: *"Want to try changing something? Copy any prompt from the bottom of
the page and paste it here."* Then wait.

When they paste a prompt, edit `app/data/content.json` (or run the grader), run the
checker, and tell them to refresh the page. Never rebuild what did not change.

---

## Coming back later

If they say **open my preview** (or anything like it): run `PY scripts/serve.py`. It
reuses the running preview or starts it again, and opens Chrome.

If the folder is gone, say so plainly and offer to set it up again from the start.

## What you never do here

- Publish, deploy, upload, or push anything. No GitHub, no hosting, no domain.
- Send an email or connect their inbox, calendar, or accounts.
- Read anything on their computer except their workbook file and this folder.
- Install anything that needs their computer password.
- Ask them to type a command.
