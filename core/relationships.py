"""Block 3 — Relationship store (spec §63 Block 3, §18, §20, §65, §85).

Every relationship = value + time of measurement (spec §20). Supports
insertion, timestamping, replacement/merging, aging (soft/hard expiry),
expiry, and per-source tracking. Geometry layer only; never used by the
topology/SOS layers (ADR-003, ADR-006).
"""
from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from domain import (
    MeasurementSource, MeasurementStatus, RelationshipMeasurement, now,
)


def _est_status() -> MeasurementStatus:
    return MeasurementStatus.ESTIMATED


class AgingLevel(enum.Enum):
    FRESH = "FRESH"
    AGING = "AGING"
    EXPIRED = "EXPIRED"


@dataclass
class RelationshipEntry:
    """All measurements for one (undirected) pair, tracked per source."""
    a: Any
    b: Any
    sources: Dict[str, RelationshipMeasurement] = field(default_factory=dict)
    first_seen: float = 0.0
    last_seen: float = 0.0

    def freshest(self) -> Optional[RelationshipMeasurement]:
        if not self.sources:
            return None
        best = max(self.sources.values(), key=lambda m: m.timestamp or 0.0)
        return best

    def merged(self) -> Optional[RelationshipMeasurement]:
        """Best-available view (spec §55): prefer MEASURED/VERIFIED over
        ESTIMATED, otherwise freshest. Frame composition is NOT done here."""
        cands = [m for m in self.sources.values() if m.timestamp]
        if not cands:
            return None
        rank = {
            "VERIFIED UNDER TEST": 3,
            "MEASURED": 2,
            "ESTIMATED": 1,
            "UNKNOWN": 0,
            "STALE": 0,
            "CONFLICTING": 0,
            "UNAVAILABLE": 0,
        }
        cands.sort(key=lambda m: (rank.get(m.status.value, 0), m.timestamp or 0.0))
        return cands[-1]


class RelationshipStore:
    """Per-pair spatial measurement store with aging/expiry/source tracking."""

    def __init__(self, soft_expiry_after: float = 60.0,
                 hard_expiry_after: float = 300.0) -> None:
        self.soft_expiry_after = soft_expiry_after
        self.hard_expiry_after = hard_expiry_after
        self._relations: Dict[Tuple[str, str], RelationshipEntry] = {}

    @staticmethod
    def _key(a: Any, b: Any) -> Tuple[str, str]:
        return (str(a), str(b)) if str(a) <= str(b) else (str(b), str(a))

    def insert(self, m: RelationshipMeasurement,
               timestamp: Optional[float] = None) -> bool:
        """Insert/merge a measurement (replace same source if newer, keep
        other sources). Returns True when anything changed."""
        if timestamp is not None:
            m.timestamp = timestamp
        if not m.timestamp:
            m.timestamp = now()
        key = self._key(m.a, m.b)
        entry = self._relations.get(key)
        if entry is None:
            entry = RelationshipEntry(m.a, m.b, first_seen=m.timestamp,
                                      last_seen=m.timestamp)
            self._relations[key] = entry
        prev = entry.sources.get(m.source.value)
        if prev is not None and prev.timestamp >= m.timestamp:
            return False
        entry.sources[m.source.value] = m
        entry.last_seen = max(entry.last_seen, m.timestamp)
        return True

    def get(self, a: Any, b: Any) -> Optional[RelationshipEntry]:
        return self._relations.get(self._key(a, b))

    def freshest(self, a: Any, b: Any) -> Optional[RelationshipMeasurement]:
        entry = self.get(a, b)
        return entry.freshest() if entry else None

    def merged(self, a: Any, b: Any) -> Optional[RelationshipMeasurement]:
        entry = self.get(a, b)
        return entry.merged() if entry else None

    def sources(self, a: Any, b: Any) -> Dict[str, RelationshipMeasurement]:
        entry = self.get(a, b)
        return dict(entry.sources) if entry else {}

    def age(self, a: Any, b: Any, t: Optional[float] = None) -> Optional[float]:
        entry = self.get(a, b)
        if entry is None:
            return None
        t = t if t is not None else now()
        return max(0.0, t - entry.last_seen) if entry.last_seen else None

    def level(self, a: Any, b: Any, t: Optional[float] = None) -> AgingLevel:
        """soft expiry -> AGING, hard expiry -> EXPIRED (spec §20)."""
        age = self.age(a, b, t)
        if age is None:
            return AgingLevel.EXPIRED
        if age > self.hard_expiry_after:
            return AgingLevel.EXPIRED
        if age > self.soft_expiry_after:
            return AgingLevel.AGING
        return AgingLevel.FRESH

    def is_expired(self, a: Any, b: Any,
                   t: Optional[float] = None) -> bool:
        return self.level(a, b, t) == AgingLevel.EXPIRED

    def expire(self, a: Any, b: Any) -> bool:
        key = self._key(a, b)
        if key not in self._relations:
            return False
        del self._relations[key]
        return True

    def prune(self, t: Optional[float] = None) -> int:
        t = t if t is not None else now()
        dead = [k for k, e in self._relations.items()
                if t - e.last_seen > self.hard_expiry_after]
        for k in dead:
            del self._relations[k]
        return len(dead)

    def count(self) -> int:
        return len(self._relations)

    def pairs(self) -> List[Tuple[Any, Any]]:
        return [(a, b) for a, b in self._relations]


