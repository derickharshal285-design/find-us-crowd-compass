"""Application layer: responder guidance instructions (spec §48 L3→L5 intake).

A device asks: "I have this local graph + this SOS gradient. What do I tell the
responder?" The answer is honest by construction (spec §53, §65): no value is
fabricated, a device never claims a route it cannot point to, and physical
direction is reported as unproven unless a sensor actually proves it.

Modes:
  NO_SOS_KNOWN   - this device has never heard of the SOS id.
  NO_VALID_ROUTE - SOS is known but this device has no adopted hop, or every
                   next-hop neighbor at hop-1 has aged out (route expired).
  NAVIGATING     - route exists; move toward the freshest hop-1 neighbor.
  AT_TARGET      - this device is (or is physically adjacent to) the origin.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

import domain


@dataclass(frozen=True)
class GuidanceInstruction:
    sos_id: domain.SosId
    mode: str
    summary: str
    my_hop: Optional[int] = None
    target: Optional[domain.NodeId] = None
    alternatives: Tuple[domain.NodeId, ...] = ()
    target_is_origin: bool = False
    hint: str = ""

    def __str__(self) -> str:
        return f"[{self.mode}] {self.summary}"

    def to_record(self) -> dict:
        return {
            "sos_id": str(self.sos_id),
            "mode": self.mode,
            "hop": self.my_hop,
            "target": str(self.target) if self.target else None,
            "alternatives": [str(a) for a in self.alternatives],
            "summary": self.summary,
            "hint": self.hint,
        }


def responder_guidance(device: "object", sos_id: Any,
                       ) -> "GuidanceInstruction":
    """Build the honest guidance instruction for `device` about `sos_id`."""
    sid = domain.SosId(str(sos_id))
    engine = device.sos_engine
    me = device.wire_id

    if sid not in engine.events or engine.events[sid].status != domain.SosStatus.ACTIVE:
        return GuidanceInstruction(sid, "NO_SOS_KNOWN",
                                   "no such emergency signal in range",
                                   my_hop=None)
    if not engine.is_active(sid, device.t):
        return GuidanceInstruction(sid, "NO_SOS_KNOWN",
                                   "emergency signal has expired",
                                   my_hop=None)

    my_hop = engine.hop_of(sid, me)
    if my_hop is None:
        return GuidanceInstruction(sid, "NO_VALID_ROUTE",
                                   "signal heard, no route adopted yet",
                                   my_hop=None)

    event = engine.events[sid]
    origin = event.origin if event.origin and str(event.origin) != "<unknown>" else None
    if my_hop == 0:
        return GuidanceInstruction(sid, "AT_TARGET",
                                   f"you are the origin of {sid}",
                                   my_hop=0, target_is_origin=True)

    freshness = getattr(device, "route_freshness", 120.0)
    cands = []
    for nb in device.graph.neighbors(me):
        ad = device.advertised(sid, nb)
        if ad is None or ad.hop != my_hop - 1:
            continue
        if device.t - ad.t > freshness:
            continue
        cands.append((nb, ad.t))
    if not cands:
        return GuidanceInstruction(
            sid, "NO_VALID_ROUTE",
            f"route broken at hop {my_hop}: no live hop-{my_hop - 1} advertiser",
            my_hop=my_hop)

    ordered = [nid for nid, _ in sorted(cands, key=lambda c: c[1], reverse=True)]
    best = ordered[0]
    alternatives = tuple(ordered[1:])

    target_is_origin = origin is not None and best == origin
    detail = (
        f"emergency at hop {my_hop}; move toward device '{best}'"
        f" ({len(ordered)} route(s) of hop {my_hop - 1})"
    )
    hint = _direction_hint(device, best)
    return GuidanceInstruction(sid, "NAVIGATING", detail, my_hop=my_hop,
                               target=best, alternatives=alternatives,
                               target_is_origin=target_is_origin, hint=hint)


def _direction_hint(device: "object", toward: domain.NodeId) -> str:
    """Physical direction is honest: false only when actually measured (spec §53-54)."""
    if device.has_direction_sensor and device.direction_to(toward) is not None:
        bearing = device.direction_to(toward)
        return f"measured bearing {bearing:.0f} deg (needs RESPONDER-GRADE validation)"
    return ("physical direction on a plain phone is UNPROVEN (research); "
            "walk and check which route stays freshest")


def _test() -> None:
    from devices import DeviceApp
    from protocol import PacketCodec
    from world import AppWorld

    w = AppWorld(dt=1.0)
    w.radio.packet_loss = 0.0
    w.add_device(DeviceApp("T"), 0.0, 0.0)
    w.add_device(DeviceApp("A"), 60.0, 0.0)
    w.add_device(DeviceApp("B"), 120.0, 0.0)
    w.add_device(DeviceApp("R", edge_expire_after=5.0, node_expire_after=10.0),
                 180.0, 0.0)
    w.add_device(DeviceApp("R2"), 180.0, 0.0)
    w.add_device(DeviceApp("LONE"), 400.0, 0.0)

    w.set_sos("T", "SOS-1")
    for _ in range(6):
        w.step()

    g = w.devices["R"].guidance("SOS-1")
    assert g.mode == "NAVIGATING", g
    assert g.my_hop == 3, g
    assert g.target == w.devices["B"].id, g
    assert "UNPROVEN" in g.hint, g

    lone = w.devices["LONE"].guidance("SOS-1")
    assert lone.mode == "NO_SOS_KNOWN", lone

    w.move_to("LONE", 60.0, 60.0)
    for _ in range(2):
        w.step()
    g2 = w.devices["LONE"].guidance("SOS-1")
    assert g2.mode == "NAVIGATING" and g2.my_hop == 2, (g2, w.devices["LONE"].hop_map("SOS-1"))

    w.split_off("R", "R2")
    for _ in range(14):
        w.step()
    g3 = w.devices["R"].guidance("SOS-1")
    assert g3.mode == "NO_VALID_ROUTE", g3
    g4 = w.devices["R2"].guidance("SOS-1")
    assert g4.mode == "NAVIGATING", g4

    codec = PacketCodec()
    for dev in w.devices.values():
        for blob in dev.outgoing():
            pkt = codec.decode(blob)
            if pkt.event_id is not None:
                assert pkt.sender == dev.id, pkt
                assert pkt.hop == (dev.sos_engine.hop_of(pkt.event_id, dev.id) or 0)

    origin = w.devices["T"].sos_engine.hop_of("SOS-1", w.devices["T"].id)
    assert origin == 0

    print("guidance selftest: PASSED")