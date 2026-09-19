# Find Us / Crowd Compass — Complete Documentation

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
# Python reference (all 6 tests)
cd core/python && python3 packet_v2.py

# Swift
cd core/swift && swift build && swift test

# Kotlin
cd core/kotlin && ./gradlew build test

# Cross-language harness
cd tests && python3 cross_language_test.py

# Relay self-test
cd relay && PYTHONPATH=../core/python python3 relay_node.py

# Responder self-test
cd responder && PYTHONPATH=../core/python python3 guidance_engine.py
```

---

## Repository Structure

```
find-us-crowd-compass/
├── README.md                    # Build overview
├── DOCUMENTATION.md             # This file
├── .gitignore
├── core/
│   ├── python/packet_v2.py      # Reference (verified 6/6 tests)
│   ├── swift/                   # iOS/macOS library
│   │   ├── Package.swift
│   │   └── Sources/FindUsPacket/
│   │       ├── PacketV2.swift
│   │       ├── FEC.swift
│   │       └── BLE.swift
│   └── kotlin/                  # Android library
│       ├── build.gradle.kts
│       └── src/main/kotlin/com/findus/packet/
│           ├── PacketV2.kt
│           ├── FEC.kt
│           └── BLE.kt
├── relay/relay_node.py          # ZDF + ESBW + Trickle
├── responder/guidance_engine.py # AR-PDR + Floor + RF + Terminal
├── ios/FindUsApp.swift          # SwiftUI app skeleton
├── android/                     # Kotlin app
│   ├── app/build.gradle.kts
│   └── app/src/main/kotlin/com/findus/crowdcompass/
│       ├── ble/BLEManager.kt
│       └── guidance/GuidanceEngine.kt
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

All research artifacts are archived in:
`/home/derick/Documents/Obsidian Vault/find us reasearch/`

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