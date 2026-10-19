#!/usr/bin/env python3
"""
Build the sample website from app/data/content.json.

    python3 scripts/build_site.py --base http://localhost:4321

Writes real HTML (not pages assembled by script in the browser), so search
engines, AI assistants, Lighthouse and our own audit all read the same words,
headings and structured data a visitor does. Output:

    app/site/*.html          the pages (profile decides which)
    app/site/sitemap.xml     every page, absolute addresses
    app/robots.txt           allows crawlers, points at the sitemap
    app/llms.txt             who this is, for AI assistants
    app/data/images.json     which library photo went in which slot

--base is the address the preview is served from. Canonical links, the
sitemap and share images must be absolute, and a canonical pointing at a
made-up domain is worse than one pointing at where the site actually is.

Runs on the Python that ships with macOS (3.9): no newer syntax.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
SITE = APP / "site"
DATA = APP / "data"
LIB = APP / "assets" / "img" / "library"


# ------------------------------------------------------------------ helpers
def esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


PH = re.compile(r"\[([^\]]{2,300})\]")


def t(s) -> str:
    """Escaped text; [square-bracket blanks] become visible placeholders."""
    return PH.sub(r'<span class="ph">[\1]</span>', esc(s))


LIST_ITEM = re.compile(r"^\s*(?:[-*\u2022]|\[ ?\]|\d+[.)])\s+")


def paras(s) -> str:
    """Paragraphs on blank lines. Lines starting "- ", "* ", "[ ]" or "1." become a list
    ("[ ]" items a checklist); a lead-in line above them stays a paragraph."""
    out = []
    for block in re.split(r"\n{2,}", str(s or "")):
        lines = [l for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        if len(lines) > 1 and all(LIST_ITEM.match(l) for l in lines[1:]) and not LIST_ITEM.match(lines[0]):
            out.append("<p>%s</p>" % t(lines[0]))
            lines = lines[1:]
        if all(LIST_ITEM.match(l) for l in lines):
            check = all(re.match(r"^\s*\[ ?\]", l) for l in lines)
            items = "".join("<li>%s</li>" % t(LIST_ITEM.sub("", l, count=1)) for l in lines)
            out.append('<ul class="%s">%s</ul>' % ("checks" if check else "ticks", items))
        else:
            out.append("<p>%s</p>" % t(block.strip()).replace("\n", "<br>"))
    return "".join(out)


def plain(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def get(d, path, default=""):
    for k in path.split("."):
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d if d not in (None, "") else default


def fit_desc(*candidates, lo=50, hi=165):
    """Search descriptions must be 50-170 characters (the audit checks). Take the first
    candidate, top it up from the next ones if short, trim at a word if long."""
    parts = [plain(c) for c in candidates if plain(c)]
    if not parts:
        return ""
    out = parts[0]
    for extra in parts[1:]:
        if len(out) >= lo:
            break
        if extra not in out:
            out = (out.rstrip(".") + ". " + extra).strip()
    if len(out) > hi:
        out = out[:hi].rsplit(" ", 1)[0].rstrip(",;:") + "."
    return out


def fit_title(title, limit=62):
    """Google shows about 60 characters. Shorten the first part, keep the business name."""
    title = plain(title)
    if len(title) <= limit:
        return title
    if " | " in title:
        head, tail = title.rsplit(" | ", 1)
        room = limit - len(tail) - 3
        if room >= 18:
            return head[:room].rsplit(" ", 1)[0].rstrip(",.:;") + " | " + tail
        return tail[:limit]
    return title[:limit].rsplit(" ", 1)[0]


# ------------------------------------------------------------------ color
def _lum(h):
    rgb = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = sorted([_lum(a), _lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mix(h, other, amt):
    a = [int(h[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * amt) for x, y in zip(a, b))


def lift_until(h, against, need, toward="#000000"):
    """lib/brand-colors.ts liftUntil(): move toward black until the contrast holds."""
    c = h
    for i in range(1, 41):
        if contrast(c, against) >= need:
            return c
        c = mix(h, toward, i / 40)
    return toward


def palette(brand_colors):
    brand = brand_colors.get("primary") or "#1f4e79"
    accent = brand_colors.get("accent") or "#c9a24b"
    bg, dark = "#fbfaf7", "#121418"
    # The alt band is the accent mixed into warm white (site.css --alt). Compute it here
    # and hand it to the page, so contrast is checked against the color actually painted.
    alt = mix("#f8f5f0", accent, 0.07)
    on_accent = "#111111" if contrast("#111111", accent) >= contrast("#ffffff", accent) else "#ffffff"
    # A light brand color (bright yellow, mint) keeps its color and gets dark text on
    # it, instead of being darkened to olive so white text fits. They asked for yellow.
    light_brand = contrast("#ffffff", brand) < 4.5 and contrast("#111111", brand) >= 4.5
    return {
        "--brand": brand if light_brand else lift_until(brand, "#ffffff", 4.5),
        "--accent": accent,                                    # decoration only (underlines, rules)
        "--on-accent": on_accent,                              # text on an accent-filled button
        "--brand-ink": lift_until(brand, alt, 4.5),
        "--accent-ink": lift_until(lift_until(accent, alt, 4.6), bg, 4.6),  # eyebrows on light and alt bands
        "--alt": alt,
        "--accent-on-dark": lift_until(accent, dark, 4.6, toward="#ffffff"),  # eyebrows on dark bands and photos
        "--on-brand": "#111111" if light_brand else "#ffffff",
    }


def color_notes(brand_colors, pal):
    """What we changed so text stays readable, so Claude can say so instead of it happening silently."""
    notes = []
    want = (brand_colors.get("primary") or "").lower()
    if want and pal["--brand"].lower() != want:
        notes.append("Your main color %s was deepened to %s so white text on it stays readable." % (want, pal["--brand"]))
    acc = (brand_colors.get("accent") or "").lower()
    if acc and contrast(acc, "#fbfaf7") < 1.6:
        notes.append("Your accent %s is very close to the page background, so it is used only for small touches." % acc)
    return notes


CSS_INLINE = (APP / "assets" / "site.css").read_text(encoding="utf-8").replace('url("fonts/', 'url("../assets/fonts/')


# ------------------------------------------------------------------ images
def load_library():
    lib = json.loads((LIB / "library.json").read_text(encoding="utf-8"))
    return {i["id"]: i for i in lib}


class Picker:
    """First unused photo from each slot's categories; Claude's own picks win."""

    def __init__(self, lib, profile, content):
        self.lib, self.used, self.chosen, self.cache = lib, set(), {}, {}
        self.profile = profile
        wanted = content.get("images") or {}
        prof = (content.get("business") or {}).get("profession", "").lower()
        self.first = None
        for pat, cat in (profile.get("professionImages") or {}).items():
            if re.search(pat, prof):
                self.first = cat
                break
        self.wanted = wanted

    def _from(self, cat):
        ids = [k for k, v in self.lib.items() if v["category"] == cat and k not in self.used]
        if not ids:
            ids = [k for k, v in self.lib.items() if v["category"] == cat]
        return ids[0] if ids else next(iter(self.lib))

    def slot(self, name, n=1):
        # The same slot on two pages is the same photo (the magnet band repeats).
        if name in self.cache and len(self.cache[name]) >= n:
            return self.cache[name][:n]
        out = self._slot(name, n)
        self.cache[name] = out
        return out

    def _slot(self, name, n):
        given = self.wanted.get(name)
        given = [given] if isinstance(given, str) else (given or [])
        cats = list(self.profile["images"].get(name, ["gen-plants"]))
        if self.first and name in ("hero", "pillars", "ticker", "services", "about"):
            cats = [self.first] + cats
        out = []
        for i in range(n):
            pick = given[i] if i < len(given) and given[i] in self.lib else self._from(cats[i % len(cats)])
            self.used.add(pick)
            out.append(self.lib[pick])
        self.chosen[name] = [o["id"] for o in out]
        return out


def img(item, cls="", eager=False, sizes="100vw", lazy_src=False):
    src = "../assets/img/library/" + item["file"]
    small = "../assets/img/library/" + item["small"]
    medium = "../assets/img/library/" + item.get("medium", item["small"])
    attrs = 'alt="%s"' % esc(item["alt"])
    if lazy_src:
        return '<img %s data-src="%s" width="1280" height="853" decoding="async">' % (attrs, src)
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    return ('<img %s src="%s" srcset="%s 640w, %s 960w, %s 1280w" sizes="%s" width="1280" height="853" %s decoding="async"%s>'
            % (attrs, src, small, medium, src, sizes, load, (' class="%s"' % cls) if cls else ""))


# ------------------------------------------------------------------ schema
def schema_graph(c, profile, base, page_url, page_name, faq=None):
    b = c.get("business", {})
    stype = b.get("schemaType") or profile["schemaType"]
    if profile["id"] == "general" and not b.get("schemaType"):
        for pat, typ in (profile.get("schemaTypeHints") or {}).items():
            if re.search(pat, b.get("profession", ""), re.I):
                stype = typ
                break
    home = base + "/site/"
    org = {"@type": "Organization", "@id": home + "#org", "name": plain(b.get("brokerage") or b.get("company") or b.get("name")), "url": home}
    if b.get("companyNmls") and not PH.search(str(b["companyNmls"])):
        org["identifier"] = {"@type": "PropertyValue", "propertyID": "NMLS", "value": plain(b["companyNmls"])}
    site = {"@type": "WebSite", "@id": home + "#website", "name": plain(b.get("name")), "url": home, "publisher": {"@id": home + "#org"}}
    person = {"@type": "Person", "@id": home + "#person", "name": plain(b.get("person")), "jobTitle": plain(b.get("profession")),
              "worksFor": {"@id": home + "#business"}}
    if b.get("nmls") and not PH.search(str(b["nmls"])):
        person["identifier"] = {"@type": "PropertyValue", "propertyID": "NMLS", "value": plain(b["nmls"])}
    biz = {"@type": stype, "@id": home + "#business", "name": plain(b.get("name")), "description": plain(b.get("oneLiner")),
           "url": home, "areaServed": [plain(a) for a in (b.get("areas") or [b.get("market")]) if a],
           "founder": {"@id": home + "#person"}, "parentOrganization": {"@id": home + "#org"}}
    if b.get("phone") and not PH.search(b["phone"]):
        biz["telephone"] = b["phone"]
    if b.get("email") and not PH.search(b["email"]):
        biz["email"] = b["email"]
    page = {"@type": "WebPage", "@id": page_url + "#webpage", "url": page_url, "name": page_name,
            "isPartOf": {"@id": home + "#website"}, "about": {"@id": home + "#business"}}
    graph = [org, site, biz, person, page]
    if faq:
        graph.append({"@type": "FAQPage", "@id": page_url + "#faq", "mainEntity": [
            {"@type": "Question", "name": plain(f["q"]), "acceptedAnswer": {"@type": "Answer", "text": plain(f["a"])}} for f in faq]})
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")


# ------------------------------------------------------------------ chrome
EHO_SVG = ('<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" '
           'd="M12 2 1 11h3v10h16V11h3L12 2zm-6 9.6L12 6.4l6 5.2V19H6v-7.4zM8 13h8v1.6H8V13zm0 3h8v1.6H8V16z"/></svg>')


class Site:
    def __init__(self, c, profile, base, lib):
        self.c, self.p, self.base = c, profile, base.rstrip("/")
        self.pick = Picker(lib, profile, c)
        self.b = c.get("business", {})
        self.pal = palette(get(c, "brand.colors", {}) or {})
        self.pages = [("index.html", "Home"), ("about.html", "About")] + [(pg["file"], pg["nav"]) for pg in profile["pages"]] + \
                     [("free-guide.html", get(c, "leadMagnet.navLabel", "Free guide")), ("contact.html", "Contact")]

    def url(self, f):
        return "%s/site/%s" % (self.base, "" if f == "index.html" else f)

    def head(self, f, title, desc, og_img):
        style = ";".join("%s:%s" % kv for kv in self.pal.items())
        return """<!doctype html>
