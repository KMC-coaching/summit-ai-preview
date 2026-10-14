/*
 * Motion and forms for the sample website. Vanilla ports of the seeds'
 * Reveal.tsx, tb-client.tsx (HeroSlideshow, CountUp, AutoVideo) and the
 * Turnberry header. The pages are complete HTML without this file; it only
 * adds movement, so a visitor with scripts off still sees everything.
 */
(function () {
  "use strict";
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.documentElement.classList.add("js");
  // Shown as a thumbnail on the dashboard: no preview bar, no motion delay.
  if (window.self !== window.top) document.documentElement.classList.add("in-frame");

  /* Scroll reveal. Not IntersectionObserver on purpose: an anchor jump can skip
     the observer's sample and leave a section invisible (Reveal.tsx). */
  const pending = new Set(document.querySelectorAll(".reveal"));
  function sweep() {
    const line = window.innerHeight * 0.92;
    pending.forEach((el) => {
      if (el.getBoundingClientRect().top < line) { el.classList.add("in-view"); pending.delete(el); }
    });
    if (!pending.size) { window.removeEventListener("scroll", onScroll); window.removeEventListener("resize", onScroll); }
  }
  let ticking = false;
  function onScroll() { if (!ticking) { ticking = true; requestAnimationFrame(() => { ticking = false; sweep(); }); } }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  sweep();

  /* Header: transparent over the hero, hides on the way down, back on the way up. */
  const header = document.querySelector(".header");
  let lastY = window.scrollY;
  function headerState() {
    const y = window.scrollY;
    header.classList.toggle("is-top", y < 40);
    header.classList.toggle("is-solid", y >= 40);
    header.classList.toggle("is-down", y > lastY && y > 240);
    lastY = y;
  }
  if (header) { window.addEventListener("scroll", headerState, { passive: true }); headerState(); }

  /* Full-screen menu. */
  const burger = document.querySelector(".burger");
  const menu = document.getElementById("menu");
  if (burger && menu) {
    burger.addEventListener("click", () => {
      const open = !menu.classList.contains("is-open");
      menu.classList.toggle("is-open", open);
      document.body.classList.toggle("menu-open", open);
      header.classList.toggle("is-menu", open);
      burger.setAttribute("aria-expanded", String(open));
      burger.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });
  }

  /* Hero slideshow: cross-fade every 7.5s with a slow Ken Burns drift (CSS). */
  const slides = [...document.querySelectorAll(".hero__slide")];
  if (slides.length > 1 && !reduced) {
    let i = 0;
    // The first slide loads with the page; the rest load once the page is idle.
    const later = () => slides.slice(1).forEach((s) => { const im = s.querySelector("img[data-src]"); if (im) { im.src = im.dataset.src; im.removeAttribute("data-src"); } });
    window.addEventListener("load", () => setTimeout(later, 600));
    setInterval(() => {
      const out = slides[i];
      i = (i + 1) % slides.length;
      const inn = slides[i];
      if (inn.querySelector("img[data-src]")) return; // not loaded yet: wait a turn
      out.classList.remove("is-active");
      out.classList.add("is-leaving");
      inn.classList.add("is-active");
      setTimeout(() => out.classList.remove("is-leaving"), 3200);
    }, 7500);
  }

  /* Count-up stats: the real number is in the HTML; motion only starts it lower. */
  document.querySelectorAll("[data-count]").forEach((el) => {
    if (reduced) return;
    const target = Number(el.dataset.count);
    if (!isFinite(target) || el.getBoundingClientRect().top < window.innerHeight) return;
    const suffix = el.dataset.suffix || "";
    const from = Math.round(target * 0.6);
    el.textContent = from.toLocaleString("en-US") + suffix;
    const go = () => {
      if (el.getBoundingClientRect().top > window.innerHeight * 0.92) return;
      window.removeEventListener("scroll", go);
      const t0 = performance.now();
      const step = (t) => {
        const p = Math.min(1, (t - t0) / 1700);
        const v = Math.round(from + (target - from) * (1 - Math.pow(1 - p, 3)));
        el.textContent = v.toLocaleString("en-US") + suffix;
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    };
    window.addEventListener("scroll", go, { passive: true });
  });

  /* Video: nothing downloads until it is near the screen; paused for reduced motion. */
  document.querySelectorAll("video[data-src]").forEach((v) => {
    const load = () => {
      if (v.getBoundingClientRect().top > window.innerHeight * 1.5) return;
      window.removeEventListener("scroll", load);
      if (v.dataset.poster) v.poster = v.dataset.poster;
      v.src = v.dataset.src;
      v.removeAttribute("data-src");
      if (!reduced) v.play().catch(() => {});
    };
    window.addEventListener("scroll", load, { passive: true });
    load();
  });

  /* Forms. Preview only: nothing leaves this computer. */
  function toast(msg) {
    const d = document.createElement("div");
    d.className = "toast";
    d.setAttribute("role", "status");
    d.textContent = msg;
    document.body.appendChild(d);
    setTimeout(() => d.remove(), 6500);
  }
  const lead = document.getElementById("leadForm");
  if (lead) lead.addEventListener("submit", (e) => {
    e.preventDefault();
    const data = { first: lead.first.value.trim(), email: lead.email.value.trim(), at: new Date().toISOString() };
    try {
      localStorage.setItem("aipreview.lastLead", JSON.stringify(data));
      const all = JSON.parse(localStorage.getItem("aipreview.leads") || "[]");
      all.push(data);
      localStorage.setItem("aipreview.leads", JSON.stringify(all));
    } catch (err) { /* private window: the guide still opens */ }
    lead.hidden = true;
    const done = document.getElementById("leadDone");
    if (done) { done.classList.add("is-on"); done.focus(); }
  });
  const contact = document.getElementById("contactForm");
  if (contact) contact.addEventListener("submit", (e) => {
    e.preventDefault();
    toast("Preview only: nothing was sent. On your live site this lands in your inbox and your phone.");
  });
  const who = document.querySelector("[data-lead-name]");
  if (who) { try { const d = JSON.parse(localStorage.getItem("aipreview.lastLead") || "{}"); if (d.first) who.textContent = d.first; } catch (e) { /* fine */ } }
})();
