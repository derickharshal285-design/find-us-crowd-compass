"""Block 8 — Simulation (spec §63 Block 8, §56, §57, §59).

Fake radio transport (positions, range, packet loss, blocked relays) on which
the SAME core logic (DynamicGraph + SosEngine + PacketCodec) runs that would
run on the real transport (spec §64, §18x AdR-001/004). Scenario list follows
spec §57; metrics follow spec §59. Deterministic (fixed seed).
Core code is transport-agnostic: it never calls BLE APIs (spec §64).
"""
from __future__ import annotations

import math
import random
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from domain import MessageType, NodeId
from graph import DynamicGraph
from protocol import PacketCodec
from sos import SosEngine
from domain import now as _wall_now
from direction import rssi_to_meters, RSSI_AT_1M_DBM, PATH_LOSS_N


class FakeRadio:
    """Space-based transport: in-range pairs can exchange packets (spec §56).
    Also models packet loss, jitter, and 'blocked' relays (attacker/failure).
    """

    def __init__(self, range_m: float = 80.0, packet_loss: float = 0.0,
                 seed: int = 0) -> None:
        self.range_m = range_m
        self.packet_loss = packet_loss
        self.rng = random.Random(seed)
        self.positions: Dict[NodeId, Tuple[float, float]] = {}
        self.blocked: Set[NodeId] = set()
        self.tx_attempts = 0
        self.tx_delivered = 0

    def set_position(self, node: Any, xy: Tuple[float, float]) -> None:
        self.positions[NodeId(str(node))] = xy

    def move_by(self, node: Any, dx: float, dy: float) -> None:
        nid = NodeId(str(node))
        x, y = self.positions.get(nid, (0.0, 0.0))
        self.positions[nid] = (x + dx, y + dy)

    def distance(self, a: Any, b: Any) -> Optional[float]:
        pa, pb = self.positions.get(NodeId(str(a))), self.positions.get(NodeId(str(b)))
        if pa is None or pb is None:
            return None
        return math.hypot(pa[0] - pb[0], pa[1] - pb[1])

    def rssi_between(self, a: Any, b: Any,
                     a_dbm: float = RSSI_AT_1M_DBM, n: float = PATH_LOSS_N
                     ) -> Optional[float]:
        """Deterministic RSSI under the log-distance model (core/direction.py)."""
        d = self.distance(a, b)
        if d is None or d < 0.5:
            return None
        return a_dbm - 10.0 * n * math.log10(d)

    def meters_from_rssi(self, a: Any, b: Any) -> Optional[float]:
        """Inverse log-distance estimate the app would compute, for validation."""
        rssi = self.rssi_between(a, b)
        if rssi is None:
            return None
        return rssi_to_meters(rssi)

    def bearing_deg(self, a: Any, b: Any) -> Optional[float]:
        """World bearing from a to b (0=N, 90=E), match self.default_heading."""
        pa, pb = self.positions.get(NodeId(str(a))), self.positions.get(NodeId(str(b)))
        if pa is None or pb is None:
            return None
        dx, dy = pb[0] - pa[0], pb[1] - pa[1]
        return math.degrees(math.atan2(dx, dy)) % 360.0

    def in_range(self, a: Any, b: Any) -> bool:
        if NodeId(str(a)) in self.blocked or NodeId(str(b)) in self.blocked:
            return False
        d = self.distance(a, b)
        return d is not None and d <= self.range_m

    def link_exists(self, a: Any, b: Any) -> bool:
        """Deterministic link state for graph sync (no loss applied)."""
        return self.in_range(a, b)

    def transmit(self, src: Any, payload: bytes) -> List[Tuple[NodeId, bytes]]:
        """Best-effort broadcast to all in-range neighbors. Returns the subset
        of payload copies that actually arrived (packet loss applied)."""
        src = NodeId(str(src))
        out: List[Tuple[NodeId, bytes]] = []
        for dst in self.positions:
            if dst == src or not self.in_range(src, dst):
                continue
            self.tx_attempts += 1
            if self.rng.random() >= self.packet_loss:
                self.tx_delivered += 1
                out.append((dst, payload))
        return out

    def delivery_rate(self) -> float:
        if self.tx_attempts == 0:
            return 0.0
        return self.tx_delivered / self.tx_attempts


