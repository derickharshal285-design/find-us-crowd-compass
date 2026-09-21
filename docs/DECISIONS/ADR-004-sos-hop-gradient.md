# ADR-004 — SOS uses a hop gradient

**Status:** Accepted (simulation-verified path; real radio unproven)

**Context (spec §22, §40, §41):** The SOS layer needs a topology-only reference
that works with no GPS, no anchor, and no measurements. A BFS distance field
(hops) from the SOS origin is simple, stale-safe via version+TTL, and does not
pretend to be physical distance.

**Decision:** SOS propagation follows §22:
1. origin creates `SOS_ID`, `hop = 0`;
2. neighbors learn `hop = 1`; only lower hops propagate;
3. versioning prevents older updates overwriting newer ones;
4. TTL/hop-limit bounds flooding;
5. dedup on `(SOS_ID, version)`;
6. expiry removes stale SOS;
7. late responders learn the current gradient from the network;
8. multiple SOS events stay independent.

`nextHops(v, s) = neighbors(v) with hop = hop(v) - 1` (§85). Multiple equal-cost
next hops may be retained (§21).

**Consequences:** The emergency layer works without any spatial measurement, so
SOS survives AR/sensor failure (spec §73). The gradient is logical hops, never
metres (CP11). Real-radio gradient behavior is marked unproven (§22 STATUS).

**Proof required:** §84 Tests E–L; scenarios 10–18, 21–22 in
`docs/EXPERIMENT_PLAN.md`.