def compose(ab: RelationshipMeasurement, bc: RelationshipMeasurement) -> Optional[RelationshipMeasurement]:
    """R(A,C) = R(A,B) + R(B,C) (spec §85) -- ONLY for relationships already
    expressed in the same reference frame (spec §5, CP1/CP8). Callers must
    guarantee `frame` compatibility; this function enforces it by requiring a
    shared, non-null `frame` tag and vector-compatible measurements.

    Returns a best-effort composed measurement with distance = |a+b| and
    direction = atan2 angle of the sum, both marked ESTIMATED (composition is
    never MEASURED).
    """
    frame_a = getattr(ab, "frame", None)
    frame_b = getattr(bc, "frame", None)
    if frame_a is None or frame_b is None or frame_a != frame_b:
        return None
    if ab.distance is None or ab.direction is None:
        return None
    if bc.distance is None or bc.direction is None:
        return None
    ax = ab.distance * math.cos(math.radians(ab.direction))
    ay = ab.distance * math.sin(math.radians(ab.direction))
    bx = bc.distance * math.cos(math.radians(bc.direction))
    by = bc.distance * math.sin(math.radians(bc.direction))
    cx, cy = ax + bx, ay + by
    dist = math.hypot(cx, cy)
    ang = math.degrees(math.atan2(cy, cx)) % 360.0
    est = _est_status()
    out = RelationshipMeasurement(
        a=ab.a, b=bc.b, source=MeasurementSource.DIRECTION_FINDING,
        status=est,
        distance=dist, distance_status=est,
        direction=ang, direction_status=est,
        timestamp=max(ab.timestamp or 0.0, bc.timestamp or 0.0),
        quality=(ab.quality or 0.0) * 0.5 + (bc.quality or 0.0) * 0.5,
    )
    out.frame = frame_a
    # Tier + bearing-uncertainty propagation through vector composition: the
    # composed edge is only as good as its weakest hop.
    ta = getattr(ab, "tier", None)
    tb = getattr(bc, "tier", None)
    if ta is not None and tb is not None:
        out.tier = ta if ta <= tb else tb
    ua = getattr(ab, "bearing_uncert_deg", None)
    ub = getattr(bc, "bearing_uncert_deg", None)
    if ua is not None and ub is not None:
        out.bearing_uncert_deg = math.hypot(ua, ub)
    return out