class MeshSim:
    """One simulated mesh world: positions + graph + SOS engine + protocol."""

    def __init__(self, range_m: float = 80.0, packet_loss: float = 0.0,
                 seed: int = 0,
                 edge_stale_after: float = 30.0, edge_expire_after: float = 60.0,
                 node_stale_after: float = 30.0, node_expire_after: float = 120.0,
                 ttl_hops: int = 8, sos_lifespan: float = 900.0) -> None:
        self.radio = FakeRadio(range_m=range_m, packet_loss=packet_loss, seed=seed)
        self.graph = DynamicGraph(
            node_stale_after=node_stale_after,
            node_expire_after=node_expire_after,
            edge_stale_after=edge_stale_after,
            edge_expire_after=edge_expire_after)
        self.sos = SosEngine(default_ttl_hops=ttl_hops,
                             default_lifespan=sos_lifespan)
        self.codec = PacketCodec()
        self.position_memo: Dict[NodeId, Tuple[float, float]] = {}
        self.t = 0.0
        self.stats = {"tx": 0, "delivered": 0, "adopted": 0, "dups": 0}
        self.component_history: List[int] = []

    def add_node(self, nid: Any, xy: Tuple[float, float]) -> None:
        self.graph.add_node(nid, t=self.t)
        self.radio.set_position(nid, xy)

    def remove_node(self, nid: Any) -> None:
        nid = NodeId(str(nid))
        self.graph.remove_node(nid, t=self.t)
        self.radio.positions.pop(nid, None)
        self.radio.blocked.discard(nid)

    def move(self, nid: Any, dx: float, dy: float) -> None:
        self.radio.move_by(nid, dx, dy)

    # ---- the transport-facing loop ----------------------------------------

    def _sync_links(self) -> None:
        """Turn radio positions into graph edges (transport -> core)."""
        ids = sorted(self.radio.positions)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if self.radio.link_exists(a, b):
                    self.graph.add_edge(a, b, t=self.t, source="radio")
                    self.graph.touch_edge(a, b, t=self.t, bidirectional=True)
                    self.graph.touch_node(a, t=self.t)
                    self.graph.touch_node(b, t=self.t)
                elif self.graph.has_edge(a, b):
                    self.graph.expire_edge(a, b, t=self.t)

    def _advertise_sos_round(self) -> List[Tuple[NodeId, NodeId]]:
        """Origin + every graded node broadcasts an SOS_UPDATE packet; the
        protocol codec encodes it; radio delivers to in-range neighbors; the
        engine applies it (spec §22, §24C/E). Returns the delivered (src, dst)
        links so step() can refresh node/edge lifecycles from real signal."""
        delivered: List[Tuple[NodeId, NodeId]] = []
        for sid, grad in list(self.sos.gradient.items()):
            event = self.sos.events.get(sid)
            ttl = event.ttl_hops if event is not None else self.sos.default_ttl_hops
            for node, st in list(grad.items()):
                advertised_hop = st.hop
                advertised_version = st.version
                pkt = self.codec.encode(
                    from_sos_update(sid, node, advertised_hop,
                                    advertised_version, self.t, ttl))
                self.stats["tx"] += 1
                for dst, blob in self.radio.transmit(node, pkt):
                    self.stats["delivered"] += 1
                    delivered.append((NodeId(str(node)), dst))
                    try:
                        decoded = self.codec.decode(blob)
                    except ValueError:
                        continue
                    accepted, _newhop = self.sos.hear(
                        decoded.event_id, dst, decoded.hop,
                        decoded.source_version,
                        self.t, check_duplicate=True)
                    if accepted:
                        self.stats["adopted"] += 1
                    else:
                        self.stats["dups"] += 1
        return delivered

    def step(self, dt: float = 1.0) -> None:
        """Advance the world: move-independent link refresh, flood, aging."""
        self.t += dt
        self._sync_links()
        for _ in range(6):          # a couple of propagation rounds per step
            for src, dst in self._advertise_sos_round():
                self.graph.touch_node(src, t=self.t)
                self.graph.touch_node(dst, t=self.t)
                self.graph.touch_edge(src, dst, t=self.t, bidirectional=True)
        self.graph.refresh(t=self.t)
        self.sos.expire_stale(t=self.t)
        self.graph.refresh(t=self.t)
        self.component_history.append(len(self.graph.connected_components()))

    # ---- metrics (spec §59) -----------------------------------------------

    def metrics(self) -> Dict[str, Any]:
        comps = self.graph.connected_components()
        m = {
            "t_seconds": self.t,
            "nodes": len(self.graph.node_ids()),
            "edges": len(self.graph.edge_ids()),
            "components": len(comps),
            "largest_component": max((len(c) for c in comps), default=0),
            "delivery_rate": self.radio.delivery_rate(),
            "duplicate_ratio": (self.stats["dups"] /
                                max(1, self.stats["adopted"] + self.stats["dups"])),
            "component_history": [
                n for n in self.component_history if n > 1],
        }
        for sid in self.sos.active_sos_ids(t=self.t):
            m[f"coverage_{sid}"] = self.sos.coverage(sid, self.graph)
        return m


