/*
 * The dashboard: a choose-your-own-adventure over everything their answers built.
 * #/            the landing: big tiles, pick where to start
 * #/site        every page of the new site as a large live thumbnail
 * #/magnet      the lead magnet, its post and its follow-up
 * #/report      their current site against the new one, every check, side by side
 * #/plan        the AI opportunity audit and the next few days, on one screen
 * #/brand       brand, ideal client, differentiator
 * #/play        prompts to paste into Claude, grouped, plus what's next
 *
 * Reads data/content.json, data/site.json, data/grade.json (their site or the one
 * they admire), data/grade-preview.json (the new site, measured after launch),
 * and config/settings.json (ours).
 */
(function () {
  "use strict";
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const t = (s) => esc(s).replace(/\[([^\]]{2,300})\]/g, '<span class="ph">[$1]</span>');
  const get = (u) => fetch(u, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch (e) { return u || ""; } };
  const color = (v) => (v == null ? "rgba(255,255,255,.25)" : v >= 90 ? "var(--good)" : v >= 70 ? "var(--mid)" : "var(--bad)");
  const D = {};
  let copyId = 0;
  const copies = {};
  const copyBtn = (text, label) => { const id = "c" + ++copyId; copies[id] = text; return `<button class="btn sm" data-copy="${id}">${esc(label || "Copy")}</button>`; };

  const VIEWS = [["site", "Demo site"], ["magnet", "Lead magnet"], ["report", "Report card"], ["plan", "Game plan"], ["brand", "Your brand"], ["gifts", "VIP gifts"], ["play", "Make it yours"]];

  function first() {
    const p = String(D.c.business.person || "").replace(/^(dr|mr|mrs|ms)\.?\s+/i, "").split(/\s+/)[0];
    return p || "You";
  }

  function topbar(active) {
    return `<div class="topbar"><div class="wrap">
      <a class="btn ghost sm" href="#/">&larr; Dashboard</a>
      <nav class="tabs" aria-label="Sections">${VIEWS.map(([k, l]) => `<a href="#/${k}"${k === active ? ' aria-current="page"' : ""}>${l}</a>`).join("")}</nav>
    </div></div>`;
  }

  const ring = (g, small) => `<div class="ring" style="--v:${g && g.overall || 0};--c:${color(g && g.overall)}${small ? ";width:64px;height:64px" : ""}"><div${small ? ' style="width:50px;height:50px"' : ""}><span><b${small ? ' style="font-size:1.3rem"' : ""}>${esc(g && g.letter || "–")}</b>${small ? "" : `<small>${g && g.overall != null ? g.overall + " / 100" : ""}</small>`}</span></div></div>`;

  /* ---------------------------------------------------------- reveal */
  function reveal() {
    let seen = false;
    try { seen = localStorage.getItem("aipreview.revealed") === "1"; localStorage.setItem("aipreview.revealed", "1"); } catch (e) { /* private window */ }
    if (seen || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const c = D.c, m = c.leadMagnet || {};
    const pages = D.s ? D.s.pages.filter((p) => p.file !== "privacy.html").length : 0;
    const checks = (D.g && D.g.checks ? D.g.checks.length : 0) + (D.gp && D.gp.checks ? D.gp.checks.length : 0);
    const photos = [...new Set(Object.values((D.s && D.s.images) || {}).flat())].length;
    const steps = [
      "Reading your answers",
      `Writing ${pages} pages in your voice`,
      photos ? `Choosing ${photos} photos` : "Choosing your photos",
      `Building "${m.title || "your free guide"}"`,
      `Writing ${(m.emails || []).length} follow-up emails`,
      checks ? `Running ${checks} checks on your websites` : "Checking your website",
      `${first()}, it's ready.`,
    ];
    const el = document.createElement("div");
    el.className = "reveal";
    el.innerHTML = `<div><p class="kicker">Built from your answers</p><ol>${steps.map((x) => `<li>${esc(x)}</li>`).join("")}</ol><button class="btn ghost sm" type="button">Skip</button></div>`;
    document.body.appendChild(el);
    const done = () => { el.classList.add("out"); setTimeout(() => el.remove(), 700); };
    el.querySelector("button").addEventListener("click", done);
    [...el.querySelectorAll("li")].forEach((li, i) => setTimeout(() => li.classList.add("on"), 350 + i * 650));
    setTimeout(done, 350 + steps.length * 650 + 1100);
  }

  /* ---------------------------------------------------------- landing */
  function landing() {
    const c = D.c, m = c.leadMagnet || {}, a = c.audit || {};
    const col = (c.brand || {}).colors || {};
    const g = D.g, gp = D.gp;
    const minutes = D.minutes ? ` in ${D.minutes} minutes` : "";
    return `<section class="landing"><div class="wrap" style="display:flex;flex-direction:column;flex:1">
      <p class="kicker">Built from your answers${minutes}</p>
      <h1>${esc(first())}, you just built all of this.</h1>
      <p class="lede">You answered the questions once. Your AI took it from there: a website in your words, your first lead magnet, a report card and a plan. Pick where to start.</p>
      <div class="tiles">
        <a class="tile tile--site" href="#/site"><div class="thumb"><iframe src="site/index.html" title="" tabindex="-1" aria-hidden="true" loading="eager"></iframe></div><div class="shade"></div>
          <span class="badge">New · built just now</span>
          <h2>Your demo website</h2><p>A demo of what your website could look like: ${D.s ? D.s.pages.filter((p) => p.file !== "privacy.html").length : 6} pages in your words and your colors, with photos, video and motion. Click to see every page.</p><span class="go">See your website &rarr;</span></a>
        <a class="tile tile--magnet" href="#/magnet"><div class="mini-cover" aria-hidden="true"><em>FREE</em>${t(m.title)}</div><div class="shade"></div>
          <span class="badge">Your first lead magnet</span>
          <h2>${t(m.title)}</h2><p>The free ${esc(m.format || "guide")}, the sign-up page, the post that promotes it, and ${(m.emails || []).length} follow-up emails.${(c.moreMagnets || []).length ? ` Plus ${(c.moreMagnets || []).length} more you made.` : ""}</p><span class="go">See your lead magnet &rarr;</span></a>
        <a class="tile tile--report" href="#/report">
          <div class="vs">${g && g.reachable ? `<div class="g" style="background:${color(g.overall)};color:#111">${esc(g.letter)}</div><span class="arrow">&rarr;</span>` : ""}<div class="g" style="background:${gp ? color(gp.overall) : "rgba(255,255,255,.1)"};color:#111">${gp ? esc(gp.letter) : "…"}</div></div>
          <h2>Your website report card</h2><p>${g && g.reachable ? `${esc(host(g.url))} against your demo site, on every check our sites must pass.` : "Your demo site, measured on every check our sites must pass."}</p><span class="go">See the report &rarr;</span></a>
        <a class="tile tile--plan" href="#/plan"><h2>Your AI game plan</h2><p>${t(a.summary)}</p><span class="go">${(a.opportunities || []).length} opportunities &rarr;</span></a>
        <a class="tile tile--brand" href="#/brand"><div class="swatch-row">${["primary", "accent"].filter((k) => col[k]).map((k) => `<span style="background:${esc(col[k])}"></span>`).join("")}</div>
          <h2>Your brand</h2><p>Your colors, your voice, your ideal client and what makes you different.</p><span class="go">See your brand &rarr;</span></a>
        ${gifts().length ? `<a class="tile tile--gifts" href="#/gifts"><div class="gift-stack" aria-hidden="true">${gifts().slice(0, 3).map((x, k) => `<span style="--k:${k}">${esc(x.title)}</span>`).join("")}</div>
          <h2>Your VIP gifts</h2><p>${gifts().length} gifts: Krista's books and tools.</p><span class="go">Open your gifts &rarr;</span></a>` : ""}
        <a class="tile tile--play${gifts().length ? " tile--half" : ""}" href="#/play"><div><h2>Now make it yours</h2><p>Change your headline, swap your colors, make another lead magnet. Paste one line into Claude and watch it happen.</p></div><span class="btn">Show me what I can do &rarr;</span></a>
      </div></div></section>
      <footer class="foot">Everything here lives only on your computer. Nothing has been published or sent anywhere.</footer>`;
  }

  /* ---------------------------------------------------------- site */
  function siteView() {
    const pages = (D.s && D.s.pages) || [];
    const g = D.g;
    const label = (p) => p.label;
    return topbar("site") + `<section class="view"><div class="wrap">
      <p class="kicker">Your demo website</p><h1>A demo of what your website could look like</h1>
      <p class="lede">Every page below was written from your answers and built a few minutes ago. Click any page to walk through it. Scroll slowly: things move.</p>
      ${g && g.reachable ? `<div class="notice">This is a demo site your AI just built from your answers. ${esc(host(g.url))} is a different site: you will find it on your report card.</div>` : ""}
      <div class="pages">${pages.filter((p) => p.file !== "privacy.html").map((p, i) => `<a class="pagecard${i === 0 ? " pagecard--wide" : ""}" href="site/${esc(p.file)}">
        <div class="shot"><iframe data-src="site/${esc(p.file)}" title="" tabindex="-1" aria-hidden="true"></iframe></div>
        <div class="cap"><b>${esc(label(p))}</b><span>Open &rarr;</span></div></a>`).join("")}</div>
    </div></section>`;
  }

  /* ---------------------------------------------------------- magnet */
  function magnetView() {
    const all = [D.c.leadMagnet || {}].concat(D.c.moreMagnets || []);
    const files = (D.s && D.s.magnets) || [{ free: "free-guide.html", guide: "guide.html" }];
    const k = Math.min(Number((location.hash.match(/^#\/magnet\/(\d+)/) || [])[1] || 0), all.length - 1);
    const m = all[k] || {};
    const f = files[k] || files[0];
    const switcher = all.length > 1 ? `<div class="chips" style="margin-top:16px">${all.map((x, i) => `<a class="btn ${i === k ? "" : "ghost"} sm" href="#/magnet/${i}">${t(x.title)}</a>`).join("")}</div>` : "";
    const posts = (D.c.posts || []).filter((p) => !p.magnet || p.magnet === (m.slug || "main"));
    return topbar("magnet") + `<section class="view"><div class="wrap">
      <p class="kicker">${k ? "Another lead magnet you made" : "Your first lead magnet"}</p><h1>${t(m.title)}</h1><p class="lede">${t(m.hook)}</p>${switcher}
      <div class="mag">
        <div><div class="bigcover"><em>FREE ${esc((m.format || "guide").toUpperCase())}</em><span>${t(m.title)}</span><small>${esc(D.c.business.name)}</small></div>
          <div style="margin-top:22px;display:flex;gap:10px;flex-wrap:wrap"><a class="btn" href="site/${esc(f.free)}">Try signing up yourself</a><a class="btn ghost" href="site/${esc(f.guide)}">Read the ${esc(m.format || "guide")}</a></div></div>
        <div>
          <div class="panel"><p class="kicker">How it works</p><div class="flow">
            <div class="m"><span class="d">1</span><span>A post sends people to your free ${esc(m.format || "guide")}.</span></div>
            <div class="m"><span class="d">2</span><span>They give their name and email on your sign-up page.</span></div>
            <div class="m"><span class="d">3</span><span>They get the ${esc(m.format || "guide")} right away, in your words.</span></div>
            ${(m.emails || []).map((e) => `<div class="m"><span class="d">Day ${esc(e.day)}</span><span><b>${t(e.subject)}</b></span></div>`).join("")}
          </div></div>
          <div class="panel"><p class="kicker">The post that brings them in</p><div class="quote">${t(m.socialPost)}</div>${copyBtn(m.socialPost || "", "Copy the post")}</div>
          ${posts.length ? `<div class="panel"><p class="kicker">More posts you asked for</p>${posts.map((p) => `<p class="muted" style="margin-top:12px">${esc(p.platform)}${p.day ? " · " + esc(p.day) : ""}</p><div class="quote">${t(p.text)}</div>${copyBtn(p.text || "", "Copy")}`).join("")}</div>` : ""}
        </div>
      </div></div></section>`;
  }

  /* ---------------------------------------------------------- report */
  function reportView() {
    const g = D.g, gp = D.gp;
    const have = g && g.reachable;
    const shot = (rep) => rep && rep.screenshot ? `<img class="phone" src="${rep.screenshot}" alt="What ${esc(rep.local ? "your demo site" : host(rep.url))} looks like on a phone">` : "";
    const side = (rep, who, cls, wait) => `<div class="side ${cls}">${shot(rep)}${rep ? ring(rep) : `<div class="ring"><div><span><b>…</b></span></div></div>`}
      <div><p class="who">${esc(who)}</p><h2>${rep ? esc(rep.local ? "Your demo site" : host(rep.url)) : esc(wait)}</h2>
      ${rep && (rep.belowBar || []).length && rep.letter !== "A" && rep.overall >= 90 ? `<p class="muted" style="margin-top:6px">Held to ${esc(rep.letter)}: ${esc(rep.belowBar.map((k) => ({ performance: "speed", accessibility: "accessibility", bestPractices: "best practices", seo: "SEO" }[k] || k)).join(", "))} is just under our launch bar.</p>` : ""}
      <p class="muted" style="margin-top:6px">${rep ? `${rep.totals.pass} passed · ${rep.totals.fail} to fix${rep.totals.todo ? " · " + rep.totals.todo + " for you to fill in" : ""} · ${rep.facts.pagesChecked} pages read` : "Measuring now. This takes about a minute."}</p></div></div>`;
    const cats = (gp || g) ? `<div class="cats"><div class="cat"><span class="cat-head">What we checked</span><span class="cat-head">${esc(have ? host(g.url) : "")}</span><span class="cat-head">Demo site</span></div>
      ${((gp || g).categories || []).map((cat) => {
        const o = have ? (g.categories.find((x) => x.name === cat.name) || {}) : {};
        const n = gp ? (gp.categories.find((x) => x.name === cat.name) || {}) : {};
        const bar = (v) => v == null ? `<div class="bar"></div><div class="num muted">${have || gp ? "not checked" : ""}</div>` : `<div class="bar"><i style="width:${v}%;background:${color(v)}"></i></div><div class="num" style="color:${color(v)}">${v}</div>`;
        return `<div class="cat"><span>${esc(cat.name)}</span><div>${have ? bar(o.score) : ""}</div><div>${gp ? bar(n.score) : '<div class="num muted">measuring…</div>'}</div></div>`;
      }).join("")}</div>` : "";

    const groups = [];
    for (const rep of [gp, g]) for (const ch of ((rep && rep.checks) || [])) if (!groups.includes(ch.group)) groups.push(ch.group);
    const find = (rep, ch) => rep && (rep.checks || []).find((x) => x.group === ch.group && x.name === ch.name);
    const label = { pass: "Pass", fail: "Fix", warn: "Warning", todo: "Fill in", local: "After launch", notMeasured: "Not measured" };
    const cell = (x) => x ? `<span class="chip ${x.status}">${label[x.status] || x.status}</span>${x.detail ? `<small>${esc(x.detail)}</small>` : ""}${x.pages && x.pages.length && x.status !== "pass" ? `<small>Pages: ${x.pages.slice(0, 4).map(esc).join(", ")}</small>` : ""}` : '<span class="chip none">–</span>';
    const groupHtml = groups.map((gname) => {
      const names = [];
      for (const rep of [gp, g]) for (const ch of ((rep && rep.checks) || [])) if (ch.group === gname && !names.some((n) => n.name === ch.name)) names.push(ch);
      const counts = (rep) => rep ? ["pass", "fail", "todo", "warn"].map((s) => { const k = (rep.checks || []).filter((x) => x.group === gname && x.status === s).length; return k ? `<span class="chip ${s}">${k} ${label[s]}</span>` : ""; }).join("") : "";
      return `<details class="group"${gname.startsWith("Not measured") ? "" : ""}><summary><span>${esc(gname)}</span><span class="counts">${counts(gp)}</span></summary>
        <div class="check" style="font:700 11px/1 var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--muted)"><span>Check</span><span>${esc(have ? host(g.url) : "")}</span><span>Demo site</span></div>
        ${names.map((ch) => `<div class="check"><div class="name"><b>${esc(ch.name)}</b>${ch.why ? `<small>${esc(ch.why)}</small>` : ""}</div><div class="cell">${have ? cell(find(g, ch)) : ""}</div><div class="cell">${cell(find(gp, ch))}</div></div>`).join("")}
      </details>`;
    }).join("");

    const ex = ((D.settings || {}).exampleSites || []).filter((e) => e.url);
    const fs = D.s && D.s.fullSite;
    // One slide per thing the full site adds, over the student's own photos. A slideshow by
    // default; "See all" lays every slide out at once for anyone who would rather skim.
    const photos = [...new Set(Object.values((D.s && D.s.images) || {}).flat())];
    const n = fs ? (fs.items || []).length : 0;
    const full = n ? `<section class="fs" aria-roledescription="carousel" aria-label="What your full site also gets">
      <p class="kicker">Beyond this preview</p><h2 class="fs-h">What your full site also gets</h2>
      <p class="fs-intro">${esc(fs.intro || "")}</p>
      <div class="fs-deck" data-deck tabindex="0">
        <div class="fs-track">${fs.items.map((it, k) => `<article class="fs-slide${k ? "" : " on"}" role="group" aria-roledescription="slide" aria-label="${k + 1} of ${n}"${k ? ' aria-hidden="true"' : ""}>
          ${photos.length ? `<img src="assets/img/library/${esc(photos[k % photos.length])}-md.webp" alt="" loading="${k ? "lazy" : "eager"}">` : ""}
          <div class="fs-body"><span class="fs-num">${String(k + 1).padStart(2, "0")}<i>/ ${String(n).padStart(2, "0")}</i></span>
          <h3>${esc(it.title)}</h3><p>${esc(it.text)}</p></div></article>`).join("")}</div>
        <div class="fs-bar"><div class="fs-dots">${fs.items.map((it, k) => `<button type="button" class="fs-dot${k ? "" : " on"}" data-go="${k}" aria-label="Show ${k + 1}: ${esc(it.title)}"></button>`).join("")}</div>
          <div class="fs-nav"><button type="button" class="fs-arrow" data-step="-1" aria-label="Previous">&larr;</button><button type="button" class="fs-arrow" data-step="1" aria-label="Next">&rarr;</button>
          <button type="button" class="btn ghost sm" data-all>See all ${n}</button></div></div>
        <div class="fs-progress"><i></i></div>
      </div></section>` : "";
    return topbar("report") + `<section class="view"><div class="wrap">
      <p class="kicker">Your website report card</p><h1>${have ? `${esc(host(g.url))}, against what we just built` : "Your demo site, measured"}</h1>
      <p class="lede">The same checks a site has to pass before we let it launch: Google's own Lighthouse test, how AI assistants read it, broken pages, the words on the page${D.c.profile === "real-estate" ? ", Fair Housing and licensing rules" : D.c.profile === "lender" ? ", fair lending and NMLS rules" : ""}, and privacy. Nothing here is estimated: every number was measured today.</p>
      ${gp && gp.lighthouseLimit === "windows" ? `<div class="notice">On Windows, Google's speed test can't run from here, so your demo site's speed shows as "Not measured". That is a Windows limit, not a problem with your site. Everything else was checked.</div>` : ""}
      ${g && !g.reachable ? `<div class="notice">We tried to check ${esc(host(g.url))} and it did not answer. If the address is wrong, tell Claude the right one and say <b>&nbsp;grade my website again</b>.</div>` : ""}
      ${have ? `<div class="notice">${esc(g.label || "This site")}: ${esc(host(g.url))}. ${g.label && /competitor/i.test(g.label) ? "A competitor in your area, measured the same way. This is who you are up against." : g.label && /admire/i.test(g.label) ? "You do not have a site of your own yet, so we measured this one instead." : ""}</div>` : ""}
      <div class="duel">${have ? side(g, g.label || "Your current website", "", "") : ""}${side(gp, "A demo, built just now from your answers", "side--new", "Your demo site")}</div>
      ${cats}
      ${full}
      <h2 style="margin-top:34px;font-size:1.6rem">Every check, side by side</h2>
      <p class="muted" style="margin-top:6px">Open any section. "Fill in" means a blank only you can complete, like your license number. "After launch" means it can only pass on a published site.</p>
      ${groupHtml}
      ${(D.others || []).length ? `<h2 style="margin-top:34px;font-size:1.6rem">Other sites you checked</h2><div class="duel">${D.others.map((o) => side(o, o.label || "Another site", "", "")).join("")}</div>` : ""}
      ${ex.length ? `<div class="panel" style="margin-top:22px"><p class="kicker">Sites built the way we teach</p><p class="muted" style="margin:6px 0 10px">Ask Claude to grade any of these and compare.</p><div class="chips">${ex.map((e) => `<a class="btn ghost sm" href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.name)}</a>`).join("")}</div></div>` : ""}
    </div></section>`;
  }

  /* ---------------------------------------------------------- plan */
  function planView() {
    const a = D.c.audit || {};
    return topbar("plan") + `<section class="view" style="padding:18px 0 24px"><div class="wrap">
      <p class="kicker">Your AI opportunity audit</p><h1 style="font-size:clamp(1.5rem,1rem+1.4vw,2.15rem)">${t(a.summary)}</h1>
      <div class="plan">${(a.opportunities || []).map((o, i) => `<div class="opp"><span class="n">${i + 1}</span><h3>${t(o.title)}</h3>
        <dl><div><dt>Why it matters</dt><dd>${t(o.why)}</dd></div><div><dt>What we saw</dt><dd>${t(o.evidence)}</dd></div><div><dt>What the full system does</dt><dd>${t(o.bossDoes)}</dd></div></dl></div>`).join("")}</div>
      <div class="days">${(a.plan || []).map((d) => `<div class="day"><span class="d">Day ${esc(d.day)}</span><b>${t(d.title)}</b><span class="muted" style="font-size:13.5px">${t(d.do)}</span>${d.prompt ? copyBtn(d.prompt, "Copy the prompt") + `<details class="full"><summary>See the full message</summary><code>${esc(d.prompt)}</code></details>` : ""}</div>`).join("")}</div>
    </div></section>`;
  }

  /* ---------------------------------------------------------- brand */
  /* ---------------------------------------------------------- VIP gifts */
  function gifts() { return ((D.settings || {}).vipGifts || []).filter((x) => x.title && (x.url || x.view)); }
  function giftsView() {
    return topbar("gifts") + `<section class="view"><div class="wrap">
      <p class="kicker">VIP gifts</p><h1>Your VIP gifts</h1>
      <p class="lede">Click any gift to open it.</p>
      <div class="gifts">${gifts().map((x, k) => `<a class="gift" href="${x.view ? "#/" + esc(x.view) : esc(x.url)}"${x.view ? "" : ' target="_blank" rel="noopener"'}>
        <div class="gift-cover" style="--k:${k}"><span class="tag">${esc(x.kind || "Gift")}</span><span class="t">${esc(x.title)}</span><span class="by">Krista Mashore</span></div>
        <span class="go">Open &rarr;</span></a>`).join("")}</div>
    </div></section>`;
  }

  /* ---------------------------------------------------------- the coach (a VIP gift) */
  // Chelsea's starter, filled in with what the preview already knows about them, so
  // every question they copy is about their business. It is installed in their AI
  // Preview folder (.claude/skills/attraction-marketing-coach) and answers in Claude.
  function coachView() {
    const co = (D.settings || {}).coach || {};
    const me = D.c.coach || {};
    const plain = (x) => String(x || "").trim();
    const what = plain(me.whatYouDo) || plain(D.c.business && D.c.business.profession).toLowerCase() || "[what you do]";
    const who = plain(me.whoYouServe) || "[who you serve]";
    const struggle = plain(me.struggle) || "[your struggle]";
    const an = /^[aeiou]/i.test(what) ? "an" : "a";
    const intro = `I’m ${an} ${what} who focuses on ${who}. Here’s what I’m struggling with: ${struggle}.`;
    const ask = (q) => `In my AI Preview, ask my coach: ${intro} ${q}`;
    const blanks = /\[[^\]]+\]/.test(intro);
    return topbar("gifts") + `<section class="view"><div class="wrap">
      <p class="kicker">VIP gift · already installed</p><h1>Your Client Attraction &amp; Authority Coach</h1>
      <p class="lede">It's already set up in your AI Preview, and it already knows your business. Ask it anything about getting known and attracting clients. It answers from Krista's teaching, tells you which part of her teaching the answer comes from, and gives you one next step.</p>
      <div class="how"><div><b>1. Copy a question</b><span class="muted">Each one below already says who you are.</span></div><div><b>2. Paste it into Claude</b><span class="muted">In the Claude window where you built your preview. Press Enter.</span></div><div><b>3. Ask "What's my next step?"</b><span class="muted">Do that one step before your next question.</span></div></div>
      <div class="panel" style="margin-top:22px"><p class="kicker">Questions to start with</p>
        <p class="muted" style="margin-top:6px">Your coach reads this as: “${t(intro)}”${blanks ? " Fill in the blank after you paste it." : ""}</p>
        <div class="finishes">${(co.finishes || []).map((f) => `<div class="prompt"><b>${esc(f.text)}</b>${copyBtn(ask(f.text), "Copy")}${f.note ? `<span class="muted" style="font-size:13.5px">${esc(f.note)}</span>` : ""}<details class="full"><summary>See the full message</summary><code>${esc(ask(f.text))}</code></details></div>`).join("")}</div></div>
      <div class="panel"><p class="kicker">Or ask in your own words</p><p class="muted" style="margin-top:6px">Copy this, paste it into Claude, and finish it with anything you want to know:</p><code class="start">In my AI Preview, ask my coach:</code>${copyBtn("In my AI Preview, ask my coach: ", "Copy the start")}</div>
      ${(co.topics || []).length ? `<div class="panel"><p class="kicker">What your coach knows</p><p class="muted" style="margin:6px 0 10px">Krista's frameworks and trainings on:</p><div class="chips">${co.topics.map((x) => `<span>${esc(x)}</span>`).join("")}</div></div>` : ""}
      <p style="margin-top:22px"><a class="btn ghost sm" href="#/gifts">&larr; All your gifts</a></p>
    </div></section>`;
  }

  function brandView() {
    const b = D.c.brand || {}, col = b.colors || {}, av = D.c.avatar || {}, d = D.c.differentiator || {};
    return topbar("brand") + `<section class="view"><div class="wrap">
      <p class="kicker">Your brand</p><h1>${esc(D.c.business.name)}</h1><p class="lede">${t(b.tagline)}${b.taglineSuggested ? ' <span class="chips" style="display:inline-flex;margin:0"><span>suggested</span></span>' : ""}</p>
      <div class="brandgrid">
        <div class="panel"><p class="kicker">Colors and voice</p>
          <div class="sw">${["primary", "accent"].filter((k) => col[k]).map((k) => `<div><span style="background:${esc(col[k])}"></span>${esc(col[k])}</div>`).join("")}</div>
          <p class="muted">${t(b.colorNote)}</p>${((D.s || {}).colorNotes || []).map((n) => `<p class="muted" style="margin-top:8px">${esc(n)}</p>`).join("")}
          <div class="chips">${(b.voice || []).map((v) => `<span>${esc(v)}</span>`).join("")}</div>
          ${b.voiceExample ? `<div class="quote">${t(b.voiceExample)}</div>` : ""}</div>
        <div class="panel"><p class="kicker">Your ideal client</p><h2 style="font-size:1.5rem;margin:8px 0">${t(av.name)}</h2><p class="muted">${t(av.snapshot)}</p>
          <p class="kicker" style="margin-top:14px">What keeps them up at night</p><ul class="list">${(av.pains || []).map((x) => `<li>${t(x)}</li>`).join("")}</ul>
          <p class="kicker" style="margin-top:10px">What they want</p><ul class="list">${(av.wants || []).map((x) => `<li>${t(x)}</li>`).join("")}</ul></div>
        <div class="panel" style="grid-column:1/-1"><p class="kicker">What makes you different</p><h2 style="font-size:1.5rem;margin:8px 0">${t(d.methodName)}${d.methodNameSuggested ? ' <span class="chips" style="display:inline-flex;margin:0;vertical-align:middle"><span>name suggested</span></span>' : ""}</h2>
          <p class="muted">${t(d.statement)}</p></div>
      </div></div></section>`;
  }

  /* ---------------------------------------------------------- play */
  function playView() {
    const groups = {};
    for (const p of (D.c.prompts || [])) (groups[p.group || "Try these"] = groups[p.group || "Try these"] || []).push(p);
    const n = (D.settings || {}).next || {};
    let video = `<div class="video">${esc(n.videoPlaceholder || "A short video goes here.")}</div>`;
    if (n.videoUrl) video = /\.(mp4|webm|mov)(\?|$)/i.test(n.videoUrl) ? `<div class="video"><video src="${esc(n.videoUrl)}" controls playsinline></video></div>` : `<div class="video"><iframe src="${esc(n.videoUrl)}" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen title="What's next"></iframe></div>`;
    return topbar("play") + `<section class="view"><div class="wrap">
      <p class="kicker">Make it yours</p><h1>You're doing great. Now change anything.</h1>
      <p class="lede">This is exactly how the full system works: you say what you want, it builds it. Pick anything below.</p>
      <div class="how"><div><b>1. Copy</b><span class="muted">Click Copy on anything below.</span></div><div><b>2. Paste into Claude</b><span class="muted">Go back to the Claude window, paste, press Enter.</span></div><div><b>3. Refresh this page</b><span class="muted">When Claude says it's done, refresh and see your change.</span></div></div>
      <div class="groups">${Object.entries(groups).map(([gname, ps]) => `<div class="pgroup"><h2>${esc(gname)}</h2>${ps.map((p) => `<div class="prompt"><b>${t(p.label)}</b>${copyBtn(p.prompt)}<code>${esc(p.prompt)}</code></div>`).join("")}</div>`).join("")}</div>
      <div class="next"><div><p class="kicker">What's next</p><h2 style="font-size:1.9rem;margin:8px 0">${esc(n.headline || "This is a glimpse.")}</h2><p class="muted">${esc(n.text || "")}</p>
        ${n.ctaUrl ? `<p style="margin-top:16px"><a class="btn" href="${esc(n.ctaUrl)}" target="_blank" rel="noopener">${esc(n.ctaText || "See how")}</a></p>` : ""}</div>${video}</div>
    </div></section>`;
  }

  /* ---------------------------------------------------------- router */
  const VIEW_FN = { site: siteView, magnet: magnetView, report: reportView, plan: planView, brand: brandView, gifts: giftsView, coach: coachView, play: playView };
  function render() {
    const key = (location.hash.match(/^#\/(\w+)/) || [])[1];
    const app = document.getElementById("app");
    app.innerHTML = (VIEW_FN[key] || landing)();
    document.title = (key ? (VIEWS.find((v) => v[0] === key) || [key, key === "coach" ? "Your coach" : "Your AI Preview"])[1] + " · " : "") + (D.c.business.name || "Your AI Preview");
    window.scrollTo(0, 0);
    // Big page thumbnails: size the 1440px page to the card, load them one by one.
    const frames = [...app.querySelectorAll(".pagecard iframe[data-src]")];
    const fit = () => app.querySelectorAll(".pagecard .shot").forEach((s) => { const f = s.querySelector("iframe"); if (f) f.style.transform = `scale(${s.clientWidth / 1440})`; });
    fit();
    window.onresize = fit;
    let i = 0;
    const next = () => { if (i >= frames.length) return; const f = frames[i++]; f.addEventListener("load", next, { once: true }); f.src = f.dataset.src; setTimeout(next, 2500); };
    next();
    app.querySelectorAll("[data-deck]").forEach(deck);
    const h = app.querySelector("h1");
    if (h && key) { h.setAttribute("tabindex", "-1"); h.focus({ preventScroll: true }); }
  }

  // The full-site slideshow: arrows, dots, swipe and arrow keys; moves on by itself every
  // 6 seconds unless the pointer is over it, it has focus, or the viewer prefers less motion.
  function deck(el) {
    const slides = [...el.querySelectorAll(".fs-slide")], dots = [...el.querySelectorAll(".fs-dot")];
    const bar = el.querySelector(".fs-progress i");
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let at = 0, timer = null, held = false;
    const show = (k) => {
      at = (k + slides.length) % slides.length;
      slides.forEach((s, j) => { s.classList.toggle("on", j === at); s.setAttribute("aria-hidden", j === at ? "false" : "true"); });
      dots.forEach((d, j) => d.classList.toggle("on", j === at));
      restart();
    };
    const restart = () => {
      clearTimeout(timer);
      if (bar) { bar.style.transition = "none"; bar.style.width = "0"; }
      if (still || held || el.classList.contains("all")) return;
      requestAnimationFrame(() => { if (bar) { bar.style.transition = "width 6s linear"; bar.style.width = "100%"; } });
      timer = setTimeout(() => { if (document.body.contains(el)) show(at + 1); }, 6000);
    };
    const hold = (v) => { held = v; restart(); };
    el.addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b) return;
      if (b.dataset.step) show(at + Number(b.dataset.step));
      else if (b.dataset.go) show(Number(b.dataset.go));
      else if (b.hasAttribute("data-all")) { const all = el.classList.toggle("all"); b.textContent = all ? "Show as slides" : "See all " + slides.length; slides.forEach((s, j) => s.setAttribute("aria-hidden", all || j === at ? "false" : "true")); restart(); }
    });
    el.addEventListener("keydown", (e) => { if (e.key === "ArrowRight") show(at + 1); if (e.key === "ArrowLeft") show(at - 1); });
    el.addEventListener("mouseenter", () => hold(true)); el.addEventListener("mouseleave", () => hold(false));
    el.addEventListener("focusin", () => hold(true)); el.addEventListener("focusout", () => hold(false));
    let x0 = null;
    el.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; held = true; clearTimeout(timer); }, { passive: true });
    el.addEventListener("touchend", (e) => { held = false; if (x0 == null) return; const dx = e.changedTouches[0].clientX - x0; x0 = null; if (Math.abs(dx) > 40) show(at + (dx < 0 ? 1 : -1)); else restart(); });
    restart();
  }

  function toast(msg) {
    const d = document.createElement("div");
    d.className = "toast"; d.setAttribute("role", "status"); d.textContent = msg;
    document.body.appendChild(d); setTimeout(() => d.remove(), 2600);
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-copy]");
    if (!b) return;
    const text = copies[b.dataset.copy] || "";
    const done = () => toast("Copied. Now paste it into Claude.");
    const fallback = () => { const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); try { document.execCommand("copy"); done(); } catch (err) { /* nothing more to try */ } ta.remove(); };
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, fallback); else fallback();
  });
  window.addEventListener("hashchange", render);

  // The new site is measured after it opens; pick the result up when it lands.
  function waitForPreviewGrade() {
    if (D.gp) return;
    const tick = setInterval(async () => {
      const gp = await get("data/grade-preview.json");
      if (gp && gp.reachable) { D.gp = gp; clearInterval(tick); const k = (location.hash.match(/^#\/(\w+)/) || [])[1]; if (!k || k === "report") render(); }
    }, 5000);
    setTimeout(() => clearInterval(tick), 10 * 60 * 1000);
  }

  Promise.all([get("data/content.built.json"), get("data/site.json"), get("data/grade.json"), get("data/grade-preview.json"), get("config/settings.json"), get("data/grades/index.json")]).then(async ([c, s, g, gp, settings, others]) => {
    if (!c) { document.getElementById("app").innerHTML = '<div class="loading"><div><h1>Your preview is not ready yet</h1><p class="muted" style="margin-top:10px">Go back to Claude and say: <b>open my preview</b>.</p></div></div>'; return; }
    c.business = c.business || {};
    const extra = (await Promise.all((others || []).map((f) => get("data/grades/" + f)))).filter((x) => x && x.reachable);
    Object.assign(D, { c, s, g, gp: gp && gp.reachable ? gp : null, settings: settings || {}, others: extra });
    const st = Date.parse((c.meta || {}).startedAt || ""), en = Date.parse((c.meta || {}).generatedAt || "");
    if (st && en && en > st) D.minutes = Math.max(1, Math.round((en - st) / 60000));
    const pal = (s && s.palette) || {};
    const col = (c.brand || {}).colors || {};
    const brand = pal["--brand"] || col.primary, acc = pal["--accent"] || col.accent;
    if (brand) document.documentElement.style.setProperty("--brand", brand);
    if (acc) document.documentElement.style.setProperty("--brand-accent", acc);
    if (pal["--on-brand"]) document.documentElement.style.setProperty("--brand-on", pal["--on-brand"]);
    render();
    if (!location.hash || location.hash === "#/") reveal();
    waitForPreviewGrade();
  });
})();
