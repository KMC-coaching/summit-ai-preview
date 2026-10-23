"""
The software behind the site: what it is built on, and whether that software has a critical,
published security flaw. Read from the outside only: response headers, cookie names, and the
addresses of the files a page loads. Nothing is probed, tried or attacked.

    security.assess(home_headers, pages) -> list of checks for grader.py to add

THE ADVISORY LIST BELOW IS DATED AND SOURCED, ON PURPOSE
  Every entry names who published it and when. A flaw goes on the list only when it is critical
  AND either being attacked or affecting a large share of sites, and only from a primary source
  (the software's own security team, CISA, or the plugin security firm that disclosed it).
  WordPress plugins alone get 200 to 300 new flaws a week (Wordfence, 2026), so this is not, and
  never claims to be, a full scan: the report says so out loud. To add next week's flaw, add one
  entry and one test case in test_engine.py.

  LIST_UPDATED is printed on every report, so a stale list can never pass as a current one.

HOW SURE EACH VERDICT IS
  A version the server or page states outright (an X-Powered-By header, a ?ver= on a plugin's
  own file) is a fact we can act on. Everything else ("runs on PHP, version hidden") is a
  warning to check, never a pass and never a fail.
"""
from __future__ import annotations

import re

LIST_UPDATED = "2026-10-23"

PHP2SHELL = {
    "name": "PHP2Shell (CVE-2026-109618 and CVE-2026-109619)",
    "published": "2026-10-21",
    # PHP's fixed releases, one per supported branch. Older branches get no release at all.
    "fixed": {(8, 2): (8, 2, 35), (8, 3): (8, 3, 36), (8, 4): (8, 4, 27), (8, 5): (8, 5, 12)},
    "sources": "CISA alert 2026-10-21 (Critical Vulnerabilities in PHP Require Immediate Patching); "
               "php.net supported versions; PHP security advisory 2026-10-21",
}
# php.net/supported-versions.php, read 2026-10-23: 8.2 is the oldest branch still getting fixes.
OLDEST_SUPPORTED_PHP = (8, 2)

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

# Platforms that never run the site owner's PHP. PHP flaws cannot reach these sites.
HOSTED = [
    ("Wix", r"static\.wixstatic\.com|x-wix-request-id|wix-dynamic-pages"),
    ("Squarespace", r"static1\.squarespace\.com|squarespace-cdn\.com"),
    ("Shopify", r"cdn\.shopify\.com|shopify-checkout"),
    ("Webflow", r"website-files\.com|data-wf-site="),
    ("GoHighLevel", r"leadconnectorhq\.com|msgsndr\.com|assets\.cdn\.filesafe\.space"),
    ("Next.js", r"/_next/static/|x-powered-by: next\.js"),
    # Seen on the 60-site test round, 2026-10-23:
    ("Duda", r"cdn-website\.com|multiscreensite\.com"),
    ("Luxury Presence", r"x-powered-by: luxury presence|cdn\.luxurypresence\.com"),
    ("Microsoft ASP.NET", r"x-powered-by: asp\.net|ASP\.NET_SessionId"),
    ("GoDaddy Website Builder", r"img1\.wsimg\.com"),
    ("Weebly / Square Online", r"editmysite\.com"),
    ("HubSpot", r"hubspotusercontent|hs-scripts\.com"),
    ("Framer", r"framerusercontent\.com"),
]
# Platforms built on PHP. Seeing one means the site runs PHP even when the server hides it.
PHP_PLATFORMS = [
    ("WordPress", r"/wp-content/|/wp-includes/|<meta[^>]{0,80}generator[^>]{0,40}WordPress"),
    ("Joomla", r"<meta[^>]{0,80}generator[^>]{0,40}Joomla|/media/jui/|/components/com_"),
    ("Drupal", r"<meta[^>]{0,80}generator[^>]{0,40}Drupal|x-generator: drupal|/sites/default/files/"),
    ("Magento", r"/static/version\d+/frontend/|Magento_"),
    ("PrestaShop", r"<meta[^>]{0,80}generator[^>]{0,40}PrestaShop|/modules/ps_"),
]
BUILDERS = [
    ("Elementor Pro", r"/wp-content/plugins/elementor-pro/"),
    ("Elementor", r"/wp-content/plugins/elementor/|elementor-kit-"),
    ("Divi", r"/wp-content/themes/Divi/|et_pb_section"),
    ("WPBakery", r"/wp-content/plugins/js_composer/"),
    ("Beaver Builder", r"/wp-content/plugins/bb-plugin/"),
    ("Avada", r"/wp-content/themes/Avada/"),
]


