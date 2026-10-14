# content.json — what Claude writes, what the preview reads

Everything the person sees is pre-built in `app/`. The only thing that changes per
person is `app/data/content.json` (plus `grade.json` from the grader). Claude writes
this file from the brain file; `scripts/check_preview.py` refuses to launch until it
is complete.

Write in **their** voice, from **their** answers. Short sentences. One reader.

## Hard rules for every word

1. **Never invent a fact about them.** No years in business, client counts, awards,
   licences, review scores, testimonials, prices, or results that are not in the
   brain file. Where the page needs one and you do not have it, write a visible
   placeholder in square brackets: `[Add a short client story here]`. The preview
   styles these so they are obviously theirs to fill.
2. **Never invent a person.** No made-up client names or quotes.
3. **No medical, legal, or financial promises.** Describe the service, not an outcome
   guarantee.
4. Colors: use theirs if the brain file has them (hex). Otherwise pick two that fit
   their personality and say so in `brand.colorNote`. Text must stay readable:
   `ink` on `paper` and white on `primary` need strong contrast.

## Shape

```jsonc
{
  "meta": { "brainFile": "summit-ai-brain.md", "generatedAt": "2026-10-20T10:12" },

  "business": {
    "name": "Bright Smile Family Dental",     // required
    "person": "Dr. Maria Lopez",              // required
    "profession": "Family dentist",           // required, plain words
    "oneLiner": "Gentle dentistry for whole families in Chula Vista.",
    "market": "Chula Vista, California",       // where they work, or "Online"
    "phone": "", "email": "",                  // only if given
    "website": "https://...",                  // their site if they have one, else ""
    "gradedUrl": "https://...",                // the site the grader ran on (theirs, or the one they admire)
    "gradedLabel": "Your website"              // or "A site you admire" / "A competitor"
  },

  "brand": {
    "colors": { "primary": "#1F4E79", "accent": "#F2A541", "ink": "#1B1F24", "paper": "#FBFAF7" },
    "colorNote": "Taken from your answers" ,
    "fonts": { "heading": "Fraunces", "body": "Inter" },   // any Google Font names
    "tagline": "Short, theirs.",
    "voice": ["warm", "plain-spoken", "reassuring"],       // 3-5 words
    "voiceExample": "One sentence that sounds exactly like them.",
    "wordsTheyUse": ["..."], "wordsTheyAvoid": ["..."]
  },

  "avatar": {
    "name": "Busy Parent Paula",                 // a label for the ideal client, not a real person
    "snapshot": "Two sentences on who they are.",
    "pains": ["...", "...", "..."],
    "wants": ["...", "...", "..."],
    "whereTheyAre": ["Facebook parent groups", "..."]
  },

  "differentiator": {
    "methodName": "The Calm Chair Method",       // name of their way of working
    "statement": "One sentence: why them and not the other 50.",
    "pillars": [ { "name": "...", "text": "..." }, { }, { } ]   // exactly 3
  },

  "site": {
    "home": {
      "heroHeadline": "...", "heroSub": "...", "primaryCta": "Book a visit",
      "whoItsFor": ["...", "...", "..."],
      "steps": [ { "title": "...", "text": "..." }, { }, { } ],  // exactly 3
      "closingHeadline": "...", "closingText": "..."
    },
    "about":    { "headline": "...", "story": ["paragraph", "paragraph"], "values": [ { "title": "...", "text": "..." } ] },
    "services": { "headline": "...", "intro": "...", "items": [ { "name": "...", "for": "...", "text": "...", "outcome": "..." } ] },
    "faq":      [ { "q": "...", "a": "..." } ],       // 4-6, real questions their avatar asks
    "contact":  { "headline": "...", "text": "..." }
  },

  "leadMagnet": {
    "title": "The 5-Minute Cavity Check",          // the free thing
    "subtitle": "...", "format": "checklist",       // checklist | guide | quiz | scorecard
    "hook": "Why someone stops scrolling for this.",
    "bullets": ["what they will get", "...", "..."],
    "formHeadline": "...", "buttonText": "Send it to me",
    "sections": [ { "heading": "...", "body": "..." } ],   // the actual content, 4-7 sections
    "closing": "Soft next step toward booking them.",
    "socialPost": "A ready post that sends people to the free thing.",
    "emails": [ { "day": 0, "subject": "...", "body": "..." }, { "day": 2 }, { "day": 5 } ]  // exactly 3
  },

  "audit": {
    "summary": "Two sentences: the biggest thing holding them back right now.",
    "opportunities": [                               // 2 or 3, ranked
      { "title": "...", "why": "...", "evidence": "what in their answers or report shows it",
        "whatChanges": "what life looks like when it is fixed", "bossDoes": "what the full system does about it" }
    ],
    "plan": [                                        // 3 to 5 days, not 30
      { "day": 1, "title": "...", "do": "...", "prompt": "a prompt they can paste into Claude" }
    ]
  },

  "prompts": [ { "label": "Change my headline", "prompt": "..." } ]   // 5-8, things they can try right now
}
```
