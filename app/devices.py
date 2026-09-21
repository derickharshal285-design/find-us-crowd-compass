"""Application layer: one phone = one DeviceApp (spec §48 L2/L3, §84, §56).

Each device keeps an entirely LOCAL view: its own dynamic graph (who have I
signaled recently) and its own SOS engine (which hops have I adopted). The app
never fabricates a hop it did not personally adopt (spec §53). Presence
heartbeats refresh node/edge lifecycles (spec §23): a neighbor that keeps
signaling is never aged out; silence is what expires you.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import domain
from graph import DynamicGraph
from protocol import PacketCodec, ProtocolError
from security import IncidentSession
from sos import SosEngine


class HopAdvertisement:
    """What a neighbor claimed about an SOS, as heard by THIS device.

    A device never stores a hop it did not hear on the wire (spec §53): the
    local routing table is built strictly from received advertisements."""

    __slots__ = ("hop", "version", "t")

    def __init__(self, hop: int, version: int, t: float) -> None:
        self.hop = hop
        self.version = version
        self.t = t


class DeviceApp:
    def __init__(self, node_id: Any, t0: float = 0.0, ttl_hops: int = 8,
                 lifespan: float = 900.0, node_expire_after: float = 120.0,
                 edge_expire_after: float = 60.0,
                 has_direction_sensor: bool = False,
                 install_key: Optional[bytes] = None,
                 incident: Optional[IncidentSession] = None) -> None:
        self.id = domain.NodeId(str(node_id))
        self.install_key = (bytes(install_key) if install_key is not None
                            else (b"crowd-install:" + str(node_id).encode()))
        self.ttl_hops = ttl_hops
        self.lifespan = lifespan
        self.t = t0
        self.incident: Optional[IncidentSession] = incident
        self.graph = DynamicGraph(node_stale_after=60.0,
                                  node_expire_after=node_expire_after,
                                  edge_stale_after=60.0,
                                  edge_expire_after=edge_expire_after)
        self.graph.add_node(self.wire_id, self.t)
        self.sos_engine = SosEngine(default_ttl_hops=ttl_hops,
                                    default_lifespan=lifespan)
        self.codec = PacketCodec()
        self.route_freshness = node_expire_after
        self.last_signal: Dict[domain.NodeId, float] = {}
        self.advertisements: Dict[domain.SosId, Dict[domain.NodeId, HopAdvertisement]] = {}
        self.adoptions = 0
        self.rejected_macs = 0
        self.has_direction_sensor = has_direction_sensor

    @property
    def wire_id(self) -> domain.NodeId:
        if self.incident is not None:
            return domain.NodeId(self.incident.pseudonym(self.install_key))
        return self.id

    def join_incident(self, session: IncidentSession) -> None:
        self.incident = session
        self.graph.add_node(self.wire_id, self.t)

    # ---- time -------------------------------------------------------------

    def begin_tick(self, t: float) -> None:
        self.t = t
        self.graph.touch_node(self.wire_id, t)
        self.graph.refresh(t)
        self.sos_engine.expire_stale(t)

    # ---- SOS lifecycle (origin role) --------------------------------------

    def start_sos(self, sos_id: Any, ttl_hops: Optional[int] = None,
                  lifespan: Optional[float] = None) -> domain.SOS:
        sid = domain.SosId(str(sos_id))
        return self.sos_engine.create_sos(
            sid, self.wire_id, t=self.t,
            ttl_hops=ttl_hops or self.ttl_hops,
            lifespan=lifespan if lifespan is not None else self.lifespan)

    def renew_sos(self, sos_id: Any) -> Optional[domain.SOS]:
        renewed = self.sos_engine.renew(sos_id, self.t)
        return renewed

    def end_sos(self, sos_id: Any) -> bool:
        return self.sos_engine.expire(sos_id, self.t)

    # ---- advert --------------------------------------------------------------

    def outgoing(self) -> List[bytes]:
        """Everything this device is allowed to say this tick, wire-encoded.
        A device never advertises a hop it does not hold (spec §53)."""
        out: List[bytes] = []
        heartbeat = domain.RelayPacket(domain.MessageType.HEARTBEAT,
                                       sender=self.wire_id, timestamp=self.t)
        out.append(self._try_encode(heartbeat))
        for sid in self.sos_engine.active_sos_ids(self.t):
            hop = self.sos_engine.hop_of(sid, self.wire_id)
            if hop is None:
                continue
            if hop > 0 and self._best_hop_advert(sid, hop - 1) is None:
                # spec §53/§20: never advertise a hop you cannot back with a
                # live fresher claim. When the origin stops signaling (or an
                # incident ends) upstream goes quiet and, within route_freshness,
                # every downstream relay stops re-advertising too — no ghost
                # gradient keeps guiding responders after the fact.
                continue
            ev = self.sos_engine.events[sid]
            pkt = domain.RelayPacket(
                domain.MessageType.SOS_UPDATE, event_id=sid,
                sender=self.wire_id, hop=int(hop), ttl=ev.ttl_hops,
                source_version=ev.version, timestamp=self.t)
            out.append(self._try_encode(pkt))
        return [b for b in out if b]

    def _best_hop_advert(self, sid: domain.SosId, want_hop: int):
        """Freshest live advertisement I hold claiming `want_hop` for `sid`."""
        best = None
        for nb in self.graph.neighbors(self.wire_id):
            ad = self.advertised(sid, nb)
            if ad is None or ad.hop != want_hop:
                continue
            if self.t - ad.t > self.route_freshness:
                continue
            if best is None or ad.t > best.t:
                best = ad
        return best

    def _try_encode(self, pkt: domain.RelayPacket) -> Optional[bytes]:
        if self.incident is not None:
            pkt = self.incident.attach(pkt)
        try:
            return self.codec.encode(pkt)
        except ProtocolError:
            return None

    # ---- receive ------------------------------------------------------------

    def on_packet(self, remote_id: Any, blob: bytes) -> int:
        """Apply one received frame. Returns 1 if a new SOS hop was adopted."""
        try:
            pkt = self.codec.decode(blob)
        except ProtocolError:
            return 0
        if pkt.sender is None:
            return 0
        if self.incident is not None and not self.incident.verify(pkt):
            self.rejected_macs += 1
            return 0
        src = pkt.sender
        self.last_signal[src] = self.t

        self._signal_seen(src, self.t)

        if pkt.event_id is not None and pkt.message_type in (
                domain.MessageType.SOS, domain.MessageType.SOS_UPDATE,
                domain.MessageType.RELAY):
            sid = domain.SosId(str(pkt.event_id))
            self._record_advertisement(sid, src, int(pkt.hop),
                                       pkt.source_version, self.t)
            self._ensure_event(sid, version=pkt.source_version,
                               ttl=pkt.ttl if pkt.ttl else self.ttl_hops)
            accepted, _ = self.sos_engine.hear(
                sid, self.wire_id, int(pkt.hop), pkt.source_version, self.t)
            if accepted:
                self.adoptions += 1
                return 1
        return 0

    def _signal_seen(self, src: domain.NodeId, t: float) -> None:
        if not self.graph.has_node(src):
            self.graph.add_node(src, t)
        self.graph.touch_node(src, t)
        edge = self.graph.add_edge(self.wire_id, src, t, source="app")
        if edge is not None:
            self.graph.touch_edge(self.wire_id, src, t, bidirectional=True)

    def _record_advertisement(self, sid: domain.SosId, src: domain.NodeId,
                              hop: int, version: int, t: float) -> None:
        bucket = self.advertisements.setdefault(sid, {})
        prev = bucket.get(src)
        if prev is None or version > prev.version or t > prev.t:
            bucket[src] = HopAdvertisement(hop, version, t)

    def advertised(self, sid: Any, node: Any) -> Optional[HopAdvertisement]:
        return self.advertisements.get(domain.SosId(str(sid)), {}).get(
            domain.NodeId(str(node)))

    def _ensure_event(self, sid: domain.SosId, version: int,
                      ttl: int) -> None:
        ev = self.sos_engine.events.get(sid)
        if ev is None:
            ev = domain.SOS(sid, domain.NodeId("<unknown>"),
                            created_at=self.t, version=max(1, version),
                            ttl_hops=max(1, ttl),
                            lifespan_seconds=self.lifespan,
                            expires_at=self.t + self.lifespan,
                            metadata={"learned": True})
            self.sos_engine.events[sid] = ev
            self.sos_engine.gradient[sid] = {}
            return
        if version > ev.version:
            ev.version = version
            if ev.lifespan_seconds is not None:
                ev.expires_at = self.t + ev.lifespan_seconds

    # ---- reading -------------------------------------------------------------

    def known_sos(self, sos_id: Any) -> bool:
        sid = domain.SosId(str(sos_id))
        ev = self.sos_engine.events.get(sid)
        return ev is not None and ev.status == domain.SosStatus.ACTIVE

    def hop_map(self, sos_id: Any) -> Dict[str, int]:
        g = self.sos_engine.gradient.get(domain.SosId(str(sos_id)), {})
        return {str(nid): st.hop for nid, st in sorted(g.items())}

    def guidance(self, sos_id: Any):
        from guidance import responder_guidance
        return responder_guidance(self, sos_id)

    def direction_to(self, other: Any) -> Optional[float]:
        return None

    def neighbors_text(self) -> str:
        nbs = self.graph.neighbors(self.wire_id)
        if not nbs:
            return "none"
        parts = []
        for nb in sorted(nbs, key=str):
            e = self.graph.get_edge(self.wire_id, nb)
            d = f", last_seen t={e.last_seen:.0f}" if e and e.last_seen is not None else ""
            parts.append(f"{nb}{d}")
        return "; ".join(parts)


def _incident_test() -> None:
    """Full secure-incident path: link join, pseudonyms, MAC ver/n spoofing."""
    from security import make_session, parse_link
    from world import AppWorld

    link = make_session("evt-STADIUM").to_link()
    session = parse_link(link)

    w = AppWorld(dt=1.0)
    w.radio.packet_loss = 0.0
    for i, name in enumerate(["T", "A", "B", "R"]):
        w.add_device(DeviceApp(name, install_key=("key-" + name).encode(),
                               edge_expire_after=30.0), 60.0 * i, 0.0)
    for dev in w.devices.values():
        dev.join_incident(session)

    # every device now publishes under an incident pseudonym, never the id
    for name, dev in w.devices.items():
        assert str(dev.wire_id) != name
        assert len(str(dev.wire_id)) == 8

    w.set_sos("T", "EVENT-1")
    for _ in range(6):
        w.step()

    grid = w.hop_grid("EVENT-1")
    assert grid["T"].get(str(w.devices["T"].wire_id)) == 0, grid["T"]

    g = w.devices["R"].guidance("EVENT-1")
    assert g.mode == "NAVIGATING" and g.my_hop == 3, g
    assert g.target == w.devices["B"].wire_id, g

    # forging: a packet signed by a foreign session must be dropped
    outsider = make_session("some-other-incident")
    forge = domain.RelayPacket(domain.MessageType.SOS_UPDATE,
                               event_id=domain.SosId("EVENT-1"),
                               sender=domain.NodeId("EVIL0001"),
                               source_version=99, hop=0, ttl=8,
                               timestamp=w.t)
    forge = outsider.attach(forge)
    from protocol import PacketCodec
    blob = PacketCodec().encode(forge)
    r = w.devices["R"]
    before = r.rejected_macs
    r.on_packet(domain.NodeId("EVIL0001"), blob)
    assert r.rejected_macs == before + 1
    assert domain.NodeId("EVIL0001") not in r.graph.neighbors(r.wire_id)

    # and a valid cooperating re-broadcast still works after the forgery
    g2 = w.devices["R"].guidance("EVENT-1")
    assert g2.mode == "NAVIGATING", g2

    print("incident security app test: PASSED")


def _connectivity_test() -> None:
    """Raw link checkout: join -> bidirectional link -> silence ages it out."""
    from security import make_session
    from world import AppWorld

    w = AppWorld(dt=1.0)
    w.radio.packet_loss = 0.0
    a = DeviceApp("A", edge_expire_after=5.0, node_expire_after=10.0)
    b = DeviceApp("B", edge_expire_after=5.0, node_expire_after=10.0)
    w.add_device(a, 0.0, 0.0)
    w.add_device(b, 40.0, 0.0)
    session = make_session("conn-check")
    for dev in w.devices.values():
        dev.join_incident(session)
    w.set_sos("A", "PING")
    for _ in range(3):
        w.step()

    ea = a.graph.get_edge(a.wire_id, b.wire_id)
    eb = b.graph.get_edge(b.wire_id, a.wire_id)
    assert ea is not None and eb is not None, "link must form both directions"
    assert ea.last_bidirectional_exchange == eb.last_bidirectional_exchange
    assert a.known_sos("PING") and a.sos_engine.hop_of("PING", a.wire_id) == 0

    w.split_off("B")
    for _ in range(6):
        w.step()
    e_aging = a.graph.get_edge(a.wire_id, b.wire_id)
    assert e_aging.lifecycle.value.upper() in ("AGING", "STALE", "EXPIRED"), e_aging

    for _ in range(10):
        w.step()
    g = a.guidance("PING")
    assert g.mode != "NAVIGATING", g
    assert g.mode in ("NO_VALID_ROUTE", "NO_SOS_KNOWN", "AT_TARGET"), g
    assert domain.NodeId(b.wire_id) not in a.graph.neighbors(a.wire_id), \
        "aged-out link must not route traffic"

    # relationship memory after FULL expiry: B signals again and is re-admitted
    bnode_was_expired = a.graph.get_node(b.wire_id).lifecycle.value == "EXPIRED"
    assert bnode_was_expired, "peer must have fully expired before the revival test"
    w.reconnect("B")
    for _ in range(4):
        w.step()
    e_revived = a.graph.get_edge(a.wire_id, b.wire_id)
    assert e_revived is not None and e_revived.lifecycle.value == "ACTIVE", e_revived
    assert a.graph.get_node(b.wire_id).lifecycle.value == "ACTIVE", \
        "re-signaling peer re-admitted (authenticated contact resumes memory)"
    assert domain.NodeId(b.wire_id) in a.graph.neighbors(a.wire_id), \
        "revived link appears in neighbors again"
    gb = b.guidance("PING")
    assert gb.mode == "NAVIGATING", gb

    print("connectivity test: PASSED (incl. revive-after-expiry)")


def _test() -> None:
    from world import AppWorld

    w = AppWorld(dt=1.0)
    names = ["T", "A", "B", "R"]
    for i, name in enumerate(names):
        w.add_device(DeviceApp(name, edge_expire_after=5.0,
                               node_expire_after=10.0), 60.0 * i, 0.0)
    w.set_sos("T", "SOS-1")
    for _ in range(5):
        w.step()

    hops = w.devices["R"].hop_map("SOS-1")
    assert hops == {"R": 3}, hops
    grid = w.hop_grid("SOS-1")
    assert grid["T"]["T"] == 0 and grid["A"]["A"] == 1
    assert grid["B"]["B"] == 2 and grid["R"]["R"] == 3, grid

    g = w.devices["R"].guidance("SOS-1")
    assert g.mode == "NAVIGATING" and g.my_hop == 3, g
    assert g.target == w.devices["B"].id, g

    # liveness: A keeps signaling; the target keeps signaling; course stays up
    w.split_off("B")
    for _ in range(12):
        w.step()
    assert w.devices["A"].graph.get_node("A").lifecycle.value != "EXPIRED"
    assert w.devices["A"].graph.get_node("T").lifecycle.value != "EXPIRED"
    bnode = w.devices["R"].graph.get_node("B")
    assert bnode is None or bnode.lifecycle.value == "EXPIRED"

    # honesty: R must not claim a route when every hop-1 neighbor is gone
    g2 = w.devices["R"].guidance("SOS-1")
    assert g2.mode == "NO_VALID_ROUTE", g2

    # an unreachable device reports NO_SOS_KNOWN, not a fake zero
    w2 = AppWorld(dt=1.0)
    w2.add_device(DeviceApp("S", edge_expire_after=5.0,
                            node_expire_after=10.0), 0.0, 0.0)
    w2.add_device(DeviceApp("FAR"), 1000.0, 0.0)
    w2.add_device(DeviceApp("MID"), 55.0, 10.0)
    w2.set_sos("S", "SOS-FAR")
    for _ in range(3):
        w2.step()
    assert w2.devices["FAR"].guidance("SOS-FAR").mode == "NO_SOS_KNOWN"
    assert w2.devices["MID"].guidance("SOS-FAR").mode == "NAVIGATING"

    _incident_test()
    _connectivity_test()

    # ghost-kill regression: origin ends an SOS; downstream relays must stop
    # re-advertising it within (hops × route_freshness), so no one keeps
    # guiding to a dead incident for the full 900 s lifetime
    wg = AppWorld(dt=1.0)
    wg.radio.packet_loss = 0.0
    from security import make_session
    ghost_session = make_session("ghost")
    for i, name in enumerate(["T", "A", "B"]):
        wg.add_device(DeviceApp(name, install_key=("ky-" + name).encode(),
                                edge_expire_after=5.0, node_expire_after=10.0),
                      60.0 * i, 0.0)
    for dev in wg.devices.values():
        dev.join_incident(ghost_session)
    wg.set_sos("T", "DEAD")
    for _ in range(3):
        wg.step()
    assert wg.devices["B"].guidance("DEAD").mode == "NAVIGATING", "precondition"
    wg.devices["T"].end_sos("DEAD")
    for _ in range(28):
        wg.step()
    from protocol import PacketCodec
    ghost_left = [p for bl in wg.devices["A"].outgoing()
                  for p in [PacketCodec().decode(bl)]
                  if p.event_id is not None and str(p.event_id) == "DEAD"]
    assert not ghost_left, "relay must not keep advertising an ended incident"
    gb = wg.devices["B"].guidance("DEAD")
    assert gb.mode != "NAVIGATING", gb

    print("devices selftest: PASSED (incl. secure incident + connectivity + ghost-kill)")


if __name__ == "__main__":
    _test()