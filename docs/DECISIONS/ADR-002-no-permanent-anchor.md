# ADR-002 — No permanent anchor requirement

**Status:** Accepted

**Context (spec §7, §8, §5):** A single permanent `(0,0)` anchor makes every
position relative to one moving, killable phone. Anchors move (CP3), disappear
(CP4), and force unrelated coordinate frames (CP1).

**Decision:** There is no mandatory permanent anchor. The primary structure is
the relationship graph `G = (V, E)`; anchors may only be used as temporary
local references when helpful, and the system must keep working when they
disappear.

**Consequences:** New nodes join by establishing at least one relationship
(`new phone → known node`, CP5). Components split/reconnect naturally with no
global frame to maintain (§11–12). The global-coordinate problem is no longer
the mandatory centerpiece of the design (§90).

**Proof required:** Tests A–D, scenario 9 in `docs/EXPERIMENT_PLAN.md`.