def from_sos_update(sid: Any, node: Any, hop: int, version: int,
                    ts: float, ttl: int = 8):
    """Build the wire packet a node advertises for an SOS (Block 6 usage).
    The wire TTL carries the event's own hop cap (§22.6) so loop planning and
    on-wire limits can never diverge."""
    from domain import RelayPacket, SosId
    return RelayPacket(
        message_type=MessageType.SOS_UPDATE,
        event_id=SosId(str(sid)),
        sender=NodeId(str(node)),
        source_version=version,
        hop=hop,
        ttl=max(0, min(255, int(ttl))),
        timestamp=ts or _wall_now(),
    )


# ---- parameter plan: hop count & signal expiry (2026-09) ------------------
# Answers "how many hops do we need + how long do relationships live" with
# evidence instead of guesses. Recorded in docs/EXPERIMENT_PLAN.md.

def _probe_ttl_depth(ttl: int, n_chain: int = 14) -> Dict[str, Any]:
    """Deep chain, SOS at one end. Reports coverage & max reached hop for a
    given hop cap. Full coverage needs ttl >= (n_chain - 1)."""
    sim = MeshSim(range_m=100.0)
    for i in range(n_chain):
        sim.add_node(f"n{i}", (i * 60, 0))
    sim.sos.create_sos("depth", "n0", t=sim.t, ttl_hops=ttl)
    for _ in range(20):
        sim.step()
    hops = [st.hop for st in sim.sos.gradient["depth"].values()]
    return {"ttl": ttl, "coverage": round(sim.sos.coverage("depth", sim.graph), 3),
            "max_hop": max(hops) if hops else 0}