<html lang="en" style="%s">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<meta name="description" content="%s">
<link rel="canonical" href="%s">
<meta property="og:type" content="website">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:image" content="%s">
<meta property="og:url" content="%s">
<meta name="theme-color" content="%s">
<link rel="preload" href="../assets/fonts/Fraunces-latin.woff2" as="font" type="font/woff2" crossorigin>
%s
<style>%s</style>
""" % (style, esc(title), esc(desc), self.url(f), esc(title), esc(desc),
            "%s/assets/img/library/%s" % (self.base, og_img["file"]), self.url(f), self.pal["--brand"],
            ('<link rel="preload" as="image" fetchpriority="high" imagesrcset="../assets/img/library/%s 640w, ../assets/img/library/%s 960w, ../assets/img/library/%s 1280w" imagesizes="100vw">'
             % (og_img["small"], og_img.get("medium", og_img["small"]), og_img["file"])),
            # Inlined: one less request in front of the first paint. Font URLs are relative
            # to the stylesheet, so they are rewritten for a page in site/.
            CSS_INLINE)

    def header(self, f):
        nav = "".join('<a href="%s"%s>%s</a>' % (h, ' aria-current="page"' if h == f else "", esc(lbl))
                      for h, lbl in self.pages if h not in ("index.html", "contact.html", "free-guide.html"))
        nav += '<a href="contact.html"%s>Contact</a>' % (' aria-current="page"' if f == "contact.html" else "")
        nav += '<a class="pill pill--solid" href="free-guide.html">%s</a>' % esc(get(self.c, "leadMagnet.navLabel", "Free guide"))
        menu = "".join('<a href="%s">%s</a>' % (h, esc(lbl)) for h, lbl in self.pages)
        contact_bits = " · ".join(esc(x) for x in (self.b.get("phone"), self.b.get("email")) if x and not PH.search(x))
        return """<a class="skip" href="#main">Skip to content</a>
