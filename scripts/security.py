"""
The software behind the site: what it is built on, and whether that software has a critical,
published security flaw. Read from the outside only: response headers, the generator tag, and the
addresses of the files a page actually loads. Nothing is probed, tried or attacked, and nothing
here touches the network.

    detect(html, headers)         -> the "What your site is built on" box (never part of the grade)
    assess(home_headers, pages)   -> scored checks, only for facts the site itself states

ONE MODULE, TWO ORIGINS (merged 2026-10-23)
  Krista's platform_detect.py (kits, 2026-10-23): read only the files a page loads, never words in
  its text; a version the site does not show is "not measured", never safe; a fixed version is
  still "ask the host to confirm"; three plain questions for the host; the box is not graded.
  Jerry's security.py (engine, 2026-10-23): a dated, sourced advisory list; builders and hosted
  platforms; a PHP version the server states and that is unpatched or past end of life fails;
  Elementor Pro's attacked CVE-2026-32475.

THE ADVISORY LIST BELOW IS DATED AND SOURCED, ON PURPOSE
  A flaw goes on the list only when it is critical AND either being attacked or affecting a large
  share of sites, and only from a primary source (the software's own security team, CISA, or the
  plugin security firm that disclosed it). WordPress plugins alone get 200 to 300 new flaws a week
  (Wordfence, 2026), so this is not, and never claims to be, a full scan: the report says so out
  loud. To add next week's flaw: one entry, one test case in test_engine.py, and LIST_UPDATED.
"""
from __future__ import annotations

import re

LIST_UPDATED = "2026-10-23"

# PHP2Shell (CVE-2026-109618, CVE-2026-109619): PHP's emergency release of 21 October 2026.
# Sources: CISA alert 2026-10-21 "Critical Vulnerabilities in PHP Require Immediate Patching";
# php.net/supported-versions.php (read 2026-10-23: 8.2 is the oldest branch still fixed).
FIXED = {(8, 5): 12, (8, 4): 27, (8, 3): 36, (8, 2): 35}
FIXED_TEXT = "8.5.12, 8.4.27, 8.3.36 and 8.2.35"
OLDEST_SUPPORTED = (8, 2)
TITLE = "PHP emergency security update, 21 Oct 2026"
QUESTIONS = (
    "What PHP version does the site run right now?",
    "Is it updated to 8.5.12, 8.4.27, 8.3.36 or 8.2.35?",
    "Does the site sit behind a firewall rule that can block this until it is updated?",
)

PLUGIN_ADVISORIES = [
    {
        "slug": "elementor-pro", "label": "Elementor Pro", "cve": "CVE-2026-32475",
        "published": "August 19, 2026", "exploited": True, "affected_max": (4, 2, 1), "fixed": "4.2.2",
        # Only sites with an Elementor Pro form that has a file-upload field can be attacked.
        "needs": "upload",
        "what": "lets an attacker upload a program through a form's file-upload field and take over the site",
        "sources": "Wordfence Intelligence, CVE-2026-32475 (rated 9.8), disclosed 2026-08-19; "
                   "Wordfence: exploitation since 2026-08-19, over 190,000 attempts blocked",
    },
]

PHP_PLATFORMS = ("WordPress", "Drupal", "Joomla", "Magento", "PrestaShop")
# Site builders that run inside WordPress, read from the folders their files load from.
BUILDERS = [
    ("Elementor Pro", "/wp-content/plugins/elementor-pro/"),
    ("Elementor", "/wp-content/plugins/elementor/"),
    ("Divi", "/wp-content/themes/divi/"),
    ("WPBakery", "/wp-content/plugins/js_composer/"),
    ("Beaver Builder", "/wp-content/plugins/bb-plugin/"),
    ("Avada", "/wp-content/themes/avada/"),
]
# The same builders, from the class names they stamp on the page's own markup (not words in its
# text). A caching plugin that bundles files hides the folders, not these (kristamashore.com,
# 2026-10-23: no Elementor folder loaded, "elementor-kit-13162" on the body).
BUILDER_CLASSES = [("Elementor", r"\belementor-kit-\d+"), ("Divi", r"\bet_pb_section\b|\bet-db\b"),
                   ("Beaver Builder", r"\bfl-builder\b")]
