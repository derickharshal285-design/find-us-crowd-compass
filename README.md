# Find Us / Crowd Compass — Build Repository

This repository contains the complete reference implementation for the Find Us (Crowd Compass) offline emergency navigation system.

**Hard requirement:** read `docs/MASTER_SPEC.md` (92 sections) before contributing.
The spec is the source of truth and stands above any single doc in this repo,
including this README. Every design decision is recorded as an ADR in
`docs/DECISIONS/`.

## Architecture Overview

```
find-us-crowd-compass/
├── core/                    # Shared cross-platform libraries
│   ├── domain.py            # Block 1: domain types + lifecycles/status (pure)
│   ├── graph.py             # Block 2/5: dynamic graph + hop BFS + events (pure)
│   ├── relationships.py     # Block 3: spatial measurement store (pure)
│   ├── sos.py               # Block 4: SOS gradient engine (pure)
│   ├── protocol.py          # Block 6: versioned binary codec (pure)
│   ├── simulation.py        # Block 8: fake radio + §57 scenarios + §59 metrics
│   ├── python/              # Reference implementation (packet v2, find_group, relative_map)
│   ├── swift/               # iOS/macOS library (FindUsPacket)
│   └── kotlin/              # Android library (com.findus.packet)
├── relay/                   # Relay node firmware
├── responder/               # Responder guidance engine
├── docs/                    # MASTER_SPEC + required doc tree (spec §83)
│   ├── PROJECT_STATUS.md    # conceptual / implemented / experimental / unknown
│   ├── ARCHITECTURE.md      # layered system (L1–L5)
│   ├── PROTOCOL.md          # packet / data model
│   └── DECISIONS/           # ADRs
├── ios/                     # iOS app (SwiftUI + CoreBluetooth + CoreMotion)
├── android/                 # Android app (Kotlin + BLE + PendingIntent)
└── tests/                   # Cross-language verification harness
```

The core `core/*.py` modules are pure logic (no Bluetooth) and run identically
on the real transport or the simulated one (spec §64).

## Verified Research Foundation (11 Tasks)

> **Status note:** figures below are simulation-derived. They are retained as a
> rare-correctness archive; wherever they conflict with the master spec
> (`docs/MASTER_SPEC.md`), the spec wins. The core engine in
> `core/graph.py`, `core/relationships.py`, `core/sos.py`, `core/protocol.py`,
> `core/simulation.py` is the current implementation being truth-checked against
> the spec (§84 Test A–L, §92 close-out). Do not ship "verified/working" claims —
> see `docs/PROJECT_STATUS.md`.

| Task | Deliverable | Key Finding |
|------|-------------|-------------|
| 01 | `doc18`, `doc19`, `byte_budget_model` | iOS background requires Service UUID filter (0x03); 23B iOS-safe ceiling |
| 02 | `doc20`, `packet_v2.py` | 56-bit packet v2 (16-bit MAC), all 6 tests pass |
| 03 | `doc21`, `sim_async_trickle.py` | Async phase transition: sync 99.97% → unmitigated 1.51% → ESBW 99.86% |
| 04 | `doc22`, `sim_spoof_resistance.py` | 16-bit MAC mandate (8-bit: 32% forgery @100 msgs; 16-bit: 0.15%) |
| 05 | `doc23`, `sim_multipath_wall_detection.py` | 94.73% accuracy, 0% FPR via multi-second RF fusion |
| 06 | `doc24`, `sim_storm_avoidance.py` | 100% discovery @60s, 87.3% collision reduction |
| 07 | `doc25`, `sim_ar_gated_pdr.py` | AR-gated PDR: 100% nav, 3.34m error vs 32.94m ungated |
| 08 | `doc26`, `sim_terminal_handoff.py` | Terminal handoff: 88.35% arrival, 0% FPR |
| 09 | `doc27`, `sim_ghost_gradient.py` | Ghost gradient: 11,207 false alerts → 0 with multi-layer rule |
| 10 | `doc28`, `sim_multilevel_baro.py` | Floor accuracy: Protocol 2 (entrance gate) 75.6% exact / 100% ±1 |
| 11 | `doc29`, `refimpl_spec.md` | Complete implementation specification |

## Core Packet v2 Specification

