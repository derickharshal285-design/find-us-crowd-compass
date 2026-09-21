# ARCHITECTURE

Source of truth: `docs/MASTER_SPEC.md` §17, §62, §64, §90. This is the layered
system. Core rules: phones-first local mesh, dynamic graph, topology separate
from geometry, no permanent anchor, SOS hop gradient, terminal finding as a
separate stage.

## Final system picture (spec §90)

```text
                    CROWD COMPASS
                          │
                          ▼
              PHONE-FIRST LOCAL MESH
                          │
                          ▼
                 DYNAMIC GRAPH
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
      LOCAL RELATIONSHIPS        SOS GRADIENT
             │                         │
     distance/direction         Hop 0,1,2,3...
     movement/time                    │
             │                         │
             └────────────┬────────────┘
                          ▼
                   LOCAL GUIDANCE
                          │
                          ▼
                   TERMINAL FINDER
                          │
                          ▼
                      🚨 TARGET
```

## Layers (spec §17)

| Layer | Question it answers | Current owner in repo |
| --- | --- | --- |
| L1 Dynamic communication graph | Who can communicate with whom now? | `relay/`, `core/graph.py` (planned) |
| L2 Local spatial relationships | What is the local spatial relationship, if measurable? | `core/relationships.py` (planned), `core/python/relative_map.py`, `core/python/find_group.py` |
| L3 Emergency gradient | How many network steps from a specific SOS? | `core/sos.py` (planned), existing gradient logic in `relay/relay_node.py`, BFS hop (spec §22) |
| L4 Local physical guidance | Which physical direction reaches a lower-hop route? | `responder/guidance_engine.py`, `find_group.py` DirectionSweep |
| L5 Terminal target finding | Which actual person/device is the target? | unproven — research only (spec §47–49) |

Each layer must keep the layers below it usable: a missing direction may degrade
L4 but SOS topology (L3) must keep working (spec §73).

## Existing repository adaptation (spec §62, §78 Phase 0)

The repo already has `android/`, `ios/`, `core/`, `relay/`, `responder/`,
`tests/`, `research/`. (Legacy `data/` and `src/` symlinks to the external
research vault were removed in 2026-09 — they were broken on this machine.)
Adaptation without blind reorganization:

- `core/python/` — existing Python implementation (packet layer, group finder,
  relative map).
- `relay/` — relay node firmware.
- `responder/` — responder guidance engine.
- New pure-core blocks are being added under `core/` (flat modules, no
  Bluetooth code): `domain.py`, `graph.py`, `relationships.py`, `sos.py`,
  `protocol.py`, `simulation.py`.
- `app/` — the runnable application: one `DeviceApp` per phone (its own local
  graph + SOS gradient; §48 L2–L3), honest `guidance.py` instructions
  (L3→L4 intake), a transport-agnostic `world.py`, and a demo/shell CLI
  (`main.py`). The world supplies the radio; on-device that transport is the
  platform BLE stack (spec §64: the app calls a transport API, never BLE
  APIs directly).
- `docs/` — MASTER_SPEC + this doc set.

## Design rule (spec §64)

Core domain code must never call Bluetooth APIs directly.

```text
Core Graph
   ↑
Transport Interface
   ↑
Android BLE / iOS BLE / Simulation
```

```text
Core Spatial Engine
   ↑
Sensor Interface
   ↑
Android sensors / iOS sensors / simulated measurements
```

```text
Terminal Guidance Interface
   ↑
BLE direction / UWB / acoustic / optical / simulated
```

The graph/emergency logic must run identically on simulation transport and real
transport (Block 8). Existing `relay_node.py` goes to the Transport Interface:
it receives BLE frames and feeds the graph; it must not implement L3-L5 policy.

## Data & lifecycle model

- Graph `G = (V, E)` (§18); node lifecycle `DISCOVERED → ACTIVE → STALE →
  EXPIRED`; edge lifecycle `SEEN → ACTIVE → AGING → EXPIRED` (§19).
- Relationship = `relationship_value + time_of_measurement` (§20). Aging → soft
  expiry → hard expiry; refresh interval; last successful bidirectional
  exchange. No arbitrary values without experiments.
- Multi-path: keep parent/next-hop sets, not a single route; avoid storing too
  much state (§21).
- Explicit optional fields only: unknown distance is `distance = null` +
  `distanceStatus = UNKNOWN`, never `0`; unknown direction is `null`, never `0°`
  (§65).
- Graph update events (§66): NodeDiscovered/Updated/Stale/Expired,
  EdgeCreated/Updated/Stale/Expired, ComponentSplit, ComponentMerged,
  SOSCreated/Updated/Expired, RouteChanged.

## Protocol & transports

- Versioned binary protocol with schema versioning and round-trip tests
  (`object → bytes → object`), see `docs/PROTOCOL.md`.
- Transport profile per link type (legacy adv 31-byte limit, BLE 5 extended
  advertising, GATT MTU) — the old "28 useful bits" is not a hard limit
  (§23).
- BLE subsystem split A–I: discovery, identity, advertisement, connection,
  relay, dedup, TTL, peer state, transport abstraction (§24).
- Optional augmentation research: UWB, Wi-Fi Aware/Direct, direction finding
  (spec §27–28, §61) — must earn their place through testing.

## Capability negotiation (spec §54) & best available sensor (spec §55)

- Devices advertise a `CapabilityProfile`; lower layers must work without a
  capability (e.g., no direction sensor → L4 degrades, L3 unaffected).

## Failure containment (spec §73–74)

- Never assume a measurement is correct; categorize UNKNOWN / STALE /
  CONFLICTING / UNAVAILABLE / ESTIMATED / MEASURED / VERIFIED UNDER TEST.
- A failed sensor must not crash the graph; a failed BLE link must not crash
  the emergency engine.

## Research note and decision discipline (spec §67–68)

- Every unresolved question lives in `docs/RESEARCH_QUESTIONS.md` with status
  OPEN → RESEARCHING → TESTABLE → EXPERIMENTAL → VERIFIED UNDER CONDITIONS →
  REJECTED/REPLACED. Never write "SOLVED" without stated conditions.
- Major decisions are recorded as ADRs in `docs/DECISIONS/`.