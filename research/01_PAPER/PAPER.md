# PAPER.md — Find Us / Crowd Compass: Cooperative Compass on a GPS Skeleton

**Status: DRAFT v0.6 · Claims tagged per the honesty constitution · Written — not yet peer-reviewed**
**Companion to:** RESEARCH_DUMP.md (synthesis) · SOURCES.md (verification ledger) · GAPS.md (gap registry)
**Rendered from the same ground truth. No fabricated results, no fabricated citations.**

> **Honesty preamble (read first).** Every claim in this paper carries one of five tags:
>
> * `[RES]` — **Research/design claim** grounded in verified prior art or internal design/math on the repo.
> * `[EXP:NOT-RUN]` — **Design-parameter / protocol estimate, explicitly NOT executed in this repo** (no run artifact exists). These are wire-model or math estimates, honest about being design estimates, never presented as measured benchmarks.
> * `[SPEC]` — Space/specification definition (wire budget, protocol constants). Definable by definition, not by experiment.
> * `[PROPOSED]` — Proposed contribution, not yet validated by any experiment in this repo.
> * `[UNVERIFIED]` — Claimed in prior art or external sources but not independently verified in this pass. Never silently upgraded.

A parallel integrity rule runs through the whole project: **no citation that was not retrieved/verified is presented as verified; no number that was not measured is presented as measured.** Where a result would require a run artifact that does not exist, the claim is tagged `[EXP:NOT-RUN]` and the number is labeled a **design-parameter estimate**.

---

## Abstract

When an emergency disperses a crowd into streets, buildings, and urban canyons, the people most likely to find each other are the people already near each other — if they carry a shared, honest spatial model. Infrastructure is absent or damaged; GPS is partly available and partly denied; no absolute frame exists that every stranger can trust. We argue that the navigable information in a crowd is fundamentally **relative and one-hop-derived**, and we design **Find Us: a cooperative crowd compass** that treats GPS as a **skeleton, not a source** — a weak global prior that fixes the global gauge, never the navigation answer.

The paper makes the case in six layers (GPS skeleton → cooperative estimation → peer calibration → uncertainty & degradation → byte-capped BLE communication → application), audits the prior art per layer, states the **integration gap** that survives the audit, and commits to an **honest, falsifiable experiment program** (H1–H7 hypotheses; E1–E10 experiments) so that the design's claims can be tested or honestly withdrawn.

**Central claim, stated falsifiably:** a crowd of heterogeneous smartphones can maintain *more honest* spatial estimates cooperatively than any single-device system operating alone — measured as **earlier admission of "I don't know" under degradation, and earlier, more correct convergence under cooperation** — while carrying the entire spatial model inside a 23-byte iOS-safe BLE advertisement budget. `[PROPOSED] · [EXP:NOT-RUN]`

**What this paper does NOT claim:** it does not claim field-measured localization accuracy; it does not claim the system "works" in deployment; every quantitative operational claim is either a wire/model design estimate (`[EXP:NOT-RUN]`) or a spec constant (`[SPEC]`).

---

## 1. The Problem We Address

### 1.1 The emergency navigation scenario
A crowd is at risk (fire, earthquake, crush, active threat). Individuals split; families and parties fragment; responders cannot reach everyone. Phones are the one thing everyone carries IPC-compromised or intact; `[RES]` there is no usable absolute reference for locating a lost person, and `[RES]` no sensor on a phone is a self-contained compass for relative navigation in a crowd.

### 1.2 The three failures we design against
1. **GPS as the source.** GPS gives meters-to-tens-of-meters accuracy, needs open sky, and silently degrades in canyons/buildings. Treating it as the navigation answer makes the system *confidently wrong*. `[RES]`
2. **Slient degradation.** A phone that goes from "10 m away" to "I don't know" does so without telling the user or the network *when* it stopped knowing. `[RES]` — L4, the uncertainty layer, is where this is most acute.
3. **The stranger paradox.** Cooperative localization only pays off if strangers relay each other. Strangers will not run your relays if doing so costs battery, confidentiality, or trust. The design must make relay cheap, confidential, and authenticated. `[RES]`

