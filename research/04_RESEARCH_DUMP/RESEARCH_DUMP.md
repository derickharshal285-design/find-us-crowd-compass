# Find Us — Clean Research Synthesis (RESEARCH_DUMP.md)

**Project:** Find Us — Infrastructure-Free Cooperative Spatial Navigation for Emergency Crowds
**Document:** Deliverable 1 (clean research synthesis; the authoritative clean view)
**Date:** 2026-09-23
**Companions:** [`PAPER.md`](PAPER.md) (paper draft), [`SOURCES.md`](SOURCES.md) (source registry), [`GAPS.md`](GAPS.md) (gap registry), [`website/`](research/website/) (static research/interview site), [`README.md`](README.md) (navigation).

---

## 0. Integrity Preamble (read first)

This document is written under the project's honesty constitution. Every research claim is tagged with exactly one of:

| Tag | Meaning |
|---|---|
| `[RES]` | Research decision / design claim — defensible as architecture, publishing-safe as design. |
| `[RES:MATH]` | Mathematical fact (e.g., SE(2) adjoint composition on a Lie group) — provable, publishable as math. |
| `[EXP:NOT-RUN]` | Designed/derived but **not executed**. No simulation run artifact, no hardware run. Explicitly NOT a result. |
| `[EXP:NOT-RUN][SIM:EST]` | A number that *looks* like a measured benchmark but is a **design-parameter estimate** from the wire/model. Retagged from a phantom "measured" line. See §1.4. |
| `[RES:NOT-VERIFIED]` | Claim known to be plausible but not resolved by this research pass. |
| `[PRIOR]` | Prior art (external) — with verification status, not invented. |
| `[SPEC]` | Speculation — clearly separated, never presented as result. |

**Rules applied in this document:**
1. No fabricated citations. Every external source is in `SOURCES.md` with a `[VERIFIED]` / `[PARTIAL]` / `[UNVERIFIED]` status.
2. No fabricated results. Any number presented "as measured" that has no run artifact is retagged `[EXP:NOT-RUN][SIM:EST]` or removed.
3. No claimed prior art. Anything not confirmed by an actual retrieved source is excluded or flagged.
4. No "seamless" language. Graceful degradation is a **design target** (`[RES]`), not a demonstrated property.
5. GPS is a weak skeleton, never the navigation source.
6. UNKNOWN is a valid first-class state, never an error.

---

## 1. Executive Summary / Claim Map

### 1.1 The problem

A crowd of heterogeneous smartphones (different sensors, calibration, coordinate frames, noise, mobility, connectivity) must estimate each other's positions **relative to one another** with **no permanent infrastructure and no reliable absolute reference** (especially in emergencies: indoor, urban canyon, GPS-denied, crushed crowds).

**Core insight (this project):** GPS is NOT the navigation source. GPS is a coarse global **skeleton** — a weak constraint that (a) fixes the global gauge/rotation/translation ambiguity, (b) seeds the optimizer, (c) anchors the cooperative frame, (d) provides weak calibration priors, (e) enables gross drift detection. **Precision comes from peer observations**, not GPS.

### 1.2 The central claim (thesis)

> A heterogeneous, mobile, infrastructure-less crowd can maintain a coherent, honest, *mode-laddered* relative spatial representation — where the mode (metric → differential → topological → historical → ghost) explicitly tags every observation — **without** requiring a shared absolute frame, continuous sigma, or a permanent anchor, **and** can detect its own failure states as first-class "I don't know" conditions.

### 1.3 Claim-level status (14 claims, honest)

| # | Claim | Status | Today |
|---|---|---|---|
| C1 | Relative frames (SE(2)/SE(3)) without absolute reference | `[RES:MATH]` | **Architecture** — publishable |
| C2 | SE(2) relative transforms compose pairwise | `[RES:MATH]` | **Math fact** — publishable |
| C3 | Wire budget fits BLE advertising ceilings | `[RES]` + `[EXP:NOT-RUN]` | **Design** — untested on real BLE |
| C4 | RSSI log-distance gives metric range | `[EXP:NOT-RUN]` | **Hypothesis** — needs calibration |
| C5 | Torso-scan / two-walk gives bearing | `[EXP:NOT-RUN]` | **Hypothesis** — unverified |
| C6 | 2-hop metric → topological ladder | `[RES]` | **Design** — coherent, untested |
| C7 | Discrete confidence classes (CERTAIN…GHOST) replace continuous σ | `[RES]` | **Design** — strong, publishable |
| C8 | Ghost decay: nothing expires, everything decays | `[RES]` | **Design** — strong, publishable |
| C9 | Mode transitions are explicit events | `[RES]` | **Design** — strong, publishable |
| C10 | Symmetric reciprocal-consistency (triangle) check | `[RES]` | **Design** — strong, publishable |
| C11 | Hop count multiplies confidence | `[RES]` | **Design** — cheap, publishable |
| C12 | ANCHOR/DRIFTER role tagging | `[RES]` | **Design** — strong |
| C13 | UNKNOWN as first-class, non-error state | `[RES]` | **Design** — strong |
| C14 | "Graces gracefully" / "74.8% at 2,500 nodes" | `[RES]` + `[EXP:NOT-RUN]` | **Aspirational** — NOT a result |

