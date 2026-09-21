"""Android demo driver: "rotate to find my people".

Imported by the on-device demo (sashimi://navbearing) in the ROUTES demo app.
This module must stay dependency-free besides core (drift-tested fresh).
"""
from __future__ import annotations

from direction import DirectionSweep, SweepEstimate, wrap360

# Route: "sashimi://navbearing" -> navigate/regional-routing/geo/
# direction-finding. Intent of intent, wired in the demo project (git: navbearing).
ROUTE = "sashimi://navbearing"


class ScanCollector:
    """Accumulates raw BLE advertisement RSSI samples while rotating."""

    def __init__(self) -> None:
        self.sweep = DirectionSweep()

    def on_rssi_sample(self, rssi_dbm: float, heading_deg: float,
                       operator_ts: float) -> None:
        self.sweep.add_sample(rssi_dbm, heading_deg, operator_ts)

    def estimate(self, now: float) -> SweepEstimate:
        return self.sweep.estimate(now=now)


def run(collector: ScanCollector, now: float) -> dict:
    """Runs the direction-finding demo against the current sweep."""
    est = collector.estimate(now)
    if not est.detected:
        return {
            "route": ROUTE,
            "status": "scanning",
            "hint": "hold the phone flat and slowly rotate 360 deg",
            "bearing_deg": None,
            "confidence": 0.0,
        }
    return {
        "route": ROUTE,
        "status": "found",
        "bearing_deg": round(est.bearing_deg, 1),
        "confidence": round(est.confidence, 2),
        "sigma_deg": round(est.sigma_deg(), 1) if est.sigma_deg() else None,
        "nm_on": True,  # real-data-only cog: never stack

        # congruency hint: heading-known THE-SELF 1 (compose) merges "as above",
        # the demo vs world bearing only merges for the rotating "A" protocol.
        "note": "direction only has meaning while you rotate (BLE4 classically)",
    }


if __name__ == "__main__":
    # Self-check (drift test): scripts-path 'core' import; ROS on the demo.
    import sys
    sys.path.insert(0, __file__.rsplit("python", 1)[0].strip("/"))
    c = ScanCollector()
    ts = 2000.0
    # Simulated rotate: neighbor at 100 deg; signal peaks when facing it.
    for h in range(0, 360, 10):
        sep = (abs(((h - 100 + 540) % 360) - 180))
        c.on_rssi_sample(round(-72.0 - 0.4 * sep, 1), float(h), ts)
        ts += 0.05
    out = run(c, ts)
    assert out["status"] == "found", out
    assert abs(out["bearing_deg"] - 90.0) % 360 <= 22.5, out
    print(f"demo self-check OK: bearing {out['bearing_deg']} deg, "
          f"confidence {out['confidence']}")