<header class="header is-top"><div class="wrap">
<a class="brandmark" href="index.html"><span class="dot" aria-hidden="true"></span>%s</a>
<nav class="nav" aria-label="Main">%s</nav>
<button class="burger" type="button" aria-expanded="false" aria-controls="menu" aria-label="Open menu"><span></span><span></span></button>
</div></header>
<div class="menu" id="menu"><div class="wrap"><nav aria-label="Menu">%s</nav><p class="label">%s</p></div></div>
""" % (esc(self.b.get("name")), nav, menu, contact_bits or t(self.b.get("market")))

    def footer(self):
        b = self.b
        kind = self.p.get("disclosure")
        lic = ""
        # The line their broker (or company) requires, exactly as they wrote it. It already
        # holds the name, number and company, so it replaces the pieced-together version
        # rather than sitting next to it with "License #" and blanks.
        if b.get("licenseLine") and kind in ("real-estate", "lender"):
            lic = '<p>Brokerage and license<br>%s</p>' % t(b["licenseLine"])
        elif kind == "real-estate":
            lic = '<p>%s<br>License # %s<br>%s</p>' % (esc(b.get("person")), t(b.get("license") or "[Your license number]"),
                                                     t(b.get("brokerage") or "[Your brokerage]"))
        elif kind == "lender":
            lic = '<p>%s, NMLS # %s<br>%s, NMLS # %s</p>' % (
                esc(b.get("person")), t(b.get("nmls") or "[Your NMLS number]"),
                t(b.get("company") or b.get("brokerage") or "[Your company]"), t(b.get("companyNmls") or "[Your company NMLS number]"))
        explore = "".join('<li><a href="%s">%s</a></li>' % (h, esc(lbl)) for h, lbl in self.pages)
        explore += "".join('<li><a href="%s">%s</a></li>' % (fr, esc(plain(m.get("navLabel") or m.get("title"))))
                           for m, fr, _ in self.magnets()[1:])
        reach = "".join("<li>%s</li>" % x for x in (
            ('<a href="tel:%s">%s</a>' % (esc(re.sub(r"[^0-9+]", "", b["phone"])), esc(b["phone"]))) if b.get("phone") and not PH.search(b["phone"]) else "",
            ('<a href="mailto:%s">%s</a>' % (esc(b["email"]), esc(b["email"]))) if b.get("email") and not PH.search(b["email"]) else "",
            t(b.get("market"))) if x)
        eho = ('<span class="eho">%s%s</span>' % (EHO_SVG, "Equal Housing Lender" if kind == "lender" else "Equal Housing Opportunity")) if kind else ""
        return """<footer class="footer"><div class="wrap">