# Platforms that never run the owner's PHP: PHP flaws cannot reach these sites. Read from loaded
# file addresses (or a header the platform sends), never from words on the page.
HOSTED = [
    ("Wix", r"static\.wixstatic\.com|parastorage\.com", "x-wix-request-id"),
    ("Squarespace", r"static1\.squarespace\.com|squarespace-cdn\.com", None),
    ("Shopify", r"cdn\.shopify\.com", None),
    ("Webflow", r"website-files\.com|webflow\.com", None),
    ("GoHighLevel", r"leadconnectorhq\.com|msgsndr\.com|filesafe\.space", None),
    ("Duda", r"cdn-website\.com|multiscreensite\.com", None),
    ("Luxury Presence", r"luxurypresence\.com", None),
    ("GoDaddy Website Builder", r"img1\.wsimg\.com", None),
    ("Weebly / Square Online", r"editmysite\.com", None),
    ("HubSpot", r"hubspotusercontent|hs-scripts\.com", None),
    ("Framer", r"framerusercontent\.com", None),
]

NOT_MEASURED = {"measured": False, "platform": None, "builders": [], "hosted": None, "php": False,
                "phpVersion": None, "evidence": [], "line": "Built on: not measured, because the page could not be read.",
                "phpNote": None}


def _generator(html):
    out = []
    for tag in re.findall(r"<meta\b[^>]{0,500}>", html, re.I):
        if re.search(r"name\s*=\s*[\"']?generator[\"']?", tag, re.I):
            m = re.search(r"content\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", tag, re.I)
            if m:
                out.append(m.group(1).strip("\"'").lower())
    return " ".join(out)


