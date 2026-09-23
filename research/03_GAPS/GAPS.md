# GAPS.md — Gap & Experiment Registry (updated)

**This registry is the living honesty instrument for the Find Us project.** Every gap is tagged:
- `[RES]` — claim gap is a research/design finding (grounded in verified prior art audit).
- `[SPEC]` — gap is a specification/definition matter (resolvable by spec, not by measurement).
- `[EXP:NOT-RUN]` / `[EXP:NOT-RUN]` — gap closes only via designed experiments **that have NOT been executed** (no run artifact exists).
- `[PROPOSED]` — gap-closer is a proposed design (novelty candidate, unvalidated).
- `[UNVERIFIED]` — gap status depends on a source not independently verified.

Prior-art audit basis: `research/find-us-audit/01_prior_art_gap_audit.md`; current numeric/design ground truth: `RESEARCH_DUMP.md`. Last updated this research pass.

---

## 1. The Surviving Core Gap — Integration (`G-INT`)

**Statement.** Every atom in the proposed system exists as verified prior art in isolation: GPS-skeleton for cooperative positioning `[RES]`; cooperative estimation over BLE (SPAWN family, CoCoA line) `[RES]`; relative-coordinate meshes (CORELS/CLIPS family) `[RES]`; emergency BLE broadcast framing (OEPB, IgniRelay, CrisisConnect) `[RES]`; P2P emergency BLE patent coverage `[RES]`; degradation/uncertainty as continuous-variance factor-graph output `[RES]`.

**The gap:** **no single system in the verified pass integrates all of these under (a) a byte-capped legacy-BLE wire budget, (b) a mode-ladder of spatial degradation (metric→differential→topological→historical/ghost), (c) discrete confidence classes in place of continuous σ, (d) explicit mode-transition events, and (e) ghost-decay (nothing deleted, everything decays, ghosts never expire).** Each integration component is `[PROPOSED]`; the *integration itself* is the contribution and is **unvalidated** `[EXP:NOT-RUN]`. `[RES]` (gap) · `[PROPOSED]` (closer) · `[EXP:NOT-RUN]` (validation).

**Falsification:** controlled experiments E1–E10 (below) that show any component performs worse or no better than single-phone GPS challenge the claim. Until E10 (2-phone real-device demo) passes, the system makes **no** "it works" claim. `[RES]`

---

## 2. Layer-by-Layer Gap Registry (12 sub-problems, priority-ordered)

### Layer 1 — GPS Skeleton `[RES]` gap class
| ID | Gap | Class | Closer |
|----|-----|-------|--------|
| G-L1.1 | No shared standard for *mode-level* GPS availability (silent skeleton↔denied transition; users see "10 m" when GPS just died) | `[RES]` gap · closer `[PROPOSED]` | L1 mode ladder: transition **events** (§3.2 ladder; E9) |
| G-L1.2 | GPS-denied bootstrapping without a common frame (strangers aligning to a frame neither owns) | `[RES]`/`[UNVERIFIED-detail]` gap · `[EXP:NOT-RUN]` | Frame-alignment protocol (E3/E5) |

### Layer 2 — Cooperative Estimation
| ID | Gap | Class | Closer |
|----|-----|-------|--------|
| G-L2.1 | 2-hop metric tier under resource cap (peer frame consistency without controversy) | `[RES]` → `[EXP:NOT-RUN]` | 2-hop relative factor mesh (E1) |
| G-L2.2 | Frame alignment without a common reference | `[RES]`/`[PARTIAL]` | Reciprocal-alignment (E5) |
| G-L2.3 | Distributed vs centralized overhead under crowd scale | `[SPEC]` | Cost model (E4) |

### Layer 3 — Calibration `[PROPOSED]` **core novelty candidate**
| ID | Gap | Class | Closer |
|----|-----|-------|--------|
| G-L3.1 | Continuous self-calibration normally assumes a known frame; in emergency there is no anchor | `[RES]` gap | Mode-aware self-cal (E1/E2) |
| G-L3.2 | **Peer/reciprocal-validated calibration oracle** — reciprocal inconsistency (disagreement vector between two peers) as the calibration oracle rather than a trusted anchor | `[PROPOSED]` · **`[EXP:NOT-RUN]`** · **not found in prior art (empty prior-art result)** | G-L3.2 falsification experiments (E6–E7) — **this is the least-supported, most-original claim; explicitly unvalidated** |

