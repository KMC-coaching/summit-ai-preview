#!/usr/bin/env python3
"""
Audit a website the way our launch gate does, and say plainly what it found.

    python3 scripts/grade_site.py <url> [--label "Your website"] [--profile real-estate|lender|general]
                                        [--local] [--out app/data/grade.json]

THIS IS THE SEED'S PROCESS, PORTED
  realtor-site-seed will not let a site launch until it passes `npm run gate`:
  smoke, validate:schema, launch:check, audit:browser, then audit:compare against
  the owner's old site. This file runs every one of those checks that can be run
  against a live site from the outside, with the same rules and the same floors,
  on standard-library Python 3.9 plus Lighthouse. The checks and their sources:

    Lighthouse floors              audit-compare.mjs   perf 85, a11y 100, best practices 95, SEO 100
    Lighthouse accessibility rules  audit-browser.mjs   axe-core: contrast, alt text, labels, tap targets
    Structured data                validate-schema.mjs JSON-LD on every page, parses, @type, @id refs resolve
    Head, links, scrub, disclosure launch-check.mjs    canonical, share preview, filler, placeholders,
                                                       Fair Housing, commission wording, em-dash/slop,
                                                       license + brokerage + Equal Housing on every page,
                                                       FAQ schema matches the page, duplicate pages, privacy
    Claims                         check-article.mjs   FTC: "#1", "best in town", "guaranteed"...

  Some of the seed's checks need a full scripted browser: dark-mode contrast,
  overlapping text, keyboard focus rings, real-visitor speed. Those are listed as
  NOT MEASURED, never as passed. Silence must never read as success.

  Fair Housing, licence and Equal Housing checks run only with --profile
  real-estate; fair lending, NMLS, Equal Housing Lender and Regulation Z claims only
  with --profile lender. Fair Housing does not apply to a plumber.

POLITE BY DESIGN
  This may be somebody's live website. Read-only, one request at a time, a pause
  between pages, at most MAX_PAGES pages and MAX_LINKS link checks.

--local
  For the new preview site on this computer. HTTPS and "can Google crawl it"
  cannot pass on a site that is not published, so they are marked "after launch"
  rather than failed: the seed's audit:compare does the same.

Runs on the Python that ships with macOS (3.9): no newer syntax.
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urldefrag, quote
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import security  # noqa: E402  (shared with the website-health skill, byte-identical)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36 AIPreviewSiteGrader"
MAX_PAGES = 25
MAX_LINKS = 60
PAUSE = 0.35
TIMEOUT = 20
LIGHTHOUSE = "lighthouse@12.8.2"

# The launch-gate floors from realtor-site-seed/scripts/audit-compare.mjs:337.
BAR = {"performance": 85, "accessibility": 100, "bestPractices": 95, "seo": 100}

# ------------------------------------------------------------- the seed's lists
# launch-check.mjs:57-77, verbatim.
FILLER = ["placehold.co", "placeholder", "lorem ipsum", "[scaffold", "has not been written yet",
          "example.com", ".example", "@example", "yourdomain", "fill in your", "test-000000",
          "(555)", "555-01", "n/a", "tbd", "todo"]
BRACKET = re.compile(r"\[[A-Z][^\]\n]{0,300}\]")  # launch-check.mjs:82, widened to match build_site's 300-character blanks

# launch-check.mjs:1122-1131 (FAIL) and 1161-1165 (WARN), verbatim.
PLACE = r"(neighbou?rhoods?|communit(?:y|ies)|areas?|part of town|streets?|subdivisions?|zip codes?)"
FH_FAIL = [
    (r"\b(perfect|great|ideal|wonderful) for (a )?(young )?famil(y|ies)\b", "familial status: describe the property, not who it suits"),
    (r"\bfamily[- ]friendly\b", "familial status"),
    (r"\bfamily " + PLACE + r"\b", "familial status"),
    (r"\b(kid|child|children)[- ]friendly\b", "familial status"),
    (r"\b(raise|raising) (your |a )?(kids|children|family)\b", "familial status"),
    (r"\bsafe " + PLACE + r"\b", "'safe' reads as coded language about residents; cite facts instead"),
    (r"\b" + PLACE + r"\W+(?:\w+\W+){0,4}(?:very |really |so )?safe\b", "'safe' reads as coded language about residents; cite facts instead"),
    (r"\b(low|no|high) crime\b", "crime claims steer; leave them to official sources"),
    (r"\bexclusive " + PLACE + r"\b", "exclusionary framing"),
    (r"\b(no children|adults only|no kids)\b", "familial status: unlawful outside qualified 55+ housing"),
    (r"\b(perfect|great|ideal) for (retirees|empty[- ]nesters|seniors|singles|couples|newlyweds)\b", "describe the home, not who should live there"),
    (r"\bbachelor pad\b", "sex/marital framing"),
    (r"\bwalking distance to (a )?(church|churches|synagogue|mosque|temple)\b", "religion: name amenities generically"),
    (r"\b(christian|catholic|jewish|muslim|hindu|mormon)( families| community| neighbou?rhoods?| area)\b", "religion"),
    (r"\bideal for young professionals\b", "describe the home, not the people"),
]
FH_WARN = [
    (r"\b(good|great|best|top|top[- ]rated|excellent) (schools|school districts?)\b", "school-quality claims can steer; name the schools or district factually"),
    (r"\b(quiet|established|desirable) " + PLACE + r"\b", "can read as coded; prefer concrete detail"),
    (r"\bhandicapped\b", "use 'accessible' or person-first language"),
    # Added 2026-10-19, not in the seed's list: a stage test carried a student's own story
    # ("the house they raised their kids in", "a widow in Land Park") onto the site untouched.
    # People's family or marital status, even a past client's, is not for an ad. The preview's
    # checker blocks these; the report card warns.
    (r"\b(raised|raising|raise) (their |his |her |our |your |my |the )?(kids|children|family|families)\b", "familial status: tell the story without who lived there"),
    (r"\b(young|growing|new) famil(y|ies)\b", "familial status"),
    (r"\b(widow|widowed|widower|divorcee|divorced|newlyweds?|empty[- ]nesters?|single (mom|mother|dad|father|parents?))\b", "marital or familial status: describe the situation, not the person"),
]
COMMISSION = [
    (r"\b(standard|customary|typical|usual|going)\s+(commission|rate|fee)s?\b", "implies fees are set rather than negotiated"),
    (r"\bcommissions?\s+(are|is)\s+(set|fixed|standard|customary)\b", "antitrust risk"),
    (r"\b6\s*%\s*commission\b", "never state a rate as if it were the norm"),
]
# check-article.mjs:36-48 (FTC), widened after a break-it run slipped past the originals.
CLAIMS = [
    (r"(#\s?1\b|\bnumber[- ]one\b|\bno\.\s?1\b)", "'#1' needs a source the reader can check"),
    (r"\b(top[- ]rated|award[- ]winning|best[- ]selling)\b", "rating or award claim needs the source named"),
    (r"\bbest (\w+ )?(agent|realtor|broker|team|company|firm|business|dentist|doctor|lawyer|attorney|coach|plumber|contractor|choice|option|service|\w+(?:er|or|ist))s? (in|of) [A-Z][a-z]+", "superlative claim"),
    (r"\bbest (in|of) (town|the city|the area|the state|the county)\b", "superlative claim"),
    (r"\b(voted|rated|awarded) (the )?(best|top|#\s?1)\b", "award claim needs the award named"),
    # "deemed reliable but not guaranteed" is the MLS disclaimer, not a claim.
    (r"(?<!not )(?<!no )(?<!never )\bguarantee(d|s)?\b(?! (of|or) (accuracy|completeness))", "a guarantee is a legal promise"),
    (r"\b(results|success) (promised|assured)\b|\bpromise (you )?(results|a sale|to sell)\b", "a promised result is a guarantee"),
    (r"\b100% (satisfaction|success|guaranteed|effective)\b", "absolute claim"),
    (r"\b(cheapest|lowest price(d)?|lowest rates?|unbeatable price)\b", "price superlative"),
    (r"\brisk[- ]free\b", "absolute claim"),
    (r"\b(always|never) (sells|closes|works|succeeds)\b", "absolute claim"),
]
# Content we WRITE only: a competitor's real, permitted reviews are not a finding.
INVENTED = [
    (r"[\"“][^\"”]{20,}[\"”]\s*[-–—]\s*[A-Z][a-z]+(\s[A-Z]\.?)?", "looks like a testimonial: only real ones from their file, used with permission"),
    (r"\b(5|five)[- ]star (review|rating)s?\b|\b\d\.\d (stars?|rating)\b", "a rating needs a real, checkable source from their file"),
]
# launch-check.mjs:1053-1107 SLOP, plus the copywriter's banned phrases.
SLOP = [
    (r"—", "em-dash"),
    (r"\bserves as\b", "'serves as'"),
    (r"\bplays a (vital|key|crucial|pivotal) role\b", "'plays a key role'"),
    (r"\bwhen it comes to\b", "'when it comes to'"),
    (r"\bin today's (market|world|landscape|fast-paced world)\b", "'in today's market'"),
    (r"\b(delve|tapestry|nestled|bustling|seamless|leverage|utilize|cutting-edge|unlock|elevate|synergy|game-changer)\b", "AI-sounding word"),
    (r"\b(let's dive in|at the end of the day|it's important to note|here's the thing)\b", "filler phrase"),
]
TRACKERS = [
    ("Meta pixel", r"connect\.facebook\.net|fbq\(", r"\b(meta|facebook|instagram)\b"),
    ("Google tag", r"googletagmanager\.com|google-analytics\.com|gtag\(", r"\bgoogle\b"),
    ("Microsoft Clarity", r"clarity\.ms", r"\b(clarity|microsoft)\b"),
]
TRACK_WORDS = re.compile(r"\b(track|tracking|pixel|cookie|cookies|analytics|advertis|retarget|measure)", re.I)

BUSINESS = re.compile(
    r"^(LocalBusiness|Organization|Corporation|ProfessionalService)$|"
    r"(Business|Agent|Store|Shop|Service|Practice|Office|Clinic|Agency|Dentist|Physician|Attorney|Restaurant)$", re.I)
RE_TYPES = ["Organization", "WebSite", "RealEstateAgent", "Person"]  # validate-schema.mjs:32-37
# Lending ads (Regulation Z, ECOA, UDAAP): the claims that get a loan officer in trouble.
LENDING = [
    (r"\bguaranteed (approval|loan|to (be )?approved)\b", "approval can never be guaranteed"),
    (r"\bno credit check\b|\bno credit\W+no problem\b|\bbad credit (ok|okay|welcome)\b", "misleading for a mortgage"),
    (r"\beveryone (qualifies|is approved|gets approved)\b", "approval can never be promised"),
    (r"\b(you('re| are)|you've been) (pre-?approved|pre-?qualified)\b", "a pre-approval needs an application"),
    (r"\d+(\.\d+)?\s?(%|percent)\s*(apr|rate|interest|down|fixed)?\b(?=[^.]{0,40}\b(apr|rate|interest|loan|mortgage|down)\b)|\b(apr|rate)s?\s+(of|at|from|starting at|as low as)\s+\d", "a rate or percentage triggers full Regulation Z disclosure"),
    (r"\bpayments?\s+(of|as low as|from|starting at|under)\s+\$?\d|\$\d[\d,]*\s*(/|per)\s*(mo|month)\b", "a payment amount triggers full Regulation Z disclosure"),
    (r"\b(zero|no|0%?)\s+down\b|\blow(est)? rates?\b", "a terms claim that needs the full disclosure"),
]
# Fair lending (ECOA, Fair Housing Act): targeting by a protected class, beyond FH_FAIL.
FAIR_LENDING = [
    (r"\b(under|over)\s+(\d{2})\b(?=[^.]{0,30}\b(buyers?|borrowers?|homeowners?|applicants?)\b)", "age targeting"),
    (r"\byoung (buyers|borrowers|couples|families|professionals)\b", "age or family targeting"),
    (r"\b(buyers?|borrowers?|homeowners?|applicants?|families)\s+(under|over|aged?)\s+\d{2}\b", "age targeting"),
    (r"\b(seniors|retirees) only\b|\b(adults|singles|couples) only\b", "protected-class restriction"),
]

# --------------------------------------------------------------------- fetching
_ctx = ssl.create_default_context()
# The last answer's headers, lowercased: security.py reads the home page's (X-Powered-By, cookies).
LAST_HEADERS = {}


def fetch(url, method="GET", limit=3_000_000):
    """(status, final_url, text). status 0 = never answered."""
    LAST_HEADERS.clear()
    req = Request(url, method=method, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urlopen(req, timeout=TIMEOUT, context=_ctx) as r:
            LAST_HEADERS.update({k.lower(): v for k, v in r.headers.items()})
            body = r.read(limit) if method == "GET" else b""
            return r.status, r.geturl(), body.decode("utf-8", "replace")
    except HTTPError as e:
        return e.code, url, ""
    except (URLError, ssl.SSLError, OSError) as e:
        if "CERTIFICATE" in str(e).upper() or isinstance(e, ssl.SSLError):
            return _curl(url, method)
        return 0, url, ""


def _curl(url, method):
    args = ["curl", "-sL", "--max-time", str(TIMEOUT), "-A", UA, "-w", "\n__STATUS__%{http_code} %{url_effective}"]
    if method == "HEAD":
        args.append("-I")
    try:
        out = subprocess.run(args + [url], capture_output=True, text=True, timeout=TIMEOUT + 5).stdout
    except Exception:
        return 0, url, ""
    m = re.search(r"\n__STATUS__(\d+) (\S*)\s*$", out)
    return (int(m.group(1)), m.group(2) or url, out[: m.start()]) if m else (0, url, "")


def check_status(url):
    status, _, _ = fetch(url, method="HEAD")
    if status in (0, 403, 405, 501) or status >= 500:  # many servers refuse HEAD
        status, _, _ = fetch(url, limit=2048)
    return status


# ---------------------------------------------------------------------- parsing
LD_RE = re.compile(r"<script\b[^>]*\btype\s*=\s*[\"']application/ld\+json[\"'][^>]*>([\s\S]*?)</script>", re.I)  # tolerant, validate-schema.mjs:54


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self._in_title = "", False
        self.meta, self.links, self.canonical = {}, [], ""
        self.h1s, self._in_h1 = [], False
        self.imgs, self.imgs_no_alt = 0, 0
        self.lang, self._skip = "", 0
        self.texts, self.main_texts, self._in_main = [], [], 0
        self.paras, self._in_p = [], False
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key:
                self.meta[key] = a.get("content", "")
        elif tag == "link" and "canonical" in a.get("rel", "").lower():
            self.canonical = a.get("href", "")
        elif tag == "a" and "href" in a:
            self.links.append(a["href"])
        elif tag == "h1":
            self._in_h1 = True
            self.h1s.append("")
        elif tag == "img":
            self.imgs += 1
            if "alt" not in a:
                self.imgs_no_alt += 1
        elif tag in ("script", "style", "noscript"):
            if tag == "script" and a.get("src"):
                self.scripts.append(a["src"])
            self._skip += 1
        elif tag == "main":
            self._in_main += 1
        elif tag == "p":
            self._in_p = True
            self.paras.append("")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False
        elif tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1
        elif tag == "main" and self._in_main:
            self._in_main -= 1
        elif tag == "p":
            self._in_p = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        if self._skip:
            return
        self.texts.append(data)
        if self._in_main:
            self.main_texts.append(data)
        if self._in_h1 and self.h1s:
            self.h1s[-1] += data
        if self._in_p and self.paras:
            self.paras[-1] += data


def norm_space(s):
    return re.sub(r"\s+", " ", s).strip()


def parse_ld(raw_html):
    """Every JSON-LD block: (parsed nodes, problems)."""
    nodes, problems = [], []
    for raw in LD_RE.findall(raw_html):
        try:
            data = json.loads(raw.strip())
        except Exception:
            problems.append("a structured-data block is not valid JSON")
            continue
        blocks = data if isinstance(data, list) else [data]
        for b in blocks:
            if isinstance(b, dict):
                nodes.extend(b.get("@graph") if isinstance(b.get("@graph"), list) else [b])
    return nodes, problems


def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def node_types(nodes):
    out = set()
    for n in nodes:
        for d in walk(n):
            t = d.get("@type")
            if isinstance(t, str):
                out.add(t)
            elif isinstance(t, list):
                out.update(x for x in t if isinstance(x, str))
    return out


def id_problems(nodes):
    """validate-schema.mjs:67-84: every pure {"@id": ...} reference must be defined on the page."""
    defined, refs = set(), set()
    for n in nodes:
        for d in walk(n):
            if "@id" in d:
                if len(d) == 1:
                    refs.add(d["@id"])
                else:
                    defined.add(d["@id"])
    return sorted(refs - defined)


# ----------------------------------------------------------------- discovery
def link_key(url):
    u = urlparse(url)
    h = u.netloc.lower()
    h = h[4:] if h.startswith("www.") else h
    return h + (u.path.rstrip("/") or "/") + ("?" + u.query if u.query else "")


def same_site(url, host):
    h = urlparse(url).netloc.lower()
    return h == host or h == "www." + host or "www." + h == host


ASSET = re.compile(r"\.(jpg|jpeg|png|gif|webp|svg|pdf|zip|mp4|mp3|webm|ico|xml|txt|css|js)(\?|$)", re.I)


def sitemap_urls(base, host):
    candidates = []
    status, _, robots = fetch(urljoin(base, "/robots.txt"))
    has_robots = status == 200 and "user-agent" in robots.lower()
    blocks_all = has_robots and bool(re.search(r"(?im)^\s*disallow:\s*/\s*$", robots))
    if has_robots:
        candidates += re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots)
    candidates += [urljoin(base, "/sitemap.xml"), urljoin(base, "/sitemap_index.xml")]
    found, pages, seen = False, [], set()
    queue = list(dict.fromkeys(candidates))
    while queue and len(seen) < 8 and len(pages) < 500:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        s, _, xml = fetch(sm)
        if s != 200 or "<loc>" not in xml:
            continue
        found = True
        locs = [l.strip() for l in re.findall(r"<loc>\s*([^<]+?)\s*</loc>", xml)]
        if "<sitemapindex" in xml:
            queue += [l for l in locs if l not in seen]
        else:
            pages += [l for l in locs if same_site(l, host)]
    return has_robots, blocks_all, found, list(dict.fromkeys(pages))


def pick_pages(home, sm_pages, home_links, host):
    pool = list(sm_pages)
    if not pool:
        for href in home_links:
            u = urldefrag(urljoin(home, href))[0]
            if u.startswith("http") and same_site(u, host) and not ASSET.search(u):
                pool.append(u)
    keyed = {}
    for p in pool:
        keyed.setdefault(link_key(p), p)
    pool = [p for k, p in keyed.items() if k != link_key(home)]
    if len(pool) > MAX_PAGES - 1:
        step = len(pool) / (MAX_PAGES - 1)
        pool = [pool[int(i * step)] for i in range(MAX_PAGES - 1)]
    return [home] + pool


# ----------------------------------------------------------------- Lighthouse
A11Y_PLAIN = {
    "color-contrast": "Text too faint to read against its background",
    "image-alt": "Images with no description",
    "link-name": "Links a screen reader cannot name",
    "button-name": "Buttons with no name",
    "label": "Form fields with no label",
    "target-size": "Buttons and links too small to tap",
    "heading-order": "Headings out of order",
    "html-has-lang": "Page language not declared",
    "document-title": "Page has no title",
    "meta-viewport": "Zooming is blocked on phones",
    "frame-title": "Embedded frames with no title",
    "list": "Lists built incorrectly",
    "listitem": "List items outside a list",
    "aria-allowed-attr": "Accessibility labels used incorrectly",
    "aria-hidden-focus": "Hidden things you can still tab to",
    "duplicate-id-aria": "Duplicate accessibility IDs",
    "link-in-text-block": "Links that only stand out by color",
}


def find_node():
    home = os.path.join(os.path.expanduser("~"), ".ai-preview", "node")
    for cand in (os.path.join(home, "bin", "node"), os.path.join(home, "node.exe"), shutil.which("node")):
        if cand and os.path.exists(cand) and os.path.exists(
                os.path.join(os.path.dirname(cand), "npx.cmd" if os.name == "nt" else "npx")):
            return cand
    return None


def read_lighthouse(lh, result):
    cats = lh.get("categories", {})
    audits = lh.get("audits", {})

    def g(k):
        v = (cats.get(k) or {}).get("score")
        return None if v is None else round(v * 100)

    def failed(cat):
        out = []
        for ref in (cats.get(cat) or {}).get("auditRefs", []):
            a = audits.get(ref.get("id")) or {}
            if a.get("score") is not None and a.get("score") < 1 and a.get("scoreDisplayMode") not in ("informative", "notApplicable", "manual") and ref.get("weight", 0) > 0:
                items = ((a.get("details") or {}).get("items") or [])
                where = []
                for it in items[:4]:
                    node = it.get("node") or {}
                    label = node.get("nodeLabel") or node.get("selector") or ""
                    if label:
                        where.append(label[:60])
                out.append({"id": a.get("id"), "title": A11Y_PLAIN.get(a.get("id"), a.get("title")), "count": len(items), "where": where})
        return out

    result.update({
        "performance": g("performance"), "accessibility": g("accessibility"),
        "bestPractices": g("best-practices"), "seo": g("seo"),
        "lcp": (audits.get("largest-contentful-paint") or {}).get("displayValue"),
        "cls": (audits.get("cumulative-layout-shift") or {}).get("displayValue"),
        "a11yFailed": failed("accessibility"), "seoFailed": failed("seo"),
        # What the phone actually showed: a picture is worth the whole report card.
        "screenshot": ((audits.get("final-screenshot") or {}).get("details") or {}).get("data"),
        "bpFailed": failed("best-practices"),
    })


def lighthouse_local(url, result):
    # A cold Chrome can take longer to start than Lighthouse waits for it ("Unable to
    # connect to Chrome", seen on Windows). The second start is warm, so try twice.
    for attempt in (1, 2):
        result.pop("_error", None)
        if _lighthouse_once(url, result):
            return True
        if "connect to Chrome" not in result.get("_error", "") and "debugging port" not in result.get("_error", ""):
            return False
    return False


def _lighthouse_once(url, result):
    node = find_node()
    if not node:
        result["_error"] = "Node is not installed here"
        return False
    bindir = os.path.dirname(node)
    npx = os.path.join(bindir, "npx.cmd" if os.name == "nt" else "npx")
    out = os.path.join(tempfile.mkdtemp(), "lh.json")
    env = dict(os.environ, PATH=bindir + os.pathsep + os.environ.get("PATH", ""))
    # A fixed free port: without one, chrome-launcher finds Chrome's port by reading Chrome's
    # log file, which fails on Windows ("waiting for dynamic debugging port").
    import socket
    with socket.socket() as sk:
        sk.bind(("127.0.0.1", 0))
        port = sk.getsockname()[1]
    args = [npx, "--yes", LIGHTHOUSE, url, "--quiet", "--port=%d" % port, "--chrome-flags=--headless=new --no-sandbox",
            "--only-categories=performance,accessibility,best-practices,seo",
            "--output=json", "--output-path=" + out]
    err = ""
    try:
        p = subprocess.run(args, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=240)
        err = (p.stderr or "").strip()
        with open(out, encoding="utf-8") as f:
            lh = json.load(f)
    except Exception as e:
        tail = err.splitlines()[-1][:200] if err else type(e).__name__
        hint = " (Google Chrome looks missing)" if "chrome" in err.lower() and "not" in err.lower() else ""
        result["_error"] = "Lighthouse could not run here%s: %s" % (hint, tail)
        result["_log"] = "\n".join(err.splitlines()[-40:])  # Lighthouse's own words, for whoever fixes it
        return False
    read_lighthouse(lh, result)
    result["_source"] = "Google Lighthouse, run on this computer"
    return result.get("performance") is not None


def pagespeed(url, result):
    api = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=" + quote(url, safe="") + \
          "".join("&category=" + c for c in ("performance", "accessibility", "best-practices", "seo")) + "&strategy=mobile"
    key = os.environ.get("PAGESPEED_API_KEY", "").strip()
    if key:
        api += "&key=" + key
    for attempt in range(2):
        try:
            with urlopen(Request(api, headers={"User-Agent": UA}), timeout=90, context=_ctx) as r:
                read_lighthouse(json.loads(r.read().decode("utf-8")).get("lighthouseResult", {}), result)
            result["_source"] = "Google Lighthouse, run by Google PageSpeed"
            return
        except HTTPError as e:
            result["_error"] = "PageSpeed answered %s" % e.code
            if e.code == 429 and attempt == 0:
                time.sleep(8)
                continue
            return
        except Exception as e:
            result["_error"] = "PageSpeed did not answer (%s)" % type(e).__name__
            return


WINDOWS_LIMIT = ("Google's speed test can't run on this Windows computer from here (a Windows limit, not a "
                 "problem with your site). Everything else on this report card was checked.")


def lighthouse_any(url, result, local_site):
    if lighthouse_local(url, result):
        result.pop("_error", None)
        return
    if local_site:
        # Google's servers cannot reach a site on this computer. On Windows, Google's speed
        # test often cannot start Chrome from a background task: a known Windows limit, not
        # a fault in their site. Say so plainly instead of showing Chrome's error.
        if os.name == "nt":
            result["_log"] = (result.get("_log") or "") + "\n" + (result.get("_error") or "")
            result["_error"] = WINDOWS_LIMIT
            result["_limit"] = "windows"
        return
    local_err = result.get("_error")
    pagespeed(url, result)
    if result.get("performance") is None and local_err:
        result["_error"] = "%s; %s" % (local_err, result.get("_error", ""))


# ------------------------------------------------------------------- the audit
class Report:
    def __init__(self):
        self.checks = []

    def add(self, group, name, status, detail="", count=None, pages=None, why=""):
        self.checks.append({"group": group, "name": name, "status": status, "detail": detail,
                            "count": count, "pages": (pages or [])[:8], "why": why})


def pathof(url):
    return urlparse(url).path or "/"


def audit(url, label, profile, local):
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    started = time.time()
    log = lambda m: print("  " + m, file=sys.stderr, flush=True)

    lh = {}
    lh_thread = threading.Thread(target=lighthouse_any, args=(url, lh, local), daemon=True)
    lh_thread.start()
    log("Checking %s (Lighthouse runs alongside)..." % url)

    status, final, html = fetch(url)
    if status == 0 or not html:
        return {"url": url, "label": label, "reachable": False, "status": status,
                "measuredAt": datetime.now().isoformat(timespec="minutes"),
                "message": "The site did not answer, so nothing could be measured."}
    home = final
    home_headers = dict(LAST_HEADERS)
    host = urlparse(home).netloc.lower()
    hp = PageParser()
    hp.feed(html)

    log("Reading the sitemap and robots file...")
    has_robots, robots_blocks_all, has_sitemap, sm_pages = sitemap_urls(home, host)
    llms_status, _, llms = fetch(urljoin(home, "/llms.txt"), limit=4096)
    has_llms = llms_status == 200 and len(llms.strip()) > 20 and "<html" not in llms[:500].lower()

    targets = pick_pages(home, sm_pages, hp.links, host)
    log("Reading %d pages, one at a time..." % len(targets))
    pages, all_links = [], {}
    for i, p in enumerate(targets):
        if i == 0:
            s, body = status, html
        else:
            time.sleep(PAUSE)
            s, _, body = fetch(p)
        pp = PageParser()
        if body:
            pp.feed(body)
        nodes, ld_problems = parse_ld(body or "")
        internal = []
        for href in pp.links:
            if re.match(r"^\s*(javascript:|data:text/html)", href, re.I):
                internal.append("__unsafe__")
                continue
            u = urldefrag(urljoin(p, href))[0]
            if u.startswith("http") and same_site(u, host):
                internal.append(u)
                all_links.setdefault(link_key(u), u)
        visible = norm_space(htmllib.unescape(" ".join(pp.texts)))
        main = norm_space(htmllib.unescape(" ".join(pp.main_texts))) or visible
        pages.append({
            "url": p, "path": pathof(p), "status": s, "title": norm_space(pp.title)[:140],
            "desc": pp.meta.get("description", ""), "h1s": [norm_space(h) for h in pp.h1s],
            "canonical": pp.canonical, "ogTitle": pp.meta.get("og:title", ""), "ogImage": pp.meta.get("og:image", ""),
            "viewport": "viewport" in pp.meta, "lang": pp.lang, "imgs": pp.imgs, "imgsNoAlt": pp.imgs_no_alt,
            "nodes": nodes, "ldProblems": ld_problems, "types": sorted(node_types(nodes)),
            "internal": internal, "visible": visible, "main": main,
            "paras": [norm_space(x) for x in pp.paras if len(norm_space(x)) > 20],
            "scripts": pp.scripts, "raw": body or "",
        })

    ok = [p for p in pages if 200 <= p["status"] < 300]
    n = len(ok) or 1
    page_keys = {link_key(p["url"]) for p in pages}
    to_check = [u for k, u in sorted(all_links.items()) if k not in page_keys and not ASSET.search(u)][:MAX_LINKS]
    log("Following %d more links to look for dead ends..." % len(to_check))
    broken_links = []
    for u in to_check:
        time.sleep(PAUSE / 2)
        s = check_status(u)
        if s >= 400 or s == 0:
            broken_links.append({"url": u, "status": s})
    broken_pages = [p["url"] for p in pages if p["status"] >= 400 or p["status"] == 0]

    log("Waiting for Lighthouse to finish...")
    lh_thread.join(timeout=max(5, 300 - (time.time() - started)))
    # Whatever stopped it (an error, or still running at the time limit), a local run on
    # Windows without a score is the known Windows limit and is labelled as one.
    if lh.get("performance") is None:
        if local and os.name == "nt":
            lh["_log"] = (lh.get("_log") or "") + "\n" + (lh.get("_error") or "still running at the time limit")
            lh["_error"], lh["_limit"] = WINDOWS_LIMIT, "windows"
        elif lh_thread.is_alive() and not lh.get("_error"):
            lh["_error"] = "Lighthouse did not finish in time"

    R = Report()
    re_profile = profile == "real-estate"
    lender_profile = profile == "lender"
    paths = lambda ps: [p["path"] for p in ps]

    # ---- 1. Google Lighthouse
    G = "Google's own test (Lighthouse, on a phone)"
    names = {"performance": "Speed", "accessibility": "Accessibility", "bestPractices": "Best practices", "seo": "SEO"}
    for k, nm in names.items():
        v = lh.get(k)
        if v is None:
            R.add(G, nm, "notMeasured", lh.get("_error") or "Lighthouse did not finish")
        else:
            excused = local and k == "seo" and all(f["id"] in ("is-crawlable", "canonical") for f in lh.get("seoFailed", []))
            st = "pass" if v >= BAR[k] else ("local" if excused else "fail")
            R.add(G, nm, st, "%d out of 100 (our bar: %d%s)" % (v, BAR[k], "+" if BAR[k] < 100 else ""))
    for f in lh.get("a11yFailed", []):
        R.add(G, f["title"], "fail", "%s found%s" % (f["count"] or "Some", (": " + "; ".join('"%s"' % w for w in f.get("where", []))) if f.get("where") else ""),
              why="Checked by axe-core inside Lighthouse, the same engine the seed's browser audit uses.")

    # ---- 2. Findable by Google and AI
    G = "Can Google and AI assistants find it"
    R.add(G, "Secure connection (https)", "pass" if home.startswith("https://") else ("local" if local else "fail"),
          "" if home.startswith("https://") else ("Comes with publishing" if local else "Browsers warn visitors away"))
    R.add(G, "Sitemap", "pass" if has_sitemap else "fail", "%d pages listed" % len(sm_pages) if has_sitemap else "No sitemap.xml: Google has to guess what pages exist")
    if robots_blocks_all:
        R.add(G, "Search engines allowed in", "local" if local else "fail", "robots.txt blocks every search engine")
    else:
        R.add(G, "Search engines allowed in", "pass" if has_robots else "warn", "" if has_robots else "No robots.txt")
    bad_title = [p for p in ok if not (10 <= len(p["title"]) <= 65)]
    R.add(G, "Page titles the right length", "pass" if not bad_title else "fail", "%d of %d pages" % (len(ok) - len(bad_title), len(ok)), pages=paths(bad_title))
    bad_desc = [p for p in ok if not (50 <= len(p["desc"]) <= 170)]
    R.add(G, "Search descriptions", "pass" if not bad_desc else "fail", "%d of %d pages have one" % (len(ok) - len(bad_desc), len(ok)), pages=paths(bad_desc))
    bad_h1 = [p for p in ok if len(p["h1s"]) != 1]
    R.add(G, "Exactly one main heading", "pass" if not bad_h1 else "fail", "%d of %d pages" % (len(ok) - len(bad_h1), len(ok)), pages=paths(bad_h1))
    no_canon = [p for p in ok if not p["canonical"]]
    rel_canon = [p for p in ok if p["canonical"] and not re.match(r"^https?://", p["canonical"])]
    wrong_canon = [p for p in ok if re.match(r"^https?://", p["canonical"] or "") and pathof(p["canonical"]).rstrip("/") != p["path"].rstrip("/")]
    if no_canon:
        R.add(G, "Canonical address on every page", "fail", "Missing on %d of %d pages" % (len(no_canon), len(ok)), pages=paths(no_canon))
    elif rel_canon or wrong_canon:
        R.add(G, "Canonical address on every page", "fail", "%d pages point somewhere else or use a partial address" % (len(rel_canon) + len(wrong_canon)), pages=paths(rel_canon + wrong_canon))
    else:
        R.add(G, "Canonical address on every page", "pass")
    no_og = [p for p in ok if not (p["ogTitle"] and p["ogImage"])]
    R.add(G, "Share preview (title + image)", "pass" if not no_og else "fail",
          "Missing on %d of %d pages: a shared link shows no picture" % (len(no_og), len(ok)) if no_og else "", pages=paths(no_og))
    R.add(G, "Works on a phone (viewport)", "pass" if all(p["viewport"] for p in ok) else "fail")
    R.add(G, "Language declared", "pass" if all(p["lang"] for p in ok) else "fail")
    R.add(G, "llms.txt for AI assistants", "pass" if has_llms else "fail", "" if has_llms else "A short file written for AI assistants that says who you are. Cheap, rarely done.")
    imgs = sum(p["imgs"] for p in ok)
    no_alt = sum(p["imgsNoAlt"] for p in ok)
    R.add(G, "Every image described", "pass" if not no_alt else "fail", "%d of %d images have no description" % (no_alt, imgs) if no_alt else "%d images" % imgs)

    # ---- 3. Structured data (validate-schema.mjs)
    G = "Structured data (how AI reads your business)"
    no_ld = [p for p in ok if not p["nodes"]]
    R.add(G, "On every page", "pass" if not no_ld else "fail", "%d of %d pages" % (len(ok) - len(no_ld), len(ok)), pages=paths(no_ld))
    bad_json = [p for p in ok if p["ldProblems"]]
    R.add(G, "Written correctly (valid JSON)", "pass" if not bad_json else "fail", pages=paths(bad_json))
    no_type = [p for p in ok if any(isinstance(nd, dict) and "@type" not in nd for nd in p["nodes"])]
    R.add(G, "Every item says what it is (@type)", "pass" if not no_type else "fail", pages=paths(no_type))
    dangling = [p for p in ok if id_problems(p["nodes"])]
    R.add(G, "Every cross-reference resolves (@id)", "pass" if not dangling else "fail", pages=paths(dangling))
    all_types = set()
    for p in ok:
        all_types.update(p["types"])
    R.add(G, "Says this is a business", "pass" if any(BUSINESS.search(t) for t in all_types) else "fail",
          "Found: %s" % ", ".join(sorted(all_types)[:8]) if all_types else "No business, organization or person markup")
    if re_profile:
        missing = [p for p in ok if not set(RE_TYPES) <= set(p["types"])]
        R.add(G, "Agent, person, brokerage and website on every page", "pass" if not missing else "fail",
              "The seed requires Organization, WebSite, RealEstateAgent and Person on every page", pages=paths(missing))
    faq_pages = [p for p in ok if "FAQPage" in p["types"]]
    R.add(G, "Questions marked up for AI answers (FAQ)", "pass" if faq_pages else "fail",
          "" if faq_pages else "AI assistants answer questions. Sites that mark up their answers are the ones they quote.")
    hidden_q = []
    for p in faq_pages:
        for nd in p["nodes"]:
            for d in walk(nd):
                if d.get("@type") == "Question" and d.get("name") and norm_space(d["name"]) not in p["visible"]:
                    hidden_q.append(p)
                    break
    if faq_pages:
        R.add(G, "FAQ markup matches what is on the page", "pass" if not hidden_q else "fail",
              "" if not hidden_q else "Google penalises questions in the markup that visitors cannot see", pages=paths(hidden_q))

    # ---- 4. Broken
    G = "Broken pages and dead ends"
    total_broken = len(broken_pages) + len(broken_links)
    R.add(G, "Pages that load", "pass" if not broken_pages else "fail", "%d of %d pages failed to load" % (len(broken_pages), len(pages)) if broken_pages else "%d of %d" % (len(pages), len(pages)), pages=[pathof(u) for u in broken_pages])
    R.add(G, "Links that go somewhere", "pass" if not broken_links else "fail",
          "%d of %d links lead nowhere" % (len(broken_links), len(to_check)) if broken_links else "%d links followed" % len(to_check),
          pages=[pathof(b["url"]) for b in broken_links])
    unsafe = [p for p in ok if "__unsafe__" in p["internal"]]
    R.add(G, "No unsafe javascript: links", "pass" if not unsafe else "fail",
          "%d pages have links that run code instead of going to a page" % len(unsafe) if unsafe else "", pages=paths(unsafe))
    home_path = re.sub(r"index\.html?$", "", pathof(home)).rstrip("/") or "/"
    is_home = lambda u: (re.sub(r"index\.html?$", "", pathof(u)).rstrip("/") or "/") == home_path
    no_home = [p for p in ok if not any(is_home(u) for u in p["internal"] if u != "__unsafe__")]
    no_contact = [p for p in ok if not any("contact" in pathof(u).lower() for u in p["internal"] if u != "__unsafe__")]
    few = [p for p in ok if len({link_key(u) for u in p["internal"] if u != "__unsafe__"}) < 5]
    R.add(G, "Every page links home", "pass" if not no_home else "fail", "Missing on %d of %d pages" % (len(no_home), len(ok)) if no_home else "", pages=paths(no_home))
    R.add(G, "Every page links to contact", "pass" if not no_contact else "fail", "Missing on %d of %d pages" % (len(no_contact), len(ok)) if no_contact else "", pages=paths(no_contact))
    R.add(G, "At least 5 internal links per page", "pass" if not few else "fail", "%d pages are near dead ends" % len(few) if few else "", pages=paths(few))

    # ---- 5. Words on the page (launch-check scrub)
    G = "Words on the page"
    filler_hits, bracket_hits = {}, {}
    for p in ok:
        low = re.sub(r"<script\b(?![^>]*application/ld\+json)[^>]*>[\s\S]*?</script>", " ", p["raw"], flags=re.I)
        low = re.sub(r"\splaceholder=([\"'])([\s\S]*?)\1", r" \2 ", low, flags=re.I)
        text = norm_space(htmllib.unescape(re.sub(r"<[^>]+>", " ", low)))
        tl = text.lower()
        for m in FILLER:
            if re.match(r"^[a-z][a-z /]*$", m):
                pat = r"(^|[^a-z0-9])" + re.escape(m) + (r"s?" if len(m) >= 6 else "") + r"([^a-z0-9]|$)"
                hit = re.search(pat, tl)
            else:
                hit = m in tl
            if hit:
                filler_hits.setdefault(m, []).append(p["path"])
        for b in set(BRACKET.findall(text)):
            bracket_hits.setdefault(b, []).append(p["path"])
    R.add(G, "No leftover template text", "pass" if not filler_hits else "fail",
          ", ".join('"%s"' % k for k in list(filler_hits)[:6]), count=len(filler_hits),
          pages=sorted({x for v in filler_hits.values() for x in v}))
    R.add(G, "Nothing left to fill in", "pass" if not bracket_hits else ("todo" if local else "fail"),
          "; ".join(list(bracket_hits)[:8]), count=len(bracket_hits),
          pages=sorted({x for v in bracket_hits.values() for x in v}),
          why="Square-bracket blanks are facts only the owner can supply. The seed will not launch with one left.")

    def scan(patterns, texts_by_page):
        hits = []
        for pat, why in patterns:
            for path, t in texts_by_page:
                for m in re.finditer(pat, t, re.I):
                    hits.append({"phrase": m.group(0), "why": why, "page": path})
        return hits

    mains = [(p["path"], p["main"]) for p in ok]
    claims = scan(CLAIMS, mains)
    R.add(G, "No claims you would have to prove (FTC)", "pass" if not claims else "fail",
          "; ".join('"%s" (%s)' % (h["phrase"], h["why"]) for h in claims[:5]), count=len(claims), pages=[h["page"] for h in claims])
    slop = scan(SLOP, mains)
    R.add(G, "Sounds like a person, not a robot", "pass" if not slop else "warn",
          "; ".join('"%s"' % h["phrase"] for h in slop[:6]), count=len(slop), pages=[h["page"] for h in slop],
          why="Em-dashes and stock AI phrases are the first thing readers notice.")
    dupes = []
    grams = {}
    for p in ok:
        w = re.findall(r"[a-z']+", p["main"].lower())
        grams[p["path"]] = {" ".join(w[i:i + 3]) for i in range(len(w) - 2)}
    keys = list(grams)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = grams[keys[i]], grams[keys[j]]
            if a and b:
                sim = len(a & b) / len(a | b)
                if sim >= 0.55:
                    dupes.append("%s and %s (%d%% the same)" % (keys[i], keys[j], round(sim * 100)))
    R.add(G, "No near-duplicate pages", "pass" if not dupes else "fail", "; ".join(dupes[:4]), count=len(dupes),
          why="Two pages saying the same thing compete with each other in Google.")

    # ---- 6. Real estate rules
    if re_profile:
        G = "Real estate rules (Fair Housing and licensing)"
        fh = scan(FH_FAIL, mains)
        R.add(G, "Fair Housing language", "pass" if not fh else "fail",
              "; ".join('"%s": %s' % (h["phrase"], h["why"]) for h in fh[:5]), count=len(fh), pages=[h["page"] for h in fh],
              why="Describe the property, never the people.")
        fhw = scan(FH_WARN, mains)
        R.add(G, "Phrases that can read as steering", "pass" if not fhw else "warn",
              "; ".join('"%s": %s' % (h["phrase"], h["why"]) for h in fhw[:5]), count=len(fhw), pages=[h["page"] for h in fhw])
        com = scan(COMMISSION, mains)
        R.add(G, "Commission wording", "pass" if not com else "warn",
              "; ".join('"%s": %s' % (h["phrase"], h["why"]) for h in com[:4]), count=len(com), pages=[h["page"] for h in com])
        # A [Your license number] blank is not a disclosure, though the seed's
        # pattern would count it ("license n..."). Blanks are stripped first and
        # reported as "to fill in", never as passed.
        bare = lambda p: BRACKET.sub(" ", p["visible"])
        # Tighter than the seed's pattern, which accepts "License #" plus any letter:
        # a real license number has digits in it (CA DRE: 8 of them).
        lic = [p for p in ok if not re.search(r"\b(DRE|BRE|License|Lic\.?)\s*(#|No\.?|number)?\s*:?\s*[A-Z]{0,4}[- ]?\d{4,}", bare(p), re.I)]
        brk = [p for p in ok if not re.search(r"broker", bare(p), re.I)]
        eho = [p for p in ok if not re.search(r"equal housing", p["visible"], re.I)]
        blank = lambda ps, word: ps and all(re.search(r"\[[^\]]*" + word, p["visible"], re.I) for p in ps)
        R.add(G, "License number on every page", "pass" if not lic else ("todo" if blank(lic, "licen") else "fail"),
              "On %d of %d pages" % (len(ok) - len(lic), len(ok)) + ("; the blank for it is there, waiting for your number" if blank(lic, "licen") else ""), pages=paths(lic))
        R.add(G, "Brokerage named on every page", "pass" if not brk else ("todo" if blank(brk, "broker") else "fail"),
              "On %d of %d pages" % (len(ok) - len(brk), len(ok)) + ("; the blank for it is there, waiting for your brokerage" if blank(brk, "broker") else ""), pages=paths(brk))
        R.add(G, "Equal Housing Opportunity on every page", "pass" if not eho else "fail", "On %d of %d pages" % (len(ok) - len(eho), len(ok)), pages=paths(eho),
              why="The words must be on the page. A logo image alone is invisible to screen readers and to the seed's gate.")

    # ---- 6b. Lender rules
    if lender_profile:
        G = "Lending rules (fair lending and NMLS)"
        fh = scan(FH_FAIL + FAIR_LENDING, mains)
        R.add(G, "Fair lending language", "pass" if not fh else "fail",
              "; ".join('"%s": %s' % (h["phrase"], h["why"]) for h in fh[:5]), count=len(fh), pages=[h["page"] for h in fh],
              why="The Fair Housing Act and ECOA apply to lending ads too: describe loans, never who should apply.")
        ln = scan(LENDING, mains)
        R.add(G, "Lending claims", "pass" if not ln else "fail",
              "; ".join('"%s": %s' % (h["phrase"], h["why"]) for h in ln[:5]), count=len(ln), pages=[h["page"] for h in ln])
        bare = lambda p: BRACKET.sub(" ", p["visible"])
        blank = lambda ps, word: ps and all(re.search(r"\[[^\]]*" + word, p["visible"], re.I) for p in ps)
        nm = [p for p in ok if not re.search(r"\bNMLS\s*(#|ID|No\.?)?\s*:?\s*\d{3,}", bare(p), re.I)]
        co = [p for p in ok if len(re.findall(r"\bNMLS\s*(?:#|ID|No\.?)?\s*:?\s*\d{3,}", bare(p), re.I)) < 2]
        ehl = [p for p in ok if not re.search(r"equal housing (lender|opportunity)", p["visible"], re.I)]
        R.add(G, "NMLS number on every page", "pass" if not nm else ("todo" if blank(nm, "nmls") else "fail"),
              "On %d of %d pages" % (len(ok) - len(nm), len(ok)) + ("; the blank for it is there, waiting for your number" if blank(nm, "nmls") else ""), pages=paths(nm),
              why="Federal and state rules require the NMLS number on mortgage advertising, including websites.")
        R.add(G, "Company NMLS number on every page", "pass" if not co else ("todo" if blank(co, "company nmls") else "fail"),
              "On %d of %d pages" % (len(ok) - len(co), len(ok)) + ("; the blank for it is there, waiting for the number" if blank(co, "company nmls") else ""), pages=paths(co))
        R.add(G, "Equal Housing Lender on every page", "pass" if not ehl else "fail", "On %d of %d pages" % (len(ok) - len(ehl), len(ok)), pages=paths(ehl))

    # ---- 7. Privacy
    G = "Privacy"
    found_trackers = set()
    for p in ok:
        blob = " ".join(p["scripts"]) + " " + p["raw"][:400000]
        for name, sig, _ in TRACKERS:
            if re.search(sig, blob, re.I):
                found_trackers.add(name)
    # Follow the site's own privacy link first; guess the usual addresses after.
    priv_links = sorted({u for p in ok for u in p["internal"] if u != "__unsafe__" and "privacy" in pathof(u).lower()})
    priv_status, priv = 0, ""
    for cand in priv_links[:2] + [urljoin(home, "/privacy")]:
        priv_status, _, priv = fetch(cand)
        if priv_status == 200:
            break
    if priv_status != 200:
        for alt in ("/privacy-policy", "/privacy-policy/", "/legal/privacy"):
            priv_status, _, priv = fetch(urljoin(home, alt))
            if priv_status == 200:
                break
    has_priv = priv_status == 200 and len(priv) > 500
    R.add(G, "Privacy policy page", "pass" if has_priv else "fail", "" if has_priv else "Required in California for any site that collects names or emails")
    if found_trackers:
        ptext = norm_space(htmllib.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style|noscript)[\s\S]*?</\1>", " ", priv, flags=re.I))))
        sentences = re.split(r"(?<=[.!?])\s+", ptext)
        undisclosed = [name for name, _, vend in TRACKERS if name in found_trackers and not any(re.search(vend, s, re.I) and TRACK_WORDS.search(s) for s in sentences)]
        R.add(G, "Tracking tools disclosed", "pass" if not undisclosed else "fail",
              "Uses %s%s" % (", ".join(sorted(found_trackers)), "; not mentioned in the privacy policy: " + ", ".join(undisclosed) if undisclosed else ""))

    # ---- 7b. The software behind the site (security.py, shared byte-identical with the
    # website-health skill). Scored rows only for versions the site states. What the site is built
    # on is an unscored row; red flags (PHP, attacked flaws, legal and visibility problems) are returned
    # as "redFlags" and the dashboard shows them in a red "Red Flags" panel (owner decision 2026-10-23). Each fix leads the explanation.
    G = "Security of the software behind the site"
    sec_checks, platform = security.assess(home_headers, ok)
    R.add(G, "What your site is built on", "notMeasured", platform.get("line", ""),
          why="Read from the page and its headers. Never part of the grade.")
    for nm, st, detail, why, fix in sec_checks:
        R.add(G, nm, st, detail, why=("Fix: %s %s" % (fix, why)) if fix else why)

    # ---- 8. Not measured, said out loud
    G = "Not measured here"
    if platform.get("php") and not platform.get("phpVersion"):
        R.add(G, "Your PHP version", "notMeasured",
              "The site does not show it, so whether it has the 21 Oct 2026 PHP security fix is for your host to confirm.")
    if "Elementor Pro" in (platform.get("builders") or []) and not any(c[0].endswith("Elementor Pro") for c in sec_checks):
        R.add(G, "Elementor Pro's version", "notMeasured",
              "The site hides it, so we could not tell whether it has the fix for CVE-2026-32475 (version 4.2.2 or newer).")
    if platform.get("platform") == "WordPress":
        R.add(G, "Every WordPress plugin's own updates", "notMeasured",
              "WordPress plugins get hundreds of new security flaws a week; only the critical, attacked ones on our "
              "list (updated %s) were checked. Keep every plugin updated." % security.LIST_UPDATED)
    for nm, why in (("Dark-mode contrast", "needs a scripted browser; the seed runs it before launch"),
                    ("Overlapping text", "needs a scripted browser"),
                    ("Keyboard focus rings", "needs a scripted browser"),
                    ("Real visitors' speed", "comes from real traffic after launch, not a test")):
        R.add(G, nm, "notMeasured", why)

    # ---- scores
    groups = []
    for c in R.checks:
        if c["group"] not in groups:
            groups.append(c["group"])
    weight = {"pass": 1.0, "local": 1.0, "todo": 1.0, "warn": 0.5, "fail": 0.0}
    categories = []
    for g in groups:
        if g == "Not measured here":
            continue
        cs = [c for c in R.checks if c["group"] == g and c["status"] in weight]
        if g.startswith("Google's own test"):
            vals = [lh.get(k) for k in names if lh.get(k) is not None]
            score = round(sum(vals) / len(vals)) if vals else None
        else:
            score = round(100 * sum(weight[c["status"]] for c in cs) / len(cs)) if cs else None
        counts = {s: sum(1 for c in R.checks if c["group"] == g and c["status"] == s) for s in ("pass", "warn", "fail", "local", "todo", "notMeasured")}
        categories.append({"name": g, "score": score, "counts": counts})
    vals = [c["score"] for c in categories if c["score"] is not None]
    overall = round(sum(vals) / len(vals)) if vals else None
    below_bar = [k for k in names if lh.get(k) is not None and lh.get(k) < BAR[k]
                 and not (local and k == "seo" and all(f["id"] in ("is-crawlable", "canonical") for f in lh.get("seoFailed", [])))]

    totals = {s: sum(1 for c in R.checks if c["status"] == s) for s in ("pass", "warn", "fail", "local", "todo", "notMeasured")}
    return {
        "url": home, "label": label, "profile": profile, "local": local, "reachable": True,
        "measuredAt": datetime.now().isoformat(timespec="minutes"), "seconds": round(time.time() - started),
        "overall": overall, "letter": cap_letter(letter(overall), below_bar), "belowBar": below_bar, "categories": categories, "checks": R.checks, "totals": totals,
        "lighthouse": {k: lh.get(k) for k in ("performance", "accessibility", "bestPractices", "seo", "lcp", "cls")},
        "lighthouseSource": lh.get("_source"), "screenshot": lh.get("screenshot"), "lighthouseLog": lh.get("_log"), "lighthouseError": lh.get("_error") if lh.get("performance") is None else None,
        "lighthouseLimit": lh.get("_limit"),
        "bar": BAR, "platform": platform, "redFlags": security.red_flags(R.checks, platform),
        "facts": {"pagesChecked": len(pages), "pagesOk": len(ok), "linksChecked": len(to_check),
                  "pagesWithSchema": len(ok) - len(no_ld), "brokenPages": broken_pages, "brokenLinks": broken_links[:20],
                  "sitemapPages": len(sm_pages), "trackers": sorted(found_trackers)},
        "pages": [{"path": p["path"], "status": p["status"], "title": p["title"], "types": p["types"]} for p in pages],
    }


def cap_letter(l, below_bar):
    """Below a Lighthouse floor, the seed will not launch it: no A, whatever the average."""
    return "B" if below_bar and l == "A" else l


def letter(score):
    if score is None:
        return "?"
    for cut, l in ((90, "A"), (80, "B"), (70, "C"), (60, "D")):
        if score >= cut:
            return l
    return "F"


def main():
    ap = argparse.ArgumentParser(description="Audit a website the way the seed's launch gate does.")
    ap.add_argument("url")
    ap.add_argument("--label", default="Your website")
    ap.add_argument("--profile", default="general", choices=["general", "real-estate", "lender"])
    ap.add_argument("--local", action="store_true", help="the preview site on this computer")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    report = audit(a.url.strip(), a.label, a.profile, a.local)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        tmp = a.out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
        os.replace(tmp, a.out)  # never leave a half-written file for the dashboard to read
    if not report.get("reachable"):
        print(report["message"])
        return 2
    t = report["totals"]
    print("\n%s  %s" % (report["label"], report["url"]))
    print("Overall: %s (%s)   %d passed, %d to fix, %d warnings, %d not measured"
          % (report["overall"], report["letter"], t["pass"], t["fail"], t["warn"], t["notMeasured"]))
    for c in report["categories"]:
        print("  %-52s %s" % (c["name"], "not measured" if c["score"] is None else c["score"]))
    if report["lighthouseError"]:
        print("  (Lighthouse: %s)" % report["lighthouseError"])
    for c in report["checks"]:
        if c["status"] in ("fail", "todo"):
            print("  - [%s] %s: %s" % (c["status"], c["name"], c["detail"][:110]))
    if a.out:
        print("\nSaved to %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
