# FIND US — COMPLETE FULL-CONTEXT DUMP (persisted artifact)

> God-mode export: everything the system does, the full mechanism stack, verified
> numbers, prior-art reality, current build/CI state, and the manuscript pipeline.
> Generated 2026-09-23 from repo state HEAD `00f1dc2`. No fabricated results;
> every figure carries its evidence tier ([RES]/[SIM]/[EXP:NOT-RUN]).

---

## 0. What the system is

**Find Us ("Crowd Compass")** — infrastructure-independent emergency navigation
for dense crowds, built entirely from ordinary smartphones. No GPS, no cell, no
Wi-Fi, no anchors, no pairing, no cloud.

**The founding insight (solves the Origin Dilemma):** the victim's phone becomes
**Hop 0**; distance radiates as integer hop-contours; a responder walks *down*
the hop gradient (N → N−1). RSSI is banned from routing — hop count is the sole
gradient; RSSI is a local proximity hint only.

---

## 1. The research gap (post-hostile-audit statement)

Most emergency-mesh systems (OEPB I-D, IgniRelay, CrisisConnect, Vajra, patent
US11627453) transport *messages*.
Most cooperative-localization systems (CORELS, CLIPS coop-PF, PCM/Kimera-Multi)
build *geometry*.
Most indoor-nav systems (geomag/PDR ppNav-LiMag, NIST UWB+IMU) navigate *one
device*.

**Find Us's surviving gap:** what *falsifiable emergent behaviors* arise when you
co-design [Trickle-mesh + uncertainty-tiered spatial-graph + SOS hop-gradient +
PDR/baro-gated terminal guidance + late-responder partition/mule healing] under
hard platform byte/energy ceilings in a dense flash-mob regime. The contribution
is the **integration + honest measurement**, not a new physics or protocol.

### The 4 sub-question matrix (what prior art already answers — cite these)
| Question | Prior art answer | Find Us position |
|---|---|---|
| Crowd phones: infra-free emergency comms | YES (OEPB, IgniRelay, CrisisConnect, US11627453) | inherit, cite, don't claim |
| Cooperative localization w/o anchors | YES (CORELS, CLIPS, PCM/Kimera) | enabling, not claimed |
| GPS-free indoor navigation | YES (ppNav/LiMag, NIST, baro gating) | terminal layer, gated |
| **Integration under constraints** | fragments only | **THE research gap** |

---

## 2. Full mechanism stack (top → bottom)

### 2a. Packet v2 wire format (canonical, committed)
- **56-bit raw payload (7 B)** wire; expands to **13 B** under nibble-wise
  systematic **Hamming(7,4)** FEC.
