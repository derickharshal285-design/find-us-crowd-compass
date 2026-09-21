# ADR-005 — RSSI is not the primary distance model

**Status:** Accepted with conditions

**Context (spec §32, §86):** RSSI varies hugely with antenna orientation,
bodies, multipath, and crowds. It cannot be trusted as a metre measurement
("waterbag" problem).

**Decision:** RSSI is used only for **robust near/far classification** and as a
**quality weight**, never as ground-truth distance. Distance values derived
from RSSI are stored with `source = RSSI`, `status = ESTIMATED`, and must not
be presented as measured metres. If a stronger sensor (UWB, direction finding)
exists and is validated, it is preferred per the best-available-sensor
principle (§55).

**Consequences:** `PeerDistanceEstimator` in `core/python/find_group.py`
currently uses Kalman-lite smoothing over RSSI-derived range — it is a
prototype flagged YELLOW (unproven). Any claim of metres from RSSI requires
experiment E65 with recorded error.

**Proof required:** E65; scenario 23 (high RSSI noise) in
`docs/EXPERIMENT_PLAN.md`.