**Key rule:** `[RES]`/`[RES:MATH]`/`[RES:NOT-VERIFIED]` claims can go into a paper as *design*. `[EXP:NOT-RUN]` claims may appear ONLY as future work, never as a result.

### 1.4 THE retag (integrity-critical correction)

The research log previously carried one line written as a measured benchmark with **no run artifact** and **no `[EXP]` marker** — a phantom:

> *"Bystander battery drain is reduced from $85.3\text{ mAh/day}$ down to $1.39\text{ mAh/day}$ … a $61.8\times$ … Confidentiality score remains $1.00$."*

**Verification (this session):** the referenced simulation `sim_encrypted_relay_overlay.py` does **not exist** in the repository (searched: 0 hits); no run artifact exists; the `[EXP:NOT-RUN]` marker count for the H6 benchmarking line has been **re-verified = 2, confirmed**. The line is now retagged in `research/research-log.md:48` to:

> `[EXP:NOT-RUN][SIM:EST] — no run artifact exists for H6 benchmarking; the numbers below are DESIGN-PARAMETER ESTIMATES from the wire/model (31-byte frame = 8-byte Public Envelope + 19-byte Authenticated Private Core), NOT measured benchmark results.`

**Why this matters:** a hostile reviewer who greps for `sim_encrypted_relay_overlay.py` (or any executed-run registry) will find nothing. The system's own "confidentiality financial honesty" constitution forbids presenting an estimate as measured. **This one line, if left, would classify the whole paper as fabricated.** It is now honest.

---

## 2. Problem Decomposition (research questions, grounded)

### 2.1 The seven-layer fallback hierarchy

| Level | Mode | Description |
|---|---|---|
| 0 | GPS skeleton + cooperative | Global frame + precise relative positions |
| 1 | Cooperative only (GPS-denied) | Relative, internally consistent, no global anchor |
| 2 | Cooperative + partial peers | Degraded precision, topological still useful |
| 3 | Dead-reckoning only | Approximate, drift accumulates |
| 4 | UNKNOWN | Honest "I don't know" — never fabricated |

**Design target (not result):** the fallback hierarchy must function at Level 1 indefinitelyainerEnjoy, degrade gracefully through 2–3, and report Level 4 honestly. **[RES]**

### 2.2 The mode ladder (the spatial model's backbone)

```
METRIC (hops 1–2)      → measured vectors, SE(2) relative transforms, torso/two-walk bearing
DIFFERENTIAL (any)     → Direction-of-Improvement (gradient, two-walk, no frame, no spin)
TOPOLOGICAL (hops 3+)  → hop count only, no coordinates, no bearing claim
HISTORICAL (beyond)    → last-known with age
GHOST (never expires)  → "was there once," decays further, never deleted
```

No mode masquerades as another. Every observation is tagged with its mode. Every mode transition is an explicit event.

### 2.3 Research questions driving the paper (RQ1–RQ15, condensed)

- RQ1 (wire budget) — max usable per-payload bytes under 31-byte / 27-byte / 23-byte / iOS ceilings. **[RES; platform ceilings derived, hardware re-verify [EXP:NOT-RUN]]**
- RQ3 (spoof/confidentiality) — does a partitioned frame with ECC+MAC detect spoof/replay? **[RES: unit-tested protocol [EXP]]; field [EXP:NOT-RUN]**
- RQ11 (SOS gradient bearing) — does coupled SOS-gradient + VRLG give navigable bearing ≤20°? **[RES: simulated [EXP]]; field [EXP:NOT-RUN]**
- RQ13 (baro floor-gating) — multi-floor routing without GPS? **[PRO; baro models only [EXP:NOT-RUN]]**
- RQ15 (fallback selection) — which fallback under which environment? **[PRO; platform-gated [EXP:NOT-RUN]]**

---

## 3. Layer-by-Layer Research Synthesis (the clean dump)

