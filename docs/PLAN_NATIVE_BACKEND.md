
> **RESEARCH-FIRST.** The single detailed paper (research/01_PAPER/01_manuscript.md) is the spine; the native build is its downstream artifact. Read the paper first.

# Native Backend Build Plan

Status: APPROVED GATE — bug check passed, connection verified, this plan is the
contract before native code is written.

## Why native

Python is the verified reference implementation (`core/`, `app/`). For shipping
phones it is too slow and too heavy. A phone's backend is small (a neighborhood
graph, an incident session, BLE I/O), but it runs continuously, so we compile it:

- **Android**: Kotlin, one foreground service + BLE dual role + local StateFlow graph.
- **iOS**: Swift/SwiftUI, BLE `CBPeripheralManager` + `CBCentralManager`, actor-isolated graph.
- Python stays ONLY as (a) simulation/sweep harness and (b) cross-language test coefficient.

## Non-negotiables (from verified reference)

Everything below is independently implemented on each platform, mirroring the
semantics proved in `core/` + `app/` (no new behavior invented at compile time):

1. Wire contract = **PROTOCOL_VERSION 3** (8-of-16-byte auth tag on the wire).
2. **Canonical MAC** = HMAC-SHA256 truncated to 8 bytes over
   `U8 mtype || 16B event_id || 8B sender || U16 version || U8 hop || U8 ttl || U32 timestamp_ms_since_EPOCH`,
   where `EPOCH = 946684800.0`. `timestamp` is `U32` — must NOT be `U16` (the
   uint16 latency bug this build was specifically armored against).
3. **Pseudonym**: 8-char human-safe id derived from `install_key` + incident
   identity; every wire address is the pseudonym, never the real install key.
4. **Incident membership** = shared-secret session derived from one link
   (`incident://<b64(incident_id||0x00||salt)>?salt=..&ttl=..&life=..`); a device
   that does not know the key can be heard but never authenticated (its packets
   count against `rejected_macs` and are dropped before graph writes).
5. **Dynamic graph semantics**: bidirectional link needs two received heartbeats
   (own + peer); freshness windows per platform config; `last_bidirectional_exchange`
   drives STALE/EXPIRED; expired edges removed; node expiry independent.
6. **SOS semantics**: event id globally unique to the origin, origin hop 0,
   flood propagates `hop+1`, dedup by `(sid, version, from-node, hop)` capped at a
   bounded window; coverage is `(TTL*2+1)/N` on a line — topology and relay hops
   matter more than TTL at 50k.
7. **Guidance**: prefer an authenticated hop-1 advertisement, freshest last-seen
   first; next-hop-2 via local advertisements; else NO_VALID_ROUTE; origin at the
   site = AT_TARGET. Honest "no data yet, offline" states are first-class UI.
8. **Per-device O(k)**: a device stores only what it hears (k neighbors, k
   advertisements, k gradient entries) — never the whole crowd. 50k scaling is
   aggregation of O(k) devices; steady-state CPU ~1 ms/s per device (measured).

## Android (Kotlin) architecture

- `app/` module, minSdk 29 (BLE advertising + peripheral), target current stable.
- **Backend package `engine/`** — pure Kotlin, no Android deps:
  - `crypto/HMac.kt`, `crypto/Pseudonym.kt`; `session/IncidentSession.kt` (parse link, HKDF-SHA256, canonical MAC attach/verify).
  - `graph/DynamicGraph.kt` (Vec2 edges keyed `(A,B)` canonical ordering, freshness, expiry sweep).
  - `sos/SosEngine.kt`, `guidance/GuidanceRules.kt` (HopAdvertisement table + GuidanceInstruction).
  - `serial/ProtocolWire.kt` (14/22-byte payload blob v3, big-endian, timestamp U32).
- **I/O layer**: `ble/Advertiser.kt` + `ble/Scanner.kt` (dual role, no-op Rx callback
  into a single `Ada16/32` — actually a single `PendingInbox`), `radio/AdvWindow.kt`
  (trickle: rotate one short adv every ~1 s so many neighbors are not a burst).