### 1.3 The insight: GPS is a skeleton, not a source
GPS is retained — but only as:
- a weak prior in the factor-graph (`[RES]`),
- a global-gauge fixer when open sky is available (`[RES]`),
- a drift and gross-error detector, never the coordinate oracle (`[RES]`).

Precise relative geometry comes from **cooperative estimation over BLE** — RSSI/bearing/IMU-constrained, peer-validated — with GPS as the anchor that ties relative frames to a global one *when it can*: physics of urban RF. `[RES]`

### 1.4 Success criterion (falsifiable, honest)
**S:** For a pair (Finder F, Target T) within ≤3 hops, the system's mode-ladder estimate of T's direction from F is **no worse, and degrades more honestly**, than F's own single-phone GPS estimate — with honesty measured as *earlier UNKNOWN emission under signal loss*. Success/failure of S is an experiment, not an assertion. `[PROPOSED] · [EXP:NOT-RUN]`

---

## 2. Prior-Art Audit (per-layer; details in RESEARCH_DUMP §3–§6 and GAPS.md)

The confirmatory prior-art pass on this project id `[RES]` — executed as an integrity gate — searched cooperative localization (SPAWN, CoCoA lines), relative-coordinate cluster fusion (CORELS/CLIPS family), emergency P2P BLE relay proposals (CrisisConnect, IgniRelay, OEPB), and the spatial mesh selected as closest prior art. Full verification ledger in SOURCES.md. Keep the layer claims below and map each to the audit result. `[RES]`

### Layer 1 — GPS skeleton `[RES]`
* **Exist:** GPS as weak constraint in factor-graph SLAM-like structures; gauge fixing in cooperative localization; GPS-denied bootstrapping. `[RES]`
* **Gap:** **mode-level GPS transition** — no shared standard for what spacetime anchored cooperative + GPS-denied relative frame mean. The mode ladder (below) is the proposal. Migrate to "layer" tagging: this is L1 gap. `[RES]`

### Layer 2 — Cooperative estimation `[RES]`
* **Exist:** cooperative localization via message-passing factor graphs (SPAWN lineage over BLE: cooperative positioning using BLE); RSSI/TOA/IMU fusion. `[RES]` (verify per SOURCES.md details; CoCoA methods reference; SPAWN Wymeersch).
* **Gap:** frame-alignment without a common reference; 2-hop emission under resource cap. `[RES]` — proposed in §3.3.

### Layer 3 — Calibration `[RES] · [EXP:NOT-RUN]`
* **Exist:** single-device self-calibration from local sensors; static peer-assisted calibration in controlled deployments. `[RES]` (partial).
* **Proposed novelty ("peer-validated calibration"):** using reciprocal inconsistency between pairs as a calibration *oracle* — disagreement between cooperative and observed metrics flags datacalibration fault. `[PROPOSED] · not yet validated` — see GAPS G-L3.2.

### Layer 4 — Uncertainty & degradation `[RES] · [EXP:NOT-RUN]`
* **Exist:** continuous-variance propagation in factor graph methods (e.g., SPAWN covariance estimates). `[RES]`
* **Gap/proposal:** "continuous σ is false precision" **discrete confidence classes** (metric/differential/topological/historical/ghost) with explicit mode-transition **events**, and **ghost-decay** — nothing fully expires, everything decays; ghosts never deleted. `[PROPOSED] · [EXP:NOT-RUN]`

### Layer 5 — Communication `[RES] · [EXP:NOT-RUN]`
* **Exist:** BLE advertising transport for IoT relaying; trickle/absorption timers; BLE adv budget ≤31 legacy bytes, ≤23 iOS-safe bytes. `[RES]`
* **Gap/proposal:** cooperative spatial exchange under an explicit byte cap carrying a *spatial model* (not just a packet). 2-hop emissions with error-tolerant FEC within the 23-byte budget. `[PROPOSED] · [EXP:NOT-RUN]` — wire/math estimates in §5; see G-L5.1.

### Layer 6 — Application `[RES]`
* The app-proposal: bare-bones Android + sample, cooperative visual interface (north-up relative map when GPS, cross-point when denied). `[RES]` (existing prototype on repo).

