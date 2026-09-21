"""Compatibility + direction-finding test battery (spec §57.26-§57.33).

Run both ways:
  PYTHONPATH=core python3 tests/test_compat_direction.py
  PYTHONPATH=core python3 -m pytest tests/test_compat_direction.py

Asserts the same claims the Kotlin (EngineSelfTest) and Swift (EngineSelfTest)
batteries certify, so all three languages stay in lockstep.
"""
from __future__ import annotations

import math

from compat import (CapabilityRegistry, NavTier, assert_legacy_wire_snapshot,
                    sideband_parse, sideband_serialize)
from direction import (BearingFusion, DirectionSweep, OobSideband,
                       StationarityGate, meters_to_band, opposite, rssi_to_meters,
                       route_metrics, wrap360)


def test_geometry() -> None:
    assert wrap360(370.0) == 10.0
    assert wrap360(-10.0) == 350.0
    assert opposite(10.0) == 190.0
    assert rssi_to_meters(-59.0) == 1.0
    assert rssi_to_meters(-80.0) > rssi_to_meters(-59.0)
    assert rssi_to_meters(-50.0) >= 0.5  # near-field floor, never <= 0
    assert meters_to_band(3.0) == "NEAR"
    assert meters_to_band(10.0) == "MEDIUM"
    assert meters_to_band(40.0) == "FAR"


def test_sweep_recovers_bearing() -> None:
    sweep = DirectionSweep()
    ts = 1000.0
    for deg in range(0, 360, 15):
        sep = abs(((deg - 120 + 540) % 360) - 180)
        sweep.add_sample(-55.0 - sep * 0.5, float(deg), ts)
        ts += 0.05
    est = sweep.estimate(now=ts + 0.01)
    assert est.detected, "sweep detected the lighthouse"
    assert abs(est.bearing_deg - 120.0) <= 22.5
    assert 0.0 < est.confidence <= 1.0
    assert est.sigma_deg() is not None
    assert not sweep.estimate(now=ts + 20.0).detected, "stale sweep reports none"


def test_sweep_min_samples_gate() -> None:
    sweep = DirectionSweep()
    for i in range(3):
        sweep.add_sample(-60.0, float(i * 90), float(i))
    assert not sweep.estimate(now=4.0).detected, "fewer than min samples -> none"


def test_fusion() -> None:
    mean, sigma = BearingFusion.fuse([(90.0, 1.0), (95.0, 1.0)])
    assert abs(mean - 92.5) < 3.0
    assert sigma is not None and sigma < 30.0
    mean2, _ = BearingFusion.fuse([(10.0, 1.0), (350.0, 1.0)])
    assert abs(mean2 - 0.0) < 1.0 or abs(mean2 - 360.0) < 1.0
    mean_anti, sigma_anti = BearingFusion.fuse([(0.0, 1.0), (180.0, 1.0)])
    assert sigma_anti is not None and sigma_anti >= 90.0, "antipodal -> collapse"
    assert BearingFusion.fuse([]) == (None, None)


def test_reciprocal_boost() -> None:
    me_b, me_s = BearingFusion.reciprocal_boost(90.0, 265.0)
    assert abs(me_b - 88.3) < 3.0
    assert me_s is not None
    selfonly, _ = BearingFusion.reciprocal_boost(90.0, None)
    assert abs(selfonly - 90.0) < 1e-6
    none_b, none_s = BearingFusion.reciprocal_boost(None, None)
    assert none_b is None and none_s is None


def test_stationarity_gate() -> None:
    gate = StationarityGate(window=8, variance_threshold=0.10)
    for _ in range(8):
        gate.add_accel(1.0)
    assert gate.is_stationary()
    for i in range(8):
        gate.add_accel(1.0 + (0.5 if i % 2 else -0.5))
    assert not gate.is_stationary()


