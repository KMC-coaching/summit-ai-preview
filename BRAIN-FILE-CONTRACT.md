# The workbook file: what the preview reads

The preview is fed by Krista's **AI Agent Digital Revolution** folder
(`Krista-Mashore-Coaching/ai-agent-digital-revolution`). There, the student builds their
Business Brain, their five profile cards and their workbook days. Those are real files in
their folder (`~/Sites/AI-Agent-Digital-Revolution`).

When they say **"build my AI preview"** in that folder, its `preview-handoff` AI team member:

1. reads what they built,
2. asks only what the preview needs and the workbook never asked: license number and
   brokerage (agents), NMLS number and company (lenders), brand colors, and a site to grade
   if they have no website of their own,
3. writes **one file**, `ai-brain.md`, to their Downloads folder,
4. hands them a prompt, with that file's full path in it, to paste into a **new** Claude
   Code session. That session runs this repo's `START-HERE.md`.

## The file

```
# AI Brain: <name>, <business>
Saved: <date>
Made by BOSS from the AI Agent Digital Revolution folder: <path>

## Preview answers
- Profession: real estate agent | lender | <their words>
- License number:      - Brokerage:      - NMLS number:      - Company:      - Company NMLS number:
- Brand colors: <their words, or "pick for me">
- Website to grade: <url or blank>
- Which site that is: Their own | A competitor | A site they admire | none

---
## FILE: 01-identity-and-positioning.md
<exact text>
---
## FILE: 02-brand-voice.md          (stops before the standard "# Writing Rules")
---
## FILE: 03-… 04-… 05-… (06-10 if built) 11-ai-context.md, My-Profile.md, Day-1.md, Day-2.md, Day-3.md
```

`START-HERE.md` Step 5 maps each part onto the preview, field by field.

## Finding it

The pasted prompt names the file's full path, so normally nothing is searched. If it is
missing, `scripts/find_brain_file.py` takes the **newest** file whose name contains
`ai-brain`, `summit…brain` or `summit…workbook` (`.md`, `.txt`, `.json`, `.pdf`, `.docx`) in
Downloads, Desktop or Documents (and their OneDrive versions on Windows), from the last 120
days.

## No workbook at all

If there is no file, `START-HERE.md` offers to ask the essentials itself, one at a time, and
saves them as `~/Downloads/ai-brain.md` in the same shape: name, business,
profession, where they work, website (or one to grade), how they want to come across,
ideal client, what makes them different, their process, services, how clients find them,
whether they have a free offer, how they follow up, what eats their week, brand colors, and
for agents license and brokerage, for lenders NMLS and company.
