# ADR-007 — UWB is optional

**Status:** Accepted (conditional)

**Context (spec §27, §61, §86):** UWB provides real ranges but is
hardware-dependent; it cannot be assumed to exist on any given phone.

**Decision:** UWB is an optional augmentation layer strictly behind the sensor
interface (§64). Terminals without UWB must be navigated by the best
available sensor (§55). UWB must earn deployment through tested accuracy —
E67 in `docs/RESEARCH_QUESTIONS.md`.

**Consequences:** The protocol reserves optional relationship/metadata fields
but carries no UWB-only requirement. Guidance degrades cleanly when UWB is
absent (scenario 25).