### LAYER 1 — GPS SKELETON LAYER `[RES]`

**Problem:** GPS is coarse, intermittently available, and unreliable indoors/urban canopy. It must be a weak prior, not navigation.

**Findings:**
- **L1.1 (GPS as weak constraint):** Treat GPS as a coarse gauge-fixing / calibration prior in a factor graph, not a hard constraint. Use robust loss (Huber) with inflated covariance. **[RES]**
- **L1.2 (availability transition):** Smooth GPS-available↔GPS-denied transitions; no discontinuity. Detect mode via availability + quality + consistency. **[RES]**
- **L1.3 (GPS for calibration):** Weak global constraint for step-length / compass calibration when briefly available. **[RES]**
- **L1.4 (GPS-denied bootstrapping):** Anchor-free bootstrap using gravity, magnetic heading, leader election, relative frame conventions. **[RES]**

**Research problems (open):** What minimal information must GPS contribute? What is a "weak prior" formulation with honest uncertainty? **[EXP:NOT-RUN]**

---

### LAYER 2 — COOPERATIVE ESTIMATION LAYER `[RES]` + `[EXP:NOT-RUN]`

**Problem:** Phones observe each other (RSSI, UWB ranging, bearing, IMU-derived motion), but each has an independent frame, sensor, calibration, and noise model.

**Findings:**
- **L2.1 (peer observation modalities):** Surveyed. RSSI ranging (log-distance, noisy, needs calibration), UWB (accurate, sparse hardware), bearing (torso scan / two-walk), dead reckoning (drifts). **[RES][PRIOR:VERIFIED]** — see SOURCES.md.
- **L2.2 (factor graph formulation):** Cooperative localization as a factor graph / graph SLAM over relative measurements; uncertainty propagates through SE(2) adjoint composition. `core/relationships.py` implements composition + cycle checks. **[RES:MATH]**
- **L2.3 (distributed vs centralized):** Distributed message-passing (trickle, trickle-absorption) suppresses broadcast storms; local triangle consistency catches errors in O(1)/edge. **[RES]**
- **L2.4 (frame alignment):** The hardest problem. Two-walk Direction-of-Improvement sidesteps frame alignment entirely at the local tier. **[RES]**

**The two fundamental fixes (contribution candidates):**
1. **Discrete confidence classes replace continuous σ:** CERTAIN / LIKELY / GUESSED / UNKNOWN — two bits on the wire, honest, zero propagation math, recomputed locally at receiver. **[RES]**
2. **Ghost decay replaces expiry:** FRESH → DEGRADED → HISTORICAL → GHOST; nothing deleted, everything loses authority with age/hop distance but never becomes "unknown-fabricated." **[RES]**

---

### LAYER 3 — CALIBRATION LAYER `[RES]` + `[EXP:NOT-RUN]`

**Problem:** Different phones, different calibration; errors accumulate and compound through relays.

**Findings:**
- **L3.1 (self-calibration):** Gyro bias (static), accel bias (gravity), mag hard/soft iron (rotation), step length (GPS/peer). **[RES][PRIOR:PARTIAL]**
- **L3.2 (peer-validated calibration — CORE NOVELTY):** When A and B observe each other reciprocally, inconsistent results (A says B is 10 m away, B says A is 8 m away, both confident) flag calibration error **without ground truth**. Reciprocal inconsistency becomes the calibration oracle. **[RES:MATH] formulation; [EXP:NOT-RUN] validation**
- **L3.3 (recalibration triggers):** Innovation/consistency thresholds, drift detection, context change. **[RES]**
- **L3.4 (calibration state):** Continuous validity, uncertainty, temporal decay, context-dependence. **[RES]**

**Honesty note:** L3.2 is the strongest novel claim but is **formulated only**; it requires the falsification experiments in GAPS.md/E1–E3 to move from `[RES]` to `[EXP:RUN]`. **[RES:NOT-VERIFIED]**

---

### LAYER 4 — UNCERTAINTY & DEGRADATION LAYER `[RES]`

**Problem:** Know what you know, know what you don't, degrade honestly.

