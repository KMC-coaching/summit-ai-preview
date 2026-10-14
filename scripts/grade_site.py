#!/usr/bin/env python3
"""
Grade a live website the way search engines and AI assistants see it.

    python3 scripts/grade_site.py https://example.com [--label "Your site"] [--out app/data/grade.json]

Lifted from the realtor-site-seed `audit:compare` battery and rebuilt for a
machine with nothing on it: standard-library Python only, no Node, no local
Chrome. Lighthouse still runs, but on Google's side, through the free
PageSpeed Insights service.

WHAT IT MEASURES, AND HOW HONESTLY
  Speed, Accessibility, Best practices, SEO   Lighthouse (mobile), via PageSpeed
  Structured data on every page                 counted, page by page
  Pages that are broken                        status codes of every page + link
  Search basics                                titles, descriptions, one H1, canonical
  AI-readiness                                 business schema, FAQ schema, llms.txt
  Images a screen reader cannot describe       <img> with no alt

  Anything that could not be measured is reported as not measured. It is never
  filled with a guess, because the person reading this will act on it.

POLITE BY DESIGN
  This is somebody's live website. Read-only, one request at a time, a pause
  between pages, at most MAX_PAGES pages and MAX_LINKS link checks. The same
  requests any visitor's browser makes.

Runs on the Python that ships with macOS (3.9): no newer syntax.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import subprocess
import sys
import threading
import time
from datetime import datetime
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urldefrag, quote
from urllib.request import Request, urlopen

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36 SummitSiteGrader"
MAX_PAGES = 25
MAX_LINKS = 60
PAUSE = 0.35
TIMEOUT = 20

# The bar a site built in BOSS has to clear before it is allowed to launch.
# These are the launch-gate floors in realtor-site-seed/scripts/audit-compare.mjs,
# not marketing numbers. If the gate changes, change these with it.
BAR = {
    "performance": 85,
    "accessibility": 100,
    "bestPractices": 95,
    "seo": 100,
    "schemaCoverage": 100,
    "brokenPages": 0,
}


# --------------------------------------------------------------------- fetching

_ctx = ssl.create_default_context()


def fetch(url: str, method: str = "GET", limit: int = 3_000_000):
    """Return (status, final_url, body_text). status 0 means it never answered."""
    req = Request(url, method=method, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urlopen(req, timeout=TIMEOUT, context=_ctx) as r:
            body = r.read(limit) if method == "GET" else b""
            return r.status, r.geturl(), body.decode("utf-8", "replace")
    except HTTPError as e:
        return e.code, url, ""
    except (URLError, ssl.SSLError, OSError) as e:
        # Some older Pythons cannot verify certain certificates. curl ships on
        # every Mac and on Windows 10+, and uses the system's own trust store.
        if "CERTIFICATE" in str(e).upper() or isinstance(e, ssl.SSLError):
            return _curl(url, method)
        return 0, url, ""


def _curl(url: str, method: str):
    args = ["curl", "-sL", "--max-time", str(TIMEOUT), "-A", UA, "-w", "\n__STATUS__%{http_code} %{url_effective}"]
    if method == "HEAD":
        args.append("-I")
    try:
        out = subprocess.run(args + [url], capture_output=True, text=True, timeout=TIMEOUT + 5).stdout
    except Exception:
        return 0, url, ""
    m = re.search(r"\n__STATUS__(\d+) (\S*)\s*$", out)
    if not m:
        return 0, url, ""
    return int(m.group(1)), m.group(2) or url, out[: m.start()]


def check_status(url: str) -> int:
    status, _, _ = fetch(url, method="HEAD")
    # Plenty of servers refuse HEAD. Only a GET's answer counts as broken.
    if status in (0, 403, 405, 501) or status >= 500:
        status, _, _ = fetch(url, limit=2048)
    return status


# ---------------------------------------------------------------------- parsing

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self.meta = {}
        self.links = []
        self.canonical = False
        self.h1 = 0
        self.imgs = 0
        self.imgs_no_alt = 0
        self.ld_blocks = []
        self._in_ld = False
        self._ld_buf = []
        self.lang = ""
        self.text_chars = 0
        self._skip = 0

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
            self.canonical = True
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "h1":
            self.h1 += 1
        elif tag == "img":
            self.imgs += 1
            if "alt" not in a:
                self.imgs_no_alt += 1
        elif tag == "script":
            if "ld+json" in a.get("type", "").lower():
                self._in_ld = True
                self._ld_buf = []
            else:
                self._skip += 1
        elif tag == "style":
            self._skip += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            if self._in_ld:
                self._in_ld = False
                self.ld_blocks.append("".join(self._ld_buf))
            elif self._skip:
                self._skip -= 1
        elif tag == "style" and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._in_ld:
            self._ld_buf.append(data)
        elif not self._skip:
            self.text_chars += len(data.strip())


def schema_types(blocks):
    types = set()

    def walk(node):
        if isinstance(node, list):
            for n in node:
                walk(n)
        elif isinstance(node, dict):
            t = node.get("@type")
            if isinstance(t, str):
                types.add(t)
            elif isinstance(t, list):
                types.update(x for x in t if isinstance(x, str))
            for k in ("@graph", "mainEntity", "itemListElement"):
                if k in node:
                    walk(node[k])

    for raw in blocks:
        try:
            walk(json.loads(raw.strip()))
        except Exception:
            pass  # malformed JSON-LD is invisible to a crawler, so it counts as none
    return sorted(types)


BUSINESS = re.compile(
    r"^(LocalBusiness|Organization|Corporation|Person)$|"
    r"(Business|Agent|Store|Shop|Service|Practice|Office|Clinic|Agency|Dentist|Physician|Attorney|Restaurant)$",
    re.I,
)


# ---------------------------------------------------------------- page discovery

def same_site(url: str, host: str) -> bool:
    h = urlparse(url).netloc.lower()
    return h == host or h == "www." + host or "www." + h == host


def sitemap_urls(base: str, host: str):
    """Pages listed in the sitemap(s), following one level of sitemap index."""
    candidates = []
    status, _, robots = fetch(urljoin(base, "/robots.txt"))
    has_robots = status == 200 and "user-agent" in robots.lower()
    if has_robots:
        candidates += re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots)
    candidates += [urljoin(base, "/sitemap.xml"), urljoin(base, "/sitemap_index.xml")]

    found_map = False
    pages = []
    seen_maps = set()
    queue = list(dict.fromkeys(candidates))
    while queue and len(seen_maps) < 8 and len(pages) < 500:
        sm = queue.pop(0)
        if sm in seen_maps:
            continue
        seen_maps.add(sm)
        s, _, xml = fetch(sm)
        if s != 200 or "<loc>" not in xml:
            continue
        found_map = True
        locs = [l.strip() for l in re.findall(r"<loc>\s*([^<]+?)\s*</loc>", xml)]
        if "<sitemapindex" in xml:
            queue += [l for l in locs if l not in seen_maps]
        else:
            pages += [l for l in locs if same_site(l, host)]
    return has_robots, found_map, list(dict.fromkeys(pages))


def pick_pages(home: str, sitemap_pages, home_links, host: str):
    """Home first, then a spread across the site rather than the first N of one section."""
    pool = sitemap_pages or []
    if not pool:
        for href in home_links:
            u = urldefrag(urljoin(home, href))[0]
            if u.startswith("http") and same_site(u, host) and not re.search(
                r"\.(jpg|jpeg|png|gif|webp|svg|pdf|zip|mp4|mp3)$|^mailto:|^tel:", u, re.I
            ):
                pool.append(u)
        pool = list(dict.fromkeys(pool))
    pool = [p for p in pool if p.rstrip("/") != home.rstrip("/")]
    if len(pool) > MAX_PAGES - 1:
        step = len(pool) / (MAX_PAGES - 1)
        pool = [pool[int(i * step)] for i in range(MAX_PAGES - 1)]
    return [home] + pool


# ----------------------------------------------------------------- PageSpeed

def pagespeed(url: str, result: dict):
    """Lighthouse on Google's servers. Fills `result` in place; leaves it empty on failure."""
    api = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=" + quote(url, safe="")
    for c in ("performance", "accessibility", "best-practices", "seo"):
        api += "&category=" + c
    api += "&strategy=mobile"
    key = os.environ.get("PAGESPEED_API_KEY", "").strip()
    if key:
        api += "&key=" + key
    for attempt in range(2):
        try:
            req = Request(api, headers={"User-Agent": UA})
            with urlopen(req, timeout=90, context=_ctx) as r:
                data = json.loads(r.read().decode("utf-8"))
            _read_lighthouse(data.get("lighthouseResult", {}), result)
            result["_source"] = "Lighthouse, run by Google PageSpeed"
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