def test_nav_tier_negotiation() -> None:
    """BLE4 + BLE5 + CS + UWB phones negotiate the lowest mutual tier."""
    ble4 = CapabilityRegistry.available_tiers
    b4 = _profile(ble_generation=4)
    b5 = _profile(ble_generation=5)
    b6 = _profile(ble_generation=6, have_cs=True)
    uwb = _profile(ble_generation=5, have_uwb=True)

    assert CapabilityRegistry.best_tier(b4) == NavTier.RSSI_LOGDIST
    assert CapabilityRegistry.best_tier(b4, b5) == NavTier.RSSI_LOGDIST
    assert CapabilityRegistry.best_tier(b5, None) in (
        NavTier.MOTION_VECTOR, NavTier.RSSI_LOGDIST)  # profile-dependent
    assert CapabilityRegistry.best_tier(b6, b4) == NavTier.RSSI_LOGDIST
    assert CapabilityRegistry.best_tier(b6, b6) == NavTier.CHANNEL_SOUNDING
    assert CapabilityRegistry.requires_both_ends(NavTier.CHANNEL_SOUNDING)
    assert CapabilityRegistry.requires_both_ends(NavTier.UWB)
    assert CapabilityRegistry.best_tier(uwb, uwb) == NavTier.UWB
    assert NavTier.HOP_GRADIENT not in ble4(b4)  # never advertised, only descended-to
    # descent never falls below hop-gradient
    assert CapabilityRegistry.descend(b6, None,
                                      {NavTier.MOTION_VECTOR: False,
                                       NavTier.RSSI_LOGDIST: False,
                                       NavTier.RSSI_BAND: False}) \
        == NavTier.HOP_GRADIENT


def _profile(ble_generation: int = 4, have_compass: bool = False,
             have_imu: bool = False, have_cs: bool = False,
             have_uwb: bool = False):
    from compat import DeviceProfile
    return DeviceProfile(ble_generation=ble_generation, have_compass=have_compass,
                         have_imu=have_imu, have_cs=have_cs, have_uwb=have_uwb)


def test_wire_frozen() -> None:
    """Old builds decode every newer-advertisement bit (forward compatible)."""
    assert assert_legacy_wire_snapshot(), "MeasurementSource must stay frozen"
    from domain import MeasurementSource
    assert len(set(MeasurementSource)) >= 5


def test_sideband() -> None:
    prof = sideband_parse(sideband_serialize(_profile(6, True, True, True, False)))
    assert prof is not None and prof.have_cs and prof.ble_generation == 6
    assert sideband_parse({"cc-oob/v1": 2}) is None


def test_oob_bearing_frame() -> None:
    assert OobSideband.parse(OobSideband.serialize(84.5)) == 84.5
    assert OobSideband.parse("X/OTHER/1\n5.0") is None
    assert OobSideband.parse("FINDUS/OOB/1\n999.0") is None


def test_route_metrics() -> None:
    graph = {
        ("A", "B"): (31.6, 115.0, 10.0),
        ("B", "C"): (32.0, 115.0, 10.0),
        ("A", "D"): (5.0, 90.0, 10.0),
        ("D", "E"): (5.0, 90.0, 10.0),
        ("E", "C"): (10.0, 90.0, 10.0),
    }
    m = route_metrics(graph, "A", "C")
    assert m["min_hops"] == (["A", "B", "C"], 2.0)
    assert m["min_meters"] == (["A", "D", "E", "C"], 20.0)
    assert m["min_meters"][1] < m["hops_path_meters"]


def test_compose_tier_and_uncertainty() -> None:
    from relationships import MeasurementSource as Src
    from relationships import RelationshipMeasurement, compose

    fa = RelationshipMeasurement("A", "B", source=Src.DIRECTION_FINDING,
                                 distance=3.0, direction=0.0)
    fb = RelationshipMeasurement("B", "C", source=Src.DIRECTION_FINDING,
                                 distance=4.0, direction=90.0)
    fa.frame = "room1"
    fb.frame = "room1"
    fa.tier = 3
    fa.bearing_uncert_deg = 10.0
    fb.tier = 4
    fb.bearing_uncert_deg = 15.0
    comp = compose(fa, fb)
    assert comp is not None
    assert comp.tier == 3, "composed tier = weakest hop"
    assert abs(comp.bearing_uncert_deg - math.hypot(10.0, 15.0)) < 1e-9


def test_sim_relative_vector_nav() -> None:
    """End-to-end: multi-hop relative vector navigation over real RSSI links."""
    from simulation import scenario_relative_vector_nav

    res = scenario_relative_vector_nav()
    assert res["scenario"] == "26-relative-vector-nav"
    assert res["failed"] == [], res["failed"]


if __name__ == "__main__":
    import traceback

    names = [n for n in sorted(globals()) if n.startswith("test_")]
    passed = 0
    for n in names:
        try:
            globals()[n]()
            passed += 1
            print(f"  PASS {n}")
        except Exception as exc:
            print(f"  FAIL {n}: {exc}")
            traceback.print_exc()

    print("-" * 40)
    print(f"compat/direction battery: {passed}/{len(names)} tests PASSED")
    raise SystemExit(0 if passed == len(names) else 1)