<div class="cols">
<div><p class="h3" style="margin-bottom:14px">%s</p><p style="color:var(--dark-muted);max-width:420px">%s</p>%s</div>
<div><p class="label">Explore</p><ul>%s<li><a href="privacy.html">Privacy</a></li></ul></div>
<div><p class="label">Reach us</p><ul>%s</ul></div>
</div>
<div class="legal"><span>&copy; %s</span>%s</div>
</div></footer>
<a class="dashlink" href="../index.html">&larr; Dashboard</a>
<div class="previewbar" role="note"><span>Demo: what your website could look like. It lives only on your computer.</span><a href="../index.html">Back to your dashboard</a></div>
<script src="../assets/site.js" defer></script>
</body></html>
""" % (esc(b.get("name")), t(get(self.c, "brand.tagline") or b.get("oneLiner")), lic, explore, reach, esc(b.get("name")), eho)

    def page(self, f, title, desc, og_img, body, faq=None, hero=False):
        title = fit_title(title)
        desc = fit_desc(desc, self.b.get("oneLiner"), get(self.c, "brand.tagline"), "%s, %s in %s." % (
            plain(self.b.get("person")), plain(self.b.get("profession")).lower(), plain(self.b.get("market"))))
        name = plain(title)
        ld = schema_graph(self.c, self.p, self.base, self.url(f), name, faq)
        out = self.head(f, title, desc, og_img)
        out += '<script type="application/ld+json">%s</script>\n</head>\n<body%s>\n' % (ld, ' class="has-hero"')
        out += self.header(f) + '<main id="main">' + body + "</main>\n" + self.footer()
        (SITE / f).write_text(out, encoding="utf-8")

    # ---------------------------------------------------------- blocks
    def pagehero(self, eyebrow, headline, sub, image, extra=""):
        return """<section class="pagehero"><div class="pagehero__img">%s</div>
<div class="pagehero__inner wrap"><p class="eyebrow">%s</p><h1 class="h-display">%s</h1>%s%s</div></section>""" % (
            img(image, eager=True), t(eyebrow), t(headline), ('<p class="hero__sub">%s</p>' % t(sub)) if sub else "", extra)

    def magnet_band(self):
        m = self.c.get("leadMagnet", {})
        bg = self.pick.slot("magnet")[0]
        bullets = "".join("<li>%s</li>" % t(x) for x in (m.get("bullets") or [])[:3])
        return """<section class="magnet" aria-labelledby="magnet-h"><div class="magnet__bg">%s</div><div class="wrap">
<div class="reveal"><p class="eyebrow" style="color:var(--accent-on-dark)">Free %s</p><h2 class="h2" id="magnet-h">%s</h2>
<p class="hero__sub">%s</p><ul class="ticks">%s</ul>
<div class="links"><a class="pill pill--accent" href="free-guide.html">%s</a></div></div>
<a class="cover reveal d1" href="free-guide.html" aria-label="Get %s"><span class="tag">Free</span><span class="t">%s</span><span class="by">%s</span></a>
</div></section>""" % (img(bg), esc(m.get("format") or "guide"), t(m.get("title")), t(m.get("hook")), bullets,
                       esc(m.get("buttonText") or "Get it free"), esc(plain(m.get("title"))), t(m.get("title")), esc(self.b.get("name")))

    def faq_block(self, faq, heading="What people ask first"):
        if not faq:
            return ""
        items = "".join("<details><summary>%s</summary><p>%s</p></details>" % (t(x["q"]), t(x["a"])) for x in faq)
        return '<section class="section section--alt"><div class="wrap"><p class="eyebrow">Questions</p><h2 class="h2 reveal">%s</h2><div class="faq reveal d1">%s</div></div></section>' % (esc(heading), items)

    def inquire(self, headline, sub):
        cta = get(self.c, "site.home.primaryCta", "Send")
        return """<section class="section section--dark on-dark" aria-labelledby="inq-h"><div class="wrap split">