LIGHTHOUSE = "lighthouse@12.8.2"


def find_node():
    import shutil
    home = os.path.join(os.path.expanduser("~"), ".summit-preview", "node")
    for cand in (os.path.join(home, "bin", "node"), os.path.join(home, "node.exe"), shutil.which("node")):
        if cand and os.path.exists(cand):
            return cand
    return None


def lighthouse_local(url: str, result: dict) -> bool:
    """Lighthouse on this computer, in headless Chrome. True if it produced scores."""
    node = find_node()
    if not node:
        result["_error"] = "Node is not installed here"
        return False
    bindir = os.path.dirname(node)
    npx = os.path.join(bindir, "npx.cmd" if os.name == "nt" else "npx")
    if not os.path.exists(npx):
        result["_error"] = "npx is missing next to node"
        return False
    import tempfile
    out = os.path.join(tempfile.mkdtemp(), "lh.json")
    env = dict(os.environ, PATH=bindir + os.pathsep + os.environ.get("PATH", ""))
    args = [npx, "--yes", LIGHTHOUSE, url, "--quiet",
            "--chrome-flags=--headless=new --no-sandbox",
            "--only-categories=performance,accessibility,best-practices,seo",
            "--output=json", "--output-path=" + out]
    try:
        subprocess.run(args, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=240)
        with open(out, encoding="utf-8") as f:
            lh = json.load(f)
    except Exception as e:
        result["_error"] = "Lighthouse could not run here (%s). Is Google Chrome installed?" % type(e).__name__
        return False
    _read_lighthouse(lh, result)
    result["_source"] = "Lighthouse, run on this computer"
    return result.get("performance") is not None