class _VerMatch:
    """The highest version seen, shaped like a regex match so the code below reads the same."""

    def __init__(self, v):
        self.v = v

    def group(self, _):
        return _vtext(self.v)


def _ver(s):
    return tuple(int(x) for x in s.split("."))


def _vtext(t):
    return ".".join(str(x) for x in t)


def assess(home_headers, pages):
    """pages: the grader's page dicts (raw HTML in "raw", script addresses in "scripts").
    Returns a list of (name, status, detail, why, fix) for the grader to add."""
    hdr = "\n".join("%s: %s" % (k.lower(), v) for k, v in (home_headers or {}).items())
    # Bounded: the first 300 KB of up to 5 pages is plenty to see what a site is built on.
    blob = hdr + "\n" + "\n".join((p.get("raw") or "")[:300000] + " ".join(p.get("scripts") or []) for p in pages[:5])
    hosted = next((n for n, pat in HOSTED if re.search(pat, blob, re.I)), None)
    platform = next((n for n, pat in PHP_PLATFORMS if re.search(pat, blob, re.I)), None)
    builders = [n for n, pat in BUILDERS if re.search(pat, blob, re.I)]
    if "Elementor Pro" in builders and "Elementor" in builders:
        builders.remove("Elementor")
    m = re.search(r"x-powered-by: [^\n]*\bPHP/(\d+)\.(\d+)(?:\.(\d+))?", hdr, re.I)
    php_version = (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)) if m else None
    php_seen = bool(php_version or platform or re.search(r"x-powered-by: [^\n]*php|set-cookie: [^\n]*PHPSESSID", hdr, re.I)
                    or any(re.search(r"\.php(\?|$)", u) for p in pages[:5] for u in (p.get("internal") or [])))
    if platform and builders:
        built = "%s with %s" % (platform, " and ".join(builders))
    else:
        built = platform or " and ".join(builders) or ("PHP" if php_seen else "")
    out = []
    on_list = "Checked against the critical flaws on our list, updated %s." % LIST_UPDATED

    # ---- PHP itself
    name = "PHP is up to date (PHP2Shell)"
    why = ("Two critical PHP flaws, PHP2Shell, were published on %s and attacks have been seen. They let an "
           "attacker run their own code on the server before the website's own code even starts. %s"
           % ("October 21, 2026", PHP2SHELL["sources"]))
    if php_version:
        branch = php_version[:2]
        fixed = PHP2SHELL["fixed"].get(branch)
        shown = "Your server says it runs PHP %s" % _vtext(php_version)
        if branch < OLDEST_SUPPORTED_PHP:
            out.append((name, "fail", "%s. That version gets no security fixes any more, so PHP2Shell will never be fixed on it." % shown,
                        why, "Ask your web host to move the site to PHP 8.4 or 8.5 now. Most hosts do it with one setting."))
        elif fixed and php_version < fixed:
            out.append((name, "fail", "%s. The PHP2Shell fix for that version is PHP %s." % (shown, _vtext(fixed)),
                        why, "Ask your web host to update PHP to %s or newer today." % _vtext(fixed)))
        elif fixed:
            out.append((name, "pass", "%s, which includes the PHP2Shell fix." % shown, why, ""))
        else:  # a branch newer than this list knows
            out.append((name, "pass", "%s, newer than every version PHP2Shell affects." % shown, why, ""))
    elif php_seen:
        out.append((name, "warn",
                    "Your site is built on %s, which runs on PHP. Its PHP version is hidden from outside (that is good "
                    "practice), so we cannot tell whether it has the PHP2Shell fix." % (built or "PHP"),
                    why, "Ask your web host to confirm the site runs PHP 8.2.35, 8.3.36, 8.4.27, 8.5.12 or newer. "
                         "If they say 8.1 or older, ask them to move it to 8.4 or 8.5."))
    elif hosted:
        out.append((name, "pass", "Your site is built on %s, which does not run PHP for you, so PHP2Shell does not apply to it." % hosted, why, ""))
    else:
        out.append((name, "notMeasured", "Nothing on the pages shows what the site runs on, so we could not tell whether PHP is involved.",
                    why, ""))

    # ---- the site builder's own critical, exploited flaws
    if platform == "WordPress":
        hits = []
        for adv in PLUGIN_ADVISORIES:
            pat = r"/wp-content/plugins/%s/[^\"'\s<>?]*\?ver=(\d+\.\d+(?:\.\d+)?)" % re.escape(adv["slug"])
            used = re.search(r"/wp-content/plugins/%s/" % re.escape(adv["slug"]), blob, re.I)
            if not used:
                continue
            # A plugin's folder also carries the small libraries it bundles, each with its own
            # ?ver= (Elementor Pro ships one at 1.2.1). The plugin's own number is the highest.
            # Measured 2026-10-23: nashvilleroofingco.com shows ?ver=1.2.1 and ?ver=4.3.2.
            found = sorted({_ver(v) for v in re.findall(pat, blob, re.I)})
            vm = _VerMatch(found[-1]) if found else None
            upload = bool(re.search(r"<input[^>]{0,300}type=[\"']?file|elementor-field-type-upload", blob, re.I))
            if vm and _ver(vm.group(1)) > adv["affected_max"]:
                hits.append(("pass", "%s %s, which includes the fix for %s." % (adv["label"], vm.group(1), adv["cve"])))
            elif vm:
                exposed = adv.get("needs") != "upload" or upload
                hits.append(("fail" if exposed else "warn",
                             "Your site uses %s %s. A critical flaw in it (%s), published %s%s, %s.%s" % (
                                 adv["label"], vm.group(1), adv["cve"], adv["published"], " and under attack since" if adv["exploited"] else "",
                                 adv["what"], "" if exposed else " We saw no file-upload field on the pages we read, so it may not be reachable, but update anyway.")))
            else:
                hits.append(("warn", "Your site uses %s, and its version is hidden. A critical flaw in older versions (%s, published %s) %s; the fix is version %s." % (
                    adv["label"], adv["cve"], adv["published"], adv["what"], adv["fixed"])))
        status = "fail" if any(h[0] == "fail" for h in hits) else "warn" if any(h[0] == "warn" for h in hits) else "pass"
        detail = " ".join(h[1] for h in hits) if hits else (
            "Built with %s. None of the site-builder plugins we can see is on our list of critical, attacked flaws." % built)
        fix = ""
        if status != "pass":
            adv = PLUGIN_ADVISORIES[0]
            fix = ("Update %s to %s or newer (WordPress, then Plugins), then ask whoever runs the site to check the "
                   "uploads folder for .php files that should not be there." % (adv["label"], adv["fixed"]))
        out.append(("No known attacked flaw in your site builder", status, detail + " " + on_list,
                    "Site builders and plugins run inside your website: a flaw in one is a flaw in your site. %s"
                    % "; ".join(a["sources"] for a in PLUGIN_ADVISORIES), fix))
    return out, {"builtWith": built or hosted or "", "phpVersion": _vtext(php_version) if php_version else "",
                 "listUpdated": LIST_UPDATED, "wordpress": platform == "WordPress"}
