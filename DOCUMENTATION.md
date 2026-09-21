# Find Us / Crowd Compass — Complete Documentation

## ⚠ READ FIRST (2026-09 pivot)

The previous "Research Cascade" section documents the *older* design lineage.
Both have been folded into a single source of truth: **`docs/MASTER_SPEC.md`**
(92 sections). The sections below `## Research Cascade` remain as archive;
wherever they conflict with the master spec, the spec wins. Current
implementation status lives in `docs/PROJECT_STATUS.md`; each design decision
is an ADR under `docs/DECISIONS/` (ADR-010 security and ADR-011 identity are
still OPEN).

New pure-Python engine (spec §63 Blocks 1–6, 8; run with `PYTHONPATH=core`):

| Module | Implements | Self-test |
|--------|------------|----------|
| `core/domain.py` | block 1 types/enums, lifecycles, statuses | – |
| `core/graph.py` | dynamic graph, hop BFS, events, aging (§84 A–D, G) | 22 checks |
| `core/relationships.py` | spatial measurement store + compose (§84 C) | 17 checks |
| `core/sos.py` | SOS gradient engine, flood, expiry (§40–41, §84 E–L) | 34 checks |
| `core/protocol.py` | versioned binary codec (§23, §84 B) | 23 checks |
| `core/simulation.py` | §57 scenarios, §58 fake radio, §59 metrics | 32 checks |
| `app/devices.py` | one phone = local graph + SOS gradient, wire-only exchange (§48 L2–L3, §56, §64) | app selftests |
| `app/guidance.py` | honest responder instructions (NO_SOS_KNOWN / NAVIGATING / NO_VALID_ROUTE / AT_TARGET) | app selftests |
| `app/world.py` + `app/main.py` | transport-agnostic world + `demo`/`shell` CLI | app selftests |

Key structural differences from the archive below: explicit `UNKNOWN` never
encoded as `0`, no permanent anchor, topology is separate from geometry,
`null` distance ceiling is explicitly unchecked (spec §65) rather than a
validated RSSI↔distance table, and the 13-byte Hamming transport is optional
rather than mandatory (vector chaining is dropped).

## Executive Summary

**Find Us / Crowd Compass** is an offline, smartphone-only emergency navigation system for dense crowds (concerts, protests, stadiums, disasters) where cellular is jammed and GPS is blocked.

**Core Architecture:** Topological Hop-Count Gradient Field — the SOS device broadcasts `Hop 0`; relays increment hops; the responder walks DOWNWARD in hop count (N → N-1 → ... → 0). No global coordinates, no vector chains, no SLAM.

---

## Research Cascade (11 Tasks — All Independently Verified)

### Task 01: BLE Transport Revalidation
**Deliverables:** `doc18`, `doc19`, `byte_budget_model.py/json`
**Key Findings:**
- iOS background scanning **requires** explicit Service UUID filter (`nil` = no scan for ANY device)
- Manufacturer Data only (0xFF) is invisible to locked iPhones
- **Solution:** Dual-AD structure — inject 16-bit Service UUID (0xFC00) anchor (4 bytes) + Manufacturer Data payload → 23B iOS-safe ceiling
- Per-hop latency: 8-30s (Herald data); Android PendingIntent wake 50ms-5s (light Doze) or 9-30min (deep Doze)
- Byte budget model reproduces exactly: Doc 06 32-bit = 4B raw, 7B Hamming, 12B RS(16,8), 16B RS-block

### Task 02: Packet v2 Definitive Specification
**Deliverables:** `doc20`, `packet_v2.py` (6/6 tests pass)
**Wire Format (56 bits / 7 bytes):**
```
Word 0 (16b): PKT_TYPE(4) | SOS_ID(12)
Word 1 (16b): HOP(4) | BARO_DIFF(6) | FLAGS(6)
Word 2 (16b): EPOCH(4) | AGE(2) | RESERVED(2) | MAC_HI(8)
Byte 6 (8b):  MAC_LO(8)
```
- Hamming(7,4) FEC: 14 nibbles × 7 = 98 bits + 6 pad = 104 bits = 13 bytes
- 16-bit HMAC-SHA256 MAC over (SOS_ID || EPOCH || PKT_TYPE)
- Canonical test vector: `17a53ee2998f42` (00010111101001010011111011100010100110011000111101000010)
- All 6 tests pass: canonical vector, 2240 boundary cases, 100k random roundtrips, MAC forgery 0.0017%, 14-bit-flip FEC, GAP slack