- **App layer**: `FindUsService.kt` (foreground, acquires WifiLock-like only for
  BLE; holds StateFlow<SosUiState>), `IncidentRepository.kt` (parse + persist link
  in DataStore; refresh-lifetime), `ui/` Jetpack Compose screens:
  `JoinScreen` (paste/QR link), `IncidentScreen` (status, hop, neighbors, guidance
  arrow when the phone has a direction input), `SettingsScreen` (identity install
  key, privacy: rotation cadence, share-only-when-armed).
- **Self-test**: `EngineSelfTest` suite mirroring `core/` assertions (MAC roundtrip,
  canonical-field parity incl. huge timestamps, link parse/join, 2-device link
  formation via unit-scope exchange, aging, forged-packet rejection).
- **50k contract**: engine clocks `attach/verify/encode/decode` µs per frame;
  warn when a frame exceeds budget.

## iOS (Swift) architecture

- SPM + XcodeGen `project.yml` (xcodegen generates the `.xcworkspace`/`.xcodeproj`;
  no checked-in project files; CI builds with xcodebuild).
- **Backend package `FindUsEngine`** — pure Swift:
  - `Crypto/IncidentCrypto.swift` (CryptoKit HMAC-SHA256 truncate 8, HKDF via CryptoKit
    `SymmetricKey` derivation, pseudonym `PseudoID.swift`).
  - `Graph/DynamicGraph.swift`, `Sos/SosEngine.swift`, `Guidance/Guidance.swift`.
  - `Serial/ProtocolWire.swift` byte-faithful to v3.
- **I/O**: `BLE/BeaconScanner.swift` (CBCentralManager, duplicate-filter off,
  single pending inbox), `BLE/BeaconAdvertiser.swift` (CBPeripheralManager adv
  packet with 8B sender + auth block), `BLE/AdvScheduler.swift`.
- **App**: `FindUsApp.swift` (triple, satisfies no-GPS privacy by default),
  `Views/*` SwiftUI screens mirroring the Android flow; `Services/IncidentStore.swift`
  (Keychain link persistence), `Services/SosViewModel.swift` (actor; equals the
  Kotlin state machine).
- **Self-test**: `XTests/*` `XCTest` port of the same assertion battery.

## BLE transport (both)

- Advertise data: `(v3 header + 8B payload summary)`; ensure ≤ 20 B of user data
  so the adv stays in BLE 4.2/5 non-connectable adv band.
- Authenticated content flows on a short-lived connectable L2CAP/custom GATT
  exchange: the adv proves identity, then a full relay packet (14/22 B + auth + ttl)
  is transferred; the receiver re-verifies the canonical MAC before ANY graph write.
- No phone-to-phone BT is proxied; iOS + Android are peers on the same custom GATT.

## Test matrix (portable, no phone required)

| assertion battery | platforms |
|---|---|
| MAC roundtrip + wire decode/encode parity | core, android, ios |
| huge-timestamp canonical fields (U32) | core, android, ios |
| link parse/join + wrong-session rejection | core, android, ios |
| 2-device link formation + aging expiry | core, android(unit), ios(unit) |
| dedup window bound | core |
| 50k envelope (O(k), CPU ~1 ms/s/device) | core |
| 10-mesh stadium demo | core, android(unit), ios(unit) |

Milestone gates: M1 engine parity green on all three → M2 Android BLE loop →
M3 iOS BLE loop → M4 field test on two real phones (acceptance: link forms
bidirectionally and MAC-rejects a third phone).

## Explicit liftable risks (honest)

- BLE advertising rates/limits differ per OS (Android 3 adv/second cap on some
  radios; iOS background adv constraints) → the trickle AdScheduler exists exactly
  for this; tune in M4.
- No GPS by default: direction requires a manual azimuth input or optional
  compass permission — spec §86 field items stay open.
- Native sources are written here but compiled on developer machines (Termux has
  no Android SDK/Xcode). Cross-language tests run against the Python coefficient.