```
56 bits / 7.0 bytes (uncoded)
13 bytes (Hamming(7,4) FEC)

Word 0 (16b): PKT_TYPE(4) | SOS_ID(12)
Word 1 (16b): HOP(4) | BARO_DIFF(6) | FLAGS(6)
Word 2 (16b): EPOCH(4) | AGE(2) | RESERVED(2) | MAC_HI(8)
Byte 6 (8b):  MAC_LO(8)

MAC: 16-bit HMAC-SHA256 over (SOS_ID || EPOCH || PKT_TYPE)
```

## Build Instructions

### Pure core engine (Python, spec §63 Blocks 1–6 & 8)
```bash
export PYTHONPATH=core
python3 -m core.graph          # DynamicGraph selftest (spec §84 A–D, G)
python3 -m core.relationships  # relationship store selftest
python3 -m core.sos            # SOS engine selftest (spec §84 E–L, §40–41)
python3 -m core.protocol       # binary codec round-trip tests
python3 -m core.security       # incident session / 8-byte MAC / pseudonym tests
python3 -m core.crowd          # 50k-device envelope benchmark (O(k) per device)
python3 -m core.simulation     # spec §57 scenarios + §59 metrics
python3 -m core.simulation --sweep  # hop-count & signal-expiry parameter plan
```

### Protocol v3 + incident security (the wire contract)
Every on-device frame is Protocol v3 with an **8-byte HMAC-SHA256 tag** over the
canonical fields (U8 type | 16B event | 8B sender | U16 version | U8 hop |
U8 ttl | **U32 timestamp**). The timestamp is uint32 so 2026+ clock times never
wrap. Same key derivation runs byte-identically in Python (`core/security.py`),
Kotlin (`android/…/engine/IncidentSession.kt`) and Swift
(`ios/…/IncidentSession.swift`), so one incident link authenticates on every OS.
Full details: `docs/DECISIONS/ADR-010.md`, `ADR-011.md` (both DECIDED).

### Application (distributed responder app on the verified engine)
```bash
PYTHONPATH=core python3 app/main.py selftest  # app selftests
PYTHONPATH=core python3 app/main.py demo      # scripted stadium incident
PYTHONPATH=core python3 app/main.py shell     # own incident: place/sos/step/guid
```
Each phone (`app/devices.py`) keeps only its own local graph + SOS gradient and
exchanges wire bytes (`core/protocol.py`), exactly like the real architecture
(spec §48, §64: the app calls a transport API, never BLE APIs directly).
The world just supplies the radio transport; on-device that transport is the
platform BLE stack.

Lifecycle contract (spec §19/§20/§22.6/§23): TTL bounds hop depth (full
coverage needs `TTL >= crowd diameter in hops`); confirmed absence kills a
route immediately while the device lingers to hard expiry (relationship
memory, no ghost routes); signaling nodes are never aged out. Evidence and
field-validation plan: `docs/EXPERIMENT_PLAN.md`.

### Python Reference (packet v2, group layer, relative map)
```bash
PYTHONPATH=core/python python3 core/python/packet_v2.py
PYTHONPATH=core/python python3 core/python/find_group.py
PYTHONPATH=core/python python3 core/python/relative_map.py
```

### Swift (iOS/macOS) — legacy `core/swift` (packet v2 archive)
```bash
cd core/swift
swift build
swift test
```

### Kotlin (Android) — legacy `core/kotlin` (packet v2 archive)
```bash
cd core/kotlin
./gradlew build test
```

### Native apps (ship on device, Python is the reference/sim harness)
```bash
# Android — full Kotlin backend on-device (engine + BLE + foreground service + Compose UI)
cd android
./gradlew :app:assembleDebug :app:testDebugUnitTest   # engine parity tests run on the JVM
# or from opencode with kotlinc installed: kotlinc app/src/main/kotlin/com/findus/crowdcompass/engine/*.kt

# iOS — Swift engine + CoreBluetooth + SwiftUI app
cd ios
brew install xcodegen
./Scripts/build.sh   # generates the project, runs EngineParityTests, builds the app
```
The device engine is a byte-faithful port of `core/` + `app/`:
- Protocol v3 + 8-byte MAC (`engine/ProtocolWire.kt`, `Sources/FindUsEngine/ProtocolWire.swift`)
- incident session, pseudonyms, canonical MAC (`IncidentSession.kt` / `.swift`)
- dynamic graph, SOS gradient, honest guidance (`DynamicGraph/SosEngine/DeviceApp`)
Every platform re-certifies the same battery (Android `EngineSelfTest` 22
checks, iOS `EngineParityTests`), and the battery is verified here via
`kotlinc` + JVM. Detail plan/contract: `docs/PLAN_NATIVE_BACKEND.md`.