<div class="reveal"><p class="eyebrow">Start a conversation</p><h2 class="h2" id="inq-h">%s</h2><p class="body" style="margin-top:20px">%s</p></div>
<form class="form reveal d1" id="contactForm">
<div><label for="cn">Your name</label><input id="cn" name="name" autocomplete="name" required></div>
<div><label for="ce">Email</label><input id="ce" name="email" type="email" autocomplete="email" required></div>
<div><label for="cm">How can we help?</label><textarea id="cm" name="message"></textarea></div>
<button class="pill pill--accent submit" type="submit">%s</button>
<p class="fine">Preview: this form does not send anything yet.</p>
</form></div></section>""" % (t(headline), t(sub), esc(cta))

    # ---------------------------------------------------------- pages
    def build_home(self):
        c, h = self.c, get(self.c, "site.home", {})
        heroes = self.pick.slot("hero", 3)
        slides = "".join('<div class="hero__slide%s">%s</div>' % (" is-active" if i == 0 else "", img(im, eager=(i == 0), lazy_src=(i > 0)))
                         for i, im in enumerate(heroes))
        lead, accent = h.get("heroLead", ""), h.get("heroAccent", "")
        p2 = self.p["pages"][0]
        hero = """<section class="hero hero--sticky" aria-label="Introduction">%s
<div class="hero__cap"><div class="wrap"><div class="inner">
<p class="eyebrow">%s</p><div class="hero__rule" aria-hidden="true"></div>
<h1 class="h-display">%s%s</h1><p class="hero__sub">%s</p>
<div class="links"><a class="pill pill--white" href="%s">%s</a><a class="tlink" href="free-guide.html">%s</a></div>
</div></div></div></section>""" % (slides, t(h.get("heroEyebrow") or "%s · %s" % (self.b.get("profession"), self.b.get("market"))),
                                    t(lead), (' <span class="accent">%s</span>' % t(accent)) if accent else "", t(h.get("heroSub")),
                                    p2["file"], esc(h.get("primaryCta") or p2["nav"]), esc(get(c, "leadMagnet.title", "Free guide")))

        statement = """<section class="section"><div class="wrap"><p class="eyebrow reveal">%s</p>
<p class="statement reveal d1">%s</p>
<div class="links reveal d2"><a class="tlink" href="about.html">About %s</a><a class="tlink" href="contact.html">Get in touch</a></div></div></section>""" % (
            t(h.get("statementEyebrow") or "Hello"), t(h.get("statement")), esc(plain(self.b.get("person")).split(" ")[0] or "us"))

        video = self.p.get("video") or {}
        video_band = ""
        if video.get("src") and not re.search(r"\bonline\b|remote|virtual", str(self.b.get("market", "")), re.I):
            poster = self.pick.slot("video")[0]
            video_band = """<section class="video reveal" aria-label="%s"><video muted loop playsinline preload="none" data-poster="../assets/img/library/%s" data-src="%s" aria-label="%s"></video>
<div class="video__cap"><div class="wrap"><p class="label">%s</p></div></div></section>""" % (
                esc(video["label"]), poster["small"], esc(video["src"]), esc(video["label"]), t(self.b.get("market")))

        stats = [s for s in (self.b.get("stats") or []) if isinstance(s.get("value"), (int, float))]
        stat_band = ""
        if stats:
            cells = "".join('<div class="stat reveal d%d"><p class="stat__num" data-count="%s" data-suffix="%s">%s%s</p><p class="label">%s</p></div>'
                            % (i % 3, s["value"], esc(s.get("suffix", "")), "{:,}".format(s["value"]), esc(s.get("suffix", "")), t(s.get("label")))
                            for i, s in enumerate(stats[:3]))
            stat_band = '<section class="section"><div class="wrap"><p class="eyebrow">By the numbers</p><div class="stats"%s>%s</div></div></section>' % (
                ' style="grid-template-columns:1fr"' if len(stats) == 1 else "", cells)

        diff_img = self.pick.slot("difference")[0]
        d = c.get("differentiator", {})
        difference = """<section class="section section--alt" id="difference"><div class="wrap split">
<div class="frame frame--tall reveal">%s</div>
<div class="stack reveal d1"><p class="eyebrow">%s</p><h2 class="h2">%s</h2><div class="body">%s</div>
<div class="links"><a class="tlink" href="about.html">About %s</a></div></div></div></section>""" % (
            img(diff_img, sizes="(min-width:900px) 50vw, 100vw"), t(h.get("differenceEyebrow") or "Why this works"),
            t(h.get("differenceHeadline") or d.get("statement")), paras(h.get("differenceBody")), esc(self.b.get("person", "").split(" ")[0] or "us"))

        pil_imgs = self.pick.slot("pillars", 4)
        pills = "".join("""<div class="pillar reveal d%d"><div class="frame frame--tall">%s</div><p class="pillar__num" aria-hidden="true">%02d</p><h3>%s</h3><p>%s</p></div>"""
                        % (i, img(pil_imgs[i], sizes="(min-width:1100px) 25vw, 50vw"), i + 1, t(pp.get("name")), t(pp.get("text")))
                        for i, pp in enumerate((d.get("pillars") or [])[:4]))
        pillars = """<section class="section section--dark on-dark"><div class="wrap"><p class="eyebrow reveal">%s</p><h2 class="h2 reveal d1">%s</h2>