### Task 03: Async Trickle Mesh
**Deliverables:** `doc21`, `sim_async_trickle.py`, 3 JSON datasets
**Phase Transition Discovery:**
- Synchronous myth: 99.97% coverage, 99.98% delivery, p95=1.83s
- **Unmitigated async reality: 1.51% coverage, 0.22% delivery** (gradient dies at Hop 1)
- Percolation cliff at 30-50% background-locked nodes
- **ESBW Mitigation:** 15s epochs, 10s burst windows, ~47 pkts/window, k=3 suppression → **99.86% coverage, 99.98% delivery**, p50=287s, p95=442s

### Task 04: Anti-Spoofing Envelope MAC
**Deliverables:** `doc22`, `sim_spoof_resistance.py`, `spoof_resistance.json`
**16-bit MAC Mandate (overturns Doc 20's 8-bit lock):**
- 8-bit: 31.6-32.4% forgery acceptance @100 msgs (unacceptable)
- 12-bit: 2.4% (still fails <1% threshold)
- **16-bit: 0.15-0.18%** (only width meeting <1% @100 msgs)
- Payload: 7B raw → 13B Hamming → 10B iOS slack (still fits)
- Birthday collision math matches empirical to 3 decimals

### Task 05: Multipath Wall Alerts
**Deliverables:** `doc23`, `sim_multipath_wall_detection.py`, `multipath_wall_detection.json`
**Multi-Second Fusion Required:**
- Single sniff: 78.9% misclassifies metal bounce as LoS gap; 100% false wall alerts on multipath
- **2.0s window (M≥4 pkts):** 94.73% accuracy, **0% FPR**, 84.2% TPR, 100% multipath rejection
- Features: RSSI band (-99 to -89.5 dBm), variance veto (σ≤4.8 dB), bearing coherence (|ρ|≤0.6)

### Task 06: Storm Backoff
**Deliverables:** `doc24`, `sim_storm_avoidance.py`, `storm_avoidance.json`
**Cold-Start Mass Rescue Protocol:**
- Naive flood: 98.6% burst collision, 77.8% discovery (22% undiscovered in 5 min)
- Passive 5s listen only: 79.3% (lockstep persists)
- **CSMA/CA backoff + passive suppression (k=1):** 100% @60s, 90.9% @30s, 12.4% collision, **87.3% reduction vs H2**

### Task 07: PDR Activity Gating
**Deliverables:** `doc25`, `sim_ar_gated_pdr.py`, `ar_gated_pdr.json`
**AR-Gated PDR Eliminates Kinematic Chaos:**
- Ungated PDR: 25.0 false vectors/mission, 32.94m mean drift, 34% nav failure
- **AR-gated (2s window, 100 samples @50Hz):** 100% nav success, 3.34m mean error, 0 false vectors
- Master gate threshold: 0.85 confidence

### Task 08: Terminal Handoff
**Deliverables:** `doc26`, `sim_terminal_handoff.py`, `terminal_handoff.json`
**Final 15m → 0m Protocol:**
- Combined protocol: Torso shadowing (15-20 dB attenuation) + Hot/Cold walk + Visual runway
- **88.35% arrival within 5m** (vs 79.92% torso-only)
- 90th percentile angular error: 59.22° → 30.01°
- Catastrophic flips: 5.49% → 2.54%
- 0% FPR on visual runway

### Task 09: Ghost Gradient Resolution
**Deliverables:** `doc27`, `sim_ghost_gradient.py`, `ghost_gradient.json`
**Data Mule False Gradient Elimination:**
- Unmitigated: 331.7-11,207 false Hop-1 alerts/5min, 100% misled rate
- **4-layer defense:** AGE bucket + MULE flag + Hop floor (≥6) + Epoch cadence gating
- **0.0 false alerts at ALL densities** (0.5→16 mules/min)
- 100% partition correction ≥4 mules/min, 0% false negatives on live targets

### Task 10: Multilevel Barometric Navigation
**Deliverables:** `doc28`, `sim_multilevel_baro.py`, `multilevel_baro.json`
**Floor-Aware Navigation + Cross-OS Calibration:**
- RF ceiling trap: 100% trapped below victim without floor gating
- **Floor-aware receiver gating + stairwell portal:** 0% entrapment, 100% arrival
- Cross-OS bias catastrophe: 0% exact floor uncalibrated
- **Protocol 2 (entrance gate baseline): 75.6% exact / 100% ±1 floor**
- Protocol 3 (peer consensus): 60.2% exact / 99.2% ±1 floor

### Task 11: Implementation Blueprint
**Deliverables:** `doc29`, `refimpl_spec.md`
Complete specification for autonomous implementation:
- Packet v2 canonical wire format + test vectors
- Relay state machine (ZDF + ESBW + Trickle)
- Responder guidance engine (4-mode: Macro → Stairwell → RF → Terminal)
- Cold-start storm avoidance
- BLE dual-AD framing (iOS Mode C: 23B ceiling)
- 16-bit MAC, Hamming FEC, barometric floor gating thresholds

---

## Build Artifacts

### Core Libraries (Cross-Platform)
| Platform | Location | Status |
|----------|----------|--------|
| Python (Reference) | `core/python/packet_v2.py` | ✅ 6/6 tests pass |
| Swift (iOS/macOS) | `core/swift/Sources/FindUsPacket/` | ✅ Complete |
| Kotlin (Android) | `core/kotlin/src/.../packet/` | ✅ Complete |

**Shared API:**
- `PacketV2` struct (pack/unpack/bitstring)
- `HammingFEC` encode/decode (7B↔13B)
- `BLEFraming` dual-AD (23B iOS ceiling)
- `EnvelopeMAC` 16-bit HMAC-SHA256
- Canonical test vector verification

### Relay Firmware
**`relay/relay_node.py`** — Reference implementation:
- Zero-Decrypt Forwarding (ZDF): relay without MAC verification, only check on hop decrease
- ESBW: 15s epochs, 10s burst windows, ~47 pkts/window
- Inhibitory Trickle (k=3): suppress if ≥3 neighbors with same/better hop
- MULE handling: virtual hop floor (6), AGE bucket, FLAGS.MULE_STORE_FORWARD

### Responder Guidance Engine
**`responder/guidance_engine.py`** — 4-mode pipeline:
1. **MACRO_GRADIENT** (Hop > 3): Hop-count descent
2. **STAIRWELL_PORTAL** (|ΔP| > 0.35 hPa): Navigate to stairwell portal
3. **RF_CONFIRMATION** (Hop ≤ 2): 2s multi-signal fusion (RSSI band, variance, bearing coherence)
4. **TERMINAL_HANDOFF** (Hop ≤ 1): Torso shadowing + visual runway

### iOS App (SwiftUI)
**`ios/FindUsApp.swift`** — Complete app skeleton:
- `BLEManager`: Dual-AD advertising + Service UUID filtered scanning
- `MotionManager`: 50Hz IMU → AR classifier (5 activities)
- `GuidanceEngine`: 4-mode responder logic
- `LocationManager`: CMAltimeter + entrance gate protocol
- Background mode: Service UUID 0xFC00 + Manufacturer Data payload

### Android App (Kotlin)
**`android/app/src/main/kotlin/com/findus/crowdcompass/`** — Complete app:
- `BLEManager`: Dual-AD advertising + Service UUID filtered scanning + PendingIntent wake for Doze
- `GuidanceEngine`: Full Kotlin port of responder engine
- `GuidanceEngine.kt`: All 4 modes + AR classifier + floor estimator + RF confirmation + terminal handoff

### Test Harness
**`tests/cross_language_test.py`** — Verification framework:
- Python reference test runner (6 tests)
- Swift test runner (`swift test`)
- Kotlin test runner (`./gradlew test`)
- Cross-language canonical vector verification

---

## Configuration Constants (Verified)

```python
# Packet v2
SESSION_KEY = b"crowd_compass_session_key_2026"  # Per-incident ECDH in production
VIRTUAL_HOP_FLOOR = 6
MAX_HOP = 15
EPOCH_DURATION_S = 15.0
BURST_WINDOW_S = 10.0
ADV_INTERVAL_MS = 211.25
INHIBIT_THRESHOLD_K = 3
JITTER_MIN_S = 0.05
JITTER_MAX_S = 2.0

# Responder
ACTIVITY_WINDOW_S = 2.0
AR_GATE_THRESHOLD = 0.85
RF_CONFIRM_WINDOW_S = 2.0
RF_MIN_PACKETS = 4
BARO_FLOOR_THRESHOLD_HPA = 0.35
BARO_SAME_FLOOR_HPA = 0.25
TERMINAL_HOP_THRESHOLD = 1
BEARING_COHERENCE_THRESHOLD = 0.6
RSSI_VARIANCE_THRESHOLD = 4.8
WALL_BLEED_RSSI_MIN = -99
WALL_BLEED_RSSI_MAX = -89.5
RPA_ROTATION_S = 15.0

# BLE
SERVICE_UUID = 0xFC00
COMPANY_ID = 0xFFFF
IOS_SAFE_CEILING = 23  # bytes
MFR_CEILING = 27  # bytes
```

---

## Verification Commands

```bash
# Pure core engine (spec §63, PYTHONPATH=core)
python3 -m core.graph                    # 22 checks
python3 -m core.relationships            # 17 checks
python3 -m core.sos                      # 34 checks
python3 -m core.protocol                 # 23 checks
python3 -m core.simulation               # 32 scenario checks (§57)

### Application (distributed responder app)
```bash
PYTHONPATH=core python3 app/main.py selftest
PYTHONPATH=core python3 app/main.py demo
PYTHONPATH=core python3 app/main.py shell
```

# Python reference layers (packet v2, group layer, relative map)
PYTHONPATH=core/python python3 core/python/packet_v2.py
PYTHONPATH=core/python python3 core/python/find_group.py
PYTHONPATH=core/python python3 core/python/relative_map.py

# Relay + responder
PYTHONPATH=core/python python3 relay/relay_node.py
PYTHONPATH=core/python python3 responder/guidance_engine.py

# Cross-language harness
PYTHONPATH=core/python python3 tests/cross_language_test.py

# Swift
cd core/swift && swift build && swift test

# Kotlin
cd core/kotlin && ./gradlew build test
```

---

## Repository Structure

```
find-us-crowd-compass/
├── README.md                    # Build overview
├── DOCUMENTATION.md             # This file (archive + pivot note)
├── docs/                        # Source of truth (spec §83)
│   ├── MASTER_SPEC.md           #   92-section master spec (§1–92)
│   ├── PROJECT_STATUS.md        #   conceptual / implemented / experimental / unknown
│   ├── CORE_PROBLEM.md          #   12 core problems (§4–16)
│   ├── ARCHITECTURE.md          #   L1–L5 layered architecture (§17)
│   ├── RESEARCH_QUESTIONS.md    #   open research (§60)
│   ├── PROTOCOL.md              #   wire + data model (§23)
│   ├── EXPERIMENT_PLAN.md       #   validation hierarchy (§63, §67–72)
│   └── DECISIONS/               #   ADR-001 … 011
├── .gitignore
├── core/
│   ├── domain.py                # Block 1 types/enums (pure)
│   ├── graph.py                 # Block 2/5 dynamic graph + hop BFS (pure)
│   ├── relationships.py         # Block 3 measurement store (pure)
│   ├── sos.py                   # Block 4 SOS gradient engine (pure)
│   ├── protocol.py              # Block 6 versioned binary codec (pure)
│   ├── simulation.py            # Block 8 §57 scenarios + §59 metrics
│   ├── python/
│   │   ├── packet_v2.py         # Reference (verified 6/6 tests)
│   │   ├── find_group.py        # Group layer (8/8)
│   │   └── relative_map.py      # Relative map (5/5)
│   ├── swift/                   # iOS/macOS library
│   └── kotlin/                  # Android library
├── relay/relay_node.py          # ZDF + ESBW + Trickle
├── responder/guidance_engine.py # AR-PDR + Floor + RF + Terminal
├── ios/FindUsApp.swift          # SwiftUI app skeleton
├── android/                     # Kotlin app
└── tests/cross_language_test.py # Verification harness
```

---

## Deployment Notes

1. **Python Reference:** Ready to run (`python3 packet_v2.py`)
2. **Swift Library:** Open `core/swift/Package.swift` in Xcode or `swift build`
3. **Kotlin Library:** Open `core/kotlin/` in Android Studio or `./gradlew build`
4. **iOS App:** Copy `ios/FindUsApp.swift` into Xcode project + add `FindUsPacket` SPM dependency
5. **Android App:** Copy `android/` into Android Studio project
5. **Relay Firmware:** Port `relay_node.py` to target MCU (Zephyr/FreeRTOS)
6. **Responder Engine:** Port `guidance_engine.py` to mobile platform

---

## Research Vault Reference

The spec-authored docs and all research source notes are mirrored **inside this
repo** under `research/` (most-current vault copy). The authoritative live vault
lives outside this repo — do not treat either as a build dependency:

`/home/derick/Documents/Obsidian Vault/find us reasearch/`

Legacy simulation scripts (`src/sim_*.py`) and datasets (`data/*.json`) belong
to that vault and are **not vendored** here; the old `data/`/`src/` symlinks
were removed in 2026-09. The current re-runnable simulation lives in
`core/simulation.py` and `core/simulation.py --sweep`.

Key files:
- `00_START_HERE_Find_Us_MOC.md` — Master map of content
- `18_BLE_ADVERTISING_TRANSPORT_REALITY.md` — Physical transport facts
- `19_ASYNC_SCHEDULE_MESH_OPERATING_MODEL.md` — Async model + iOS fix
- `20_PACKET_V2_WIRE_FORMAT.md` — 56-bit spec (amended 16-bit MAC)
- `21_ASYNC_TRICKLE_MESH_DESIGN.md` — ESBW protocol
- `22_ANTI_SPOOFING_ENVELOPE_MAC.md` — 16-bit MAC decision
- `23_RF_CONFIRMATION_WALL_ALERTS.md` — Multipath fusion
- `24_STORM_BACKOFF_PROTOCOL.md` — Cold-start protocol
- `25_PDR_ACTIVITY_GATING_SPEC.md` — AR-gated PDR
- `26_TERMINAL_HANDOFF_PROTOCOL.md` — Terminal layer
- `27_GHOST_GRADIENT_RESOLUTION.md` — Ghost gradient elimination
- `28_MULTILEVEL_BARO_AND_STAIRWELL.md` — Floor-aware nav
- `29_IMPLEMENTATION_BLUEPRINT_V1.md` — Build spec
- `refimpl_spec.md` — Autonomous implementation spec
- `data/*.json` — All simulation datasets
- `src/sim_*.py` — All simulation scripts (re-runnable)
## Deploy

- **Live URL:** https://find-us-crowd-compass.vercel.app
- **Platform:** Vercel (# Find Us / Crowd Compass), project `find-us-crowd-compass`
- **Deployed:** 2026-09-19 via Vercel CLI 59.23.2, node 26.9.0, interactive stream (torus-scan / hot-cold-walk / combined-handoff) — sim numbers on the live page cross-checked against `data/*.json` before deploy (99.86% async coverage, 11,207 ghost gradient → 0, 88.35% terminal, baro within-1-floor 100%).
- **Envelope MAC anti-spoof:** 0.15% forgery (16-bit), per `data/spoof_resistance.json`.
