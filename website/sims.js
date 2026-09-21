"use strict";
/* Find Us / Crowd Compass — simulation engines.
   Each SIM is registered into window.SIMS for the host in app.js. A SIM is an
   object with: reset(), tick(dt, t) OR advance(dt), draw(ctx), optional
   step()/setTier()/setScene(), optional speed (sim-seconds per real second).

   Honesty: every SIM is a teaching port of the repo engine's *rules*
   (adopt-on-live-fresher-claim, one-hop backing, TTL/dedup/freshness). None of
   them are field measurements. Readouts say which is which. */

(function () {
  // ---- palette ----
  const C = {
    bg: "#0a0e14", ok: "#7ee787", warn: "#f2cc60", bad: "#ff7b72",
    accent: "#4cc2ff", dim: "#9aa7b6", line: "#2a3243", ink: "#e6edf3",
    hop: ["#ff7b72", "#7ee787", "#f2cc60", "#4cc2ff", "#b39dff"],
  };
  function circle(g, x, y, r, fill, stroke, lw) {
    const ctx = g.ctx;
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw || 1.5; ctx.stroke(); }
  }
  function line(g, x1, y1, x2, y2, color, w, dash) {
    const ctx = g.ctx;
    ctx.strokeStyle = color; ctx.lineWidth = w || 1.5; ctx.setLineDash(dash || []);
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
    ctx.setLineDash([]);
  }
  function text(g, s, x, y, color, size, align) {
    const ctx = g.ctx;
    ctx.fillStyle = color || C.dim;
    ctx.font = (size || 12) + "px " + (g.font || "ui-monospace, Menlo, monospace");
    ctx.textAlign = align || "left"; ctx.textBaseline = "middle";
    ctx.fillText(s, x, y);
  }
  function muted(ctx, alpha) { ctx.save(); ctx.globalAlpha = alpha; }
  function phone(g, x, y, label, hopC, r) {
    circle(g, x, y, r || 13, "#121a28", hopC || C.dim, 2);
    text(g, label, x, y, C.ink, 11, "center");
  }
  const P = { mulberry32: (s) => { let a = s >>> 0; return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; } };

  /* ============================================================
     MESH ENTRY — how a third device joins a working mesh
     ============================================================ */
  const MESH_STEPS = 7;
  window.SIMS["mesh-entry"] = {
    speed: 1,
    reset() {
      if (!this._ptr) {
        this._ptr = true;
        // allow replay by re-reading log/state nodes each draw
      }
      this.fStep = 0;
      this.foreignSpawned = false;
      this._auto = 0;
      this.state = { foreignRejected: 0, hopsAdopted: 0, macOk: 0, edges: 0 };
      this.frame = 0;
    },
    advance(dt) {
      this._auto += dt;
      if (this._auto >= 1.7) {
        this._auto = 0;
        if (this.fStep < MESH_STEPS - 1) { this.fStep += 1; this.onStep(); }
        else { this.run = false; }
      }
    },
    step() {
      if (this.fStep < MESH_STEPS - 1) this.fStep += 1;
      this.onStep();
    },
    onStep() {
      const s = Math.floor(this.fStep);
      const log = dom.$("#mesh-log");
      const kv = dom.$("#mesh-state");
      const msgs = [
        "A new device (N) appears at the edge of radio range. It is running FindUs, has no idea what is nearby.",
        "N starts dual-role: it ADVERTISES its own identity heartbeat. Advertising is broadcast — even a joining phone is heard instantly.",
        "N's owner scans the incident link someone shared. The phone derives the same team key every responder derived, from the same text. No server.",
        "N hears R3's frame. Envelope MAC over (SOS_ID ‖ EPOCH ‖ PKT_TYPE) verifies → R3 may touch N's graph. A nearby spammer fails the same MAC and is counted but dropped.",
        "R3's claim is hop 3 and live (120 s freshness). N adopts hop 4. It now holds one honest number towards the origin.",
        "N may now advertise hop 4 — but only because R3's hop-3 claim is still live. The one-hop backing rule is in force.",
        "Done. N is a full relay: a third person just joined the mesh with no tower, no cloud, no account.",
      ];
      const stateLines = {
        0: [["Wire id", "hidden (no incident yet)"], ["Foreign rejected", "0"], ["Hops adopted", "none"]],
        1: [["Wire id", "hb-… local"], ["Advertising", "identity only"], ["Foreign rejected", "0"]],
        2: [["Team key", "derived from link"], ["Incident signed in", "yes"], ["Foreign rejected", "0"]],
        3: [["MAC verify R3", "PASS"], ["MAC verify spammer", "REJECT"], ["Foreign rejected", "1"]],
        4: [["Adopted hop", "4 (from R3, live)"], ["Backed by", "R3 @ hop 3"], ["Foreign rejected", "1"]],
        5: [["Advertising", "hop 4 (backed)"], ["Ghost rule", "active"], ["Foreign rejected", "1"]],
        6: [["Role", "full relay"], ["Hops held", "1 (hop 4)"], ["Graph edges", "1 (↔ R3)"]],
      };
      log.innerHTML = "";
      for (let i = 0; i <= s; i++) {
        const li = document.createElement("li");
        li.textContent = msgs[i];
        log.appendChild(li);
      }
      const sl = stateLines[s];
      kv.innerHTML = sl.map(([k, v]) => "<b>" + k + "</b><span>" + v + "</span>").join("");
    },
    draw(g) {
      const W = g.W, H = g.H;
      const ctx = g.ctx;
      ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
      const s = Math.floor(this.fStep);
      const unit = (W - 60) / 6;
      const srcX = 60, y0 = H / 2;
      const ex = 30;

      const nodes = [
        { x: srcX + unit * 0.5, y: y0 - 40, label: "O", hop: 0 },
        { x: srcX + unit * 1.5, y: y0 + 30, label: "R1", hop: 1 },
        { x: srcX + unit * 2.5, y: y0 - 30, label: "R2", hop: 2 },
        { x: srcX + unit * 3.5, y: y0 + 20, label: "R3", hop: 3 },
      ];
      // newcomer slides in from the right during steps 0..6
      const nx = srcX + unit * 4.2 + Math.max(0, 1 - (s + 1) / 6) * 240;
      const ny = y0 - 20;
      nodes[4] = { x: nx, y: ny, label: "N", hop: s >= 4 ? 4 : -1, active: true };

      // edges
      muted(ctx, 0.25);
      line(g, nodes[0].x, nodes[0].y, nodes[1].x, nodes[1].y, C.dim, 1, s >= 1 ? [] : [2,4]);
      line(g, nodes[1].x, nodes[1].y, nodes[2].x, nodes[2].y, C.dim, 1, s >= 1 ? [] : [2,4]);
      line(g, nodes[2].x, nodes[2].y, nodes[3].x, nodes[3].y, C.dim, 1, s >= 1 ? [] : [2,4]);
      ctx.restore();
      // entry edge (N-R3)
      if (s >= 3) line(g, nodes[3].x, nodes[3].y, nodes[4].x, nodes[4].y, C.ok, 2);

      const colourFor = (hop) => (hop < 0 ? C.dim : C.hop[Math.min(hop, 4)]);
      nodes.forEach((n, i) => {
        if (i === 4 && s < 3) { phone(g, n.x, n.y, "N", C.accent, 12); return; }
        phone(g, n.x, n.y, i === 4 ? "N" : n.label, colourFor(n.hop), 13);
        if (n.hop >= 0) text(g, "hop " + n.hop, n.x, n.y + 30, colourFor(n.hop) === C.dim ? C.dim : colourFor(n.hop), 11, "center");
      });

      // caption of current step
      const msgs = [
        "Step 1 · a stranger appears at the edge of range",
        "Step 2 · N advertises its identity — heard instantly, nothing asked",
        "Step 3 · Team key derived from the shared incident link",
        "Step 4 · R3's frame passes the envelope MAC; spammer rejected",
        "Step 5 · N adopts hop 4 — one honest number towards the origin",
        "Step 6 · N advertises hop 4, backed by R3's live hop-3 claim",
        "Step 7 · N is a relay. A third person just joined the mesh.",
      ];
      text(g, msgs[s], 30, H - 26, C.accent, 13);
      text(g, "● origin (hop 0)", 30, 26, C.hop[0], 11);
      text(g, s >= 3 ? "✓ MAC-passed link (counted, never stored if invalid)" : "radio range", W - 30, 26, C.dim, 11, "right");
      if (s >= 3) {
        circle(g, srcX + unit * 4.9, y0 - 70, 9, "#28222a", C.bad, 2);
        text(g, "spammer ✗", srcX + unit * 4.9, y0 - 88, C.bad, 11, "center");
      }
    },
  };

  /* ============================================================
     NAV TIERS
     ============================================================ */
  window.SIMS["tiers"] = {
    speed: 1,
    tier: "gradient",
    setTier(name) { this.tier = name; this.reset(); },
    attachPointer() {
      if (this._ptr) return; this._ptr = true;
      this.pointer = { active: false, move: false };
      const cv = this.canvas;
      const toPos = (e) => {
        const r = cv.getBoundingClientRect();
        const x = (e.clientX || e.touches[0].clientX) - r.left;
        const y = (e.clientY || e.touches[0].clientY) - r.top;
        return { x, y };
      };
      const down = (e) => { this.pointer.active = true; Object.assign(this.pointer, toPos(e)); };
      const move = (e) => {
        if (!this.pointer.active) return;
        Object.assign(this.pointer, toPos(e)); this.pointer.move = true;
      };
      const up = () => { this.pointer.active = false; };
      cv.addEventListener("mousedown", down); cv.addEventListener("mousemove", move);
      cv.addEventListener("mouseup", up); cv.addEventListener("mouseleave", up);
      cv.addEventListener("touchstart", down, { passive: true });
      cv.addEventListener("touchmove", move, { passive: true });
      cv.addEventListener("touchend", up);
    },
    reset() {
      this.attachPointer();
      this.angle = 0; this.t2 = 0;
      this.A = { x: 170, y: 210, r: 90 };
      this.B = { x: 640, y: 210, r: 90 };
      this.orientation = 0;
      this.steps = [];
      this.px = 200; this.py = 210;
      this.sweepSamples = [];
      this.baroNoise = 0;
    },
    tick(dt, t) {
      this.t2 += dt;
      // keep A/B draggable near their anchors when pointer active
      if (this.pointer && this.pointer.move) {
        if (this.tier === "rssiBand" || this.tier === "rssiLog") {
          const p = this.pointer;
          if (Math.hypot(p.x - this.B.x, p.y - this.B.y) < 46) this.B = { x: p.x, y: p.y };
          if (Math.hypot(p.x - this.A.x, p.y - this.A.y) < 46) this.A = { x: p.x, y: p.y };
        }
      }
      if (this.tier === "heading") this.angle = (this.angle + dt * 36) % 360;
      if (this.tier === "motion") {
        const heading = this.t2 * 40;
        this.steps.push({ x: this.px, y: this.py });
        this.px += Math.cos((heading * Math.PI) / 180) * 2.2;
        this.py += Math.sin((heading * Math.PI) / 180) * 2.2;
        if (this.steps.length > 60) this.steps.shift();
      }
      if (this.tier === "sweep") {
        this.angle = (this.angle + dt * 55) % 360;
        // log a couple samples per degree change
        if (this.sweepSamples.length < 120) {
          const az = this.angle;
          // signal stronger when the phone points at B
          const relAz = (Math.atan2(this.B.y - this.A.y, this.B.x - this.A.x) * 180) / Math.PI;
          const diff = Math.abs(az - relAz) % 360; const d = Math.min(diff, 360 - diff);
          this.sweepSamples.push({ az, rssi: -78 - d * 0.22 + (P.mulberry32(this.sweepSamples.length)() * 4 - 2) });
        }
        if (this.t2 > 8 && this.sweepSamples.length > 30 && !this.pour) {
          this.pour = true; // mark bearing ready once
        }
        if (this.t2 > 11) { this.t2 = 0; this.sweepSamples = []; this.pour = false; }
      }
      if (this.tier === "baro") this.baroNoise = Math.sin(this.t2 * 9) * 0.08 + (window.Utils ? Utils.clamp(Math.random() * 0.1 - 0.05, -0.2, 0.2) : 0);
    },
    draw(g) {
      this.drawTier(g, this.tier);
    },
    drawTier(g, tier) {
      const W = g.W, H = g.H;
      const ctx = g.ctx;
      ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
      g.font = "12px ui-monospace, Menlo, monospace";
      // RSSI tiers share draggable anchors — keep them on the canvas whatever
      // the window size (default anchor B sits at x=640, off-screen on phones).
      if (tier === "rssiBand" || tier === "rssiLog") {
        this.A.x = Utils.clamp(this.A.x, 45, W - 45); this.A.y = Utils.clamp(this.A.y, 55, H - 55);
        this.B.x = Utils.clamp(this.B.x, 45, W - 45); this.B.y = Utils.clamp(this.B.y, 55, H - 55);
      }

      if (tier === "gradient") { this.gradientTier(g); }
      else if (tier === "rssiBand") { this.bandTier(g); }
      else if (tier === "rssiLog") { this.logTier(g); }
      else if (tier === "heading") { this.headingTier(g); }
      else if (tier === "motion") { this.motionTier(g); }
      else if (tier === "sweep") { this.sweepTier(g); }
      else if (tier === "baro") { this.baroTier(g); }
    },

    gradientTier(g) {
      const W = g.W, H = g.H;
      const chain = [0, 1, 2, 3, 4, 5];
      chain.forEach((hop, i) => {
        const x = 110 + i * 125, y = H / 2;
        circle(g, x, y, 15, "#121a28", C.hop[Math.min(hop, 4)], 3);
        text(g, "hop " + hop, x, y - 34, C.hop[Math.min(hop, 4)], 13, "center");
        text(g, hop === 0 ? "victim" : "responder", x, y + 32, C.dim, 11, "center");
        const pulse = (this.t2 * 1.4 + i) % 5;
        if (pulse < 1) circle(g, x + (i < 5 ? 55 : 0), y, 26, "rgba(78,194,255,0.10)");
        if (i < 5) line(g, x + 16, y, x + 109, y, C.accent, 2);
      });
      text(g, "grades: walk UP the chain toward hop 0 · ties broken by freshness (newest claim wins)", W / 2, H - 34, C.dim, 12, "center");
      text(g, "freshness 120 s · one live hop-1 claim is enough to keep advertising", W / 2, H - 16, C.dim, 12, "center");
    },

    bandTier(g) {
      const W = g.W, H = g.H;
      const dist = Math.hypot(this.A.x - this.B.x, this.A.y - this.B.y);
      const threshold = 210;
      const d = (dist - threshold) / 165; // -1..+~2
      const near = d <= 0;
      const peak = this.pointer && this.pointer.move ? 0 : 1;
      circle(g, this.A.x, this.A.y, 13, "#121a28", C.accent, 2);
      text(g, "you", this.A.x, this.A.y, C.accent, 12, "center");
      circle(g, this.B.x, this.B.y, 13, "#121a28", near ? C.ok : C.warn, 2);
      text(g, "peer", this.B.x, this.B.y, C.dim, 12, "center");
      circle(g, this.B.x, this.B.y, threshold, "rgba(126,231,135,0.06)", "rgba(126,231,135,0.35)", 1.5);
      text(g, "threshold band", this.B.x + threshold + 24, this.B.y - threshold, C.ok, 11);
      text(g, "drag the PEER into/out of the band →", W / 2, 24, C.dim, 12, "center");
      text(g, near ? "NEAR — steer toward it" : "FAR — move until the band flips", W / 2, H - 22, near ? C.ok : C.warn, 15, "center");
      text(g, "no range number, only a band — BLE4 safe", W / 2, H - 4, C.dim, 11, "center");
    },

    logTier(g) {
      const W = g.W, H = g.H;
      const dist = Math.max(22, Math.hypot(this.A.x - this.B.x, this.A.y - this.B.y));
      const n = 2.4, d0 = 1, P0 = -55;
      const rssi = P0 + 10 * n * Math.log10(dist / d0);
      const est = d0 * Math.pow(10, (P0 + 62) / (10 * n)); // cosmetic anchor
      line(g, 20, H - 30, W - 20, H - 30, C.line, 1);
      line(g, 40, 120, W - 40, 120, C.dim, 0.6);
      circle(g, this.A.x, this.A.y, 13, "#121a28", C.accent, 2);
      text(g, "you", this.A.x, this.A.y, C.accent, 12, "center");
      circle(g, this.B.x, this.B.y, 13, "#121a28", C.ok, 2);
      text(g, "peer", this.B.x, this.B.y, C.dim, 12, "center");
      line(g, this.A.x, this.A.y, this.B.x, this.B.y, "rgba(78,194,255,0.25)", 2);
      const mx = Math.min(W - 60, 60 + (dist / 560) * (W - 120));
      circle(g, mx, H - 30, 5, C.warn);
      text(g, "RSSI ≈ " + rssi.toFixed(1) + " dBm → range ≈ " + est.toFixed(1) + " m", W / 2, H - 60, C.warn, 14, "center");
      text(g, "d = d0 · 10^((P0 − R)/10n)  — open-air model; walls & crowds twist n (that is a NOT-RUN problem)", W / 2, H - 8, C.dim, 11, "center");
      text(g, "drag peer → RSSI and estimate move together", W / 2, 24, C.dim, 12, "center");
    },

    headingTier(g) {
      const W = g.W, H = g.H;
      const cx = 300, cy = H / 2;
      const relAz = Math.atan2(this.B.y - this.A.y, this.B.x - this.A.x) * 180 / Math.PI;
      const my = this.angle;
      text(g, "compass heading " + my.toFixed(0) + "°", 30, 28, C.accent, 14);
      // compass rose
      circle(g, cx, cy, 150, "rgba(30,40,60,0.5)", C.line, 2);
      for (let a = 0; a < 360; a += 15) {
        const r1 = a % 90 === 0 ? 140 : 145;
        const rad = (a - 90) * Math.PI / 180;
        line(g, cx + Math.cos(rad) * r1, cy + Math.sin(rad) * r1,
          cx + Math.cos(rad) * 150, cy + Math.sin(rad) * 150, a % 90 === 0 ? C.ink : C.dim, 1);
      }
      const radHead = (my - 90) * Math.PI / 180;
      line(g, cx, cy, cx + Math.cos(radHead) * 90, cy + Math.sin(radHead) * 90, C.ink, 3);
      // desired bearing line
      const radB = (relAz - 90) * Math.PI / 180;
      line(g, cx, cy, cx + Math.cos(radB) * 110, cy + Math.sin(radB) * 110, C.ok, 2, [6,4]);
      circle(g, cx + Math.cos(radB) * 110, cy + Math.sin(radB) * 110, 6, C.ok);
      const turn = ((relAz - my + 540) % 360) - 180;
      text(g, "CL-relative bearing to peer " + relAz.toFixed(0) + "°", cx, cy - 176, C.dim, 12, "center");
      text(g, "turn " + (turn >= 0 ? "RIGHT " : "LEFT ") + Math.abs(turn).toFixed(0) + "°", cx, H - 30, turn < 6 && turn > -6 ? C.ok : C.warn, 16, "center");
      text(g, "indoors, rebar bends the compass — heading is a hint, never the whole map", cx, H - 10, C.dim, 11, "center");
    },

    motionTier(g) {
      const W = g.W, H = g.H;
      this.steps.forEach((s, i) => {
        if (i === 0) return;
        const p = this.steps[i - 1];
        line(g, p.x, p.y, s.x, s.y, i % 3 === 0 ? C.accent : C.dim, 1.5);
      });
      this.steps.forEach((s, i) => circle(g, s.x, s.y, 2.4, i === this.steps.length - 1 ? C.ok : C.dim));
      if (this.steps.length > 1) {
        const a = this.steps[this.steps.length - 1], b = this.steps[this.steps.length - 12];
        const dx = a.x - b.x, dy = a.y - b.y;
        const len = Math.hypot(dx, dy) || 1;
        const hx = a.x + (dx / len) * 26, hy = a.y + (dy / len) * 26;
        line(g, a.x, a.y, hx, hy, C.ok, 3);
        text(g, "motion vector (your own pace, no radio needed)", 30, 28, C.accent, 14);
        text(g, "last 12 steps → matters more than any single RSSI guess", W - 30, 28, C.dim, 12, "right");
        text(g, "drift warning: integrate too long without a fix and the arrow rotates", W / 2, H - 18, C.warn, 12, "center");
      } else {
        text(g, "walk a little — steps will accumulate into a motion vector", W / 2, H / 2 - 20, C.dim, 14, "center");
      }
    },

    sweepTier(g) {
      const W = g.W, H = g.H;
      const cx = 250, cy = 210;
      circle(g, cx, cy, 140, "rgba(20,30,45,0.5)", C.line, 2);
      line(g, cx, cy, cx, cy - 90, C.dim, 1.5, [4,4]);
      const radH = (this.angle - 90) * Math.PI / 180;
      line(g, cx, cy, cx + Math.cos(radH) * 60, cy + Math.sin(radH) * 60, C.warn, 4);
      // samples on right polar plot
      const sc = cx + 240;
      circle(g, sc + 130, cy, 130, "rgba(20,30,45,0.5)", C.line, 2);
      if (this.sweepSamples.length) {
        this.sweepSamples.forEach((s2) => {
          const r = 130 * Utils.clamp((s2.rssi + 95) / 40, 0, 1);
          const ang = (s2.az - 90) * Math.PI / 180;
          circle(g, sc + 130 + Math.cos(ang) * r, cy + Math.sin(ang) * r, 1.8, "rgba(126,231,135,0.55)");
        });
        // peak
        const best = this.sweepSamples.reduce((m, s2) => (s2.rssi > m.rssi ? s2 : m), this.sweepSamples[0]);
        const peakRad = (best.az - 90) * Math.PI / 180;
        line(g, sc + 130, cy, sc + 130 + Math.cos(peakRad) * 118, cy + Math.sin(peakRad) * 118, C.ok, 2);
        text(g, "bearing " + best.az.toFixed(0) + "°", sc + 130, cy - 160, C.ok, 13, "center");
      }
      text(g, "rotate-to-find (plain phone, RSSI-class)", 30, 28, C.accent, 14);
      text(g, "sweep 360° · record RSSI vs heading · pick the peak", W - 30, 28, C.dim, 12, "right");
      const note = this.pour ? "bearing noted — PROVISIONAL: sweep accuracy is experiment E17, still NOT-RUN" : "turning… samples accumulating on the right";
      text(g, note, W / 2, H - 18, this.pour ? C.warn : C.dim, 12, "center");
      text(g, "the arrow is RSSI-variance-shaped, not AoA hardware", 30, H - 18, C.dim, 11);
    },

    baroTier(g) {
      const W = g.W, H = g.H;
      // two phones on stacked floors
      const dPb = Utils.clamp((this.pointer && this.pointer.move ? (this.pointer.x / W) * 3 - 1.5 : 0.6) + this.baroNoise, -1.5, 1.5);
      const m = 8.4; // m per hPa
      const elev = dPb * m;
      const floor = Math.round(elev / 3.2);
      const uncertainty = Math.abs(elev - floor * 3.2) > 1.2;
      const baseH = 200;
      [-1, 0, 1].forEach((fl) => {
        line(g, 60, baseH - fl * 60 - 60, W - 60, baseH - fl * 60 - 60, C.line, 1);
        text(g, "floor " + fl, 40, baseH - fl * 60 - 60, C.dim, 11, "right");
      });
      // device A at floor 0, device B at computed floor
      const fax = 260, fb = Math.round(dPb * m / 3.2);
      circle(g, fax - 120, baseH - 0 * 60 - 60, 13, "#121a28", C.accent, 2);
      text(g, "A @ floor 0", fax - 120, baseH - 0 * 60 - 60, C.accent, 11, "center");
      const by = baseH - fb * 60 - 60;
      circle(g, fax + 80, Utils.clamp(by, 60, H - 60), 13, "#121a28", C.ok, 2);
      text(g, "B @ " + (uncertainty ? "~" : "") + "floor " + fb, fax + 80, Utils.clamp(by, 60, H - 60), C.ok, 11, "center");
      text(g, "ΔP = " + dPb.toFixed(2) + " hPa → Δelev ≈ " + (dPb * m).toFixed(1) + " m", W / 2, 34, C.warn, 14, "center");
      text(g, "move across the canvas horizontally to change the pressure delta", W / 2, 56, C.dim, 12, "center");
      text(g, uncertainty ? "FLOOR_UNCERTAINTY — drafts & HVAC corrupt the bin (E21/E22, NOT-RUN)" : "floor bin usable within tolerance", W / 2, H - 24, uncertainty ? C.warn : C.ok, 13, "center");
    },
  };

  /* ============================================================
     GRADIENT & GHOST RULE
     ============================================================ */
  window.SIMS["gradient"] = {
    speed: 6, // sim-seconds per real second
    reset() {
      this.range = Number((dom.$("#g-range") || {}).value || 150);
      this.originSilent = !!(dom.$("#g-fail") || {}).checked;
      const rng = P.mulberry32(424242);
      this.nodes = [];
      for (let i = 0; i < 42; i++) {
        this.nodes.push({
          x: 40 + rng() * 760, y: 40 + rng() * 340,
          hop: -1, lastAd: -1e9, live: false, ring: rng,
        });
      }
      this.T = 0;
      this.origin = { x: 70, y: 190, hop: 0, lastAd: 0, live: true };
      this.maxHop = 0; this.adopted = 1;
      // gradient slider + checkbox live binding (once)
      const range = dom.$("#g-range");
      if (range && !range._bound) { range._bound = true; range.oninput = () => { this.range = Number(range.value); }; }
      const fail = dom.$("#g-fail");
      if (fail && !fail._bound) { fail._bound = true; fail.onchange = () => { this.originSilent = fail.checked; }; }
    },
    tick(dt, t) {
      this.T += dt;
      const F = 20, P = 6; // freshness (sim-s) and advertise period
      // origin advertises unless silenced
      if (!this.originSilent && this.T - this.origin.lastAd > P) this.origin.lastAd = this.T;
      if (this.originSilent && this.T < 40) this.origin.lastAd = this.T; // live until the 40 s cut
      // adoption + backing pass
      this.adopted = 1; this.maxHop = 0; let liveCount = 0;
      for (const n of this.nodes) {
        let bestHop = -1;
        for (const o of [this.origin].concat(this.nodes)) {
          if (o === n) continue;
          if (o.hop < 0) continue;
          if (Math.hypot(o.x - n.x, o.y - n.y) > this.range) continue;
          if (this.T - o.lastAd > F) continue; // stale claim
          if (o.hop + 1 <= 8 && (bestHop < 0 || o.hop + 1 < bestHop)) bestHop = o.hop + 1;
        }
        n.hop = bestHop;
        if (bestHop >= 0) {
          this.adopted++;
          if (bestHop > this.maxHop) this.maxHop = bestHop;
          // advertise only if still backed (lastAd refreshes only while backed)
          if (this.T - n.lastAd > P && this.backed(n)) n.lastAd = this.T;
          if (this.T - n.lastAd <= F) liveCount++;
        }
      }
      this.liveCount = liveCount;
      this.stateLine = "adopted=" + this.adopted + " · maxHop=" + this.maxHop + " · live advertisers=" + liveCount +
        (this.originSilent && this.T >= 40 ? "  ← origin silent: gradient collapsing (ghost rule)" : "");
    },
    backed(n) {
      for (const o of [this.origin].concat(this.nodes)) {
        if (o === n || o.hop !== n.hop - 1) continue;
        if (Math.hypot(o.x - n.x, o.y - n.y) > this.range) continue;
        if (this.T - o.lastAd <= 20) return true;
      }
      return n.hop === 1 && this.T - this.origin.lastAd <= 20;
    },
    draw(g) {
      const W = g.W, H = g.H;
      const ctx = g.ctx;
      ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
      // links for backs
      const all = [this.origin].concat(this.nodes);
      for (let i = 0; i < all.length; i++) {
        for (let j = i + 1; j < all.length; j++) {
          const a = all[i], b = all[j];
          if (Math.hypot(a.x - b.x, a.y - b.y) <= this.range) {
            line(g, a.x, a.y, b.x, b.y, "rgba(140,150,170,0.12)", 1);
          }
        }
      }
      circle(g, this.origin.x, this.origin.y, 15, C.hop[0], C.ink, 2);
      text(g, "hop 0 · victim", this.origin.x, this.origin.y - 26, C.hop[0], 12, "center");
      if (this.originSilent && this.T >= 40) text(g, "✕ silent", this.origin.x + 22, this.origin.y + 22, C.bad, 11, "center");
      for (const n of this.nodes) {
        if (n.hop < 0) continue;
        const age = this.T - n.lastAd;
        const alive = age <= 20;
        circle(g, n.x, n.y, 11, "#121a28", alive ? C.hop[Math.min(n.hop, 4)] : "rgba(154,167,182,0.4)", 2);
        text(g, n.hop, n.x, n.y, alive ? C.ink : C.dim, 10, "center");
      }
      text(g, this.stateLine || "", W / 2, 22, C.accent, 13, "center");
      text(g, "colour = hop ring · dimmed/wireless circle = claim aged out (ghost killed)", W / 2, H - 14, C.dim, 11, "center");
      // ring range circle around origin hint
      circle(g, this.origin.x, this.origin.y, this.range, "rgba(78,194,255,0.05)", "rgba(78,194,255,0.25)", 1);
    },
  };

  /* ============================================================
     TRICKLE
     ============================================================ */
  window.SIMS["trickle"] = {
    speed: 1,
    reset() {
      this.count = Number((dom.$("#t-count") || {}).value || 12);
      this.window = 1200;
      const rng = P.mulberry32(1337);
      this.devices = [];
      for (let i = 0; i < this.count; i++) {
        this.devices.push({ slot: rng() * this.window, skew: 1 + (rng() - 0.5) * 0.5, on: rng() > 0.5 ? 1 : 0 });
      }
      this.T = 0;
      const tcount = dom.$("#t-count");
      if (tcount && !tcount._bound) { tcount._bound = true; tcount.oninput = () => { this.count = Number(tcount.value); this.reset(); }; }
    },
    tick(dt, t) { this.T += dt * 1000; if (this.T > this.window * 2) this.T %= this.window; },
    draw(g) {
      const W = g.W, H = g.H;
      const ctx = g.ctx;
      ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
      const slotW = (W - 60) / this.window;
      const rowH = H / Math.max(1, this.count);
      let bursts = 0;
      for (let i = 0; i < this.count; i++) {
        const d = this.devices[i];
        const y = i * rowH + rowH * 0.18;
        line(g, 40, i * rowH, W - 20, i * rowH, "rgba(42,50,67,0.6)", 1);
        text(g, "D" + (i + 1), 12, y + 4, C.dim, 10, "right");
        // slot within each window (draw two windows for continuity)
        for (let win = 0; win < 2; win++) {
          const tOff = this.T - this.window * win;
          const slotT = ((d.slot * d.skew - tOff) % this.window + this.window) % this.window;
          const x = 40 + slotT * slotW;
          circle(g, x, y + 4, 5, d.on ? C.accent : C.ok);
          bursts += d.on ? 1 : 0;
        }
      }
      const ceil = Math.ceil(bursts / 2);
      const duty = this.count ? (ceil / this.count) * (14 / this.window) : 0;
      text(g, "bursts in window: " + ceil + "/" + this.count, 40, H - 10, C.dim, 12);
      text(g, "avg airtime/device ≈ " + (duty * 100).toFixed(2) + "% (" + (duty * 1000 * this.count).toFixed(2) + " ms/s of RX) — the O(k) bound, not O(N)", W - 40, H - 10, C.accent, 12, "right");
      text(g, "↑ slots are jittered, so bursts rarely collide (red = exact overlap only when timing is unlucky)", W / 2, 16, C.dim, 11, "center");
    },
  };

  /* ============================================================
     SOS FLOOD · DEDUP · REJECTIONS
     ============================================================ */
  window.SIMS["dedup"] = {
    speed: 1,
    reset() {
      this.tb = 0;
      this.events = [];
      this.accepted = 0; this.dup = 0; this.rejected = 0;
      this.rng = P.mulberry32(99);
      const spam = dom.$("#d-spam");
      if (spam && !spam._bound) { spam._bound = true; spam.oninput = () => { this.spam = Number(spam.value); }; }
      this.spam = Number((dom.$("#d-spam") || {}).value || 40);
      this.sosSeq = new Set();
    },
    tick(dt, t) {
      this.tb += dt * 30;
      const arrivals = 3 + Math.floor(this.rng() * 3);
      for (let i = 0; i < arrivals; i++) {
        const r = this.rng();
        const kind = r < 0.5 ? "grad" : (r < 0.85 ? "dup" : "forg");
        if (kind === "forg" && this.rng() > this.spam / 80) continue;
        this.events.push({ x: 60 + this.tb * 14 % 760, kind });
        if (kind === "grad") this.accepted++;
        else if (kind === "dup") this.dup++;
        else this.rejected++;
      }
      if (this.events.length > 400) this.events = this.events.slice(-400);
    },
    draw(g) {
      const W = g.W, H = g.H;
      const ctx = g.ctx;
      ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
      line(g, 20, H / 2, W - 20, H / 2, C.line, 1);
      this.events.forEach((e) => {
        const c = e.kind === "grad" ? C.ok : (e.kind === "dup" ? "rgba(154,167,182,0.6)" : C.bad);
        const yv = e.kind === "grad" ? H / 2 - 70 : (e.kind === "dup" ? H / 2 + 20 : H / 2 + 70);
        circle(g, e.x % W, yv, 3, c);
      });
      text(g, "gradient updates (accepted)", 30, H / 2 - 78, C.ok, 12);
      text(g, "duplicates (absorbed by dedup window)", 30, H / 2 + 14, C.dim, 12);
      text(g, "foreign frames (MAC-rejected, counted)", 30, H / 2 + 64, C.bad, 12);
      text(g, "accepted=" + this.accepted + " · dup-absorbed=" + this.dup + " · rejected=" + this.rejected, W / 2, 26, C.accent, 14, "center");
      text(g, "every rejected frame is counted; not one touches the graph", W / 2, H - 12, C.dim, 12, "center");
    },
  };

  /* ============================================================
     MULE BURST
     ============================================================ */
  window.SIMS["mule"] = {
    speed: 1,
    reset() {
      const rng = P.mulberry32(7);
      this.clusterA = [];
      for (let i = 0; i < 8; i++) {
        this.clusterA.push({ x: 70 + rng() * 180, y: 60 + rng() * 240, hop: 1 + Math.floor(rng() * 3) });
      }
      this.clusterB = [];
      for (let i = 0; i < 8; i++) {
        this.clusterB.push({ x: 560 + rng() * 190, y: 60 + rng() * 240, hop: -1 });
      }
      this.muleX = 300;
      this.burst = -1;
      this.cache = 6;
      this.T = 0;
    },
    tick(dt, t) {
      this.T += dt;
      this.muleX += dt * 85;
      if (this.muleX > 545 && this.burst < 0) {
        this.burst = this.T;
        this.clusterB.forEach((n) => { n.hop = this.cache; });
      }
      this.cache = Math.max(1, 6 - Math.floor((this.muleX - 300) / 60));
    },
    draw(g) {
      const W = g.W, H = g.H;
      const ctx = g.ctx;
      ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
      line(g, 280, 20, 280, H - 20, "rgba(255,123,114,0.5)", 1, [4,4]);
      line(g, 545, 20, 545, H - 20, "rgba(126,231,135,0.5)", 1, [4,4]);
      text(g, "GAP", 282, 18, C.bad, 11);
      text(g, "radio gap (big corridor, thick wall)", 545, H - 8, C.dim, 11, "center");
      this.clusterA.forEach((n) => {
        circle(g, n.x, n.y, 11, "#121a28", C.hop[Math.min(n.hop, 4)], 2);
        text(g, n.hop, n.x, n.y, C.ink, 10, "center");
      });
      this.clusterB.forEach((n) => {
        const alive = n.hop >= 0;
        circle(g, n.x, n.y, 11, "#121a28", alive ? C.hop[Math.min(n.hop, 4)] : "rgba(154,167,182,0.35)", 2);
        if (alive) text(g, n.hop, n.x, n.y, C.ink, 10, "center");
      });
      // mule
      circle(g, this.muleX, H / 2, 12, "#1c2536", C.warn, 2);
      text(g, "mule · cache " + this.cache + " hops", this.muleX, H / 2 + 30, C.warn, 11, "center");
      if (this.burst >= 0 && this.T - this.burst < 2.5) {
        for (let i = 0; i < 14; i++) {
          const a = (i / 14) * Math.PI * 2;
          line(g, 545, H / 2, 545 + Math.cos(a) * (60 + (this.T - this.burst) * 30), H / 2 + Math.sin(a) * (60 + (this.T - this.burst) * 30), "rgba(126,231,135,0.5)", 1);
        }
      }
      text(g, "MULE_STORE_FORWARD flag: a cached gradient physically carried across the gap", W / 2, 20, C.accent, 13, "center");
      text(g, "far side lights up once the burst lands — a second mesh joins the first", W / 2, H - 18, C.dim, 12, "center");
    },
  };

  /* ============================================================
     WALKTHROUGH PLAYER (3 scenes)
     ============================================================ */
  const P1 = P.mulberry32(2026);
  const SCENES = [
    {
      title: "Walkthrough 1 · The crowd flood",
      captions: [
        [0, "An emergency starts at the origin (red). It is the only device that holds hop 0."],
        [20, "Nearby phones adopt hop 1 — but only while they still hear the origin."],
        [50, "The gradient radiates outward ring by ring; each device holds one honest number."],
        [90, "Trickle keeps the broadcast bounded — O(k) small frames per second per receiver, not O(N)."],
        [130, "TTL 8 caps the radius: a gradient does not try to own the whole world."],
        [180, "Freshness clocks run: a clique that stops moving begins to age out normally."],
        [220, "Any phone now sees: ‘my hop, my freshest hop-1 neighbour — walk that way.’"],
        [270, "Crowd steady-state: bounded load, authenticated frames, honest topology."],
      ],
      build() { return { type: "flood" }; },
    },
    {
      title: "Walkthrough 2 · Mule across a gap",
      captions: [
        [0, "Two meshes, one emergency each. Between them: a radio gap too wide for hops."],
        [30, "A mule walks the gap carrying a cached gradient (MULE_STORE_FORWARD)."],
        [80, "The far side has been quiet — no claims, sleeping topology."],
        [140, "Burst! The cache lands and the far mesh lights up with adopted hops."],
        [200, "The two meshes now form one navigable gradient across the whole floor."],
        [260, "Delivery is as honest as the carrier: cached hops are labelled with their age."],
      ],
      build() { return { type: "mule2" }; },
    },
    {
      title: "Walkthrough 3 · Handoff & ghost collapse",
      captions: [
        [0, "Rescuers adopt hops 1–3 toward the origin. All arrows point inward. Good."],
        [40, "The victim is reached. The incident is marked resolved at the source."],
        [80, "The origin stops advertising its hop-0 claim."],
        [130, "Without a live hop 0, hop-1 devices lose their backing and fall silent — one ring at a time."],
        [190, "There is never a ghost gradient: nobody advertises a hop somebody else can no longer back."],
        [240, "Rescuers see routes dissolve honestly instead of walking toward a phantom."],
        [285, "Collapse complete in finite time. Honest subtraction beats invented directions."],
      ],
      build() { return { type: "collapse" }; },
    },
  ];

  window.SIMS["player"] = {
    speed: 1,
    setScene(i) {
      this.scene = i;
      this.reset();
      this.t = 0;
      const s = SCENES[i];
      dom.$("#w-title").textContent = s.title;
    },
    reset() {
      this.scene = this.scene || 0;
      const type = SCENES[this.scene].build().type;
      this.rng = P.mulberry32(2026);
      this.phones = [];
      if (type === "flood") {
        for (let i = 0; i < 60; i++) {
          this.phones.push({ x: 60 + this.rng() * 720, y: 50 + this.rng() * 320 });
        }
        this.origin = this.phones[0];
        this.origin.x = 90; this.origin.y = 200;
      } else if (type === "mule2") {
        for (let i = 0; i < 24; i++) this.phones.push({ x: 40 + this.rng() * 250, y: 50 + this.rng() * 320, zone: 0, hop: -1 });
        for (let i = 0; i < 24; i++) this.phones.push({ x: 560 + this.rng() * 230, y: 50 + this.rng() * 320, zone: 1, hop: -1 });
        this.mule = { x: 285, y: 200 };
      } else {
        for (let i = 0; i < 40; i++) this.phones.push({ x: 60 + this.rng() * 720, y: 50 + this.rng() * 320, hop: -1 });
        this.origin = this.phones[0];
        this.origin.x = 90; this.origin.y = 200;
      }
    },
    advance(dt) {
      this.t += dt * 30; // scene length ~10 s
      const max = 300;
      if (this.t >= max) { this.t = max; this.run = false; }
      const scrub = dom.$("#w-scrub");
      if (scrub) scrub.value = this.t;
    },
    draw(g) {
      const scene = SCENES[this.scene];
      const type = scene.build().type;
      const t = this.t;
      const W = g.W, H = g.H;
      const ctx = g.ctx;
      ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
      if (type === "flood" || type === "collapse") this.drawCrowd(g, t, type);
      else this.drawMuleScene(g, t);
      // caption
      let cap = scene.captions[scene.captions.length - 1][1];
      for (const [at, txt] of scene.captions) {
        if (t >= at) cap = txt;
      }
      dom.$("#w-caption").innerHTML = scene.captions.map(([at, txt]) =>
        "<li" + (t >= at ? ' class="capon"' : "") + ">" + at + "s · " + txt + "</li>").join("");
      const style = document.createElement("style");
      style.id = "capstyle";
      style.textContent = ".caption-list li.capon { color: #e6edf3; }";
      if (!dom.$("#capstyle")) document.head.appendChild(style);
      text(g, scene.title + "  ·  t = " + Math.floor(t) + " s", 30, 22, C.accent, 13);
    },
    drawCrowd(g, t, type) {
      const W = g.W, H = g.H;
      const expand = type === "flood";
      // determine hops geometrically from origin
      const origin = this.origin;
      const F = 20;
      for (const p of this.phones) {
        if (p === origin) continue;
        const d = Math.hypot(p.x - origin.x, p.y - origin.y);
        const hop = Math.min(8, Math.max(1, Math.ceil(d / 110)));
        p.hop = hop;
      }
      const originLive = !(type === "collapse" && t > 80);
      for (const p of this.phones) {
        if (p === origin) continue;
        const d = Math.hypot(p.x - origin.x, p.y - origin.y);
        const baseHop = Math.min(8, Math.max(1, Math.ceil(d / 110)));
        const collapseTo = type === "collapse" ? (t - 80) / 30 : -1; // rings die after 80 s
        const hop = originLive ? baseHop : Math.max(-1, baseHop - Math.floor(collapseTo));
        const alive = hop >= 0;
        const c = hop < 0 ? "rgba(154,167,182,0.25)" : C.hop[Math.min(hop, 4)];
        circle(g, p.x, p.y, 8, "#141b28", alive ? c : "rgba(154,167,182,0.3)", alive ? 1.5 : 1);
      }
      circle(g, origin.x, origin.y, 13, C.bad, C.ink, 2);
      text(g, "hop 0", origin.x, origin.y - 24, C.bad, 12, "center");
      if (type === "collapse" && t > 80) text(g, "✕ resolved", origin.x, origin.y + 24, C.bad, 11, "center");
      // range circles
      for (const r of [110, 220, 330]) {
        circle(g, origin.x, origin.y, r, "rgba(78,194,255,0.03)", "rgba(78,194,255,0.22)", 1);
      }
    },
    drawMuleScene(g, t) {
      const W = g.W, H = g.H;
      const m = this.mule;
      const dx = (t / 300) * 300;
      m.x = 285 + dx;
      // left zone phones
      this.phones.filter((p) => p.zone === 0 && p.hop < 0).forEach((p) => { p.hop = 1 + Math.floor(this.rng() * 3); });
      this.phones.forEach((p) => {
        if (p.zone === 0) {
          circle(g, p.x, p.y, 8, "#141b28", C.hop[Math.min(Math.max(p.hop, 1), 4)] || C.hop[1], 1.5);
          text(g, p.hop, p.x, p.y, C.ink, 9, "center");
        } else {
          const lit = m.x > 505 && p.hop > 0;
          const h = lit ? p.hop : -1;
          circle(g, p.x, p.y, 8, "#141b28", h < 0 ? "rgba(154,167,182,0.3)" : C.hop[Math.min(h, 4)], 1.5);
          if (h > 0) text(g, h, p.x, p.y, C.ink, 9, "center");
        }
      });
      line(g, 285, 20, 285, H - 20, "rgba(255,123,114,0.5)", 1, [4,4]);
      line(g, 540, 20, 540, H - 20, "rgba(126,231,135,0.5)", 1, [4,4]);
      circle(g, m.x, m.y, 10, "#1c2536", C.warn, 2);
      text(g, "mule (cached: 6 hops)", m.x, m.y + 26, C.warn, 11, "center");
      if (m.x > 500 && t < 260) {
        for (let i = 0; i < 12; i++) {
          const a = (i / 12) * Math.PI * 2;
          line(g, m.x, m.y, m.x + Math.cos(a) * 50, m.y + Math.sin(a) * 50, "rgba(126,231,135,0.6)", 1.5);
        }
      }
      // light right zone up
      if (m.x > 505) this.phones.filter((p) => p.zone === 1).forEach((p) => { if (p.hop < 0) p.hop = 2 + Math.floor(this.rng() * 3); });
      text(g, "HOT SIDE (has gradient)", 200, 36, C.accent, 12, "center");
      text(g, "COLD SIDE (sleeping)", 690, 36, C.dim, 12, "center");
    },
  };

  /* ============================================================
     RADIO FLOOR — channels, half-duplex, byte budget
     ============================================================ */
  window.SIMS["radio"] = {
    speed: 1,
    reset() {
      this.t = 0;
      this.period = 0.9; // advert cadence (s)
      this.burstW = 0.12; // on-air window (s)
      this.devices = [
        { ch: 0, slot: 0.10 },
        { ch: 0, slot: 0.46 },
        { ch: 1, slot: 0.22 },
        { ch: 2, slot: 0.60 },
      ];
      this.read = "press Run — the now-cursor sweeps one trickle-like period";
    },
    tick(dt, t) {
      this.t += dt;
      const P = this.period;
      // an advert slot coincides when two devices on the same channel
      // have slots closer than the on-air window (this period)
      const coincidents = this.devices.filter((d) => this.devices.some(
        (o) => o.ch === d.ch && o !== d && Math.abs(o.slot - d.slot) < this.burstW));
      this.read = "clock t = " + this.t.toFixed(1) + " s   ·   coincident advert slots this period: " + (coincidents.length ? coincidents.length + " (rare — jitter is the point)" : "none (jitter dodges the collision)");
    },
    draw(g) {
      const W = g.W, H = g.H;
      const ctx = g.ctx;
      ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
      const t = this.t, P = this.period;

      const colA = { x: 28, w: 300 };
      const colB = { x: 350, w: 290 };
      const colC = { x: 666, w: Math.max(60, W - 666 - 18) };

      // ---- zone A: three advertising channels ----
      text(g, "3 of 40 RF channels advertise (CH 37 · 38 · 39)", colA.x, 22, C.accent, 13);
      const y0 = 52, bandH = 58, gap = 14;
      const chans = ["CH 37 · 2402 MHz", "CH 38 · 2426 MHz", "CH 39 · 2480 MHz"];
      for (let c = 0; c < 3; c++) {
        const yb = y0 + c * (bandH + gap);
        ctx.fillStyle = "#101722"; ctx.fillRect(colA.x, yb, colA.w, bandH);
        line(g, colA.x, yb + bandH, colA.x + colA.w, yb + bandH, C.line, 1);
        text(g, chans[c], colA.x, yb + 12, C.dim, 10);
        this.devices.filter((d) => d.ch === c).forEach((d) => {
          for (let k = -1; k <= 2; k++) {
            const at = d.slot + k * P;
            const dx = (t - at) / P;            // fraction of the window
            if (dx < 0 || dx > 1) continue;
            const x = colA.x + dx * colA.w;
            const w2 = (this.burstW / P) * colA.w;
            ctx.fillStyle = c === 0 ? C.accent : (c === 1 ? C.ok : C.warn);
            ctx.fillRect(x, yb + 20, Math.max(3, w2), 16);
          }
        });
      }
      // "now" cursor sweeping the window
      const cx = colA.x + ((t / P) % 1) * colA.w;
      if (cx <= colA.x + colA.w) {
        line(g, cx, y0 - 6, cx, y0 + 3 * (bandH + gap) - 6, "#ffffff", 1.5);
        text(g, "now →", Math.min(W - 60, cx + 6), y0 - 12, C.ink, 10);
      }

      // ---- zone B: half-duplex trade between two phones ----
      text(g, "half-duplex: advert & scan must overlap", colB.x, 22, C.accent, 13);
      const advW = 0.18, scanW = 0.4;
      const rows = [
        { label: "phone A", adv0: 0.0, y: 80 },
        { label: "phone B", adv0: 0.5 * P, y: 150 },
      ];
      for (const r of rows) {
        text(g, r.label, colB.x, r.y - 8, C.ink, 11);
        ctx.fillStyle = "#101722"; ctx.fillRect(colB.x, r.y, colB.w, 34);
        const wrapAdv = ((t - r.adv0) % P + P) % P / P;
        const wrapScan = ((t - r.adv0 - P * 0.5) % P + P) % P / P;
        // advert block (teal) then scan block (greenish) each period
        ctx.fillStyle = "rgba(78,194,255,0.9)";
        ctx.fillRect(colB.x + wrapAdv * colB.w, r.y + 4, (advW / P) * colB.w, 12);
        ctx.fillStyle = "rgba(126,231,135,0.35)";
        ctx.fillRect(colB.x + wrapScan * colB.w, r.y + 20, (scanW / P) * colB.w, 12);
      }
      text(g, "■ advert", colB.x, 215, C.accent, 10);
      text(g, "■ scan", colB.x + 70, 215, C.ok, 10);
      // a trade exists when A's advert sits inside B's scan, or vice versa
      const wraps = {
        Aadv: ((t - 0) % P + P) % P / P,
        Ascan: ((t - P * 0.5) % P + P) % P / P,
        Badv: ((t - P * 0.5) % P + P) % P / P,
        Bscan: ((t - 0) % P + P) % P / P,
      };
      const inScan = (slotT, scanStart) => ((slotT - scanStart) % P + P) % P <= scanW;
      const trade = inScan(wraps.Aadv, wraps.Bscan) || inScan(wraps.Badv, wraps.Ascan);
      if (trade) {
        text(g, "⚡ TRADE — a peer was heard", colB.x, 250, C.ok, 11);
        text(g, "(adv from one has to land in the other's scan)", colB.x, 268, C.dim, 10);
      } else {
        text(g, "no trade this instant — overlap is stochastic", colB.x, 250, C.dim, 10);
      }

      // ---- zone C: byte budget under each ceiling ----
      text(g, "the 13 B frame vs the ceilings", colC.x, 22, C.accent, 13);
      const bars = [
        { label: "56-bit core + Hamming FEC", b: 13, col: C.accent, y: 70 },
        { label: "Android Type-0xFF ceiling", b: 27, col: C.warn, y: 110 },
        { label: "iOS dual-AD ceiling", b: 23, col: C.ok, y: 150 },
      ];
      const scale = (colC.w - 60) / 27;
      for (const bb of bars) {
        text(g, bb.label, colC.x, bb.y - 6, bb.col, 10);
        ctx.fillStyle = "#101722"; ctx.fillRect(colC.x, bb.y, colC.w - 60, 20);
        ctx.fillStyle = bb.col;
        ctx.fillRect(colC.x, bb.y, bb.b * scale, 20);
        text(g, bb.b + " B", colC.x + Math.max(bb.b * scale + 6, 40), bb.y + 10, C.ink, 10);
      }
      line(g, colC.x + 13 * scale, 56, colC.x + 13 * scale, 190, C.ink, 1, [3, 3]);
      text(g, "13 B core fits both ceilings — the byte budget is closed", colC.x, 205, C.dim, 10);

      text(g, this.read || "", W / 2, H - 10, C.dim, 12, "center");
      text(g, "data channels 0–36 stream after discovery — advertising is the meet-the-neighbour floor", W / 2, H - 30, C.dim, 11, "center");
    },
  };

  /* ============================================================
     DIRECTION FINDING — what a phone can and cannot deliver
     ============================================================ */
  window.SIMS["dirfind"] = {
    speed: 1,
    reset() {
      this.t = 0;
      this.angle = 0;
      this.samples = [];
      this.peerDeg = 60;
      this.read = "sweep: rotating…";
    },
    tick(dt, t) {
      this.t += dt;
      this.angle = (this.angle + dt * 70) % 360;
      if (this.samples.length < 90 && this.t % 0.05 < 0.01) {
        const rel = Math.abs(((this.angle - this.peerDeg) % 360 + 360) % 360);
        const d = Math.min(rel, 360 - rel);
        this.samples.push({ az: this.angle, rssi: -80 - d * 0.35 + (P.mulberry32(this.samples.length)() * 3 - 1.5) });
      }
      if (this.t > 3.6) { this.t = 0; this.samples = []; }
      if (this.samples.length > 20) this.read = "peak bearing candidate ≈ " + bestBearing(this.samples).toFixed(0) + "°  ·  RSSI-class, provisional (E17)";
    },
    draw(g) {
      const W = g.W, H = g.H;
      const ctx = g.ctx;
      ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
      const panW = (W - 40) / 3;

      // ---- panel 1: AoA/AoD not available ----
      const p1x = 20, p1y = 60, p1w = panW, p1h = 300;
      ctx.fillStyle = "#101722"; ctx.fillRect(p1x, p1y, p1w, p1h);
      line(g, p1x, p1y, p1x + p1w, p1y + p1h, C.bad, 2);
      line(g, p1x + p1w, p1y, p1x, p1y + p1h, C.bad, 2);
      text(g, "AoA / AoD", p1x + p1w / 2, p1y + 26, C.bad, 14, "center");
      // tiny antenna-array glyph (crossed out)
      for (let i = 0; i < 4; i++) circle(g, p1x + p1w / 2 - 45 + i * 30, p1y + 90, 7, "#1c2536", C.bad, 2);
      text(g, "✕ needs a switched array + CTE IQ", p1x + p1w / 2, p1y + 140, C.bad, 11, "center");
      text(g, "not present on commodity phones", p1x + p1w / 2, p1y + 160, C.bad, 11, "center");
      text(g, "BLE 5.1 spec reality · acknowledged §39.1", p1x + p1w / 2, p1y + 200, C.dim, 10, "center");

      // ---- panel 2: swept-RSSI / rotate-to-find ----
      const p2x = p1x + panW + 10, p2y = p1y, p2w = panW, p2h = p1h;
      const cx = p2x + p2w / 2, cy = p2y + p2h / 2, R = Math.min(p2w, p2h) / 2 - 34;
      ctx.fillStyle = "#101722"; ctx.fillRect(p2x, p2y, p2w, p2h);
      circle(g, cx, cy, R, "rgba(20,30,45,0.5)", C.line, 1.5);
      for (let a = 0; a < 360; a += 30) {
        const rad = (a - 90) * Math.PI / 180;
        line(g, cx + Math.cos(rad) * (R - 8), cy + Math.sin(rad) * (R - 8), cx + Math.cos(rad) * R, cy + Math.sin(rad) * R, C.dim, 1);
      }
      // samples
      this.samples.forEach((s2) => {
        const r = R * (0.3 + 0.7 * ((-s2.rssi - 74) / 40));
        const rad = (s2.az - 90) * Math.PI / 180;
        circle(g, cx + Math.cos(rad) * r, cy + Math.sin(rad) * r, 2, "rgba(126,231,135,0.6)");
      });
      // rotating scan line
      const radH = (this.angle - 90) * Math.PI / 180;
      line(g, cx, cy, cx + Math.cos(radH) * (R - 16), cy + Math.sin(radH) * (R - 16), C.warn, 2.5);
      // true peer bearing
      const radB = (this.peerDeg - 90) * Math.PI / 180;
      line(g, cx, cy, cx + Math.cos(radB) * (R - 10), cy + Math.sin(radB) * (R - 10), C.ok, 2, [5, 3]);
      circle(g, cx + Math.cos(radB) * (R - 10), cy + Math.sin(radB) * (R - 10), 6, C.ok);
      text(g, "swept-RSSI rotate-to-find", p2x + p2w / 2, p2y + 20, C.accent, 13, "center");
      text(g, "green = peer · amber = scan line · dots = RSSI", p2x + p2w / 2, p2y + p2h - 12, C.dim, 10, "center");

      // ---- panel 3: torso-shadowing cardioid ----
      const p3x = p2x + panW + 10, p3y = p2y, p3w = panW, p3h = p1h;
      const cx3 = p3x + p3w / 2, cy3 = p3y + p3h / 2;
      const peerA = 60 * Math.PI / 180;
      ctx.fillStyle = "#101722"; ctx.fillRect(p3x, p3y, p3w, p3h);
      circle(g, cx3, cy3, 16, "#121a28", C.warn, 2);
      circle(g, cx3, cy3, 12, "#121a28", C.ink, 1);
      text(g, "body", cx3, cy3 + 34, C.dim, 10, "center");
      // cardioid: r = 1 - cos(theta - peerA) … strong facing peer, null behind
      for (let a = 0; a < 360; a += 4) {
        const rad = a * Math.PI / 180;
        const k = (1 - Math.cos(rad - peerA)) / 2; // 0..1, 1 toward peer
        const rr = 14 + k * (R - 20);
        circle(g, cx3 + Math.cos(rad) * rr, cy3 + Math.sin(rad) * rr, 2.4, "rgba(126,231,135," + (0.25 + 0.6 * k).toFixed(2) + ")");
      }
      text(g, "torso-shadowing cardioid", p3x + p3w / 2, p3y + 20, C.accent, 13, "center");
      text(g, "the body occludes ~50 dB behind you", p3x + p3w / 2, p3y + p3h - 34, C.dim, 10, "center");
      text(g, "a rotation reads as a cardioid → bearing", p3x + p3w / 2, p3y + p3h - 18, C.dim, 10, "center");
      text(g, "terminal-handoff exploit · run exp_012", p3x + p3w / 2, p3y + 40, C.ok, 10, "center");

      text(g, this.read || "", W / 2, H - 10, C.warn, 12, "center");
    },
  };

  function bestBearing(ss) {
    return ss.reduce((m, s2) => (s2.rssi > m.rssi ? s2 : m), ss[0]).az;
  }

  // expose draw helpers for debugging in console
  window.CanvasKit = { circle, line, text, phone, P };
})();