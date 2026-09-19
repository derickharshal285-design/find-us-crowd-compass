# Find Us / Crowd Compass — Build Repository

This repository contains the complete reference implementation for the Find Us (Crowd Compass) offline emergency navigation system, built from the verified research cascade (11 tasks, all independently reproduced).

## Architecture Overview

```
find-us-build/
├── core/                    # Shared cross-platform libraries
│   ├── python/              # Reference implementation (verified)
│   ├── swift/               # iOS/macOS library (FindUsPacket)
│   └── kotlin/              # Android library (com.findus.packet)
├── relay/                   # Relay node firmware (ZDF + ESBW + Trickle)
├── responder/               # Responder guidance engine (AR-gated PDR + RF + Terminal)
├── ios/                     # iOS app (SwiftUI + CoreBluetooth + CoreMotion)
├── android/                 # Android app (Kotlin + BLE + PendingIntent)
└── tests/                   # Cross-language verification harness
```

## Verified Research Foundation (11 Tasks)

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

### Python Reference (Core)
```bash
cd core/python
python3 packet_v2.py  # Runs full 6-test verification suite
```

### Swift (iOS/macOS)
```bash
cd core/swift
swift build
swift test
```

### Kotlin (Android)
```bash
cd core/kotlin
./gradlew build test
```

### Cross-Language Verification
```bash
cd tests
python3 cross_language_test.py
```

## Platform Apps

### iOS (SwiftUI)
- `ios/FindUsApp.swift` — Complete app with BLE dual-ad advertising, AR-gated PDR, floor estimation, RF confirmation, terminal handoff
- Requires: iOS 15+, CoreBluetooth, CoreMotion, CoreLocation
- Background mode: Uses Service UUID `0xFC00` filter + Manufacturer Data (0xFF) payload

### Android (Kotlin)
- `android/app/src/main/kotlin/com/findus/crowdcompass/`
- BLEManager: Dual-AD advertising + Service UUID filtered scanning
- GuidanceEngine: Full responder engine port
- Background wake: PendingIntent + ScanSettings with report delay for Doze

## Relay Firmware
- `relay/relay_node.py` — Reference implementation of ZDF + ESBW + Inhibitory Trickle (k=3)
- Zero-Decrypt Forwarding: Relays don't verify MAC, only check when hop decreases
- ESBW: 15s epochs, 10s burst windows, ~47 packets/window
- Inhibitory gating: Suppress if ≥3 neighbors with same/better hop

## Key Configuration Constants

```python
# Packet v2
SESSION_KEY = b"crowd_compass_session_key_2026"  # Per-incident ECDH in production
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