<div class="pillars">%s</div></div></section>""" % (t(d.get("methodName")), t(h.get("pillarsHeadline") or d.get("statement")), pills)

        caps = h.get("tickerCaptions") or []
        tick_imgs = self.pick.slot("ticker", 6)
        shapes = "ababcb"
        items = "".join('<figure class="tick tick--%s">%s<figcaption>%s</figcaption></figure>' % (shapes[i], img(tick_imgs[i], sizes="40vw"), t(caps[i] if i < len(caps) else ""))
                        for i in range(6))
        ticker = """<section class="section" aria-labelledby="tick-h"><div class="wrap"><p class="eyebrow">%s</p><h2 class="h2 reveal" id="tick-h">%s</h2></div>
<div class="ticker"><div class="ticker__track">%s<div aria-hidden="true" style="display:contents">%s</div></div></div></section>""" % (
            t(h.get("tickerEyebrow") or "What we do"), t(h.get("tickerHeadline")), items, items.replace("<figcaption>", '<figcaption aria-hidden="true">'))

        split_img = self.pick.slot("split")[0]
        split = """<section class="section section--alt"><div class="wrap split split--flip">
<div class="frame frame--wide reveal">%s</div>
<div class="stack reveal d1"><p class="eyebrow">%s</p><h2 class="h2">%s</h2><div class="body">%s</div>
<div class="links"><a class="tlink" href="%s">%s</a></div></div></div></section>""" % (
            img(split_img, sizes="(min-width:900px) 50vw, 100vw"), t(h.get("splitEyebrow") or "How we work"), t(h.get("splitHeadline")),
            paras(h.get("splitBody")), p2["file"], esc(h.get("splitLink") or "See how it works"))

        faq = get(c, "site.faq", [])
        body = hero + statement + self.magnet_band() + video_band + stat_band + difference + pillars + ticker + split + \
            self.faq_block(faq) + self.inquire(h.get("closingHeadline"), h.get("closingText"))
        self.page("index.html", "%s | %s" % (plain(self.b.get("name")), plain(self.b.get("profession"))),
                  plain(self.b.get("oneLiner")), heroes[0], body, faq=faq, hero=True)

    def build_about(self):
        a = get(self.c, "site.about", {})
        im = self.pick.slot("about")[0]
        d = self.c.get("differentiator", {})
        vals = "".join('<div class="reveal d%d"><h3 class="h3">%s</h3><p class="body" style="margin-top:10px">%s</p></div>' % (i, t(v.get("title")), t(v.get("text")))
                       for i, v in enumerate(a.get("values") or []))
        body = self.pagehero("About %s" % plain(self.b.get("person")), a.get("headline"), a.get("sub"), im) + \
            '<section class="section"><div class="wrap"><div class="doc reveal">%s</div></div></section>' % "".join(paras(p) for p in (a.get("story") or [])) + \
            '<section class="section section--alt"><div class="wrap"><p class="eyebrow">%s</p><h2 class="h2 reveal">%s</h2><div class="chapters">%s</div></div></section>' % (
                t(d.get("methodName")), t(d.get("statement")),
                "".join('<div class="chapter reveal"><p class="chapter__num" aria-hidden="true">%02d</p><div><h3>%s</h3><p>%s</p></div></div>' % (i + 1, t(p.get("name")), t(p.get("text")))
                        for i, p in enumerate(d.get("pillars") or []))) + \
            '<section class="section"><div class="wrap"><p class="eyebrow">What we stand for</p><div class="cards cards--3">%s</div></div></section>' % vals + \
            self.magnet_band() + self.inquire(get(self.c, "site.home.closingHeadline"), get(self.c, "site.home.closingText"))
        self.page("about.html", "About %s | %s" % (plain(self.b.get("person")), plain(self.b.get("name"))),
                  plain(a.get("sub") or self.b.get("oneLiner")), im, body)

    def build_steps(self, pg):
        s = get(self.c, "site." + pg["key"], {})
        im = self.pick.slot(pg["key"])[0]
        steps = "".join('<div class="chapter reveal"><p class="chapter__num" aria-hidden="true">%02d</p><div><h3>%s</h3><p>%s</p></div></div>' % (i + 1, t(x.get("title")), t(x.get("text")))
                        for i, x in enumerate(s.get("steps") or []))
        body = self.pagehero(s.get("eyebrow") or pg["nav"], s.get("headline"), s.get("sub"), im,
                             '<div class="links"><a class="pill pill--white" href="contact.html">%s</a></div>' % esc(s.get("cta") or "Talk with us")) + \
            '<section class="section"><div class="wrap"><div class="statement reveal" style="max-width:900px">%s</div>' % t(s.get("intro")) + \
            '<div class="chapters">%s</div></div></section>' % steps + \
            self.magnet_band() + self.inquire(s.get("closingHeadline") or get(self.c, "site.home.closingHeadline"), s.get("closing") or get(self.c, "site.home.closingText"))
        self.page(pg["file"], "%s | %s" % (plain(s.get("headline"))[:48], plain(self.b.get("name"))),
                  plain(s.get("sub") or s.get("intro"))[:160], im, body)

    def build_services(self, pg):
        s = get(self.c, "site." + pg["key"], {})
        im = self.pick.slot(pg["key"])[0]
        items = s.get("items") or []
        card_imgs = self.pick.slot("ticker", len(items)) if items else []
        cards = "".join('<article class="card reveal d%d"><div class="frame">%s</div><p class="for">For %s</p><h3>%s</h3><p>%s</p><p><strong>%s</strong></p></article>'
                        % (i % 3, img(card_imgs[i], sizes="(min-width:1100px) 33vw, 50vw"), t(x.get("for")), t(x.get("name")), t(x.get("text")), t(x.get("outcome")))
                        for i, x in enumerate(items))
        body = self.pagehero(s.get("eyebrow") or "Services", s.get("headline"), s.get("sub"), im,
                             '<div class="links"><a class="pill pill--white" href="contact.html">Talk with us</a></div>') + \
            '<section class="section"><div class="wrap"><div class="statement reveal" style="max-width:900px">%s</div><div class="cards cards--3">%s</div></div></section>' % (t(s.get("intro")), cards) + \
            self.magnet_band() + self.inquire(get(self.c, "site.home.closingHeadline"), get(self.c, "site.home.closingText"))
        self.page(pg["file"], "%s | %s" % (plain(s.get("headline"))[:48], plain(self.b.get("name"))),
                  plain(s.get("sub") or s.get("intro"))[:160], im, body)

    # What each kind of lead magnet is called on the page. "book" is a mini book, "companion"
    # an AI companion: a prompt the visitor pastes into ChatGPT or Claude (Krista's bundle model).
    KIND = {"checklist": "checklist", "guide": "guide", "book": "mini book", "companion": "AI companion"}

    def kind(self, m):
        return self.KIND.get(m.get("format") or "guide", "guide")

    def magnets(self):
        """The main lead magnet, then any more they asked for: [(magnet, free page, guide page)]."""
        out = [(self.c.get("leadMagnet", {}), "free-guide.html", "guide.html")]
        for m in self.c.get("moreMagnets") or []:
            slug = re.sub(r"[^a-z0-9]+", "-", str(m.get("slug") or m.get("title") or "guide").lower()).strip("-")[:40] or "guide"
            out.append((m, "free-%s.html" % slug, "guide-%s.html" % slug))
        return out

    def build_magnet(self, m, free_file, guide_file):
        im = self.pick.slot("guide")[0]
        bullets = "".join("<li>%s</li>" % t(x) for x in (m.get("bullets") or []))
        body = """<section class="pagehero" style="min-height:100svh"><div class="pagehero__img">%s</div>