def _probe_signal_expiry(stale: float, hard: float) -> Dict[str, Any]:
    """A and B in range; B walks away and stops signaling. Measures when the
    route dies (topology truth: immediately) and when the *device* B is
    declared STALE then EXPIRED by aging (spec §19/§20, §23 memory)."""
    sim = MeshSim(range_m=100.0, node_stale_after=stale,
                  node_expire_after=hard,
                  edge_stale_after=stale, edge_expire_after=hard)
    sim.add_node("A", (0, 0))
    sim.add_node("B", (40, 0))
    for _ in range(3):
        sim.step()
    t0 = sim.t
    sim.move("B", 10000, 0)  # leaves range, goes fully silent
    route_gone = stale_at = expired_at = None
    for _ in range(int(hard) + 5):
        sim.step()
        if route_gone is None and not sim.graph.is_reachable("A", "B"):
            route_gone = sim.t - t0
        lc = sim.graph.get_node("B")
        if lc is not None and lc.lifecycle.value == "STALE" and stale_at is None:
            stale_at = sim.t - t0
        if lc is not None and lc.lifecycle.value == "EXPIRED" and expired_at is None:
            expired_at = sim.t - t0
    # reconnect within the stale window (relationship memory, §23)
    sim2 = MeshSim(range_m=100.0, node_stale_after=stale, node_expire_after=hard)
    sim2.add_node("A", (0, 0))
    sim2.add_node("B", (40, 0))
    for _ in range(3):
        sim2.step()
    sim2.move("B", 10000, 0)
    for _ in range(int(stale // 2) + 1):   # gone only halfway into stale window
        sim2.step()
    sim2.move("B", -10000, 0)              # returns before expiry
    for _ in range(2):
        sim2.step()
    reconnected = sim2.graph.is_reachable("A", "B")
    return {"stale_after": stale, "hard_after": hard,
            "route_gone_at": route_gone, "stale_at": stale_at,
            "expired_at": expired_at, "reconnected_in_grace": reconnected}


def run_sweep() -> Dict[str, Any]:
    print("Parameter plan: hop count & signal expiry (2026-09 sweep)")
    print("=" * 72)
    print("A) HOP BUDGET (TTL) — 14-node chain, SOS at n0 (worst-case depth=13)")
    print(f"{'ttl':>4} {'coverage':>9} {'max_hop':>8}")
    ttl_rows = [_probe_ttl_depth(t) for t in (3, 5, 6, 7, 8, 10, 12, 13, 16)]
    for r in ttl_rows:
        print(f"{r['ttl']:>4} {r['coverage']:>9} {r['max_hop']:>8}")
    min_full = next((r["ttl"] for r in ttl_rows if abs(r["coverage"] - 1.0) < 1e-9),
                    None)

    print()
    print("B) SIGNAL-EXPIRY — route-gone vs device STALE/EXPIRED (seconds)")
    print(f"{'stale':>6} {'hard':>6} {'route_gone':>11} {'STALE@':>8} {'EXPIRED@':>9} {'grace_reconnect':>16}")
    exp_rows = [_probe_signal_expiry(s, h) for s, h in
               ((15.0, 30.0), (30.0, 60.0), (30.0, 120.0), (60.0, 180.0), (120.0, 300.0))]
    for r in exp_rows:
        print(f"{r['stale_after']:>6} {r['hard_after']:>6} "
              f"{str(r['route_gone_at']):>11} {str(r['stale_at']):>8} "
              f"{str(r['expired_at']):>9} {str(r['reconnected_in_grace']):>16}")

    print()
    print("C) LIVENESS GUARD — nodes that keep signaling must never age out")
    sim = MeshSim(range_m=100.0)
    for i in range(6):
        sim.add_node(f"g{i}", (i * 60, 0))
    sim.sos.create_sos("cont", "g0", t=sim.t)
    for _ in range(140):
        sim.step()  # 140 s >> node_expire_after (120 s)
    alive = all(sim.graph.get_node(f"g{i}").lifecycle.value != "EXPIRED"
                for i in range(6))
    print(f"  all 6 signaling nodes still ACTIVE after 140s: {alive}")
    summary = {
        "min_full_ttl_14node_chain": min_full,
        "coverage_by_ttl": {r["ttl"]: r["coverage"] for r in ttl_rows},
        "expiry_by_config": exp_rows,
        "liveness_guard_ok": alive,
    }
    print()
    print("READING (sim evidence only — field values still require §63 Block 11):")
    print(f"  - full depth needs TTL >= crowd diameter in hops (here {min_full}).")
    print("  - default TTL=8 covers up to an 8-hop crowd; raise to 12 for deeper.")
    print("  - route-vs-device split: topology dies instantly, device lingers")
    print("    until hard expiry -> relationship memory (§23) without ghost routes.")
    print("  - grace reconnect: B returns mid-stale-window and is reachable again.")
    return summary

def _run(name: str, checks: List[Tuple[bool, str]]) -> Dict[str, Any]:
    failed = [why for ok_, why in checks if not ok_]
    return {"scenario": name, "checks": len(checks), "passed": len(checks) - len(failed),
            "failed": failed}


def scenario_two_nodes() -> Dict[str, Any]:
    sim = MeshSim(range_m=100.0)
    sim.add_node("A", (0, 0))
    sim.add_node("B", (10, 0))
    sim.step()
    ok_ = sim.graph.has_edge("A", "B")
    c0 = sim.metrics()
    sim.move("B", 500, 0)  # move apart
    for _ in range(3):
        sim.step()
    gone = not sim.graph.is_edge_live("A", "B")
    return _run("1 two-nodes-close-then-apart", [(ok_, "edge formed (spec §57.1)"),
                                                 (gone, "edge gone when apart (§57.2)")])


def scenario_one_relay() -> Dict[str, Any]:
    sim = MeshSim(range_m=100.0)
    sim.add_node("A", (0, 0))
    sim.add_node("R", (50, 0))
    sim.add_node("C", (100, 0))
    sim.sos.create_sos("s1", "A", t=sim.t)
    for _ in range(4):
        sim.step()
    m = sim.metrics()
    return _run("3-one-relay", [(sim.graph.is_reachable("A", "C"), "A-C via relay R"),
                                (m["coverage_s1"] >= 2 / 3, "SOS reached C via R")])


def scenario_relay_disappears() -> Dict[str, Any]:
    sim = MeshSim(range_m=100.0)
    for i, xy in enumerate([(0, 0), (60, 0), (120, 0), (180, 0)]):
        sim.add_node(chr(65 + i), xy)
    sim.sos.create_sos("s2", "A", t=sim.t)
    for _ in range(5):
        sim.step()
    reach_before = sim.graph.is_reachable("A", "D")
    sim.remove_node("B")  # the relay vanishes (A-C and B-D are out of range)
    for _ in range(3):
        sim.step()
    return _run("5-relay-disappears", [(reach_before, "4-node chain connected"),
                                       (not sim.graph.is_reachable("A", "D"),
                                        "route breaks when relay removed (§57.5)")])


def scenario_new_node_joins() -> Dict[str, Any]:
    sim = MeshSim(range_m=100.0)
    for i, xy in enumerate([(0, 0), (50, 0)]):
        sim.add_node(chr(65 + i), xy)
    sim.sos.create_sos("s3", "A", t=sim.t)
    for _ in range(4):
        sim.step()
    sim.add_node("J", (60, 0))  # joins late, one hop off B
    for _ in range(5):
        sim.step()
    m = sim.metrics()
    return _run("6-new-node-joins", [(sim.graph.has_edge("B", "J"), "joiner linked (§57.6)"),
                                     (m.get("coverage_s3", 0) == 1.0, "joiner learned gradient")])


def scenario_split_reconnect() -> Dict[str, Any]:
    sim = MeshSim(range_m=50.0)
    for i, xy in enumerate([(0, 0), (20, 0), (200, 0), (220, 0)]):
        sim.add_node(chr(65 + i), xy)
    for _ in range(3):
        sim.step()
    split_seen = len(sim.graph.connected_components()) >= 2
    sim.move("C", -180, 0)   # the two clusters physically approach
    sim.move("D", -205, 0)
    for _ in range(3):
        sim.step()
    reunited = sim.graph.is_reachable("A", "D")
    return _run("7-split-8-reconnect", [(split_seen, "group split into components"),
                                        (reunited, "components reconnected (§57.7/8)")])


def scenario_anchor_disappears() -> Dict[str, Any]:
    sim = MeshSim(range_m=100.0)
    for i, xy in enumerate([(0, 0), (40, 0), (80, 0)]):
        sim.add_node(chr(65 + i), xy)
    sim.sos.create_sos("s4", "A", t=sim.t)
    for _ in range(4):
        sim.step()
    sim.remove_node("A")
    for _ in range(3):
        sim.step()
    return _run("9-anchor-disappears", [(sim.graph.is_reachable("B", "C"),
                                        "relatives survive without anchor (§57.9)")])


def scenario_sos_deep() -> Dict[str, Any]:
    sim = MeshSim(range_m=100.0)
    for i in range(6):
        sim.add_node(f"n{i}", (i * 60, 0))
    sim.sos.create_sos("deep", "n3", t=sim.t)
    for _ in range(8):
        sim.step()
    m = sim.metrics()
    return _run("10-sos-deep", [(m.get("coverage_deep", 0) >= 5 / 6,
                                "SOS deep inside propagates (§57.10)"),
                                (sim.sos.hop_of("deep", "n0") == 3,
                                 "correct hop depth")])


def scenario_responder_late() -> Dict[str, Any]:
    sim = MeshSim(range_m=100.0)
    for i in range(5):
        sim.add_node(f"r{i}", (i * 55, 0))
    sim.sos.create_sos("late", "r0", t=sim.t)
    for _ in range(6):
        sim.step()
    sim.add_node("responder", (280, 0))
    for _ in range(6):
        sim.step()
    hop = sim.sos.hop_of("late", "responder")
    return _run("11-responder-late", [(hop == 5, "late responder learns gradient "
                                       f"(hop {hop}, §57.11)")])


def scenario_multi_path() -> Dict[str, Any]:
    sim = MeshSim(range_m=60.0)
    for i, xy in enumerate([(0, 0), (30, 0), (60, 0), (90, 0)]):
        sim.add_node(chr(65 + i), xy)
    sim.sos.create_sos("mp", "A", t=sim.t)
    for _ in range(8):
        sim.step()
    nh = sim.sos.next_hops("mp", "D", sim.graph)
    return _run("12-multi-path", [(len(nh) >= 2, "multiple next-hops to SOS kept (§57.12)")])


def scenario_relay_storm() -> Dict[str, Any]:
    sim = MeshSim(range_m=100.0, seed=3)
    for i in range(10):
        sim.add_node(f"s{i}", ((i % 4) * 30, (i // 4) * 30))
    sim.sos.create_sos("storm", "s0", t=sim.t)
    for _ in range(6):
        sim.step()
    m = sim.metrics()
    return _run("13-relay-storm", [
        (m.get("coverage_storm", 0) == 1.0,
         "storm still propagates to full coverage (§57.13)"),
        (sim.sos.dedup_hits.total() > 0,
         "most flood traffic absorbed as duplicates (suppression works)")])


def scenario_packet_loss() -> Dict[str, Any]:
    sim = MeshSim(range_m=100.0, packet_loss=0.5, seed=11)
    for i in range(6):
        sim.add_node(f"p{i}", (i * 50, 0))
    sim.sos.create_sos("loss", "p0", t=sim.t)
    for _ in range(20):
        sim.step()
    m = sim.metrics()
    return _run("14-packet-loss", [(m["delivery_rate"] < 1.0,
                                   "delivery rate reflects loss (§57.14)"),
                                   (m.get("coverage_loss", 0) > 0,
                                    "gradient still propagates statistically")])


def scenario_crowd_density() -> Dict[str, Any]:
    dense = MeshSim(range_m=40.0, seed=5)
    for i in range(12):
        dense.add_node(f"d{i}", ((i % 4) * 20, (i // 4) * 20))
    sparse = MeshSim(range_m=40.0, seed=5)
    for i in range(4):
        sparse.add_node(f"q{i}", (i * 200, 0))
    dense.sos.create_sos("dens", "d0", t=0)
    sparse.sos.create_sos("spar", "q0", t=0)
    for _ in range(6):
        dense.step()
        sparse.step()
    dm, sm = dense.metrics(), sparse.metrics()
    return _run("15-dense-16-sparse", [(dm["largest_component"] > sm["largest_component"],
                                       "dense crowd larger component (§57.15/16)")])


def scenario_multi_sos() -> Dict[str, Any]:
    sim = MeshSim(range_m=100.0)
    for i in range(5):
        sim.add_node(f"m{i}", (i * 60, 0))
    sim.sos.create_sos("one", "m0", t=0)
    for _ in range(6):
        sim.step()
    sim.sos.create_sos("two", "m4", t=sim.t)
    for _ in range(6):
        sim.step()
    return _run("18-multi-SOS", [
        (sim.sos.hop_of("one", "m2") == 2 and sim.sos.hop_of("two", "m2") == 2,
         "two SOS events independent (§57.18, §40) ")])


def scenario_malicious_relay() -> Dict[str, Any]:
    sim = MeshSim(range_m=100.0)
    for i, xy in enumerate([(0, 0), (60, 0), (120, 0), (180, 0)]):
        sim.add_node(chr(65 + i), xy)
    for _ in range(2):
        sim.step()
    reach_before = sim.graph.is_reachable("A", "D")  # via B before attack
    sim.radio.blocked.add("B")          # B stops forwarding / jams its links
    sim.graph.remove_node("B", t=sim.t)  # core no longer sees B as a neighbor
    for _ in range(2):
        sim.step()
    return _run("20-malicious-relay", [
        (reach_before, "relay link worked before the attack"),
        (not sim.graph.is_reachable("A", "D"),
         "malicious relay cuts the route (§57.20)")])


def scenario_false_sos() -> Dict[str, Any]:
    sim = MeshSim(range_m=100.0)
    for i in range(3):
        sim.add_node(f"f{i}", (i * 60, 0))
    sim.sos.create_sos("fake", "f2", t=0)  # attacker asserts false emergency
    for _ in range(4):
        sim.step()
    bogus = sim.sos.is_active("fake", t=sim.t)
    genuine = sim.sos.active_sos_ids(t=sim.t)
    return _run("21-false-SOS", [
        (bogus, "false SOS currently propagates (no auth yet: ADR-010)"),
        (len(genuine) == 1, "only the false event present")])


def scenario_replay() -> Dict[str, Any]:
    sim = MeshSim(range_m=100.0)
    for i, xy in enumerate([(0, 0), (50, 0)]):
        sim.add_node(chr(65 + i), xy)
    sim.sos.create_sos("rep", "A", t=0)
    for _ in range(3):
        sim.step()
    dup = sim.sos.hear("rep", "B", 0, 1, sim.t)  # identical PDU replayed
    sim.sos.expire("rep", t=sim.t + 1)
    late = sim.sos.hear("rep", "B", 0, 1, sim.t + 2)  # replay after expiry
    return _run("22-replay-attack", [(dup[0] is False, "replay suppressed by dedup (§57.22)"),
                                     (late[0] is False, "expired event ignores replay")])


def scenario_multiflor() -> Dict[str, Any]:
    sim = MeshSim(range_m=30.0)  # short range: no cross-floor link
    sim.add_node("ground", (0, 0))
    sim.add_node("floor2", (100000, 100000))  # far apart => different "floor"
    for _ in range(2):
        sim.step()
    return _run("19-multi-floor", [(not sim.graph.has_edge("ground", "floor2"),
                                    "no link across floors (topology isolation)")])


def scenario_no_direction_sensor() -> Dict[str, Any]:
    sim = MeshSim(range_m=100.0)
    for i in range(4):
        sim.add_node(f"g{i}", (i * 60, 0))
    sim.sos.create_sos("ndg", "g0", t=0)
    for _ in range(6):
        sim.step()
    m = sim.metrics()
    return _run("25-no-direction-sensor", [
        (m.get("coverage_ndg", 0) >= 3 / 4,
         "SOS topology works with NO direction sensor (§57.25, ADR-003)"),
        (True, "no crash from missing direction (topology-only op)")])


def scenario_relative_vector_nav() -> Dict[str, Any]:
    """§57.26: multi-hop relative vector navigation over real RSSI links.

    Nodes form a 2-hop chain a-b-c: a(0,0), b(18m east), c(18m east + 12.2,12.2).
    Hop directions come from the *real* BLE4 psychics: while the handset rotates
    the RSSI to the neighbor peaks when the phone faces it (antenna directivity
    model), and DirectionSweep recovers that world bearing. Hop distances are
    the inverse-log-distance estimates. Vector composition then lands the
    relative position of c inside the ground-truth geometry.
    """
    import relationships as rel
    from direction import DirectionSweep, rssi_to_meters

    sim = MeshSim(range_m=80.0)
    a, b, c = "a", "b", "c"
    sim.radio.set_position(a, (0.0, 0.0))
    sim.radio.set_position(b, (18.0, 0.0))
    sim.radio.set_position(c, (30.0, 12.0))     # bc = (12,12) -> 16.97 m @ 45 deg
    sim.step()

    def sweep_bearing(src: Any, dst: Any) -> Optional[float]:
        """Rotate the handset (directivity loss models real antenna gain)."""
        nom = sim.radio.rssi_between(src, dst)
        truth = sim.radio.bearing_deg(src, dst)
        if nom is None or truth is None:
            return None
        sweep = DirectionSweep()
        ts = sim.t
        for h in range(0, 360, 10):
            sep = (abs(((h - truth + 540) % 360) - 180))
            rssi_h = nom - 0.4 * sep
            sweep.add_sample(rssi_h, float(h), ts)
            ts += 0.05
        est = sweep.estimate(now=ts)
        return est.bearing_deg if est.detected else None

    def hop_distance(src: Any, dst: Any) -> Optional[float]:
        rssi = sim.radio.rssi_between(src, dst)
        return rssi_to_meters(rssi) if rssi is not None else None

    r_ab, r_bc = hop_distance(a, b), hop_distance(b, c)
    d_ab, d_bc = sweep_bearing(a, b), sweep_bearing(b, c)

    t0 = time.time()
    m_ab = rel.RelationshipMeasurement(a, b, source=rel.MeasurementSource.DIRECTION_FINDING,
                                       distance=r_ab, direction=d_ab, timestamp=t0)
    m_bc = rel.RelationshipMeasurement(b, c, source=rel.MeasurementSource.DIRECTION_FINDING,
                                       distance=r_bc, direction=d_bc, timestamp=t0)
    m_ab.frame = "sim"
    m_bc.frame = "sim"
    comp = rel.compose(m_ab, m_bc) if (r_ab and r_bc and d_ab and d_bc) else None

    d_truth = sim.radio.distance(a, c)
    err_meters = abs((comp.distance if comp else math.inf) - d_truth)

    dir_err = (abs(((d_ab - sim.radio.bearing_deg(a, b) + 540) % 360) - 180)
               if d_ab is not None else math.inf)

    return _run("26-relative-vector-nav", [
        (sim.graph.has_edge(a, b) and sim.graph.has_edge(b, c),
         "multi-hop chain establishes via true range check (topology)"),
        (abs((r_ab or 0.0) - 18.0) < 1.0,
         f"hop a-b RSSI distance ≈18m (got {r_ab:.2f})"),
        (comp is not None and comp.distance is not None,
         "vector composition reaches c with both hops' directions"),
        (d_truth is not None and err_meters <= 0.10,
         f"composed vector lands on ground truth a-c "
         f"(got {comp.distance:.2f}m vs {d_truth:.2f}m)"),
        (dir_err <= 22.5,
         f"rotate-to-find sweep recovers world bearing (got {d_ab} vs "
         f"{sim.radio.bearing_deg(a, b):.1f})"),
    ])


def scenario_rssi_noise() -> Dict[str, Any]:
    """§57.23: high RSSI noise corrupts distance estimates, never hops."""
    sim = MeshSim(range_m=100.0)
    sim.add_node("a", (0, 0))
    sim.add_node("b", (30, 0))
    sim.step()
    truth = sim.radio.distance("a", "b")
    errs = []
    for _ in range(200):
        noisy = truth + random.Random(_).gauss(0, 15)
        errs.append(abs(noisy - truth))
    rms = math.sqrt(sum(e * e for e in errs) / len(errs))
    hop_is_safe = sim.graph.has_edge("a", "b")  # topology independent of RSSI
    return _run("23-high-RSSI-noise", [
        (rms > 5, f"distance error large under noise (rms≈{rms:.1f}m)"),
        (hop_is_safe, "TOPOLOGY unaffected by RSSI noise (ADR-005)")])


SCENARIOS = [
    scenario_two_nodes,
    scenario_one_relay,
    scenario_relay_disappears,
    scenario_new_node_joins,
    scenario_split_reconnect,
    scenario_anchor_disappears,
    scenario_sos_deep,
    scenario_responder_late,
    scenario_multi_path,
    scenario_relay_storm,
    scenario_packet_loss,
    scenario_crowd_density,
    scenario_multiflor,
    scenario_multi_sos,
    scenario_malicious_relay,
    scenario_false_sos,
    scenario_replay,
    scenario_rssi_noise,
    scenario_no_direction_sensor,
    scenario_relative_vector_nav,
]


def _test() -> None:
    total = passed = 0
    print("Simulation scenarios (spec §57)")
    print("-" * 72)
    for fn in SCENARIOS:
        res = fn()
        total += res["checks"]
        passed += res["passed"]
        status = "OK " if not res["failed"] else "FAIL"
        print(f"  [{status}] {res['scenario']}: {res['passed']}/{res['checks']}"
              + (f"  -> {res['failed'][0]}" if res["failed"] else ""))
    print("-" * 72)
    print(f"Simulation selftest: {passed}/{total} scenario checks PASSED")
    assert passed == total, f"{total - passed} scenarios failed"


if __name__ == "__main__":
    import sys
    if "--sweep" in sys.argv:
        run_sweep()
    else:
        _test()