**Layer summary after audit:** every atomic component in L1–L6 exists somewhere in the literature. **No single system in the confirmatory pass integrates all of them under a byte-capped, honesty-laddered emergency mesh.** The integration is the contribution and the risk. `[RES]` — see GAPS.md.

---

## 3. Proposed System — Find Us

### 3.1 Architecture (6 layers)
```
UI → Estimation → Sensor → Communication → Logging
```
Layers 1–4 core; §5 wire; §6 app. `[RES]` (design).

### 3.2 The mode ladder — "knowing you don't know"
The core spatial model is a **mode ladder** of four explicit degradation modes, authored under the honesty constitution:

| Mode | Range condition | What it knows | Frame needed |
|------|----------------|---------------|--------------|
| METRIC | ≤2 hops, recent | vector (distance + bearing) in a shared frame | shared local frame |
| DIFFERENTIAL | any reachable | direction of walking-improvement (walk-gradient), no absolute position | none (reference-free) |
| TOPOLOGICAL | 3+ hops | hop-count topology + direction sign | none |
| HISTORICAL/ GHOST | beyond live reach | last-known bearing of the target, decaying; ghost never expires, it decays | none |

`[RES]` (design) · `[PROPOSED]` (unvalidated) · `[EXP:NOT-RUN]` (no experiments yet)

**Why a ladder is honest:** emergent separation — a system that names its mode (METRIC vs TOPOLOGICAL) cannot silently claim the better mode. Every transition is an **event** the UI must render, and every event is an opportunity to tell the user "degraded from metric to differential." `[PROPOSED] · [RES]`

**Ghost-decay:** nothing is deleted; a target that leaves range becomes a *ghost* with monotonically decaying certainty, driving "head toward where I last saw it," and contradicting ghosts (two peers disagreeing) signal an unsolved conflict — an honest alarm. `[PROPOSED] · [EXP:NOT-RUN]`

### 3.3 Peer-validated calibration (L3) — design
Reciprocal inconsistency (pairwise disagreement vector) replaces a trusted self-calibration oracle: a device that sees its own RSSI-vs-reported-distance disagreeing with its neighbor's does not know *who* is wrong, but the *disagreement itself* is the signal — the flag that calibration is drifting, worth a recalibration event. `[PROPOSED]` — this is the identified **unvalidated core novelty candidate (G-L3.2)**. Not yet proven by any experiment.

### 3.4 Discrete confidence classes
Continuous σ is false precision for a budget-constrained mesh. Instead: discrete classes encode sufficient honesty with 2 bits. Confidence classes (e.g., `[CERTAIN | LIKELY | GUESSED | UNKNOWN]`) — the wire carries the class, the UI renders it, and the user is never misled by a number the system does not actually know. `[PROPOSED] · [EXP:NOT-RUN]`

---

## 4. Falsifiable Hypotheses (H1–H7)

Each is stated so a controlled experiment can reject it. All tags `[PROPOSED] · [EXP:NOT-RUN]` — none has been executed on repo; no fabricated results.

- **H1 — Cooperative ≥ Solo under GPS skeleton.** A 2-phone + relays experiment: cooperative mode yields no worse (mean ≤ solo) target direction error than solo GPS. Rejected if solo strictly wins.
- **H2 — RSSI calibration is learnable on-device.** RSSI→distance mapping calibrates to a bound via local sensitivity runs. Rejected if calibration fails to converge.
- **H3 — Bearing via two-walk/symmetric anchor**. Bearing estimate via spatial diversity anchored to peer geometry. Rejected if bearing error exceeds margin.
- **H4 — Ghost-decay > binary deletion.** A target that decays as a ghost finds the user to the target more often than a target that simply "disappears." Rejected if ghost == deletion.
- **H5 — Discrete classes beat continuous σ on the wire.** Same information with fewer bytes; efficiency claim. Rejected if classes mislead under degradation vs σ.
- **H6 — Zero-decrypt forwarding is fast and confidential.** Stranger relays execute zero-decrypt forwarding within the BLE budget with no plaintext leakage (ZDF). `[RES]` protocol framing locked · `[EXP:NOT-RUN]` — see §5. `[NOTE that a sim_encrypted_relay_overlay design-parameter estimate was wrongly tagged as run — see Honesty section]`
- **H7 — Mode-ladder honesty: explicit degradation events.** Under GPS loss, the system emits a mode-transition event (not silent flip) within a bound; system is rejected if users see "metric" when the mode is topological.

