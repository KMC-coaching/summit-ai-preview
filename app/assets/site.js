/*
 * Renders the sample website from data/content.json.
 * Every page is the same shell; <body data-page="..."> picks what goes in <main>.
 * Nothing here leaves this computer: forms save to this browser only.
 */
(function () {
  "use strict";

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  // [Square-bracket text] is a placeholder for them to fill, never a fact we made up.
  const t = (s) => esc(s).replace(/\[([^\]]{2,300})\]/g, '<span class="ph">[$1]</span>');
  const paras = (s) => String(s || "").split(/\n{2,}/).map((p) => `<p>${t(p).replace(/\n/g, "<br>")}</p>`).join("");
  const list = (a) => (a || []).map((x) => `<li>${t(x)}</li>`).join("");
  const initials = (name) => String(name || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();

  const PAGES = [
    ["index.html", "Home"],
    ["about.html", "About"],
    ["services.html", "Services"],
    ["free-guide.html", "Free guide"],
    ["contact.html", "Contact"],
  ];

  function brand(c) {
    const b = c.brand || {};
    const col = b.colors || {};
    const r = document.documentElement.style;
    for (const k of ["primary", "accent", "ink", "paper"]) if (col[k]) r.setProperty("--" + k, col[k]);
    const f = b.fonts || {};
    const fams = [f.heading, f.body].filter(Boolean);
    if (fams.length) {
      const l = document.createElement("link");
      l.rel = "stylesheet";
      l.href = "https://fonts.googleapis.com/css2?" + fams.map((x) => "family=" + encodeURIComponent(x) + ":wght@400;600;700").join("&") + "&display=swap";
      document.head.appendChild(l);
      if (f.heading) r.setProperty("--h", `"${f.heading}", Georgia, serif`);
      if (f.body) r.setProperty("--b", `"${f.body}", system-ui, sans-serif`);
    }
  }

  // Structured data on every page: the thing the report card says their site is missing.
  function schema(c) {
    const biz = c.business || {};
    const s = document.createElement("script");
    s.type = "application/ld+json";
    const graph = [{
      "@type": "LocalBusiness",
      name: biz.name,
      description: biz.oneLiner,
      areaServed: biz.market,
      founder: { "@type": "Person", name: biz.person, jobTitle: biz.profession },
      telephone: biz.phone || undefined,
      email: biz.email || undefined,
    }];
    const faq = (c.site || {}).faq || [];
    if (faq.length) graph.push({
      "@type": "FAQPage",
      mainEntity: faq.map((f) => ({ "@type": "Question", name: f.q, acceptedAnswer: { "@type": "Answer", text: f.a } })),
    });
    s.textContent = JSON.stringify({ "@context": "https://schema.org", "@graph": graph });
    document.head.appendChild(s);
  }

  function chrome(c, page) {
    const biz = c.business || {};
    const label = page === "thank-you.html" ? "Thank you" : (PAGES.find((p) => p[0] === page) || [, "Home"])[1];
    document.title = label + " | " + (biz.name || "Preview");
    const desc = document.createElement("meta");
    desc.name = "description";
    desc.content = biz.oneLiner || "";
    document.head.appendChild(desc);

    const bar = `<div class="preview-bar">Preview. This site lives only on your computer. Nobody else can see it yet. <a href="../index.html">Back to your dashboard</a></div>`;
    const nav = PAGES.map(([href, label]) => `<a href="${href}"${href === page ? ' aria-current="page"' : ""}>${label}</a>`).join("");
    const header = `<header class="top"><div class="wrap"><a class="brand" href="index.html"><span class="mono" aria-hidden="true">${esc(initials(biz.name))}</span>${esc(biz.name)}</a><nav class="links" aria-label="Main">${nav}</nav></div></header>`;
    const footer = `<footer class="bottom"><div class="wrap"><div><strong>${esc(biz.name)}</strong><br>${t(biz.market)}${biz.phone ? " · " + esc(biz.phone) : ""}${biz.email ? " · " + esc(biz.email) : ""}</div><div>${t((c.brand || {}).tagline)}</div></div></footer>`;
    document.body.insertAdjacentHTML("afterbegin", bar + header);
    document.body.insertAdjacentHTML("beforeend", footer);
  }

  function magnetBand(c) {
    const m = c.leadMagnet || {};
    return `<section class="band"><div class="wrap"><div class="magnet">
      <div><div class="eyebrow" style="color:var(--accent)">Free ${esc(m.format || "guide")}</div>
      <h2>${t(m.title)}</h2><p>${t(m.hook)}</p>
      <a class="btn accent" href="free-guide.html">${esc(m.buttonText || "Get it free")}</a></div>
      <div class="cover"><span class="tag">Free</span><div class="t">${t(m.title)}</div><div>${esc((c.business || {}).name)}</div></div>
    </div></div></section>`;
  }

  const render = {
    "index.html"(c) {
      const h = (c.site || {}).home || {};
      const d = c.differentiator || {};
      return `
      <section class="hero"><div class="wrap">
        <div class="eyebrow">${t(c.business.profession)} · ${t(c.business.market)}</div>
        <h1>${t(h.heroHeadline)}</h1>
        <p class="sub">${t(h.heroSub)}</p>
        <div class="actions"><a class="btn" href="contact.html">${esc(h.primaryCta || "Get in touch")}</a><a class="btn alt" href="free-guide.html">${esc((c.leadMagnet || {}).title || "Free guide")}</a></div>
      </div></section>
      <section class="band"><div class="wrap split">
        <div><div class="eyebrow">Who this is for</div><h2>${t((c.avatar || {}).snapshot ? "Sound familiar?" : "Who we help")}</h2><p>${t((c.avatar || {}).snapshot)}</p></div>
        <ul class="check">${list(h.whoItsFor)}</ul>
      </div></section>
      <section class="band soft"><div class="wrap">
        <div class="eyebrow">${t(d.methodName)}</div><h2>${t(d.statement)}</h2>
        <div class="grid3">${(h.steps || []).map((s, i) => `<div class="card"><div class="n">${i + 1}</div><h3>${t(s.title)}</h3><p>${t(s.text)}</p></div>`).join("")}</div>
      </div></section>
      ${magnetBand(c)}
      <section class="band"><div class="wrap doc"><div class="eyebrow">Questions</div><h2>What people ask first</h2>
        ${((c.site || {}).faq || []).map((f) => `<details class="faq"><summary>${t(f.q)}</summary><p>${t(f.a)}</p></details>`).join("")}
      </div></section>
      <section class="band soft"><div class="wrap" style="text-align:center"><h2>${t(h.closingHeadline)}</h2><p>${t(h.closingText)}</p><a class="btn" href="contact.html">${esc(h.primaryCta || "Get in touch")}</a></div></section>`;
    },
    "about.html"(c) {
      const a = (c.site || {}).about || {};
      const d = c.differentiator || {};
      return `
      <section class="hero"><div class="wrap"><div class="eyebrow">About ${t(c.business.person)}</div><h1>${t(a.headline)}</h1></div></section>
      <section class="band"><div class="wrap split"><div>${(a.story || []).map((p) => `<p>${t(p)}</p>`).join("")}</div>
        <div class="card"><div class="eyebrow">${t(d.methodName)}</div>${(d.pillars || []).map((p) => `<h3>${t(p.name)}</h3><p>${t(p.text)}</p>`).join("")}</div></div></section>
      <section class="band soft"><div class="wrap"><h2>What we stand for</h2><div class="grid3">${(a.values || []).map((v) => `<div class="card"><h3>${t(v.title)}</h3><p>${t(v.text)}</p></div>`).join("")}</div></div></section>
      ${magnetBand(c)}`;
    },
    "services.html"(c) {
      const s = (c.site || {}).services || {};
      return `
      <section class="hero"><div class="wrap"><div class="eyebrow">Services</div><h1>${t(s.headline)}</h1><p class="sub">${t(s.intro)}</p></div></section>
      <section class="band"><div class="wrap grid3">${(s.items || []).map((i) => `<div class="card"><h3>${t(i.name)}</h3><p style="color:var(--muted);font-size:.92rem">For: ${t(i.for)}</p><p>${t(i.text)}</p><p><strong>${t(i.outcome)}</strong></p></div>`).join("")}</div></section>
      ${magnetBand(c)}`;
    },
    "free-guide.html"(c) {
      const m = c.leadMagnet || {};
      return `
      <section class="hero"><div class="wrap split">
        <div><div class="eyebrow">Free ${esc(m.format || "guide")}</div><h1>${t(m.title)}</h1><p class="sub">${t(m.subtitle)}</p><ul class="check">${list(m.bullets)}</ul></div>
        <div class="panel card"><h3>${t(m.formHeadline)}</h3>
          <form class="lead" id="leadForm">
            <div><label for="fn">First name</label><input id="fn" name="first" autocomplete="given-name" required></div>
            <div><label for="em">Email</label><input id="em" name="email" type="email" autocomplete="email" required></div>
            <button class="btn" type="submit">${esc(m.buttonText || "Send it to me")}</button>
            <p style="font-size:.82rem;color:var(--muted);margin:0">Preview: this saves only in this browser. Nothing is sent.</p>
          </form></div>
      </div></section>`;
    },
    "thank-you.html"(c) {
      const m = c.leadMagnet || {};
      let who = {};
      try { who = JSON.parse(localStorage.getItem("summit.lastLead") || "{}"); } catch (e) { /* private window */ }
      const name = who.first ? esc(who.first) : "there";
      return `
      <section class="hero"><div class="wrap"><div class="eyebrow">It's on its way</div><h1>Thanks, ${name}. Here is your ${esc(m.format || "guide")}.</h1>
        <p class="sub">In the real version, this lands in their inbox and three follow-up emails go out on their own. Below is exactly what they would get.</p></div></section>
      <section class="band"><div class="wrap doc"><h2>${t(m.title)}</h2><p>${t(m.subtitle)}</p>
        ${(m.sections || []).map((s) => `<section><h3>${t(s.heading)}</h3>${paras(s.body)}</section>`).join("")}
        <p style="margin-top:20px"><strong>${t(m.closing)}</strong></p></div></section>
      <section class="band soft"><div class="wrap"><div class="eyebrow">The follow-up that runs itself</div><h2>What happens after someone signs up</h2>
        <div class="flow">${(m.emails || []).map((e) => `<div class="step"><div class="day">Day ${esc(e.day)}</div><div class="email"><div class="meta">Subject</div><strong>${t(e.subject)}</strong><div class="body" style="margin-top:10px">${t(e.body)}</div></div></div>`).join("")}</div>
      </div></section>`;
    },
    "contact.html"(c) {
      const k = (c.site || {}).contact || {};
      const b = c.business || {};
      return `
      <section class="hero"><div class="wrap split"><div><div class="eyebrow">Contact</div><h1>${t(k.headline)}</h1><p class="sub">${t(k.text)}</p>
        <p>${b.phone ? "Phone: " + esc(b.phone) + "<br>" : ""}${b.email ? "Email: " + esc(b.email) + "<br>" : ""}${t(b.market)}</p></div>
        <div class="panel card"><form class="lead" id="contactForm">
          <div><label for="cn">Name</label><input id="cn" required autocomplete="name"></div>
          <div><label for="ce">Email</label><input id="ce" type="email" required autocomplete="email"></div>
          <div><label for="cm">What can we help with?</label><input id="cm"></div>
          <button class="btn" type="submit">${esc(((c.site || {}).home || {}).primaryCta || "Send")}</button>
        </form></div></div></section>`;
    },
  };

  function toast(msg) {
    const d = document.createElement("div");
    d.className = "toast";
    d.setAttribute("role", "status");
    d.textContent = msg;
    document.body.appendChild(d);
    setTimeout(() => d.remove(), 6000);
  }

  function wire() {
    const lead = document.getElementById("leadForm");
    if (lead) lead.addEventListener("submit", (e) => {
      e.preventDefault();
      const data = { first: lead.first.value.trim(), email: lead.email.value.trim(), at: new Date().toISOString() };
      try {
        localStorage.setItem("summit.lastLead", JSON.stringify(data));
        const all = JSON.parse(localStorage.getItem("summit.leads") || "[]");
        all.push(data);
        localStorage.setItem("summit.leads", JSON.stringify(all));
      } catch (err) { /* private window: the thank-you page still works without a name */ }
      location.href = "thank-you.html";
    });
    const contact = document.getElementById("contactForm");
    if (contact) contact.addEventListener("submit", (e) => {
      e.preventDefault();
      toast("Preview only: nothing was sent. On a live site, this message goes straight to you and you get a text.");
    });
  }

  const page = document.body.dataset.page;
  fetch("../data/content.json", { cache: "no-store" })
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((c) => {
      c.business = c.business || {};
      brand(c);
      schema(c);
      chrome(c, page);
      document.querySelector("main").innerHTML = (render[page] || render["index.html"])(c);
      wire();
    })
    .catch(() => {
      document.querySelector("main").innerHTML = '<div class="wrap" style="padding:60px 20px"><h1>Not built yet</h1><p>Your preview has not been generated. Go back to Claude and say: <strong>build my preview</strong>.</p></div>';
    });
})();