def _read_lighthouse(lh: dict, result: dict):
    cats = lh.get("categories", {})

    def g(k):
        v = (cats.get(k) or {}).get("score")
        return None if v is None else round(v * 100)

    audits = lh.get("audits", {})
    result.update({
        "performance": g("performance"),
        "accessibility": g("accessibility"),
        "bestPractices": g("best-practices"),
        "seo": g("seo"),
        "lcp": (audits.get("largest-contentful-paint") or {}).get("displayValue"),
        "cls": (audits.get("cumulative-layout-shift") or {}).get("displayValue"),
    })


def lighthouse_any(url: str, result: dict):
    """Local first: Google's free service turns anonymous callers away under load."""
    if os.environ.get("PAGESPEED_API_KEY"):
        pagespeed(url, result)
        if result.get("performance") is not None:
            return
    if lighthouse_local(url, result):
        result.pop("_error", None)
        return
    local_err = result.get("_error")
    pagespeed(url, result)
    if result.get("performance") is None and local_err:
        result["_error"] = "%s; %s" % (local_err, result.get("_error", ""))


# ------------------------------------------------------------------- scoring

def pct(n, d):
    return None if not d else round(100 * n / d)


def avg(values):
    vals = [v for v in values if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals)) if vals else None


def letter(score):
    if score is None:
        return "?"
    for cut, l in ((90, "A"), (80, "B"), (70, "C"), (60, "D")):
        if score >= cut:
            return l
    return "F"