def _php(headers):
    """(named, version). named: X-Powered-By names PHP. version: all three numbers, or None.
    A header saying only "PHP/8.3" gives no patch number, so the version is not measured."""
    m = re.search(r"(?<![\w.-])php(?![\w-])(?:/(\d+)\.(\d+)(?:\.(\d+))?)?", headers.get("x-powered-by", ""), re.I)
    if not m:
        return False, None
    if m.group(1) and m.group(3):
        return True, (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return True, None


def _strip(page):
    """Drop comments, script bodies (keeping the <script ...> tag itself) and style blocks, in ONE
    pass. A regex like <!--.*?--> rescans to the end of the page for every unclosed '<!--', so a
    hostile page of 150,000 of them froze the check (break-it run, 2026-10-23). An unclosed comment,
    script or style runs to the end of the page, as it does in a browser."""
    low = page.lower()
    out, i, n = [], 0, len(page)
    while i < n:
        j = low.find("<", i)
        if j < 0:
            out.append(page[i:])
            break
        out.append(page[i:j])
        if low.startswith("<!--", j):
            end = low.find("-->", j + 4)
            if end < 0:
                break
            out.append(" ")
            i = end + 3
        elif low.startswith("<script", j) or low.startswith("<style", j):
            tag = "script" if low.startswith("<script", j) else "style"
            gt = low.find(">", j)
            if gt < 0:
                break
            if tag == "script":
                out.append(page[j:gt + 1])  # the opening tag carries src=
            close = low.find("</" + tag, gt + 1)
            if close < 0:
                break
            end = low.find(">", close)
            i = end + 1 if end >= 0 else n
        else:
            out.append("<")
            i = j + 1
    return "".join(out)


def _loaded(page):
    """Addresses the page itself loads or declares (script, link, img, source, iframe tags), not words
    in its text, not links to other pages. A page that writes ABOUT WordPress does not run on it."""
    page = _strip(page)
    out = []
    for tag in re.findall(r"<(?:script|link|img|source|iframe)\b[^>]{0,2000}>", page, re.I):
        out += [v.strip("\"'").lower() for v in re.findall(r"(?:src|href|srcset|data-src)\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>\"']+)", tag, re.I)]  # quoted or bare, as minifiers write them
        if re.search(r"data-drupal-selector\s*=\s*[\"']?drupal-settings-json", tag, re.I):
            out.append("drupal-settings-json")
    return " ".join(out)


def _vtext(t):
    return ".".join(str(x) for x in t)


def _verdict(version):
    """For a PHP version the site states: ("fail", why) when it is unpatched or out of support,
    ("pass", why) when it matches a fixed release, (None, why) for a branch newer than this list."""
    v = _vtext(version)
    fixed = FIXED.get(version[:2])
    if version[:2] < OLDEST_SUPPORTED:
        return "fail", ("The site reports PHP %s. That version gets no security fixes any more, so this update will never "
                        "reach it. Ask the host to move the site to PHP 8.4 or 8.5." % v)
    if fixed is None:
        return None, ("The site reports PHP %s, a version line not in that list. Ask the host whether it is still supported "
                      "and covered by this update." % v)
    if version[2] >= fixed:
        return "pass", ("The site reports PHP %s, which matches a release with the fix. The header can be out of date or "
                        "wrong, so ask the host to confirm." % v)
    return "fail", ("The site reports PHP %s, which is below the fixed %d.%d.%d. Ask the host to update it."
                    % (v, version[0], version[1], fixed))


def _note(version):
    base = ("The PHP project released an emergency security update on 21 Oct 2026 for two critical flaws "
            "(CVE-2026-109618 and CVE-2026-109619), and attacks have been seen. The fixed versions are %s. " % FIXED_TEXT)
    if version is None:
        detail = (base + "The PHP version is not measured: the site does not show it, and a site can hide it, so only the "
                  "host can say. Send the three questions below to whoever hosts the site.")
    else:
        detail = base + _verdict(version)[1]
    return {"title": TITLE, "detail": detail, "fixedVersions": ["8.5.12", "8.4.27", "8.3.36", "8.2.35"], "questions": list(QUESTIONS)}


def detect(html, headers):
    """Read-only. html is the home page's source, headers its response headers (any case)."""
    if not isinstance(html, str) or (not html.strip() and not headers):
        return dict(NOT_MEASURED)
    headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    page = html[:600_000]
    low = _loaded(page)
    gen = _generator(page)
    ev = []
    platform = None
    if "wordpress" in gen or "/wp-content/" in low or "/wp-includes/" in low or "wp-json" in low:
        platform = "WordPress"
        ev = [e for e, hit in (("generator tag", "wordpress" in gen), ("wp-content files", "/wp-content/" in low or "/wp-includes/" in low),
                               ("wp-json address", "wp-json" in low)) if hit]
    elif "drupal" in gen or "drupal" in headers.get("x-generator", "").lower() or "x-drupal-cache" in headers or "drupal-settings-json" in low:
        platform = "Drupal"
        ev = ["generator tag or header"]
    elif "joomla" in gen or "/media/jui/" in low or "/components/com_" in low:
        platform = "Joomla"
        ev = ["generator tag or Joomla files"]
    elif "magento" in gen or re.search(r"/static/version\d+/frontend/", low):
        platform = "Magento"
        ev = ["Magento files"]
    elif "prestashop" in gen or "/modules/ps_" in low:
        platform = "PrestaShop"
        ev = ["generator tag or PrestaShop files"]
    elif "next.js" in headers.get("x-powered-by", "").lower() or "/_next/static/" in low:
        platform = "Next.js"
        ev = ["Next.js files or header"]
    builders = [n for n, folder in BUILDERS if folder in low] if platform == "WordPress" else []
    if platform == "WordPress":
        classes = " ".join(re.findall(r"\bclass\s*=\s*[\"']([^\"']{0,500})", _strip(page)))
        for n, pat in BUILDER_CLASSES:
            if n not in builders and not (n == "Elementor" and "Elementor Pro" in builders) and re.search(pat, classes):
                builders.append(n)
    if "Elementor Pro" in builders and "Elementor" in builders:
        builders.remove("Elementor")
    hosted = None
    if not platform:
        for name, files, header in HOSTED:
            if re.search(files, low) or (header and header in headers):
                hosted, ev = name, ["%s files" % name]
                break
    if not platform and not hosted and re.search(r"(?<![\w-])asp\.net", headers.get("x-powered-by", ""), re.I):
        hosted, ev = "Microsoft ASP.NET", ["X-Powered-By header names ASP.NET"]
    named, version = _php(headers)
    if named:
        ev.append("X-Powered-By header names PHP")
    elif re.search(r"(?<![\w-])phpsessid=", headers.get("set-cookie", ""), re.I):
        named = True  # only PHP sets a PHPSESSID cookie
        ev.append("a PHPSESSID cookie")
    php = platform in PHP_PLATFORMS or named
    name = platform + (" with " + " and ".join(builders) if builders else "") if platform else None
    if platform in PHP_PLATFORMS:
        line = "Built on %s, which runs on PHP." % name
    elif platform:
        line = "Built on %s." % name
    elif hosted:
        line = "Built on %s, which does not run PHP for you, so PHP flaws do not reach it." % hosted
    elif named:
        line = "Runs on PHP; the site's own %s says so." % ("header" if "X-Powered-By header names PHP" in ev else "cookie")
    else:
        line = "Platform not recognised: nothing on the page or in its headers names one."
    return {"measured": True, "platform": platform, "builders": builders, "hosted": hosted, "php": php,
            "phpVersion": _vtext(version) if version else None, "evidence": ev, "line": line,
            "phpNote": _note(version) if php else None}


class _VerMatch:
    """The highest version seen, shaped like a regex match."""

    def __init__(self, v):
        self.v = v

    def group(self, _):
        return _vtext(self.v)


def _ver(s):
    return tuple(int(x) for x in s.split("."))


def assess(home_headers, pages):
    """Scored checks, only for facts the site states outright: a PHP version in a header, a plugin
    version on its own files. Returns ([(name, status, detail, why, fix)], platform). A version the
    site hides is never scored (it goes under "Not measured"), so it can never lower the grade."""
    home = pages[0] if pages else {}
    platform = detect(home.get("raw") or "", home_headers)
    # The site's own page addresses ending in .php (index.php, contact.php) are PHP running on it.
    # Same-site links only (the grader's "internal" list): a link to someone else's .php is not.
    php_pages = sorted({u for p in pages[:25] for u in (p.get("internal") or [])
                        if isinstance(u, str) and re.search(r"\.php$", u.split("?")[0].split("#")[0], re.I)})
    if php_pages and not platform["php"] and not platform["hosted"] and platform["measured"]:
        platform = dict(platform, php=True, phpNote=_note(None), evidence=platform["evidence"] + ["its own pages end in .php"],
                        line="Runs on PHP: the site's own pages end in .php." if not platform["platform"] else platform["line"])
    out = []
    named, version = _php({str(k).lower(): str(v) for k, v in (home_headers or {}).items()})
    if version:
        st, why_v = _verdict(version)
        if st:
            fix = "" if st == "pass" else (
                "Ask your web host to move the site to PHP 8.4 or 8.5." if version[:2] < OLDEST_SUPPORTED
                else "Ask your web host to update PHP to %d.%d.%d or newer today." % (version[0], version[1], FIXED[version[:2]]))
            out.append(("PHP is up to date (PHP2Shell)", st, why_v,
                        "Two critical PHP flaws (CVE-2026-109618 and CVE-2026-109619) were fixed on 21 Oct 2026 and attacks "
                        "have been seen. They let an attacker run their own code on the server. Source: CISA, 21 Oct 2026.", fix))
    if platform.get("platform") == "WordPress":
        blob = "\n".join((p.get("raw") or "")[:300000] for p in pages[:25])
        loaded = _loaded(blob)
        for adv in PLUGIN_ADVISORIES:
            folder = "/wp-content/plugins/%s/" % adv["slug"]
            if folder not in loaded:
                continue
            # A plugin's folder also carries the libraries it bundles, each with its own ?ver=
            # (Elementor Pro ships one at 1.2.1). The plugin's own number is the highest.
            # Measured 2026-10-23: nashvilleroofingco.com shows ?ver=1.2.1 and ?ver=4.3.2.
            found = sorted({_ver(v) for v in re.findall(re.escape(folder) + r"[^\s\"'<>?]*\?ver=(\d+\.\d+(?:\.\d+)?)", loaded)})
            if not found:
                continue  # version hidden: listed under "Not measured" by the grader, never scored
            vm = _VerMatch(found[-1])
            upload = bool(re.search(r"<input[^>]{0,300}type=[\"']?file|elementor-field-type-upload", blob, re.I))
            name = "No known attacked flaw in %s" % adv["label"]
            why = "Site builders and plugins run inside your website: a flaw in one is a flaw in your site. " + adv["sources"]
            if found[-1] > adv["affected_max"]:
                out.append((name, "pass", "%s %s includes the fix for %s." % (adv["label"], vm.group(1), adv["cve"]), why, ""))
                continue
            exposed = adv.get("needs") != "upload" or upload
            out.append((name, "fail" if exposed else "warn",
                        "Your site uses %s %s. A critical flaw in it (%s), published %s%s, %s.%s" % (
                            adv["label"], vm.group(1), adv["cve"], adv["published"], " and under attack since" if adv["exploited"] else "",
                            adv["what"], "" if exposed else " We saw no file-upload field on the pages we read, so it may not be reachable, but update anyway."),
                        why, "Update %s to %s or newer (WordPress, then Plugins), then ask whoever runs the site to check the uploads "
                             "folder for .php files that should not be there." % (adv["label"], adv["fixed"])))
    return out, platform
