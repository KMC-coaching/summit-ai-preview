# content.json: what Claude writes, what gets built from it

Everything the person sees is pre-built. The only thing that changes per person is
`app/data/content.json`. `scripts/check_preview.py` refuses to build until it is
complete and clean; `scripts/build_site.py` turns it into a real website.

Write in **their** voice, from **their** answers. Short sentences. One reader.

## Hard rules for every word

1. **Never invent a fact about them.** No years in business, sales or client counts,
   awards, rankings, licence numbers, reviews, testimonials, prices or results that are
   not in their file. Where a page needs one and you do not have it, write a visible
   blank in square brackets: `[Your license number]`, `[Add a short client story here]`.
   Those show up highlighted, and on the report card as "fill in", never as passed.
2. **Never invent a person.** No made-up client names or quotes.
3. **No em-dashes** (use a colon, a comma, or a new sentence) and no stock AI phrases
   ("delve", "seamless", "when it comes to", "in today's market").
4. **FTC, everyone:** no "#1", "best in town", "guaranteed", "risk-free", "cheapest".
5. **Real estate only (Fair Housing):** describe the property, never the people. Never
   "perfect for families", "family-friendly", "safe neighborhood", "exclusive community",
   "good schools", "walking distance to church", "ideal for young professionals". Never
   "standard" or "customary" commission.
6. **No medical, legal or financial promises.** Describe the service, not an outcome.

`check_preview.py` runs rules 3 to 5 automatically with the same lists the audit uses.

## Pick the profile first

- `"profile": "real-estate"` for agents, teams and brokers. Pages: Home, About, **Sell**,
  **Buy**, Free guide, Contact. Footer carries license, brokerage, Equal Housing.
- `"profile": "general"` for everyone else. Pages: Home, About, **Services**, Free guide,
  Contact.

## Shape

```jsonc
{
  "profile": "real-estate",                      // or "general"
  "meta": { "brainFile": "...", "startedAt": "2026-10-20T10:02", "generatedAt": "2026-10-20T10:11" },

  "business": {
    "name": "...", "person": "...", "profession": "...",       // required
    "oneLiner": "One sentence: what they do, for whom, where.",
    "market": "City, State",                                    // or "Online"
    "areas": ["...", "..."],                                    // real estate: neighborhoods they named
    "phone": "", "email": "",                                   // only if given
    "website": "",                                              // their own site, or ""
    "gradedUrl": "https://...", "gradedLabel": "Your website",  // or "A site you admire" / "A competitor's website"
    "license": "", "brokerage": "",                             // real estate: ONLY if given. Blank = placeholder in footer
    "schemaType": "",                                           // optional, e.g. "Dentist"; the profile has a default
    "stats": []                                                 // ONLY real numbers from their file: [{ "value": 120, "suffix": "+", "label": "homes sold" }]
  },

  "brand": {
    "colors": { "primary": "#......", "accent": "#......" },    // theirs, or chosen to fit; contrast is fixed automatically
    "colorNote": "Why these colors, one line",
    "tagline": "...", "taglineSuggested": true,                 // true when they gave none and you wrote it
    "voice": ["3 to 5 words"], "voiceExample": "One sentence that sounds exactly like them.",
    "wordsTheyUse": [], "wordsTheyAvoid": []
  },

  "avatar": { "name": "A label, not a real person", "snapshot": "...", "pains": ["", "", ""], "wants": ["", "", ""], "whereTheyAre": [] },

  "differentiator": {
    "methodName": "...", "methodNameSuggested": true,           // true when their process had no name
    "statement": "One sentence: why them and not the other 50.",
    "pillars": [ { "name": "...", "text": "..." } ]             // exactly 4, in order: their process
  },

  "images": {},   // optional. Slot -> library photo id(s) from app/assets/img/library/library.json.
                  // Slots: hero (3), difference, pillars (4), ticker (6), split, magnet, about,
                  // sell, buy, services, contact, guide. Leave out and the profile picks.

  "site": {
    "home": {
      "heroEyebrow": "Profession · Where", "heroLead": "Headline as a claim, not a greeting", "heroAccent": "the underlined last words",
      "heroSub": "...", "primaryCta": "Short action, 2-3 words",
      "statementEyebrow": "...", "statement": "Two or three sentences in their voice, big type.",
      "differenceEyebrow": "...", "differenceHeadline": "...", "differenceBody": "Two short paragraphs, \n\n between",
      "pillarsHeadline": "...",
      "tickerEyebrow": "...", "tickerHeadline": "...", "tickerCaptions": ["exactly 6 short captions"],
      "splitEyebrow": "...", "splitHeadline": "...", "splitBody": "...", "splitLink": "...",
      "closingHeadline": "...", "closingText": "..."
    },
    "about": { "headline": "...", "sub": "...", "story": ["paragraphs; a [blank] for anything you do not know"], "values": [ { "title": "", "text": "" } ] },  // values: exactly 3
    "sell": { "eyebrow": "", "headline": "", "sub": "", "cta": "", "intro": "", "steps": [ { "title": "", "text": "" } ], "closingHeadline": "", "closing": "" },  // real estate, 3-5 steps
    "buy":  { "...same as sell..." },                                                                                                                         // real estate
    "services": { "eyebrow": "", "headline": "", "sub": "", "intro": "", "items": [ { "name": "", "for": "", "text": "", "outcome": "" } ] },                 // general, 2-6
    "faq": [ { "q": "Real questions their ideal client asks", "a": "..." } ],   // 4-6
    "contact": { "headline": "", "sub": "", "text": "" }
  },

  "leadMagnet": {
    "navLabel": "Free checklist", "title": "...", "subtitle": "...", "format": "checklist",   // checklist | guide | quiz | scorecard
    "hook": "Why someone stops scrolling for this.", "bullets": ["3 to 5"],
    "formHeadline": "...", "buttonText": "Send me the ...", "thankYou": "...",
    "sections": [ { "heading": "...", "body": "The real content, not an outline" } ],   // 4-7
    "closing": "Soft next step toward booking them.",
    "socialPost": "A ready post that sends people to it.",
    "emails": [ { "day": 0, "subject": "", "body": "" }, { "day": 2 }, { "day": 5 } ]  // exactly 3
  },

  "audit": {
    "summary": "One or two sentences: the biggest thing holding them back right now.",
    "opportunities": [ { "title": "", "why": "", "evidence": "their words or the report's numbers", "whatChanges": "", "bossDoes": "" } ],  // 2-3
    "plan": [ { "day": 1, "title": "", "do": "", "prompt": "In my Summit AI Preview, ..." } ]   // 3-5 days
  },

  "prompts": [ { "group": "Change your website", "label": "New headline", "prompt": "In my Summit AI Preview, ..." } ]  // 5-10
}
```

Prompt groups, in this order: **Change your website**, **Make more lead magnets**,
**Check any website**, **Create content**. Every prompt starts with
`In my Summit AI Preview,` so it works in any Claude session later.
