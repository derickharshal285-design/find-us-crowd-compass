# ADR-003 — Topology and geometry are separated

**Status:** Accepted

**Context (spec §38, §86):** Communication ("is there a path / how many
hops?") and geometry ("how far / which direction in metres?") answer different
questions with different uncertainty. Hop count is not physical distance (CP11)
and does not give direction (CP12). Mixing them lets a topology problem fail
because of a geometry problem and vice versa.

**Decision:** Two explicit layers:
- **Topology layer** — dynamic communication graph, hop gradient, components.
  Works with no measurements at all.
- **Geometry/spatial layer** — local measurements (RSSI class, direction,
  UWB, baro, composition) that are null when unknown (§65).

A missing measurement degrades the spatial layer only; it must never crash or
disable the graph/emergency layer (spec §73).

**Consequences:** `core/graph.py` computes hops from edges only. Geometry lives
in `core/relationships.py` + `relative_map.py` and is consulted by L4 guidance
(`guidance_engine.py`) only when present.

**Proof required:** §84 tests, scenario 25 (no directional sensor) in
`docs/EXPERIMENT_PLAN.md`.