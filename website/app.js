"use strict";
/* Find Us / Crowd Compass — interactive explainer shell.
   Owns: hash routing, the simulation host (buttons/loop/lifecycle), readouts,
   tier switching, and the walkthrough-player plumbing. All sim logic lives in
   sims.js and registers via window.SIMS. */

(function () {
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  window.dom = { $, $$ };

  // Deterministic PRNG so every reset reproduces the same world (and the
  // walkthrough player renders the same frame for the same scrub position).
  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  window.Utils = {
    prng: mulberry32,
    clamp: (v, lo, hi) => Math.max(lo, Math.min(hi, v)),
    fmtMs: (v) => (v * 1000).toFixed(1) + " ms",
    fmtHz: (v) => v.toFixed(1) + " frames/s",
  };

  /* ---------------- routing ---------------- */
  const pages = dom.$$("[data-page]");
  const tabLinks = dom.$$("#tabs a");
  function show(name) {
    pages.forEach((p) => { p.hidden = p.dataset.page !== name; });
    tabLinks.forEach((a) => a.classList.toggle("active", a.dataset.tab === name));
  }
  function route() {
    const key = (location.hash || "#overview").replace("#", "");
    show((key && dom.$(`[data-page="${key}"]`)) ? key : "overview");
  }
  window.addEventListener("hashchange", route);
  route();

  /* ---------------- sim host ---------------- */
  window.SIMS = window.SIMS || {};

  function mkContext(canvas) {
    const ctx = canvas.getContext("2d");
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const cssW = canvas.clientWidth || canvas.width;
    const cssH = canvas.clientHeight || canvas.height;
    canvas.width = cssW * dpr;
    canvas.height = cssH * dpr;
    ctx.scale(dpr, dpr);
    return { ctx, W: cssW, H: cssH, DPR: dpr };
  }

  class Host {
    constructor(canvas) {
      this.canvas = canvas;
      this.name = canvas.dataset.sim;
      this.def = window.SIMS[this.name];
      this.card = canvas.closest(".sim-card");
      this.run = false;
      this.t = 0;
      this.c = mkContext(canvas);
      // Mix the SIM's methods + data onto the host so sims can call sibling
      // methods via `this` (e.g. advance → this.onStep), like a prototype.
      Object.assign(this, this.def);
      this.def.reset.call(this);
      this.bind();
    }
    bind() {
      const card = this.card;
      dom.$$("[data-sim-btn]", card).forEach((btn) => {
        btn.addEventListener("click", () => {
          const fn = btn.dataset.simBtn;
          if (fn === "reset") { this.run = false; this.t = 0; this.def.reset.call(this); this.draw(); }
          else if (fn === "play") { this.play(); }
          else if (fn === "pause") { this.pause(); }
          else if (fn === "step") { this.step(); }
        });
      });
      if (this.name === "player") this.bindPlayerExtras();
    }
    bindPlayerExtras() {
      const scrub = dom.$("#w-scrub");
      if (scrub) {
        scrub.addEventListener("input", () => {
          this.run = false;
          this.t = Number(scrub.value);
          this.draw();
        });
      }
      dom.$$("[data-scene]").forEach((b) => {
        b.addEventListener("click", () => {
          this.setScene(Number(b.dataset.scene));
          dom.$$("[data-scene]").forEach((x) => x.classList.toggle("active", x === b));
        });
      });
    }
    play() { this.run = true; }
    pause() { this.run = false; }
    step() {
      if (this.def.step) this.def.step.call(this);
      else if (this.def.advance) this.def.advance.call(this, 1 / 30);
      else this.def.tick.call(this, 1, ++this.t);
      this.draw();
    }
    setScene(i) { this.def.setScene && this.def.setScene.call(this, i); this.run = false; this.draw(); }
    draw() {
      // Re-create the context if the canvas is being shown for the first time
      // (hidden tabs start 0×0) or the layout actually changed.
      const cw = this.canvas.clientWidth || this.canvas.width;
      const ch = this.canvas.clientHeight || this.canvas.height;
      if (cw !== this.c.W || ch !== this.c.H) this.c = mkContext(this.canvas);
      const g = this.c;
      g.ctx.save();
      // Draw in CSS-pixel space over a DPR-scaled bitmap.
      g.ctx.setTransform(g.DPR, 0, 0, g.DPR, 0, 0);
      this.def.draw.call(this, g);
      g.ctx.restore();
      const ro = dom.$("#" + this.name + "-readout");
      if (ro && this.read) ro.textContent = this.read;
    }
    loop(dt) {
      if (!this.run) return;
      const dts = this.def.speed ? dt * this.def.speed : dt;
      this.t += dts;
      this.def.advance ? this.def.advance.call(this, dts) : this.def.tick.call(this, dts, this.t);
      this.draw();
    }
  }

  const hosts = [];
  function scanHosts() {
    dom.$$("canvas[data-sim]").forEach((cv) => {
      if (cv._host) return;
      const host = new Host(cv);
      cv._host = host;
      hosts.push(host);
      host.draw();
    });
  }

  // Global play/pause when the page is hidden.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) hosts.forEach((h) => { h.run = false; });
  });

  let last = performance.now();
  function raf(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    hosts.forEach((h) => h.loop(dt));
    requestAnimationFrame(raf);
  }

  /* ---------------- tier switch ---------------- */
  const TIER_DESC = {
    gradient: "Gradient is the ground floor: every device knows only its adopted hop. Guidance says: pick the freshest neighbour claiming hop-1. No compass, no maths — just freshness and the one-hop rule.",
    rssiBand: "Before any ranging, even a BLE4 phone can say CLOSE vs FAR: RSSI above a threshold = near, below = far. That is already enough to steer around corners: move until the bad neighbour gets NEAR.",
    rssiLog: "RSSI decays with log-distance in the clear. Two phones can stretch RSSI into a coarse range estimate — but walls and crowds twist the constant, which is exactly why the coefficients are a NOT-RUN, field-open question.",
    heading: "A phone with a magnetometer can hold a heading. When a peer reports a CL-relative bearing, your compass turns it into 'walk 023° until the hop drops'. This needs the bearing source to be honest (see rotate-to-find).",
    motion: "An IMU integrates steps into a motion vector: your direction of travel, your own pace. Dead reckoning keeps the arrow pointing the way you actually walked, even when no radio measurement is available this second.",
    sweep: "Rotate-to-find: sweep 360°, log RSSI vs device bearing, take the peak. On plain phones this is RSSI-class observation, not AoA hardware. The manuscript is explicit: bearings from sweeps are provisional on experiments E17 — honesty over fantasy.",
    baro: "Barometric pressure differences stack with height. A baro differential between two phones bins into an elevation delta — with a FLOOR_UNCERTAINTY bin because HVAC and weather drafts are real. Cross-floor resolution is E21/E22, NOT-RUN.",
  };
  const TIER_CAPTION = {
    gradient: "The only tier every phone has. Risk: none — it is purely topological.",
    rssiBand: "Cheap and robust. Risk: a metal wall reads 'distance' when it is really attenuation.",
    rssiLog: "Needs a live peer link and calibrated constants. Risk: multi-path makes meters optimistic.",
    heading: "Needs a magnetometer and a believable bearing. Risk: indoors, steel rebar bends the compass.",
    motion: "Needs an IMU. Risk: drift — the vector is only as good as the last trusted fix.",
    sweep: "Needs motion (spinning in place). Risk: RSSI variance can fake a peak. Provisional on E17.",
    baro: "Needs two devices and careful calibration. Risk: drafts. Floor bins are a research target.",
  };
  function buildTierSwitch() {
    const band = dom.$("#tier-switch");
    if (!band) return;
    band.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-tier]");
      if (!btn) return;
      dom.$$("button[data-tier]", band).forEach((x) => x.classList.toggle("active", x === btn));
      const name = btn.dataset.tier;
      dom.$("#tier-title").textContent = {
        gradient: "Hop gradient",
        rssiBand: "RSSI near / far band",
        rssiLog: "RSSI log-distance",
        heading: "Compass relative heading",
        motion: "IMU motion vector",
        sweep: "Rotate-to-find",
        baro: "Elevation / floor",
      }[name];
      const tierHost = hosts.find((h) => h.name === "tiers");
      if (tierHost) { tierHost.run = false; tierHost.t = 0; tierHost.def.setTier.call(tierHost, name); tierHost.draw(); }
      dom.$("#tier-desc").innerHTML =
        "<b>Gist</b><span>" + TIER_DESC[name] + "</span>" +
        "<b>Method</b><span>" + tierMethod(name) + "</span>";
      dom.$("#tier-caption").innerHTML = "Risk: " + TIER_CAPTION[name];
      dom.$("#tier-status").innerHTML = statusTag(name);
    });
  }
  function tierMethod(name) {
    return {
      gradient: "adopt hop H when a live H−1 claim is fresher; advertise only while backed",
      rssiBand: "threshold on dBm into NEAR/FAR; guide on band transitions",
      rssiLog: "d = d0·10^((P0−R)/10n) with n from live link calibration",
      heading: "bearing from peer + compass heading fused; CL-relative",
      motion: "step detection → unit step vectors; integrate over time",
      sweep: "360° sample of RSSI vs heading; peak = presumed bearing (RSSI-class)",
      baro: "ΔP → Δelevation via hypsometric formula; bin to floors or FLOOR_UNCERTAINTY",
    }[name];
  }
  function statusTag(name) {
    const open = { sweep: 1, rssiLog: 1, baro: 1 };
    if (open[name]) return "<b>FIELD OPEN</b> — physics modelled, field coefficients not yet measured";
    return "<b>IMPLEMENTED</b> in the engine (Kotlin + Swift) — tier negotiation is live in both apps";
  }

  /* ---------------- concepts curriculum ---------------- */
  function renderConcepts() {
    const root = dom.$("#concepts-root");
    if (!root || !window.CONCEPTS) return;
    const CHIP_CLS = { measured: "chip-measured", model: "chip-model", open: "chip-open", notrun: "chip-notrun" };
    let h = '<nav class="concepts-jump">';
    window.CONCEPTS.forEach((ch, i) => { h += '<a href="#chap' + i + '">' + ch.chapter.split("·")[0].trim() + "</a>"; });
    h += "</nav>";
    window.CONCEPTS.forEach((ch, i) => {
      h += '<section class="conch" id="chap' + i + '">';
      h += "<h3>" + ch.chapter + "</h3>";
      if (ch.lead) h += '<p class="conlead">' + ch.lead + "</p>";
      ch.items.forEach((it) => {
        h += '<div class="con">';
        h += '<div class="con-h"><b class="ct">' + it.term + "</b>" +
          '<span class="chip ' + (CHIP_CLS[it.cls] || "chip-open") + '">' + it.tag + "</span></div>";
        h += '<p class="ca">' + it.ans + "</p>";
        h += "</div>";
      });
      h += "</section>";
    });
    root.innerHTML = h;
  }

  /* ---------------- init ---------------- */
  window.addEventListener("resize", () => {
    hosts.forEach((h) => { h.c = mkContext(h.canvas); h.draw(); });
  });

  // Boot order: build switch + scan (defines SIMS module in sims.js loaded after
  // app.js, so scanning must happen when both scripts exist).
  document.addEventListener("DOMContentLoaded", () => {
    renderConcepts();
    buildTierSwitch();
    scanHosts();
    requestAnimationFrame(raf);
  });
})();