**Findings:**
- **L4.1 (uncertainty propagation):** SE(2) adjoint covariance propagation within the metric tier. **[RES:MATH]**
- **L4.2 (graceful degradation):** The mode ladder IS the degradation: metric → differential → topological → historical → ghost, each with defined failure state and UI rendering. **[RES]**
- **L4.3 (knowing when you don't know):** UNKNOWN is first-class. Every "I don't know" is renderable, never an error, never filled with fabricated data. **[RES]**

**Degradation tiers (honest render):**
- **PRECISE** (metric, <1 m) — hop ≤2, recent, direct
- **APPROXIMATE** (metric, >1 m) — hop ≤2, older
- **TOPOLOGICAL** (hop count) — hop 3+, no coordinates
- **HISTORICAL** (last known, aged) — beyond reach
- **UNKNOWN** (no observation) — valid state, "searching..."

**[RES]** — all design; **none measured.**

---

### LAYER 5 — COMMUNICATION LAYER `[RES]` + `[EXP:NOT-RUN]`

**Problem:** Spatial observations must travel through byte-capped, lossy, partial-connectivity BLE meshes without leaking plaintext.

**Findings:**
- **L5.1 (measurement context):** Each observation must carry timestamp, frame ID, modality, uncertainty class, calibration state. Protocol designed. **[RES]**
- **L5.2 (partial connectivity / partition healing):** Reconciling independent spatial states on reconnection; stale-info handling; delay-tolerant / store-and-forward (/ data mule). **[RES]**
- **L5.3 (enough information):** Minimum sufficient exchange — not full state, not full covariance; discrete classes, hop counts, ghost decay, direction-of-improvement. **[RES]**

**Wire-integrity findings:**
- Trickle (RFC 6206) + absorption suppresses re-broadcast storms. **[RES][PRIOR:VERIFIED]**
- Legacy BLE 31-byte ceiling partitions: Public Envelope + Authenticated Private Core. **[RES] — but benchmark numbers are `[EXP:NOT-RUN][SIM:EST]` per §1.4.**

---

### LAYER 6 — APPLICATION LAYER `[RES]` + partial `[EXP]`

**Findings:**
- Android/iOS app architecture (sensor logging, BLE discovery/exchange, estimation, UI) designed; `app/`, `android/`, `ios/`, `core/` implemented. **[RES]**
- CI state: Android empty-message battery case + 5 iOS compile errors pending green (see README.md/CI). **[EXP:NOT-RUN]**

---

## 4. The Core Novel Contributions (candidate, honest)

1. **The mode-laddered spatial model** — four/five explicit modes tagged at observation level, no mode masquerading as another, explicit mode transitions as events, ghost-decay instead of expiry. **[RES]** — the strongest defensible contribution.
2. **Discrete confidence classes** replacing continuous σ — "continuous sigma is false precision," honest classes, two bits, zero propagation math. **[RES]**
3. **Direction-of-Improvement** (differential, two-walk, gradient) replacing absolute bearing — sidesteps frame alignment. **[RES]**
4. **Peer-validated self-calibration** (reciprocal inconsistency as oracle) — novel, **formulated only**, requires experiments. **[RES:NOT-VERIFIED]**
5. **Symmetric composition invariant / triangle cycle check** — local O(1) error detection, no global consistency engine. **[RES:MATH]**
6. **UNKNOWN as first-class, anti-fabrication failure state** — emergency systems must not fabricate. **[RES]**

**Each requires prior-art confirmation (see §7).**

---

## 5. What We CanNOT Claim Today (honest negative registry)

- ❌ "Gracefully degrades" as measured — design target only. **[RES→[EXP:NOT-RUN]**
- ❌ Any RSSI/bearing/σ accuracy number — constants unmeasured. **[EXP:NOT-RUN]**
- ❌ 85.3→1.39 mAh/day, 61.8×, 1.00 — **phantom, retagged.** **[EXP:NOT-RUN][SIM:EST]**
- ❌ "74.8% at 2,500 nodes" as measured — simulated-design estimate. **[SET: on-line]**
- ❌ "2,000-node scale" — E31 explicitly `[EXP:NOT-RUN]`.
- ❌ Any battery/CPU/confidentiality number — no run artifact, no real hardware.

---

## 6. Cross-Project Prior-Art Comparison (this study vs. the field)

| Work | What it does | What it does NOT do (our relation) |
|---|---|---|
| CoCoA (Rangoni? per SOURCES) | Mobile anchor beacon + RSSI Bayesian localization w/ energy coordination | no mode-ladder, no ghost-decay, no peer-validated calibration |
| SPAWN (Wymeersch et al.) | Cooperative UWB localization, Factor-Graph/Message-Passing | metric-only; no degradation modes; privacy not first-class |
| NBP hierarchical-graph (Cui/Chen) | cooperative WSN localization with NBP layers | metric-only, error-mitigation focus; not ad hoc emergency crowd |
| OEPB (IETF I-D) | Emergency P2P BLE broadcast mesh | no spatial estimation integration |
| IgniRelay/DisasterMesh | BLE advertising mesh relays, store-and-forward | relay-only, no cooperative estimation |
| CrisisConnect/BlueSOS | BLE mesh SOS | no relative spatial estimation |
| CORELS/CLIPS | relative-coordinate cooperative localization | no emergency mode-ladder / ghost /
| Patent US11627453 | Emergency comms over non-persistent P2P BLE | mechanism TBD vs our relay overlay |

**[Basic: prior-art gap audit: full audit at `research/find-us-audit/01_prior_art_gap_audit.md`; confirmatory search this session found no system combining mode-ladder + ghost-decay + discrete classes + peer-validated calibration.]**

---

## 7. The Gap That Survives (the integration gap) `[RES:NOT-VERIFIED — needs confirmatory search]`

**The single defensible research gap:** No prior work integrates:
1. a **mode-laddered spatial degradation model** (metric/differential/topological/historical/ghost),
2. **discrete confidence classes** with explicit **ghost-decay** (never-expire),
3. **peer-validated reciprocal calibration** as the calibration oracle,
4. first-class **UNKNOWN/anti-fabrication** states,
5. all within a **byte-capped legacy-BLE relay mesh** for emergency crowds.

This is a **claims-level gap**, not a component gap: each component exists in isolation (SPAWN, CoCoA, DTN, Trickle, ghost gradients in robotics), but the **integration is unclaimed**. **[PRIOR:PARTIAL] — confirmatory one broad search done this session; no direct integration found; further per-layer RRQ searches are marked future work.]**

---

## 8. Honest "State of the Art" (with error-flagged honesty)

- Relative-coordinate cooperative localization: **exists, substantial** (SPAWN, CoCoA, CLIPS, NBP). They are metric/normal-estimation systems.
- Emergency P2P BLE relay meshes: **exist** (OEPB, IgniRelay, DisasterMesh, BlueSOS, Vajra, patent).
- Trickle/broadcast suppression: **exists** (RFC 6206), applied in SOS meshes.
- Uncertainty in WSN coop localization: **exists** (CRLB/FIM, NBP). Continuous, metric-bound.
- **Graceful degradation to topological/historical/ghost + discrete class + peer-validated calib + UNKNOWN-as-state in a BLE emergency mesh: NOT FOUND in one broad confirmatory search.** → the gap.

---

## 9. Research Questions, Layer, and the 10 Experiments That Would Move This From Design to Demonstrated

(Full experiment specs in GAPS.md; condensed falsification-relevant list here.)

| # | Experiment | Serves | Pass criteria (example) |
|---|---|---|---|
| E1 | RSSI log-distance calibration sweep | C4, RQ1 | ≤ tier-1 σ on ≥70% of devices |
| E2 | Bearing: torso-scan vs two-walk | C5 | median ≤ target bearing error |
| E3 | Compass drift across walks | C4/C5 | within hop tolerance |
| E4 | BLE budget fit at 30-phone crowd | C3 | PRR ≥ target, budget intact |
| E5 | Multihop chain error accumulation | C6/C14 | error within tier bounds ≤2 hops |
| E6 | Ghost-decay navigation utility | C8 | ghost beats unknown in success |
| E7 | Triangle cycle-consistency detect rate | C10 | detects ≥ X% injected corrupt edges |
| E8 | ANCHOR/DRIFTER stability under motion | C12 | anchor frame stable vs drifter drift |
| E9 | Mode-transition event integrity | C9 | no silent mode flips |
| E10 | Real 2-phone end-to-end demo | C1–C14 | searcher reaches victim, phone-only |

**E10 is the gate.** Until a 2-phone + relays real-device demo runs, claims are design-level only.

---

## 10. Deliverables Map

- **This document (RESEARCH_DUMP.md)** — clean synthesis, the "read this first" research document.
- **PAPER.md** — full paper draft (the companion).
- **SOURCES.md** — every source, with `[VERIFIED]/[PARTIAL]/[UNVERIFIED]` status, no fabrication.
- **GAPS.md** — updated gap registry, now distinguishing `[RES]` (design) from `[EXP:NOT-RUN]` (unexecuted) from `[SPEC]` (speculative).
- **website/** — static research + interview site (research/interview layering, prior-art, gap analysis, proposed system, interview synthesis).
- **README.md** — navigation.
- **Render note:** all deliverables rendered to PDF (A4) and mirrored to Downloads for the interview/PDF workflow.

---

*End of RESEARCH_DUMP.md. Written under the project's honesty constitution: no fabricated citations, no fabricated results, no claimed prior art without verification.*
</content>
