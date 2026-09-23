
> **RESEARCH-FIRST.** The single detailed paper (research/01_PAPER/01_manuscript.md) is the spine; the native build is its downstream artifact. Read the paper first.

# PROJECT STATUS

Source of truth: `docs/MASTER_SPEC.md`. This file mirrors spec §60 and adds the
actual state of this repository. Status wording follows spec §67 rules:
nothing is "SOLVED" unless the conditions are clearly stated.

## What is conceptual (GREEN — basic conceptual foundations)

From spec §60, accepted design foundations:

- Phone-first architecture.
- Offline peer communication as a core requirement.
- BLE as a primary candidate transport.
- Multi-hop relay concept.
- Small emergency packet concept.
- Dynamic graph concept.
- Relationship-based spatial model.
- No mandatory permanent anchor.
- New-node joining through graph relationships.
- Node/edge aging and expiry concept.
- Split/reconnect graph concept.
- SOS as a temporary logical reference.
- Hop gradient concept.
- Topology vs physical distance distinction.
- Need for terminal guidance as a separate stage.

Core thesis (spec §80):

> Can a dynamic smartphone mesh create and maintain a useful emergency
> navigation gradient without requiring GPS or a permanent global coordinate
> anchor, while local spatial relationships and optional stronger sensing
> provide the physical direction and terminal guidance needed by a responder?

## What is implemented (verified in this repository)

Legacy layers run from the repo root with `PYTHONPATH=core/python`; the pure
core engine (spec §63 Blocks 1–6, 8) runs with `PYTHONPATH=core`.

| Module | Purpose | Verification |
| --- | --- | --- |
| `core/domain.py` | Block 1: domain types/enums, lifecycles, statuses, explicit-null rule (§65) | type-safe base |
| `core/graph.py` | Block 2/5: dynamic graph, lifecycles, components, hop BFS, events, route tracking (§84 A–D, G); revive-after-expiry (§23) | 25 selftest checks |
| `core/relationships.py` | Block 3: per-source measurement store, aging, frame-gated compose (§20, §85) | 17 selftest checks |
| `core/sos.py` | Block 4: SOS gradient, hop adoption, dedup, TTL cap, expiry/renew, flood (§22, §40–41, §84 E–L) | 34 selftest checks |
| `core/protocol.py` | Block 6: versioned binary codec, explicit nulls, unknown-version/truncation rejection (§23, §65, ADR-009) | 23 selftest checks |
| `core/simulation.py` | Block 8: fake radio + §57 scenarios + §59 metrics + `--sweep` TTL/expiry parameter plan | 32/32 scenario checks |
| `app/` (`devices.py`, `guidance.py`, `world.py`, `main.py`) | Distributed per-device app: local graph + gradient per phone, honest responder guidance (`NO_SOS_KNOWN` / `NAVIGATING` / `NO_VALID_ROUTE`), demo + interactive shell (spec §48 L2–L4, §56); includes secure-incident test (MAC join/verify, foreign-forgery rejection), raw connectivity test (link join → bidirectional link → silence ages it out), and ghost-kill regression (relay stops advertising an ended incident, guidance decays) | app selftests pass |
| `tests/robustness_suite.py` | Adversarial phone-to-phone audit: 91 checks across wire/codec/MAC tamper, link/session edges, transport loss/burst/overload/simplex/flap/blackout, graph churn, SOS gradient storms, forgery/replay/clock skew, guidance honesty; spec §53/§20 rule enforced: a relay only advertises an SOS hop it can back with a live fresher claim, so ghosts decay within (hops × route_freshness) instead of the full 900 s lifetime | 91/91 checks PASSED |
| `core/security.py` | Incident layer (ADR-010/011 DECIDED): incident link ↔ session, 8-byte HMAC-SHA256 canonical MAC over U32-timestamp fields, incident-scoped 8-char pseudonyms, ephemeral id pool; length-prefixed link payload (0x00-in-salt safe); `query_life` clamp | 15 selftest checks |
| `core/crowd.py` | 50k-device envelope: per-frame µs, memory/entry, bounded dedup, ring-coverage formula (measured at n=2000, extrapolated to 50k); per-device O(k), ~1 ms/s CPU | 50k benchmark run |
| `android/` (Kotlin native) | On-device backend: engine port (Protocol v3, IncidentSession, DynamicGraph, SosEngine, DeviceApp, EngineSelfTest), BLE dual-role + AdvScheduler, foreground service + StateFlow UI, Compose Mesh/Join/Settings; ghost-kill gate mirrors Python (§53) | engine compiled via kotlinc, parity battery 28 checks PASSED on JVM |
| `ios/` (Swift native) | On-device backend: SPM+XcodeGen app; engine port (CryptoKit canonical MAC), CoreBluetooth advertiser/scanner + AdvScheduler, SwiftUI views, Keychain incident store | XCTest parity battery (run on macOS via `Scripts/build.sh`) |
| `core/python/packet_v2.py` | 56-bit packet layer, FEC, MAC, BLE framing, decode of 7B/11B/13B/15B/17B/21B frames, `BLEFraming`, `CanonicalVectors` | 6 self-tests pass |
| `relay/relay_node.py` | Relay node: frame decode on receive, gradient transmit preserves origin EPOCH (MAC validity across hops), hop-0 adoption, self-test with real MAC chain 0→1→2 | self-test passes |
| `responder/guidance_engine.py` | Responder guidance: mode ladder, gradient aging, AR gate, responder-relative baro, StairDetector, RSSI-only RF confirmation, rotate-scan bearing, TrackedGradient | self-test 6/6 pass |
| `core/python/find_group.py` | Group-finding layer: JoinCode → PBKDF2 key, member beacons, Kalman-lite distance estimator, DirectionSweep bearing, GroupFollower | 8/8 checks pass |
| `core/python/relative_map.py` | Relative graph map: trilateration init + coarse-to-fine spring embed, `align_to_north`, `ascii_map`, stress, `follower_to_edges` bridge | 5/5 checks pass |
| `tests/cross_language_test.py` | Cross-language harness (py/swift/kotlin fixtures; swift/kotlin skip without toolchains; static check passes) | all pass |