### Cross-Language Verification
```bash
PYTHONPATH=core/python python3 tests/cross_language_test.py
```

### Full regression run
```bash
PYTHONPATH=core python3 -m core.graph core.relationships core.sos core.protocol core.simulation
PYTHONPATH=core/python python3 core/python/packet_v2.py
PYTHONPATH=core/python python3 core/python/find_group.py
PYTHONPATH=core/python python3 core/python/relative_map.py
PYTHONPATH=core/python python3 relay/relay_node.py
PYTHONPATH=core/python python3 responder/guidance_engine.py
PYTHONPATH=core/python python3 tests/cross_language_test.py
```

## Platform Apps (current — native backend on-device)

- **Android (Kotlin)** — `android/` (full Gradle project):
  - pure engine: `app/…/engine/` (Types, ProtocolWire v3, IncidentSession,
    DynamicGraph, SosEngine, DeviceApp, EngineSelfTest)
  - BLE dual-role: `app/…/ble/` (BleTransport adv/scan, AdvScheduler trickle)
  - backend service: `app/…/service/FindUsService.kt` (foreground, StateFlow UI)
  - Compose UI: `app/…/ui/` (Mesh / Join / Settings + on-device parity self-test)
- **iOS (Swift)** — `ios/` (SPM + XcodeGen):
  - engine: `Sources/FindUsEngine/` (byte-faithful port, CryptoKit canonical MAC)
  - BLE: `Sources/FindUsBLE/` (BeaconAdvertiser + BeaconScanner + AdvScheduler)
  - app: `Sources/FindUsApp/` (SwiftUI views, Keychain incident store, SosViewModel)
- Legacy archive: `ios/FindUsApp.swift` (old SwiftUI skeleton),
  `android/…/guidance/GuidanceEngine.kt`, `core/swift`, `core/kotlin` (packet v2).

## Relay Firmware
- `relay/relay_node.py` — Reference implementation of ZDF + ESBW + Inhibitory Trickle (k=3)
- Zero-Decrypt Forwarding: Relays don't verify MAC, only check when hop decreases
- ESBW: 15s epochs, 10s burst windows, ~47 packets/window
- Inhibitory gating: Suppress if ≥3 neighbors with same/better hop

## Key Configuration Constants

```python
# Packet v2 (historical archive)
SESSION_KEY = b"crowd_compass_session_key_2026"  # LEGACY ONLY — never used by the
                                                # current engine; see ADR-010 for
                                                # the incident-session key design.
VIRTUAL_HOP_FLOOR = 6      # MULE packets clamp hop ≥ 6
EPOCH_DURATION_S = 15.0
BURST_WINDOW_S = 10.0
ADV_INTERVAL_MS = 211.25

# Responder
ACTIVITY_WINDOW_S = 2.0
AR_GATE_THRESHOLD = 0.85
RF_CONFIRM_WINDOW_S = 2.0
RF_MIN_PACKETS = 4
BARO_FLOOR_THRESHOLD_HPA = 0.35
BEARING_COHERENCE_THRESHOLD = 0.6
RSSI_VARIANCE_THRESHOLD = 4.8
```

## Testing

All implementations share the same canonical test vector:
```
Packet: pktType=1, sosId=0x7A5, hop=3, baroDiff=-5, flags=0x22, epoch=9, age=2, reserved=1, mac=0x8F42
Hex:    17a53ee2998f42
Bits:   00010111101001010011111011100010100110011000111101000010
FEC:    13 bytes (14 nibbles × 7 bits + 6 pad)
MAC:    16-bit HMAC-SHA256 (forgery rate 1/65536 = 0.0015%)
```

## License

Proprietary — Find Us / Crowd Compass Emergency Navigation System