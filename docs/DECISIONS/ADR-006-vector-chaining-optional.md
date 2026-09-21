# ADR-006 — Vector chaining remains optional

**Status:** Accepted (not trusting yet)

**Context (spec §30–31, §61):** Composing local vector relationships across a
path (`R(A,C) = R(A,B) + R(B,C)`, §85) is conceptually attractive but requires
a shared reference frame and accumulates error (§31, Level-3 Q14). Frame
alignment across phones is unresolved (CP1, CP8).

**Decision:** Vector/relative-map chaining is an optional research path — not
part of the mandatory emergency architecture. The maintained prototype is
`core/python/relative_map.py` (trilateration init + spring embed), validated on
synthetic data only. It must not feed the SOS topology layer.

**Consequences:** `relative_map.py` and `find_group.py` bridging stay isolated
in `core/python/`; the core modules (`core/graph.py`, `core/sos.py`) never
depend on them.

**Proof required:** Level-3 questions 13–15, E69/E75 in
`docs/RESEARCH_QUESTIONS.md`.