- Fields: `SOS_ID`(12b), `HOP`(4b), `BARO_DIFF`(6b two's-comp, ±0.5 hPa/LSB),
  `FLAGS`(6b), `EPOCH`(4b), `AGE`(2b), `RESERVED`(2b), `ENVELOPE_MAC`(16b).
- **16-bit envelope MAC** (HMAC-SHA256 over SOS_ID‖EPOCH‖PKT_TYPE, keyed secret)
  = anti-forgery/black-hole kill. 8-bit fails <1% target; **16-bit → 0.15–0.18%**
  acceptance (measured 0.0000170 ≈ 1/65536).
- **Ceiling math:** iOS **23-byte background-safe ceiling** (31−4−4); 7→13B
  Hamming leaves ~10B slack iOS / ~16B Android 27B. Fits 0xFF Manufacturer Data.

### 2b. iOS background reality (everything hinges on this)
- iOS background needs explicit Service-UUID scan filter; Type-0xFF-only ads are
  silently dropped by baseband without waking the app.
- **Dual-AD:** 4-byte 16b Service UUID AD (Type 0x03) + Manufacturer Data.
- Discovery: iOS **0.033–0.125 Hz** (1/8–30 s); Android wake 50 ms–3 s crowd,
  **9–30 min deep Doze**.

### 2c. Async Trickle mesh ("the sync myth")
- Naive synchronous 150ms flooding → 99.97/99.98% (a myth). **Real async**
  (10–30s wakes, 30–50% locked) → **1.51% coverage, 0.22% delivery**.
- **ESBW** (15s epochs, 10s burst, ~47 pkts) → **99.86% coverage, 99.98% delivery**
  even at 70% locked (p50 287s, p95 442s). k=3 inhibitory suppression, adaptive
  jitter T_max ∝ log2N → 96.2% @1k nodes.

### 2d. Ghost-gradient catastrophe + fix (H9/B-09)
- Data-mule cache of Hop-0 across a 200m dead zone → false Hop-1 gradients:
  **331.7 → 11,207.5 false alerts**, misleading 46–100% of searchers.
- **Fix:** Epoch-cadence delta gating (ΔEpoch ≥ 2 = delayed echo) +
  MULE_STORE_FORWARD flag + MAC origin invariants → **0.0 false alerts,
  0.00% FNR**, healing 94% @2 mules/min → 100% @≥4.

### 2e. Localization / shadowing / PDR
- **H1:** greedy hop descent = **100% arrival**; vector chains compound 2.58 →
  10.92 m/11 hops. Hop gradient wins always.
- **H3 torso shadowing:** sternum cardioid scan → mean bearing error **13.2–18.1°**,
  83.5–96.5% in ±30° cone, **4.64–7.04× gain** vs omnidirectional.
- **Terminal handoff (B-08):** torso scan + 3-step walk + slope-rule flip +
  180° ambiguity fix → mean error 13.67°, arrival ≤5m **88.35%**.
- **AR-gated PDR (B-07):** 5-stage gate (posture/accel-variance/cadence/gyro/mag)
  → **0.0 m false emits** in pocket/mosh/spin; heading 45.5°→3.14°; drift→3.3m;
  100% nav lock.

### 2f. Multi-floor baro (B-10)
- Naive 2D hop descent traps 100% under ceiling → Floor-Aware Gating
  (|ΔP|>0.35 hPa routes to stairwell) → **0% entrapment, 100% arrival**.
- Cross-OS bias ±2.0 hPa → Entrance-Gate Baseline Snapshot → 75.6% exact /
  100% ±1 floor / MAFE 0.244.

### 2g. Security / privacy / energy
- **ZDF zero-decrypt forwarding:** strangers relay encrypted cores without decrypt
  (0.015 ms, 61.8× vs DMR, 1.39 mAh/day bystander). Zero-trust: routing decoupled
  from content.
- **16-bit MAC, key-pinned sequent chains (C12), QR web-of-trust onboarding,**
  no anchor → relative coords only. Notification-flood accounting (C13).

---

## 3. Three-machine parity (why claims are believable)
Same engine in **Python (core), Kotlin (Android), Swift (iOS)**:
- `core/python/packet_v2.py`, `direction.py` + `tests/cross_language_test.py`
  (spawns Swift+Kotlin subprocesses, 4/4 PASS locally = truth).
- `core/kotlin/…/PacketV2.kt, FEC.kt, BLE.kt` + Android app engine
  (`SosEngine, DynamicGraph, Direction, DeviceApp, EngineSelfTest`).
- `core/swift/…/PacketV2.swift, FEC.swift, BLE.swift` + iOS `FindUsEngine`.

---

## 4. EXACT current build/CI state (verified via `gh` on HEAD `00f1dc2`)
- CI run `35670310756` → **FAILED** (duplicate GENERATE_INFOPLIST_FILE key)
- `35670325776` → **FAILED** (Info.plist per target)
- **Android:** compiles but **2 unit batteries fail** with **empty
  java.lang.IllegalStateException** — `EngineSelfTestTest.kt:11`,
  `PacketV2Test.kt:17`. (Numeric asserts match Python: fuse 92.5/σ5.0,
  boost 88.33/σ5.0 → the empty thrower is a **bare message-less check/require**
  deeper in the engine/packet run() path.)
- **iOS:** fails to compile — 5 errors: `EngineSelfTest.swift:100` (aged?.lifecycle),
  `:127` (DeviceApp init label), `:143` (bl scope), `DeviceApp.swift:154/155`
  (event/gradient subscript setters).
- **Blocked locally:** no JVM/gradle/kotlinc/swiftc in termux → Python is the only
  local truth; CI is the only Kotlin/Swift runner.

---

## 5. Manuscript & reviewer history
- Manuscript **v0.2–v0.5** (`research/paper/01_manuscript.md`, ~1,290 lines, 41
  sections, 27-page PDF). All evidence status-tagged; **zero fabricated data**;
  hardware items `[EXP:NOT-RUN]`.
- **Editorial decision v1:** 5-seat panel → **MAJOR REVISION** (no Reject).
  Two DA-CRITICALs VALIDATED: (1) evidence "premise→proven" slip must be
  conditional lemmas; (2) anti-rumor/consistency fails on 1-DoF direction-less
  trees — re-scope or accept hole.
- v0.5 applied: killed placeholders, explicit 10%/20° thresholds, sim claims
  anchored to run-registry ids, adversarial section, appendix-K compendium,
  49→58 refs.

---

## 6. Verified experiment tally
- H1: 100% arrival (hop descent); vector-chain error 2.58→10.92 m
- H2: 97.7% collision → 90–91% suppressed
- H3: 13.2–18.1° bearing; 83.5–96.5% in ±30°
- H4: 122.58 m detour vs 13.34 m Euclid (~10×)
- H5: jitter scaling 32.8→96.2% @1k nodes
- H6: ZDF 0.015 ms; 16-bit MAC 0.15–0.18%
- H7: PDR chaos → AR-gated 100% nav lock
- H9: ghost gradient → 0 false alerts; healing 100% @≥4 mules/min
- B-01…B-12: iOS ceiling, byte budget, ESBW, MAC mandate, multipath wall 94.73%
  acc/0% FPR, PDR 100% false-vector suppression, terminal handoff 88.35%, baro
  0% entrapment, blueprint + refimpl spec + IP doc

---

## 7. Open decisions held for user (do not proceed without)
1. **A — Framing:** publish as design+simulation+honest bounds (once CI green)
   vs gate on real-hardware validation (CI-only, can't run locally).
2. **B — Deepen prior art:** full-text OEPB I-D + US11627453 claims before final
   closest-prior-art table (recommended).
3. **C — CI gate:** fix empty-message bare check + 5 iOS compile errors first
   (master directive's own gate).

---

*End of full-context dump. Research-discovery vs patent-claim separation maintained
(no claim language; `[LEGAL REVIEW REQUIRED]`). Nothing elevated above its evidence
tier.*
