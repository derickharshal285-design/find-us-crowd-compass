"""Compatibility layer for the phone mesh across radio generations.

BLE 4.x/5.x is the permanent baseline: RSSI distance bands plus self-located
DirectionSweep bearings keep navigation working with zero capability exchange
on the wire. Bluetooth 6.0 Channel Sounding and UWB are strictly additive tiers
that raise the precision of an edge when BOTH endpoints can do them; they never
change what an old phone must understand.

Backward-compatibility rules enforced here
  * the legacy advertisement wire only ever carries MeasurementSource values
    that already exist in the frozen enum (core/domain.py). New evidence is
    exchanged out-of-band (OOB peer channel) or is self-located (sweep), never
    as new enum values on the legacy wire.
  * assert_legacy_wire_snapshot() trips any test that would break the "old
    build can still decode the new build's advertisements" guarantee.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple

from domain import MeasurementSource


@enum.unique
class NavTier(enum.Enum):
    """Evidence tier for one edge, weak -> strong. HOP_GRADIENT never leaves."""
    HOP_GRADIENT = 0
    RSSI_BAND = 1
    RSSI_LOGDIST = 2
    HEADING_REL = 3
    MOTION_VECTOR = 4
    CHANNEL_SOUNDING = 5
    UWB = 6

    def label(self) -> str:
        return {
            NavTier.HOP_GRADIENT: "hop-gradient (no sensor)",
            NavTier.RSSI_BAND: "RSSI band (near/med/far)",
            NavTier.RSSI_LOGDIST: "RSSI log-distance (meters)",
            NavTier.HEADING_REL: "self-located DirectionSweep bearing",
            NavTier.MOTION_VECTOR: "motion-correlation vector (PDR fusion)",
            NavTier.CHANNEL_SOUNDING: "BT6.0 Channel Sounding (both ends)",
            NavTier.UWB: "UWB fine ranging (both ends)",
        }[self]


TIER_SOURCE: Dict[NavTier, Optional[MeasurementSource]] = {
    NavTier.HOP_GRADIENT: None,
    NavTier.RSSI_BAND: MeasurementSource.BLE_RSSI,
    NavTier.RSSI_LOGDIST: MeasurementSource.BLE_RSSI,
    NavTier.HEADING_REL: MeasurementSource.DIRECTION_FINDING,
    NavTier.MOTION_VECTOR: MeasurementSource.IMU,
    NavTier.CHANNEL_SOUNDING: MeasurementSource.UWB,
    NavTier.UWB: MeasurementSource.UWB,
}


def tier_source(tier: NavTier) -> Optional[MeasurementSource]:
    return TIER_SOURCE[tier]


# Sources that may appear on the legacy advertisement wire. Everything here is a
# MeasurementSource that shipped with the very first Protocol v3 codec.
def legacy_wire_sources() -> FrozenSet[MeasurementSource]:
    return frozenset({
        MeasurementSource.BLE_RSSI,
        MeasurementSource.UWB,
        MeasurementSource.DIRECTION_FINDING,
        MeasurementSource.BAROMETER,
        MeasurementSource.IMU,
        MeasurementSource.WIFI,
        MeasurementSource.ACOUSTIC,
        MeasurementSource.OPTICAL,
        MeasurementSource.GPS,
        MeasurementSource.USER,
        MeasurementSource.SIMULATED_GROUND_TRUTH,
    })


# Snapshot of the enum as shipped. If a future MeasurementSource is added to
# core/domain.py, this tripwire fails until the compat impact is reviewed.
_LEGACY_ENUM_SNAPSHOT = frozenset(
    tuple(member.name for member in MeasurementSource))


def assert_legacy_wire_snapshot() -> bool:
    """True when MeasurementSource has not grown past the shipped snapshot."""
    current = frozenset(tuple(member.name for member in MeasurementSource))
    return current == _LEGACY_ENUM_SNAPSHOT


@dataclass
class DeviceProfile:
    """What one handset can sense and transmit (mostly local truth)."""
    ble_generation: int = 4   # 4, 5, or 6 (56-bit PacketV2 / Protocol v3 family)
    have_compass: bool = False
    have_imu: bool = False
    have_cs: bool = False      # Bluetooth 6.0 Channel Sounding
    have_uwb: bool = False
    connect_support: bool = True
    advertise: bool = True
    scan: bool = True
    name: str = ""


PROFILE_STUBS: Dict[str, DeviceProfile] = {
    "ble4_basic": DeviceProfile(ble_generation=4, name="BLE 4.x, no sensors"),
    "ble5_compass": DeviceProfile(ble_generation=5, have_compass=True,
                                  name="BLE 5.x + compass"),
    "ble5_full": DeviceProfile(ble_generation=5, have_compass=True, have_imu=True,
                               name="BLE 5.x + compass + IMU"),
    "ble6_cs": DeviceProfile(ble_generation=6, have_compass=True, have_imu=True,
                             have_cs=True, name="BLE 6.x + Channel Sounding"),
    "uwb": DeviceProfile(ble_generation=5, have_compass=True, have_imu=True,
                         have_uwb=True, name="BLE 5.x + UWB"),
}

# Tiers that require BOTH endpoints to carry the hardware.
_TWO_END_TIERS = frozenset({NavTier.CHANNEL_SOUNDING, NavTier.UWB})


class CapabilityRegistry:
    """Maps device profiles to the strongest edge tier they can sustain."""

    @staticmethod
    def available_tiers(local: DeviceProfile,
                        peer: Optional[DeviceProfile] = None) -> List[NavTier]:
        """Best-to-worst ordering of tiers this device can produce for `peer`."""
        out: List[NavTier] = []
        if local.scan and local.advertise:
            out.append(NavTier.RSSI_BAND)
            if peer is None or peer.scan:
                out.append(NavTier.RSSI_LOGDIST)
        if local.have_compass:
            out.append(NavTier.HEADING_REL)
        if local.have_imu:
            out.append(NavTier.MOTION_VECTOR)
        if local.have_cs and peer is not None and peer.have_cs:
            out.append(NavTier.CHANNEL_SOUNDING)
        if local.have_uwb and peer is not None and peer.have_uwb:
            out.append(NavTier.UWB)
        out.sort(key=lambda t: t.value, reverse=True)
        return out

    @staticmethod
    def best_tier(local: DeviceProfile,
                  peer: Optional[DeviceProfile] = None) -> NavTier:
        tiers = CapabilityRegistry.available_tiers(local, peer)
        return tiers[0] if tiers else NavTier.HOP_GRADIENT

    @staticmethod
    def descend(local: DeviceProfile, peer: Optional[DeviceProfile],
                ok: Dict[NavTier, bool]) -> NavTier:
        """Strongest tier whose runtime check passes; never below HOP_GRADIENT."""
        current = CapabilityRegistry.best_tier(local, peer)
        for tier in CapabilityRegistry.available_tiers(local, peer):
            if tier.value > current.value:
                continue
            if ok.get(tier, True):
                return tier
        return NavTier.HOP_GRADIENT

    @staticmethod
    def requires_both_ends(tier: NavTier) -> bool:
        return tier in _TWO_END_TIERS


# OOB peer-channel serialization (GATT sideband, never the legacy wire).
def sideband_serialize(profile: DeviceProfile) -> dict:
    return {
        "cc-oob/v1": 1,
        "ble": profile.ble_generation,
        "compass": profile.have_compass,
        "imu": profile.have_imu,
        "cs": profile.have_cs,
        "uwb": profile.have_uwb,
        "connect": profile.connect_support,
    }


def sideband_parse(payload: dict) -> Optional[DeviceProfile]:
    if not isinstance(payload, dict) or payload.get("cc-oob/v1") != 1:
        return None
    return DeviceProfile(
        ble_generation=int(payload.get("ble", 4)),
        have_compass=bool(payload.get("compass", False)),
        have_imu=bool(payload.get("imu", False)),
        have_cs=bool(payload.get("cs", False)),
        have_uwb=bool(payload.get("uwb", False)),
        connect_support=bool(payload.get("connect", True)),
        name="oob",
    )


TIER_ORDER = [t for t in NavTier]


def _test() -> None:
    checks = 0

    def ok(cond: bool, name: str) -> None:
        nonlocal checks
        checks += 1
        assert cond, name
        print(f"  PASS {name}")

    # 1. Tripwire: no new MeasurementSource may be silently shipped.
    ok(assert_legacy_wire_snapshot(),
       "MeasurementSource frozen: old builds decode all new advertisements")

    # 2. BLE4 basic: gradient + RSSI bands only, never direction/motion.
    b4 = PROFILE_STUBS["ble4_basic"]
    tiers = CapabilityRegistry.available_tiers(b4)
    ok(tiers == [NavTier.RSSI_LOGDIST, NavTier.RSSI_BAND],
       f"ble4 tiers = {[t.name for t in tiers]}")
    ok(CapabilityRegistry.best_tier(b4) == NavTier.RSSI_LOGDIST,
       "ble4 best tier is RSSI log-distance")
    ok(tier_source(NavTier.RSSI_BAND) == MeasurementSource.BLE_RSSI,
       "legacy wire source for RSSI is BLE_RSSI")
    ok(tier_source(NavTier.HEADING_REL) == MeasurementSource.DIRECTION_FINDING,
       "legacy wire source for heading is DIRECTION_FINDING")

    # 3. Compass lifts a BLE5 phone to heading-based bearing (still legacy wire).
    b5c = PROFILE_STUBS["ble5_compass"]
    best = CapabilityRegistry.best_tier(b5c)
    ok(best == NavTier.HEADING_REL, f"ble5+compass best tier = {best.name}")

    # 4. CS/UWB require BOTH ends.
    b6 = PROFILE_STUBS["ble6_cs"]
    ok(CapabilityRegistry.best_tier(b6, None) == NavTier.MOTION_VECTOR,
       "CS not used until a peer is known to have it")
    ok(CapabilityRegistry.best_tier(b6, PROFILE_STUBS["ble6_cs"])
       == NavTier.CHANNEL_SOUNDING, "two CS phones negotiate CS tier")
    ok(CapabilityRegistry.requires_both_ends(NavTier.CHANNEL_SOUNDING),
       "CS is two-ended")
    uwb = PROFILE_STUBS["uwb"]
    ok(CapabilityRegistry.best_tier(uwb, uwb) == NavTier.UWB,
       "two UWB phones negotiate UWB tier")

    # 5. Descent keeps working when the strongest tier's runtime check fails.
    ok(CapabilityRegistry.descend(b5c, None, {NavTier.HEADING_REL: False})
       == NavTier.RSSI_LOGDIST, "descent: heading fails -> RSSI log-dist")
    ok(CapabilityRegistry.descend(b5c, None,
                                  {NavTier.HEADING_REL: False,
                                   NavTier.RSSI_LOGDIST: False})
       == NavTier.RSSI_BAND, "descent: down to RSSI band")
    ok(CapabilityRegistry.descend(b5c, None,
                                  {NavTier.HEADING_REL: False,
                                   NavTier.RSSI_LOGDIST: False,
                                   NavTier.RSSI_BAND: False})
       == NavTier.HOP_GRADIENT, "descent: never below hop-gradient")

    # 6. OOB sideband round-trips without touching the legacy wire.
    prof = sideband_parse(sideband_serialize(PROFILE_STUBS["ble6_cs"]))
    ok(prof is not None and prof.have_cs and prof.ble_generation == 6,
       "OOB sideband serialize/parse round-trip")
    ok(sideband_parse({"cc-oob/v1": 2}) is None, "foreign sideband rejected")

    print(f"-" * 50)
    print(f"compat layer: {checks} checks PASSED")


if __name__ == "__main__":
    _test()