### Layer 4 — Uncertainty & Degradation
| ID | Gap | Class | Closer |
|----|-----|-------|--------|
| G-L4.1 | Continuous σ is false precision in a mesh; **discrete confidence classes** + **mode-ladder** + **explicit transition events** not found as integrated boundary | `[PROPOSED]` · **`[EXP:NOT-RUN]`** | H5/E9; ghost-decay (H4) |
| G-L4.2 | "Ghost" lifecycle — nothing deleted, everything decays; contradicting ghosts as honest alarm | `[PROPOSED]` · `[EXP:NOT-RUN]` | H4/E8 |

### Layer 5 — Communication
| ID | Gap | Class | Closer |
|----|-----|-------|--------|
| G-L5.1 | Byte-capped legacy-BLE wire (≤23B iOS-safe) carrying a **spatial model** (not just a packet) | `[RES]` (bytes) · `[EXP:NOT-RUN]` (spatial-content) | E4 wire budget + DOC-06 frame |
| G-L5.2 | 2-hop emissions w/ error-tolerant FEC in byte cap; iOS background receipt (RPA, ≤23B) | `[RES]`/`[PARTIAL]` | E4/E10 |

### Layer 6 — Application
| ID | Gap | Class | Closer |
|----|-----|-------|--------|
| G-L6.1 | Honest degradation **UI** — rendering "I don't know" with the same honesty as "I know" | `[PROPOSED]` · `[EXP:NOT-RUN]` | E9 (degradation-event rendering); H7 |
| G-L6.2 | Ghost UI + "head toward where I last saw them"; contradicting ghosts surfaced, not hidden | `[PROPOSED]` · `[EXP:NOT-RUN]` | E8 |

---

## 3. Honest Empty Results (novelty candidates with NO prior-art hit)

| Candidate | Prior-art audit result | Load-bearing? |
|-----------|----------------------|---------------|
| Peer/reciprocal-validated calibration oracle (G-L3.2) | **No verified prior-art integration found** | Yes — flagged `[PROPOSED]·[EXP:NOT-RUN]`, **never** claimed as proven |
| Discrete confidence classes + mode-ladder + ghost-decay as integrated spatial-resolution boundary (G-L4.1) | **No verified integrated hit** | Yes — flagged `[PROPOSED]·[EXP:NOT-RUN]` |
| Byte-capped cooperative spatial exchange inside BLE budget (G-L5.1) | Components exist; **integration absent** | Yes — flagged `[PROPOSED]·[EXP:NOT-RUN]` |

These empty results are the *survivable* integration gap; they are the honest, falsifiable contribution — and they are **design, not results**.

---

## 4. The Falsification Program (per RESEARCH_DUMP.md §8 / paper §6 — all `[EXP:NOT-RUN]`)

| ID | Falsifies / proves | Pass (example, `[DESIGN-PARAMETER]`) |
|----|--------------------|--------------------------------------|
| E1 | RSSI calibration (log-distance) | σ within tier-1 target on ≥70% devices |
| E2 | Bearing (two-walk vs torso-scan consistency) | median bearing error ≤ target |
| E3 | Compass drift across walks | within 2-hop tolerance |
| E4 | Byte budget in 30-phone crowd (BLE) | trickle delivery ≥ target PRR |
| E5 | Multihop error accumulation | error within tier bounds ≤2 hops |
| E6 | **Peer-validated calibration oracle (G-L3.2)** | reciprocal inconsistency exposes drift |
| E7 | **Calibration honesty under adversarial drift** | oracle says UNKNOWN, not wrong |
| E8 | Ghost-decay navigation utility | ghost beats "unknown" in success rate |
| E9 | Mode-transition event integrity | no silent mode flips; UI renders event |
| E10 | **2-device end-to-end demo (GATE)** | searcher reaches victim using UI alone |

**GATE E10:** until the 2-phone + relays real-device demo runs, the paper's "works" claims remain `[PROPOSED]`, and every number is a `[DESIGN-PARAMETER]` estimate. `[RES]`

---

*End of GAPS.md. A gap that is honestly empty beats a claim that is quietly full.*
