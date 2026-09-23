
> **RESEARCH-FIRST.** The single detailed paper (research/01_PAPER/01_manuscript.md) is the spine; the native build is its downstream artifact. Read the paper first.

# CORE PROBLEM

Derived from `docs/MASTER_SPEC.md` §4–16. The original problem was not "how do
phones communicate?" — BLE already provides nearby-device communication and
discovery. The hard problem was spatial meaning.

## Original problem statement (spec §4)

> Multiple phones can communicate locally, but there is no automatic common
> spatial coordinate system shared by every phone in a dynamic crowd. A system
> must determine how local relationships between phones can be represented,
> propagated, updated, joined, removed, and used to locate or navigate toward
> an emergency target.

## Core subproblems

### CP1 — Independent coordinate systems (§5)

Every phone could pick itself as `(0,0)`; the frames do not refer to the same
space. Fix concept: represent the system as a graph of relative relationships,
not one shared permanent origin. Relationship composition `A→B + B→C = A→C`
only after frames are aligned. Status: conceptual, not validated.

### CP2 — Distance/spatial information does not automatically travel through the mesh (§6)

A packet traversing `A→B→C→D→E` gives E no physical relationship to A.
Communication path length ≠ physical distance. Fix concept: compose compatible
local relationships ("relationship graph"). Status: composition math simple;
measurement quality and frame alignment unresolved.

### CP3 — The anchor phone can move (§7)

A single permanent `(0,0)` anchor makes everything relative to a moving point.
Fix: no permanent anchor; relationships are the primary structure; anchors only
temporary local references.

### CP4 — The anchor phone can disappear (§8)

With one mandatory anchor, losing it loses the reference. Fix: distributed
relationships; if an anchor disappears its node/edges go, remaining graph
continues. Status: conceptual.

### CP5 — A new person joins (§9)

A late phone has no knowledge of the existing frame/graph. Fix: establish one
known relationship — `new phone → known node` — to become a node of the graph.
Open sub-question: how much info must be exchanged before the newcomer can
navigate. Frame-merging process unresolved.

### CP6 — People leave (§10)

Edges/nodes are not permanent. Fix: dynamic topology with lifecycle
created → updated → stale → expired; timestamps and aging; do not erase on one
missed advertisement. Good software model; physical behavior needs testing.

### CP7 — The network splits (§11)

Crowds separate into disconnected components. Fix: maintain disconnected
components independently; no information crosses the gap; a later new edge is a
bridge enabling reconciliation. Status: conceptual.

### CP8 — Two previously separate groups meet (§12)

Two groups have unrelated origins/histories. Fix: bridge edge allows
propagation and reconciliation; the spatial frame problem reappears at the
meeting point. See also layered architecture in `docs/ARCHITECTURE.md`.

### CP9 — SOS origin is outside any private group, responder inside, or responder outside the private group (§13)

Simple single-group SOS does not cover all cases. The emergency layer must work
across groups; see SOS engine design in `core/sos.py` and `docs/PROTOCOL.md`.

### CP10 — Responder enters late (§14)

A late responder must learn the current gradient from the network rather than
missing the event (spec §22 step 8). Must be a first-class scenario in the
gradient engine and in `docs/EXPERIMENT_PLAN.md`.

### CP11 — Hop count is not physical distance (§15)

`hop=3` may be 10 m in a sparse mesh or 300 m in a dense one. The graph layer
may not assert meters from hops; geometry must come from measurement layer.

### CP12 — Hop count does not automatically give walking direction (§16)

Knowing "one hop toward the SOS" does not tell the responder which way to walk.
This is the biggest open technical question (spec §87), separate from the graph
problem.

## What the code must therefore do

1. Model the network as a dynamic relationship graph `G = (V, E)` (§18) with
   per-edge `{communication, spatial_measurement, direction, timestamp, expiry,
   source}`.
2. Keep topology (communication) and geometry (measurement) as separate layers.
3. Use explicit `null`/`UNKNOWN` for missing values, never `0` (spec §65).
4. Let core code run identically over simulation and real transport
   (spec §64, §63 Block 8).