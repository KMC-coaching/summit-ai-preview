/*
 * The dashboard: everything their answers produced, on one page.
 * Reads data/content.json (written by Claude), data/grade.json (written by the
 * grader) and config/settings.json (ours: example sites, the next-step video).
 */
(function () {
  "use strict";

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const t = (s) => esc(s).replace(/\[([^\]]{2,300})\]/g, '<span class="ph">[$1]</span>');
  const get = (u) => fetch(u, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const color = (v, bar) => (v == null ? "#b9b3a6" : v >= (bar || 90) ? "var(--good)" : v >= 60 ? "var(--mid)" : "var(--bad)");
  const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch (e) { return u; } };

  let copyId = 0;
  const copies = {};
  const copyBtn = (text, label) => { const id = "c" + ++copyId; copies[id] = text; return `<button class="btn small line" data-copy="${id}">${esc(label || "Copy")}</button>`; };

  function brandCard(c) {
    const b = c.brand || {}, col = b.colors || {}, a = c.avatar || {}, d = c.differentiator || {};
    return `<div class="card s5"><div class="label"><span class="num">1</span>Your brand, from your answers</div>
      <h2>${t(c.business.name)}</h2><p class="muted">${t(b.tagline || c.business.oneLiner)}${b.taglineSuggested ? ' <span class="chip">suggested</span>' : ""}</p>
      <div class="swatches">${["primary", "accent", "ink", "paper"].filter((k) => col[k]).map((k) => `<div class="sw"><span style="background:${esc(col[k])}"></span>${esc(col[k])}</div>`).join("")}</div>
      <div class="small muted">Voice</div><div class="chips">${(b.voice || []).map((v) => `<span class="chip">${esc(v)}</span>`).join("")}</div>
      ${b.voiceExample ? `<div class="quote">${t(b.voiceExample)}</div>` : ""}
      <h3 style="margin-top:16px">Your ideal client: ${t(a.name)}</h3><p class="small">${t(a.snapshot)}</p>
      <div class="small muted">What keeps them up at night</div><ul class="tight small">${(a.pains || []).map((p) => `<li>${t(p)}</li>`).join("")}</ul>
      <h3>What makes you different</h3><p class="small"><strong>${t(d.methodName)}.</strong>${d.methodNameSuggested ? ' <span class="chip">name suggested</span>' : ""} ${t(d.statement)}</p>
    </div>`;
  }

  function gradeCard(g, c, settings) {
    if (!g) return `<div class="card s7"><div class="label"><span class="num">2</span>Website report card</div>
      <h2>No website was checked</h2><p class="muted">Your answers did not include a website. Ask Claude: <strong>grade a website for me</strong>, and give it yours or one you admire.</p></div>`;
    if (!g.reachable) return `<div class="card s7"><div class="label"><span class="num">2</span>Website report card</div>
      <h2>${esc(host(g.url))} did not answer</h2><p class="muted">We tried to check it and got nothing back. That alone is worth knowing: if we cannot reach it, neither can Google. Ask Claude to <strong>try grading it again</strong>.</p></div>`;
    const v = g.overall;
    const bars = g.categories.map((k) => `<div class="bar"><div>${esc(k.name)}</div>
      <div class="track" title="${esc(k.source)}"><i style="width:${k.score || 0}%;background:${color(k.score, k.bar)}"></i><span class="goal" style="left:${k.bar}%"></span></div>
      <div class="v" style="color:${color(k.score, k.bar)}">${k.score == null ? "–" : k.score}</div></div>`).join("");
    const f = g.facts || {};
    const sev = { high: "var(--bad)", medium: "var(--mid)", low: "#8a8f99" };
    const findings = (g.findings || []).slice(0, 6).map((x) => `<div class="finding"><span class="dot" style="background:${sev[x.severity]}"></span><div><strong>${esc(x.text)}</strong><div class="small muted">${esc(x.detail)}</div></div></div>`).join("");
    const lh = g.lighthouse || {};
    const row = (name, theirs, bar) => `<tr><td>${name}</td><td>${theirs}</td><td><strong>${bar}</strong></td></tr>`;
    const yn = (b) => (b ? "Yes" : "No");
    const examples = (settings.exampleSites || []).filter((e) => e.url);
    return `<div class="card s7"><div class="label"><span class="num">2</span>${esc(g.label || "Website")} report card</div>
      <div class="grade-top"><div class="ring" style="--v:${v || 0};--c:${color(v, 90)}"><div><span><b>${esc(g.letter)}</b><small>${v == null ? "" : v + " / 100"}</small></span></div></div>
      <div><h2 style="margin:0">${esc(host(g.url))}</h2><p class="muted small" style="margin:4px 0 0">${f.pagesChecked} pages and ${f.linksChecked} links checked, ${esc(g.measuredAt.replace("T", " at "))}.
      ${g.lighthouseError ? "<br>Google's speed test did not run this time, so those rows say –. Ask Claude to grade it again." : ""}</p></div></div>
      <div class="bars">${bars}</div><div class="legend"><i></i> the bar a site has to clear before we let it launch</div>
      <h3 style="margin-top:22px">What we found</h3>${findings || '<p class="muted">Nothing major. That is rare.</p>'}
      <h3 style="margin-top:22px">Your site against the bar</h3>
      <table class="compare"><thead><tr><th></th><th>${esc(g.label || "This site")}</th><th>The bar we build to</th></tr></thead><tbody>
      ${row("Pages with structured data", `${f.pagesWithSchema} of ${f.pagesOk}`, "Every page")}
      ${row("Broken pages and links", (f.brokenPages || []).length + (f.brokenLinks || []).length, "0")}
      ${row("Speed on a phone", lh.performance == null ? "–" : lh.performance, g.bar.performance + "+")}
      ${row("Accessibility", lh.accessibility == null ? "–" : lh.accessibility, g.bar.accessibility)}
      ${row("Google's SEO check", lh.seo == null ? "–" : lh.seo, g.bar.seo)}
      ${row("Business schema", yn(f.businessSchema), "Yes")}
      ${row("FAQ markup for AI answers", yn(f.faqSchema), "Yes")}
      ${row("llms.txt for AI assistants", yn(f.llmsTxt), "Yes")}
      </tbody></table>
      ${examples.length ? `<h3 style="margin-top:22px">Sites built the way we teach</h3><p class="small muted">Want to see the difference? Ask Claude to grade any of these, then compare.</p>
        <div class="chips">${examples.map((e) => `<a class="chip" href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.name)}</a>`).join("")}</div>` : ""}
    </div>`;
  }

  function siteCard(c) {
    return `<div class="card s6"><div class="label"><span class="num">3</span>Your sample website</div>
      <h2>Five pages, in your words and your colors</h2>
      <p class="muted small">Built from your answers in a few minutes, with structured data on every page. It lives only on this computer: nobody else can see it, and it is not published anywhere.</p>
      <div class="frame"><iframe src="site/index.html" title="Your sample website" loading="lazy" tabindex="-1"></iframe><a class="cover-link" href="site/index.html" aria-label="Open your sample website"></a></div>
      <div style="margin-top:14px;display:flex;gap:10px;flex-wrap:wrap"><a class="btn dark" href="site/index.html">Open your website</a>${copyBtn("In my Summit AI Preview, change the headline on my sample website's home page to: ", "Copy a prompt to change it")}</div>
    </div>`;
  }

  function magnetCard(c) {
    const m = c.leadMagnet || {};
    return `<div class="card s6"><div class="label"><span class="num">4</span>Your first lead magnet</div>
      <div class="mag"><div class="mcover"><em>FREE</em>${t(m.title)}</div>
      <div><h2>${t(m.title)}</h2><p class="muted small">${t(m.hook)}</p>
      <p class="small"><strong>The whole path is built:</strong> a social post sends people to the sign-up page, they get the ${esc(m.format || "guide")}, and ${(m.emails || []).length} follow-up emails go out on their own.</p>
      <div style="display:flex;gap:10px;flex-wrap:wrap"><a class="btn dark" href="site/free-guide.html">Try signing up yourself</a></div></div></div>
      <h3 style="margin-top:18px">The post that sends people to it</h3><div class="quote">${t(m.socialPost)}</div>${copyBtn(m.socialPost || "", "Copy the post")}
    </div>`;
  }

  function auditCard(c) {
    const a = c.audit || {};
    return `<div class="card s12"><div class="label"><span class="num">5</span>Your AI opportunity audit</div>
      <h2>${t(a.summary)}</h2>
      ${(a.opportunities || []).map((o, i) => `<div class="opp"><div class="rank">${i + 1}</div><div><h3 style="margin:0">${t(o.title)}</h3>
        <dl><dt>Why it matters</dt><dd>${t(o.why)}</dd><dt>What we saw</dt><dd>${t(o.evidence)}</dd><dt>When it is fixed</dt><dd>${t(o.whatChanges)}</dd><dt>What the full system does</dt><dd>${t(o.bossDoes)}</dd></dl></div></div>`).join("")}
      <h3 style="margin-top:14px">Your next few days</h3>
      <div class="days">${(a.plan || []).map((d) => `<div class="day"><div class="d">Day ${esc(d.day)}</div><strong>${t(d.title)}</strong><div class="small">${t(d.do)}</div>${d.prompt ? copyBtn(d.prompt, "Copy the prompt") : ""}</div>`).join("")}</div>
    </div>`;
  }

  function promptsCard(c) {
    return `<div class="card s12"><div class="label"><span class="num">6</span>Things to try right now</div>
      <h2>Paste any of these into Claude</h2><p class="muted small">Go back to the Claude window, paste, and watch this page change. Refresh this page after Claude says it is done.</p>
      <div class="prompts">${(c.prompts || []).map((p) => `<div class="prompt"><strong>${t(p.label)}</strong><code>${esc(p.prompt)}</code>${copyBtn(p.prompt)}</div>`).join("")}</div></div>`;
  }

  function nextCard(settings) {
    const n = settings.next || {};
    let video = `<div class="video"><div>${esc(n.videoPlaceholder || "Video coming soon")}</div></div>`;
    if (n.videoUrl) {
      video = /\.(mp4|webm|mov)(\?|$)/i.test(n.videoUrl)
        ? `<div class="video"><video src="${esc(n.videoUrl)}" controls playsinline></video></div>`
        : `<div class="video"><iframe src="${esc(n.videoUrl)}" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen title="What's next"></iframe></div>`;
    }
    return `<div class="card s12 next"><div class="grid" style="margin:0;padding:0;grid-template-columns:repeat(12,1fr);gap:24px;align-items:center">
      <div class="s5" style="grid-column:span 5"><div class="label" style="color:var(--gold)">What's next</div><h2>${esc(n.headline || "This is a glimpse.")}</h2>
      <p>${esc(n.text || "")}</p>${n.ctaUrl ? `<a class="btn" href="${esc(n.ctaUrl)}" target="_blank" rel="noopener">${esc(n.ctaText || "See how")}</a>` : ""}</div>
      <div class="s7" style="grid-column:span 7">${video}</div></div></div>`;
  }

  function render(c, g, settings) {
    const b = c.brand || {};
    const col = b.colors || {};
    if (col.primary) document.documentElement.style.setProperty("--brand", col.primary);
    if (col.accent) document.documentElement.style.setProperty("--brand-accent", col.accent);
    document.title = (c.business.person || c.business.name) + " · AI Preview";
    const first = String(c.business.person || "").replace(/^(dr|mr|mrs|ms)\.?\s+/i, "").split(/\s+/)[0] || "Here";
    document.getElementById("app").innerHTML = `
      <div class="hero"><div class="wrap"><div class="kicker">Built from your answers</div>
        <h1>${esc(first)}, here is what your AI built for ${esc(c.business.name)}.</h1>
        <p>You answered the questions once. Everything below came from those answers, with nothing else typed in. Click around: it is all yours to play with.</p>
        <div class="row"><a class="btn" href="site/index.html">Open your website</a><a class="btn ghost" href="site/free-guide.html">See your lead magnet</a></div>
      </div></div>
      <div class="wrap grid">${brandCard(c)}${gradeCard(g, c, settings)}${siteCard(c)}${magnetCard(c)}${auditCard(c)}${promptsCard(c)}${nextCard(settings)}</div>
      <footer>Everything on this page lives only on your computer. Nothing here is published or sent anywhere.</footer>`;

    document.body.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-copy]");
      if (!btn) return;
      const text = copies[btn.dataset.copy] || "";
      const done = () => toast("Copied. Paste it into Claude.");
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, () => fallback(text, done));
      else fallback(text, done);
    });
  }

  function fallback(text, done) {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); done(); } catch (e) { /* nothing else to try */ }
    ta.remove();
  }

  function toast(msg) {
    const d = document.createElement("div");
    d.className = "toast";
    d.setAttribute("role", "status");
    d.textContent = msg;
    document.body.appendChild(d);
    setTimeout(() => d.remove(), 2600);
  }

  Promise.all([get("data/content.json"), get("data/grade.json"), get("config/settings.json")]).then(([c, g, s]) => {
    if (!c) {
      document.getElementById("app").innerHTML = '<div class="loading"><h1>Not built yet</h1><p>Go back to Claude and say: <strong>build my preview</strong>.</p></div>';
      return;
    }
    c.business = c.business || {};
    render(c, g, s || {});
  });
})();