<div class="pagehero__inner wrap"><div class="split" style="align-items:end">
<div><p class="eyebrow">Free %s</p><h1 class="h-display">%s</h1><p class="hero__sub">%s</p><ul class="ticks">%s</ul></div>
<div style="background:rgba(10,12,16,.72);backdrop-filter:blur(10px);padding:clamp(24px,4vw,40px)">
<h2 class="h3">%s</h2>
<form class="form" id="leadForm" style="margin-top:20px">
<div><label for="fn">First name</label><input id="fn" name="first" autocomplete="given-name" required></div>
<div><label for="em">Email</label><input id="em" name="email" type="email" autocomplete="email" required></div>
<button class="pill pill--accent submit" type="submit">%s</button>
<p class="fine">Preview: this saves only in this browser. Nothing is sent.</p></form>
<div class="done" id="leadDone" tabindex="-1"><p class="h3">You're all set!</p><p style="margin-top:10px">%s</p>
<div class="links"><a class="pill pill--accent" href="%s">Read your %s now</a></div></div>
</div></div></div></section>""" % (img(im, eager=True), esc(self.kind(m)), t(m.get("title")), t(m.get("subtitle")), bullets,
                                   t(m.get("formHeadline")), esc(m.get("buttonText") or "Send it to me"),
                                   t(m.get("thankYou") or "Your guide is ready. Read it now; a copy is on its way to your inbox."), guide_file, esc(self.kind(m)))
        self.page(free_file, "%s | %s" % (plain(m.get("title")), plain(self.b.get("name"))), plain(m.get("subtitle") or m.get("hook"))[:160], im, body)

        sections = "".join("<section><h3>%s</h3>%s</section>" % (t(s.get("heading")), paras(s.get("body"))) for s in (m.get("sections") or []))
        mails = "".join(  # shown on the dashboard, not on this public page; kept for reference
'<div class="mail reveal"><p class="day">Day %s</p><div class="body"><p class="subj">%s</p>%s</div></div>' % (esc(e.get("day")), t(e.get("subject")), t(e.get("body")))
                        for e in (m.get("emails") or []))
        # An AI companion's page leads with the prompt itself, ready to copy and paste.
        prompt = ""
        if m.get("format") == "companion" and m.get("prompt"):
            prompt = ('<div class="companion"><p class="eyebrow">Your companion</p><pre id="companionPrompt">%s</pre>'
                      '<button class="pill pill--accent" type="button" data-copy-target="companionPrompt">Copy the companion</button></div>') % esc(m.get("prompt"))
        body = self.pagehero("Your free %s" % self.kind(m), m.get("title"), m.get("subtitle"), self.pick.slot("magnet")[0]) + \
            '<section class="section"><div class="wrap"><p class="body" style="margin-bottom:24px">Thanks, <span data-lead-name>there</span>. Here it is.</p><div class="doc">%s%s<p style="margin-top:30px"><strong>%s</strong></p></div></div></section>' % (sections, prompt, t(m.get("closing"))) + \
            self.inquire(get(self.c, "site.home.closingHeadline"), get(self.c, "site.home.closingText"))
        self.page(guide_file, "%s, the full %s | %s" % (plain(m.get("title"))[:40], self.kind(m), plain(self.b.get("name"))),
                  plain(m.get("hook"))[:160], im, body)

    def build_contact(self):
        k = get(self.c, "site.contact", {})
        im = self.pick.slot("contact")[0]
        body = self.pagehero("Contact", k.get("headline"), k.get("sub") or k.get("text"), im) + \
            self.inquire(k.get("headline"), k.get("text")) + self.faq_block(get(self.c, "site.faq", [])[:3], "Before you reach out")
        self.page("contact.html", "Contact %s | %s" % (plain(self.b.get("person")), plain(self.b.get("name"))),
                  plain(k.get("text") or k.get("sub"))[:160], im, body, faq=get(self.c, "site.faq", [])[:3])

    def build_privacy(self):
        n = esc(self.b.get("name"))
        body = self.pagehero("Privacy", "How %s handles what you send" % n, "", self.pick.slot("contact")[0]) + """