---

## 5. Wire Budget (for the spatial model inside the byte cap)

*All numbers below are wire/model design estimates `[EXP:NOT-RUN]`, not measured benchmarks.* `[SPEC]` defines the frame.

* Legacy BLE advertisement: ≤31 bytes total (≤23 bytes iOS-safe after required AD/header). `[RES]` (industry constrained).
* The DOC-06 smallest spatial packet carries a 4-byte base; FEC widens it (`[RES]` — 7,4 Hamming: 7B; RS(16,8): 12–16B). Within 23B iOS cap. `[EXP:NOT-RUN]`
* 16-bit HMAC-SHA256 authenticity envelope (forgery rate 1/65536 operation) `[RES]` — spec attribute, defines per-frame authenticity; operational rate is benchmark, not run. `[EXP:NOT-RUN]` for measured.
* envelope MAC + age-of-packet + mode + confidence fit in the DOC-06 budget (paragraph 7 bytes vs 4-byte base). `[EXP:NOT-RUN]` — see research#01.

**On the "zero-decrypt" relay claim:** the repo-formatted 31-byte legacy BLE advertisement framing is locked; the quantitative "speedup" / "battery mA" figures are **design-parameter estimates** from the wire model, and the associated simulation does **not** have a run artifact — they are `[EXP:NOT-RUN]`. This correction is recorded in the audit trail (research-log.md) and RESEARCH_DUMP.md §14. `[RES]` honesty marker.

---

## 6. The Missing Denominator: What Must Be Measured

The single most important missing thing in the paper is a *denominator.* `[RES]` No experiment in the current repo claims a "baseline" that is not either a spec constant or a wire model. The honest lab program E1–E10 in GAPS.md gives the falsifying grounds. Until E1–E9 (per-layer experiments) and E10 (2-phone, relays, real-device) run, the claims below are proposals.

---

## 7. Honest Limits & Disclaimer

- **`[EXP:NOT-RUN]`** marks every number that needs a run artifact and has none.
- **No field deployment is claimed.** The system's "works" claim is gated on E10 (real-device 2-phone + relays end-to-end finding), which has not been executed.
- **No prior-art citation is upgraded beyond its verified status.** Some items in Layer 2 are cited from secondary sources and remain `[UNVERIFIED or PARTIAL]` in SOURCES.md (e.g., specifics of a claimed method behavior). Where confidence is absent, the claim carries the UNKNOWN class honestly.
- **The peer-validation calibration (`G-L3.2`) is the least-supported claim in this paper.** It is explicitly a novelty candidate — formulated and interesting, unproven)Skip.

---

## 8. Conclusion

Find Us is a design that places **honesty as a first-class system property** — the mode ladder, discrete confidence, ghost-decay, and explicit degradation events exist to make a crowd system that *knows when it doesn't know*. The prior-art audit confirms we can cite each component; the gap audit confirms no single integrated system combines them under a sentence-capped byte budget. The next milestone is not another assertion: it is E1–E10, the falsification program, run under the same honesty constitution. `[PROPOSED]`

---

## Appendices

**A. Tag definitions** — `[RES] [EXP:NOT-RUN] [SPEC] [PROPOSED] [UNVERIFIED]` (see preamble).
**B. Claim-level map** — see RESEARCH_DUMP.md §Claim summary and GAPS.md tables; the one-line phantom-retag correction below.
**C. Correction register.** This session corrected a `[RES → EXP:NOT-RUN]` mis-tag where a zero-decrypt forwarding result had been phrased as if measured when no run artifact exists; the line was verified and retagged, and no fabricated results remain in this paper. See research-log.md.

*End of PAPER.md draft. Integrity: every quantitative claim is `[RES]` spec, `[EXP:NOT-RUN]` design estimate, or `[UNVERIFIED]`; nothing is silently upgraded.*