def grade(url: str, label: str) -> dict:
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    started = time.time()
    log = lambda m: print("  " + m, file=sys.stderr, flush=True)

    psi = {}
    psi_thread = threading.Thread(target=lighthouse_any, args=(url, psi), daemon=True)
    psi_thread.start()
    log("Running Google Lighthouse for speed and accessibility (a minute or two)...")

    status, final, html = fetch(url)
    if status == 0 or not html:
        return {
            "url": url, "label": label, "reachable": False, "status": status,
            "measuredAt": datetime.now().isoformat(timespec="minutes"),
            "message": "The site did not answer, so nothing could be measured.",
        }
    home = final
    host = urlparse(home).netloc.lower()
    home_parser = PageParser()
    home_parser.feed(html)

    log("Reading the sitemap...")
    has_robots, has_sitemap, sm_pages = sitemap_urls(home, host)
    llms_status, _, llms = fetch(urljoin(home, "/llms.txt"), limit=4096)
    has_llms = llms_status == 200 and len(llms.strip()) > 20 and "<html" not in llms[:500].lower()

    targets = pick_pages(home, sm_pages, home_parser.links, host)
    log("Checking %d pages, one at a time..." % len(targets))

    pages = []
    all_links = set()
    for i, p in enumerate(targets):
        if i == 0:
            s, body = status, html
        else:
            time.sleep(PAUSE)
            s, _, body = fetch(p)
        pp = PageParser()
        if body:
            pp.feed(body)
        types = schema_types(pp.ld_blocks)
        for href in pp.links:
            u = urldefrag(urljoin(p, href))[0]
            if u.startswith("http") and same_site(u, host):
                all_links.add(u)
        pages.append({
            "url": p,
            "status": s,
            "title": pp.title.strip()[:120],
            "titleLen": len(pp.title.strip()),
            "descLen": len(pp.meta.get("description", "")),
            "h1": pp.h1,
            "canonical": pp.canonical,
            "schema": types,
            "business": any(BUSINESS.search(t) for t in types),
            "faq": any(t in ("FAQPage", "QAPage") for t in types),
            "og": bool(pp.meta.get("og:title")) and bool(pp.meta.get("og:image")),
            "imgs": pp.imgs,
            "imgsNoAlt": pp.imgs_no_alt,
            "viewport": "viewport" in pp.meta,
            "lang": bool(pp.lang),
            "thin": 0 < pp.text_chars < 900,
        })

    ok = [p for p in pages if 200 <= p["status"] < 300]
    broken_pages = [p["url"] for p in pages if p["status"] >= 400 or p["status"] == 0]

    page_urls = {p["url"].rstrip("/") for p in pages}
    to_check = [u for u in sorted(all_links) if u.rstrip("/") not in page_urls
                and not re.search(r"\.(jpg|jpeg|png|gif|webp|svg|pdf|zip|mp4)$", u, re.I)][:MAX_LINKS]
    log("Following %d links to look for dead ends..." % len(to_check))
    broken_links = []
    for u in to_check:
        time.sleep(PAUSE / 2)
        s = check_status(u)
        if s >= 400 or s == 0:
            broken_links.append({"url": u, "status": s})

    n = len(ok) or 1
    with_schema = sum(1 for p in ok if p["schema"])
    imgs = sum(p["imgs"] for p in ok)
    no_alt = sum(p["imgsNoAlt"] for p in ok)
    good_title = sum(1 for p in ok if 10 <= p["titleLen"] <= 65)
    good_desc = sum(1 for p in ok if 50 <= p["descLen"] <= 170)
    one_h1 = sum(1 for p in ok if p["h1"] == 1)
    canon = sum(1 for p in ok if p["canonical"])
    og = sum(1 for p in ok if p["og"])
    business = any(p["business"] for p in ok)
    faq = any(p["faq"] for p in ok)
    https = home.startswith("https://")

    psi_thread.join(timeout=max(5, 300 - (time.time() - started)))

    schema_coverage = pct(with_schema, len(ok))
    search_basics = avg([
        pct(good_title, n), pct(good_desc, n), pct(one_h1, n), pct(canon, n),
        100 if has_sitemap else 0, 100 if has_robots else 0, 100 if https else 0,
    ])
    ai_ready = avg([
        schema_coverage or 0,
        100 if business else 0,
        100 if faq else 0,
        100 if has_llms else 0,
        pct(og, n),
    ])
    total_checked = len(pages) + len(to_check)
    health = None if not total_checked else max(0, 100 - round(
        100 * (len(broken_pages) + len(broken_links)) / total_checked * 4))

    categories = [
        {"key": "speed", "name": "Speed on a phone", "score": psi.get("performance"),
         "bar": BAR["performance"], "source": "Google Lighthouse"},
        {"key": "accessibility", "name": "Accessibility", "score": psi.get("accessibility"),
         "bar": BAR["accessibility"], "source": "Google Lighthouse"},
        {"key": "seo", "name": "Google's SEO check", "score": psi.get("seo"),
         "bar": BAR["seo"], "source": "Google Lighthouse"},
        {"key": "basics", "name": "Search basics", "score": search_basics, "bar": 100,
         "source": "titles, descriptions, headings, sitemap"},
        {"key": "ai", "name": "Ready for AI assistants", "score": ai_ready, "bar": 100,
         "source": "structured data, FAQ, llms.txt"},
        {"key": "health", "name": "No broken pages", "score": health, "bar": 100,
         "source": "every page and link checked"},
    ]
    overall = avg([c["score"] for c in categories])

    findings = []

    def add(sev, text, detail=""):
        findings.append({"severity": sev, "text": text, "detail": detail})

    if schema_coverage is not None and schema_coverage < 100:
        add("high", "Structured data on %d of %d pages checked." % (with_schema, len(ok)),
            "This is the label that tells Google and AI assistants what a page is about. "
            "Pages without it are much harder for them to recommend.")
    if not business:
        add("high", "No page tells search engines this is a business.",
            "There is no business or organization schema, so an AI assistant cannot connect "
            "this site to a name, a location, or a service.")
    if not faq:
        add("medium", "No question-and-answer markup anywhere.",
            "AI assistants answer questions. Sites that mark up their answers are the ones they quote.")
    if not has_llms:
        add("medium", "No llms.txt file.",
            "A short file written for AI assistants that says who you are and what you do. Newer, cheap to add, rarely done.")
    if broken_pages or broken_links:
        add("high", "%d broken page%s or link%s found." % (
            len(broken_pages) + len(broken_links),
            "" if len(broken_pages) + len(broken_links) == 1 else "s",
            "" if len(broken_pages) + len(broken_links) == 1 else "s"),
            "Every dead end is a visitor who leaves and a signal to Google that the site is not looked after.")
    if imgs and no_alt:
        add("medium", "%d of %d images have no description." % (no_alt, imgs),
            "Screen readers cannot describe them to someone who cannot see them, and search engines cannot read them either.")
    if isinstance(psi.get("performance"), int) and psi["performance"] < BAR["performance"]:
        add("high" if psi["performance"] < 50 else "medium",
            "Speed on a phone scores %d out of 100." % psi["performance"],
            "Most visitors are on a phone. Slow pages lose them before they read a word, and Google ranks slow pages lower.")
    if isinstance(psi.get("accessibility"), int) and psi["accessibility"] < BAR["accessibility"]:
        add("medium", "Accessibility scores %d out of 100." % psi["accessibility"],
            "Contrast, labels, and structure that let everyone use the site. It also counts toward ranking.")
    if pct(good_desc, n) is not None and pct(good_desc, n) < 80:
        add("medium", "%d of %d pages are missing a proper search description." % (n - good_desc, n),
            "That is the two-line summary under your link in Google. Without one, Google guesses.")
    if pct(one_h1, n) is not None and pct(one_h1, n) < 80:
        add("low", "%d of %d pages do not have exactly one main heading." % (n - one_h1, n),
            "The main heading is how a search engine knows what the page is about.")
    if not has_sitemap:
        add("medium", "No sitemap found.", "The list of pages Google uses to find everything on the site.")
    if not https:
        add("high", "The site is not secure (no https).", "Browsers warn visitors away from it.")

    order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: order[f["severity"]])

    return {
        "url": home,
        "label": label,
        "reachable": True,
        "measuredAt": datetime.now().isoformat(timespec="minutes"),
        "seconds": round(time.time() - started),
        "overall": overall,
        "letter": letter(overall),
        "categories": categories,
        "lighthouse": {k: psi.get(k) for k in ("performance", "accessibility", "bestPractices", "seo", "lcp", "cls")},
        "lighthouseError": psi.get("_error") if psi.get("performance") is None else None,
        "lighthouseSource": psi.get("_source"),
        "facts": {
            "pagesChecked": len(pages),
            "pagesOk": len(ok),
            "pagesWithSchema": with_schema,
            "schemaCoverage": schema_coverage,
            "businessSchema": business,
            "faqSchema": faq,
            "llmsTxt": has_llms,
            "sitemap": has_sitemap,
            "sitemapPages": len(sm_pages),
            "robots": has_robots,
            "https": https,
            "images": imgs,
            "imagesNoAlt": no_alt,
            "linksChecked": len(to_check),
            "brokenPages": broken_pages,
            "brokenLinks": broken_links[:20],
        },
        "bar": BAR,
        "findings": findings,
        "pages": pages,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("url")
    ap.add_argument("--label", default="Your website")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    report = grade(a.url.strip(), a.label)
    text = json.dumps(report, indent=2)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
    if not report.get("reachable"):
        print(report["message"])
        return 2
    print("\n%s  %s" % (report["label"], report["url"]))
    print("Overall: %s (%s)" % (report["overall"], report["letter"]))
    for c in report["categories"]:
        print("  %-26s %s" % (c["name"], "not measured" if c["score"] is None else c["score"]))
    if report["lighthouseError"]:
        print("  (Google's speed test: %s)" % report["lighthouseError"])
    for f in report["findings"][:6]:
        print("  - [%s] %s" % (f["severity"], f["text"]))
    if a.out:
        print("\nSaved to %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