<section class="section"><div class="wrap doc">
<p>When you fill in a form on this site, %s receives your name, your email address, and anything you choose to write. That is used only to reply to you and, if you asked for a guide, to send it and a short series of follow-up emails. You can ask to stop at any time by replying to any email.</p>
<p>This site does not use advertising trackers or sell personal information.</p>
<p><span class="ph">[%s]</span></p>
</div></section>""" % (n, "Have your broker or attorney review this page before the site goes live" if self.p.get("disclosure") == "real-estate"
                                else "Have your compliance department review this page before the site goes live" if self.p.get("disclosure") == "lender"
                                else "Have a professional review this page before the site goes live")
        self.page("privacy.html", "Privacy | %s" % plain(self.b.get("name")), "How %s uses the details you send through this website." % plain(self.b.get("name")), self.pick.slot("contact")[0], body)

    def build(self):
        SITE.mkdir(parents=True, exist_ok=True)
        self.build_home()
        self.build_about()
        for pg in self.p["pages"]:
            (self.build_steps if pg["kind"] == "steps" else self.build_services)(pg)
        extra_files, labels_extra = [], []
        for i, (m, free_file, guide_file) in enumerate(self.magnets()):
            self.build_magnet(m, free_file, guide_file)
            labels_extra.append((guide_file, "Your %s, delivered" % plain(m.get("format") or "guide")))
            if i:
                extra_files += [free_file, guide_file]
                labels_extra.append((free_file, plain(m.get("navLabel") or m.get("title") or "Free guide")))
        self.build_contact()
        self.build_privacy()
        files = [f for f, _ in self.pages] + ["guide.html"] + extra_files + ["privacy.html"]
        (SITE / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s</urlset>\n'
                                          % "".join("  <url><loc>%s</loc></url>\n" % self.url(f) for f in files), encoding="utf-8")
        (APP / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: %s/site/sitemap.xml\n" % self.base, encoding="utf-8")
        b = self.b
        (APP / "llms.txt").write_text(
            "# %s\n\n> %s\n\n%s, %s. Serving %s.\n\n## Pages\n%s\n" % (
                plain(b.get("name")), plain(b.get("oneLiner")), plain(b.get("person")), plain(b.get("profession")),
                ", ".join(plain(a) for a in (b.get("areas") or [b.get("market")]) if a),
                "".join("- [%s](%s)\n" % (lbl, self.url(f)) for f, lbl in self.pages)), encoding="utf-8")
        (DATA / "images.json").write_text(json.dumps(self.pick.chosen, indent=1), encoding="utf-8")
        # What the dashboard needs to show every page as a thumbnail.
        labels = dict(self.pages + labels_extra + [("privacy.html", "Privacy")])
        brand_colors = get(self.c, "brand.colors", {}) or {}
        (DATA / "site.json").write_text(json.dumps({
            "base": self.base, "profile": self.p["id"],
            "pages": [{"file": f, "label": labels[f]} for f in files],
            "magnets": [{"title": plain(m.get("title")), "format": plain(m.get("format") or "guide"), "free": fr, "guide": gd}
                        for m, fr, gd in self.magnets()],
            "palette": self.pal, "colorNotes": color_notes(brand_colors, self.pal),
            "images": self.pick.chosen,
            "fullSite": self.p.get("fullSite"),
        }, indent=1), encoding="utf-8")
        return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="where the preview is served, e.g. http://localhost:4321")
    a = ap.parse_args()
    content = json.loads((DATA / "content.json").read_text(encoding="utf-8"))
    pid = content.get("profile") or "general"
    profile = json.loads((ROOT / "profiles" / (pid + ".json")).read_text(encoding="utf-8"))
    files = Site(content, profile, a.base, load_library()).build()
    print(json.dumps({"built": files, "profile": pid}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
