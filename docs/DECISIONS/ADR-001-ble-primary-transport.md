# ADR-001 — BLE as primary transport

**Status:** Accepted (default assumption; subject to research §25)

**Context (spec §24, §60):** Crowd Compass must work phone-to-phone with no
internet. The candidates are BLE, Wi-Fi Aware/Direct, UWB, acoustic.
BLE is the only transport present on effectively all target phones with
discovery + advertising + connectable GATT built in and offline-capable.

**Decision:** BLE is the primary candidate transport, split into: discovery,
identity, advertisement, connection, relay, dedup, TTL, peer state, and
transport abstraction (§24A–I). No transport is treated as solved until §25–28
research completes.

**Consequences:** BLE-specific code lives behind `TransportInterface`; the core
graph never calls BLE APIs (spec §64). Wi-Fi and UWB remain optional
augmentations (§28, §27). "28 useful bits" is not treated as a hard limit; the
protocol defines an explicit transport profile per link type (§23).

**Proof required:** experiments E63–E68 in `docs/RESEARCH_QUESTIONS.md`.