def _test() -> None:
    checks = 0

    def ok(cond: bool, name: str) -> None:
        nonlocal checks
        checks += 1
        assert cond, name
        print(f"  PASS {name}")

    store = RelationshipStore(soft_expiry_after=30, hard_expiry_after=60)
    t = 1000.0

    m1 = RelationshipMeasurement("A", "B", source=MeasurementSource.BLE_RSSI,
                                 distance=5.0, direction=None,
                                 distance_status=_est_status(),
                                 direction_status=MeasurementStatus.UNKNOWN,
                                 timestamp=t, quality=0.6)
    ok(store.insert(m1) is True, "insert first measurement")
    ok(store.count() == 1, "count=1 after insert")

    older = RelationshipMeasurement("A", "B", source=MeasurementSource.BLE_RSSI,
                                    distance=9.0, timestamp=t - 10)
    ok(store.insert(older) is False, "older same-source measurement rejected")

    newer = RelationshipMeasurement("B", "A", source=MeasurementSource.BLE_RSSI,
                                    distance=4.0, timestamp=t + 1)
    ok(store.insert(newer) is True, "same source newer measurement replaces")
    ok(store.freshest("A", "B").distance == 4.0, "replacement honored")

    uwb = RelationshipMeasurement("A", "B", source=MeasurementSource.UWB,
                                  distance=4.2, timestamp=t + 2,
                                  distance_status=MeasurementStatus.MEASURED,
                                  direction=None,
                                  direction_status=MeasurementStatus.UNKNOWN)
    ok(store.insert(uwb) is True, "second source kept alongside (merge)")
    ok(set(store.sources("A", "B").keys()) == {"BLE_RSSI", "UWB"},
       "per-source tracking exposes both sources")
    ok(store.merged("A", "B").source == MeasurementSource.UWB,
       "best-available-sensor merge prefers MEASURED UWB")

    # aging / expiry
    ok(store.level("A", "B", t=t + 40) == AgingLevel.AGING, "soft expiry -> AGING")
    ok(store.is_expired("A", "B", t=t + 63), "hard expiry -> EXPIRED")
    ok(store.prune(t=t + 70) == 1, "prune removes hard-expired relations")
    ok(store.count() == 0, "store empty after prune")

    # composition (spec §85) is gated on a shared reference frame
    fa = RelationshipMeasurement("A", "B", source=MeasurementSource.DIRECTION_FINDING,
                                 distance=3.0, direction=0.0,
                                 distance_status=_est_status(),
                                 direction_status=_est_status(), timestamp=t)
    fb = RelationshipMeasurement("B", "C", source=MeasurementSource.DIRECTION_FINDING,
                                 distance=4.0, direction=90.0,
                                 distance_status=_est_status(),
                                 direction_status=_est_status(), timestamp=t + 1)
    fa.frame = "room1"
    fb.frame = "room1"
    comp = compose(fa, fb)
    ok(comp is not None, "compose works within a shared frame")
    ok(abs(comp.distance - 5.0) < 1e-6, "composed distance 3-4-5 -> 5.0")
    ok(abs(comp.direction - math.degrees(math.atan2(4, 3))) < 1e-6,
       "composed direction matches vector sum")

    fa2 = RelationshipMeasurement("A", "B", source=MeasurementSource.BLE_RSSI,
                                  distance=3.0, direction=0.0, timestamp=t)
    fb2 = RelationshipMeasurement("B", "C", source=MeasurementSource.BLE_RSSI,
                                  distance=4.0, direction=90.0, timestamp=t)
    fa2.frame = "room1"
    fb2.frame = "room2"  # different frame -> refuse
    ok(compose(fa2, fb2) is None, "composition refused across frames (CP1/CP8)")

    null_dir = RelationshipMeasurement("A", "B", source=MeasurementSource.BLE_RSSI,
                                       distance=3.0, direction=None, timestamp=t)
    null_dir.frame = "room1"
    fb3 = RelationshipMeasurement("B", "C", source=MeasurementSource.BLE_RSSI,
                                  distance=4.0, direction=None, timestamp=t)
    fb3.frame = "room1"
    ok(compose(null_dir, fb3) is None, "composition refused without direction")

    # tier + bearing-uncertainty propagation through composition
    fa.tier = 3
    fa.bearing_uncert_deg = 10.0
    fb.tier = 4
    fb.bearing_uncert_deg = 15.0
    comp2 = compose(fa, fb)
    ok(comp2 is not None and comp2.tier == 3,
       "composed tier = weakest hop (3)")
    ok(abs(comp2.bearing_uncert_deg - math.hypot(10.0, 15.0)) < 1e-9,
       "composed bearing uncertainty = quadrature sum")

    print(f"\nRelationshipStore selftest: {checks} checks PASSED")


if __name__ == "__main__":
    _test()