Lifecycle contract (2026-09, spec §19/§20/§22.6/§23): TTL bounds hop depth
(full coverage needs `TTL >= crowd diameter in hops`); confirmed absence kills
a route immediately while the device lingers to hard expiry (relationship
memory, no ghost routes); nodes that keep signaling are never aged out (radio
contact refreshes node/edge lifecycles). Evidence: `core/simulation.py --sweep`
→ recorded in `docs/EXPERIMENT_PLAN.md`.

## What is experimental (YELLOW — conceptually promising but unproven)

From spec §60:

- relative vector chaining;
- graph-based relative localization;
- dead reckoning integration;
- static/stationary node assistance;
- RSSI-based near/far classification;
- multiple-path spatial reconstruction;
- local direction from phone sensors;
- UWB optional layer;
- Wi-Fi augmentation;
- terminal acoustic guidance;
- optical target handoff;
- sophisticated relay optimization;
- multi-floor graph model.

Current working prototypes that MUST NOT be presented as validated science:

- `relative_map.py` spring-embedding geometry (synthetic validation only).
- `find_group.py` distance/bearing estimators (synthetic validation only).
- DirectionSweep / rotate-scan bearing (RSSI-noise sensitive, unproven in crowds).
- Baro-based floor inference in `guidance_engine.py` (responder-relative only).

## What is unknown (RED — not yet solved)

From spec §60:

- reliable physical direction to lower-hop neighbor on ordinary phones;
- universal Android/iOS background equivalence;
- real-world dense-crowd radio performance (field validation, spec §86);
- robust indoor 3D navigation;
- guaranteed emergency delivery;
- proven terminal locator;
- production-level responder UX.

Resolved since earlier status (now implemented): large-scale crowd performance
(envelope measured: O(k) per device, steady-state ~1 ms/s CPU at 50k);
security model (ADR-010 DECIDED: incident-session 8-byte MAC, Protocol v3);
privacy-preserving identity (ADR-011 DECIDED: per-incident pseudonyms,
ephemeral routine ids).

Biggest open technical questions (spec §87–89):

1. Physical direction of a lower-hop neighbor on an ordinary moving phone in a
   crowded, obstructed environment without direction-finding hardware.
2. How large/dynamic a phone graph can grow before BLE scanning/advertising,
   battery, and packet collisions make the system impractical.
3. Whether the emergency gradient stays usable under continuous movement,
   phones disappearing, splits, merges, and late responders.

## Hard truths that must never be hidden (spec §86)

- Bluetooth range in a crowd is variable.
- RSSI is not a reliable universal metre measurement.
- Hop count is not physical distance.
- Standard smartphones do not necessarily expose BLE AoA/AoD.
- Android/iOS background rules differ and are version-dependent.
- UWB is hardware-dependent and cannot be assumed universally.
- A graph gives network topology, not automatically a walking direction.
- A perfect indoor map is not automatically achievable from phone-to-phone
  measurements.
- Real crowd conditions must be tested.
- Emergency systems require security and failure handling.