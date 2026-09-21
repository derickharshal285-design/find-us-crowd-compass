"""Block 4 — SOS engine (spec §63 Block 4, §22, §40–41, §14 responder-late).

Gradient logic over the dynamic graph:
  1. origin creates SOS_ID, hop = 0 (spec §22.1–2)
  2. neighbor learns hop = h+1 from an advertiser at hop = h (§22.3)
  3. only strictly-lower hop values update a node's route (§22.4)
  4. version + dedup stop old/repeated updates overwriting or flooding (§22.7)
  5. TTL (hop cap) bounds propagation (§22.6)
  6. expiry removes stale events (§41); multiple SOS stay independent (§40)
  7. a late responder learns the current gradient from the network (§22.8)
"""
from __future__ import annotations

import collections
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from domain import SOS, SosStatus, SOSUpdate, NodeId, SosId, now


@dataclass
class GradEvent:
    kind: str
    sos_id: SosId
    node: Optional[NodeId] = None
    hop: Optional[int] = None
    version: int = 0
    detail: str = ""

    def __str__(self) -> str:  # Block 9 diagnostics
        return (f"{self.kind} sos={self.sos_id} node={self.node} "
                f"hop={self.hop} v{self.version} {self.detail}".strip())


@dataclass
class HopState:
    hop: int
    version: int
    updated_at: float


class SosEngine:
    def __init__(self, default_ttl_hops: int = 8,
                 default_lifespan: Optional[float] = 900.0,
                 dedup_window: int = 20000) -> None:
        self.default_ttl_hops = default_ttl_hops
        self.default_lifespan = default_lifespan
        self.events: Dict[SosId, SOS] = {}
        self.gradient: Dict[SosId, Dict[NodeId, HopState]] = {}
        self.log: List[GradEvent] = []
        self.dedup_hits = collections.Counter()
        self.max_dedup = dedup_window
        self._seen: Set[Tuple[str, int, str, int]] = set()

    # ---- lifecycle --------------------------------------------------------

    def create_sos(self, sos_id: Any, origin: Any,
                   t: Optional[float] = None, ttl_hops: Optional[int] = None,
                   lifespan: Optional[float] = None) -> SOS:
        sid = SosId(str(sos_id))
        o = NodeId(str(origin))
        t = t if t is not None else now()
        ttl = ttl_hops if ttl_hops is not None else self.default_ttl_hops
        life = lifespan if lifespan is not None else self.default_lifespan
        sos = SOS(sid, o, created_at=t, version=1, ttl_hops=ttl,
                  lifespan_seconds=life,
                  expires_at=(t + life) if life is not None else None)
        self.events[sid] = sos
        self.gradient[sid] = {o: HopState(hop=0, version=1, updated_at=t)}
        self.log.append(GradEvent("SOSCreated", sid, o, 0, 1,
                                  detail="origin hop 0"))
        return sos

    def is_active(self, sos_id: Any, t: Optional[float] = None) -> bool:
        sid = SosId(str(sos_id))
        sos = self.events.get(sid)
        if sos is None or sos.status != SosStatus.ACTIVE:
            return False
        t = t if t is not None else now()
        return not (sos.expires_at is not None and t > sos.expires_at)

    def active_sos_ids(self, t: Optional[float] = None) -> List[SosId]:
        t = t if t is not None else now()
        return [sid for sid in self.events if self.is_active(sid, t)]

    def expire(self, sos_id: Any, t: Optional[float] = None) -> bool:
        sid = SosId(str(sos_id))
        sos = self.events.get(sid)
        if sos is None:
            return False
        if sos.status != SosStatus.EXPIRED:
            sos.status = SosStatus.EXPIRED
            self.log.append(GradEvent("SOSExpired", sid, None, None,
                                      sos.version, detail="lifetime ended"))
        self.gradient.pop(sid, None)
        return True

    def expire_stale(self, t: Optional[float] = None) -> List[SosId]:
        t = t if t is not None else now()
        expired = [sid for sid, sos in self.events.items()
                   if sos.status == SosStatus.ACTIVE and
                   (sos.expires_at is not None and t > sos.expires_at)]
        for sid in expired:
            self.events[sid].status = SosStatus.EXPIRED
            self.log.append(GradEvent("SOSExpired", sid, None, None,
                                      self.events[sid].version))
            self.gradient.pop(sid, None)
        return expired

    def renew(self, sos_id: Any, t: Optional[float] = None) -> Optional[SOS]:
        """Origin refresh: bump version so newer echoes supersede old ones."""
        sid = SosId(str(sos_id))
        sos = self.events.get(sid)
        if sos is None or sos.status != SosStatus.ACTIVE:
            return None
        t = t if t is not None else now()
        sos.version += 1
        if sos.expires_at and sos.lifespan_seconds:
            sos.expires_at = t + sos.lifespan_seconds
        self.log.append(GradEvent("SOSUpdated", sid, sos.origin, 0,
                                  sos.version, detail="origin renew"))
        return sos

    # ---- gradient diffusion (spec §22.3–5) ---------------------------------

    def hear(self, sos_id: Any, from_node: Any, advertiser_hop: int,
             version: int = 1, t: Optional[float] = None,
             check_duplicate: bool = True) -> Tuple[bool, Optional[int]]:
        """A node receives 'X is at hop `advertiser_hop` (version v)'. Returns
        (accepted, new_hop). Accepts when strictly better:
        (a) event active; (b) version not older than node's learned version;
        (c) candidate = advertiser_hop+1 < current hop; (d) within TTL cap.
        """
        sid = SosId(str(sos_id))
        node = NodeId(str(from_node))
        t = t if t is not None else now()
        if not self.is_active(sid, t):
            self.log.append(GradEvent("rejected-not-better", sid, node,
                                      advertiser_hop, version,
                                      detail="sos inactive"))
            return False, None
        sos = self.events[sid]
        if check_duplicate and self._mark_seen(sid, version, from_node,
                                               advertiser_hop):
            self.dedup_hits[(str(sid), version)] += 1
            self.log.append(GradEvent("duplicate-suppressed", sid, node,
                                      advertiser_hop, version))
            return False, None
        candidate = advertiser_hop + 1
        if candidate > sos.ttl_hops:
            self.log.append(GradEvent("rejected-not-better", sid, node,
                                      advertiser_hop, version,
                                      detail=f"ttl cap {sos.ttl_hops}"))
            return False, None
        cur = self.gradient[sid].get(node)
        if cur is not None and version < cur.version:
            self.log.append(GradEvent("rejected-not-better", sid, node,
                                      advertiser_hop, version,
                                      detail="older version"))
            return False, None
        if cur is not None and candidate >= cur.hop:
            self.log.append(GradEvent("rejected-not-better", sid, node,
                                      advertiser_hop, version,
                                      detail=f"current hop {cur.hop}"))
            return False, None
        self.gradient[sid][node] = HopState(hop=candidate, version=version,
                                            updated_at=t)
        self.log.append(GradEvent("adopted", sid, node, candidate, version,
                                  detail=f"<== {from_node}@{advertiser_hop}"))
        return True, candidate

    def _mark_seen(self, sid: SosId, version: int, sender: Any, hop: int) -> bool:
        key = (str(sid), int(version), str(sender), int(hop))
        if key in self._seen:
            return True
        if len(self._seen) >= self.max_dedup:
            self._seen = set()  # bounded memory, test-only scenarios
        self._seen.add(key)
        return False

    def receive_update(self, update: SOSUpdate,
                       t: Optional[float] = None) -> Tuple[bool, Optional[int]]:
        return self.hear(update.sos_id, update.sender, update.hop,
                         update.version, t)

    def hop_of(self, sos_id: Any, node: Any) -> Optional[int]:
        st = self.gradient.get(SosId(str(sos_id)), {}).get(NodeId(str(node)))
        return st.hop if st else None

    def next_hops(self, sos_id: Any, node: Any, graph: Any) -> Set[NodeId]:
        """Block 5 gradient/routing: neighbors of `node` with hop exactly
        hop(node)-1 (spec §85)."""
        sid = SosId(str(sos_id))
        node = NodeId(str(node))
        cur = self.gradient.get(sid, {}).get(node)
        if cur is None or cur.hop <= 0:
            return set()
        want = cur.hop - 1
        return {nb for nb in graph.neighbors(node)
                if (st := self.gradient.get(sid, {}).get(nb)) is not None
                and st.hop == want}

    # ---- simulation helpers -----------------------------------------------

    def flood_once(self, sos_id: Any, graph: Any,
                   t: Optional[float] = None) -> Tuple[int, int]:
        """One diffusion round: every node advertises its current hop to its
        neighbors. Returns (adopted_count, duplicate_count)."""
        sid = SosId(str(sos_id))
        t = t if t is not None else now()
        if not self.is_active(sid, t):
            return 0, 0
        adopted = 0
        dups = 0
        snapshot = list(self.gradient.get(sid, {}).items())
        for src, st in snapshot:
            for nb in graph.neighbors(src):
                accepted, _ = self.hear(sid, nb, st.hop, st.version, t)
                if accepted:
                    adopted += 1
                else:
                    dups += 1
        return adopted, dups

    def gradient_bfs(self, sos_id: Any, graph: Any,
                     t: Optional[float] = None) -> Dict[NodeId, int]:
        """Theoretical optimum hop field via BFS (convergence metric)."""
        sid = SosId(str(sos_id))
        if not self.is_active(sid, t):
            return {}
        return graph.hop_distance(self.events[sid].origin)

    def coverage(self, sos_id: Any, graph: Any) -> float:
        """% of live nodes holding a gradient value (spec §59 Emergency)."""
        sid = SosId(str(sos_id))
        live = [n for n in graph.node_ids()
                if (g := graph.get_node(n)) is not None
                and g.lifecycle.value != "EXPIRED"]
        if not live:
            return 0.0
        got = sum(1 for n in live if n in self.gradient.get(sid, {}))
        return got / len(live)

    def flood_to_convergence(self, sos_id: Any, graph: Any,
                             t: Optional[float] = None,
                             max_rounds: int = 64) -> Tuple[int, int, int]:
        """Repeat flood rounds until no node adopts a new hop.
        Returns (total_adopted, total_duplicates, rounds)."""
        total_a = total_d = 0
        for r in range(1, max_rounds + 1):
            a, d = self.flood_once(sos_id, graph, t)
            total_a += a
            total_d += d
            if a == 0:
                return total_a, total_d, r
        return total_a, total_d, max_rounds


def _test() -> None:
    from graph import DynamicGraph
    checks = 0

    def ok(cond: bool, name: str) -> None:
        nonlocal checks
        checks += 1
        assert cond, name
        print(f"  PASS {name}")

    t = 2000.0
    g = DynamicGraph()
    for n in "ABCDEF":
        g.add_node(n, t=t)
    g.add_edge("A", "B", t=t)
    g.add_edge("B", "C", t=t)
    g.add_edge("C", "D", t=t)
    g.add_edge("D", "E", t=t)
    g.add_edge("E", "F", t=t)

    eng = SosEngine()
    sos = eng.create_sos("sos-1", "A", t=t)
    ok(str(sos.origin) == "A", "Test E: SOS created at A")
    ok(eng.hop_of("sos-1", "A") == 0, "Test F: origin hop 0")

    tot_a, tot_d, rounds = eng.flood_to_convergence("sos-1", g, t=t)
    ok(tot_a == 5, f"Test F: chain converges with 5 adoptions (got {tot_a})")
    ok(rounds == 6, f"Test F: 5 adopting rounds + 1 empty round (got {rounds})")
    for n, expect in [("B", 1), ("C", 2), ("D", 3), ("E", 4), ("F", 5)]:
        ok(eng.hop_of("sos-1", n) == expect, f"Test F: hop({n})={expect}")
    ok(eng.next_hops("sos-1", "C", g) == {"B"},
       "Test F: nextHops(C) = {B} toward SOS")

    # Test H: node joining after SOS exists learns current gradient
    g.add_node("G", t=t)
    g.add_edge("F", "G", t=t)
    ok(eng.hop_of("sos-1", "G") is None, "Test H: late node has no gradient yet")
    a2, tot_d2, _ = eng.flood_to_convergence("sos-1", g, t=t)
    ok(a2 == 1, f"Test H: only G adopts ({a2}) for the joiner")
    ok(tot_d2 >= 1, f"Test H: existing gradient flooded dups ({tot_d2})")
    ok(eng.hop_of("sos-1", "G") == 6, "Test H: late node learns hop 6")

    # Test G via graph: removing shortest-path relay breaks/moves the route
    eng2 = SosEngine()
    g2 = DynamicGraph()
    for n in "ABCDE":
        g2.add_node(n, t=t)
    g2.add_edge("A", "B", t=t)
    g2.add_edge("B", "C", t=t)
    g2.add_edge("C", "D", t=t)
    g2.add_edge("D", "E", t=t)
    eng2.create_sos("s2", "A", t=t)
    eng2.flood_to_convergence("s2", g2, t=t)
    ok(eng2.hop_of("s2", "D") == 3, "Test G: D hop=3 before (A-B-C-D)")
    ok(eng2.next_hops("s2", "C", g2) == {"B"}, "Test G: C routes via B")
    g2.expire_edge("B", "C", t=t)
    for dead in "CDE":
        eng2.gradient["s2"].pop(dead, None)
    eng2.flood_to_convergence("s2", g2, t=t)
    ok(eng2.hop_of("s2", "D") is None, "Test G: route to D lost with relay C")
    ok(len(eng2.next_hops("s2", "D", g2)) == 0, "Test G: no next hops after loss")

    # Test I: two SOS events simultaneously, independent gradients
    g3 = DynamicGraph()
    for n in "ABCD":
        g3.add_node(n, t=t)
    g3.add_edge("A", "B", t=t)
    g3.add_edge("B", "C", t=t)
    g3.add_edge("C", "D", t=t)
    eng3 = SosEngine()
    eng3.create_sos("sos-A", "A", t=t)
    eng3.create_sos("sos-D", "D", t=t)
    eng3.flood_to_convergence("sos-A", g3, t=t)
    eng3.flood_to_convergence("sos-D", g3, t=t)
    ok(eng3.hop_of("sos-A", "C") == 2 and eng3.hop_of("sos-D", "C") == 1,
       "Test I: two SOS events independent gradients")

    # Test J: expire an old SOS
    ok(eng3.is_active("sos-A", t=t), "Test J: SOS active before expiry")
    eng3.expire("sos-A", t=t)
    ok(not eng3.is_active("sos-A", t=t), "Test J: SOS expired")
    ok(eng3.hop_of("sos-A", "B") is None, "Test J: gradient removed after expiry")
    ok(eng3.is_active("sos-D", t=t), "Test J: other SOS unaffected")

    # Test K1: dense clique flood -> duplicate suppression absorbs the storm
    eng4 = SosEngine()
    g4 = DynamicGraph()
    nodes = [f"n{i}" for i in range(12)]
    for n_ in nodes:
        g4.add_node(n_, t=t)
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            g4.add_edge(nodes[i], nodes[j], t=t)
    eng4.create_sos("clique", "n0", t=t)
    tot_dup = 0
    for _ in range(3):
        _, d = eng4.flood_once("clique", g4, t=t)
        tot_dup += d
    ok(tot_dup > 0, "Test K1: duplicate suppression absorbed flood traffic")
    ok(sum(eng4.dedup_hits.values()) > 0, "Test K1: dedup counter recorded")

    # Test K2: TTL (hop cap) bounds propagation on a long chain
    eng4b = SosEngine(default_ttl_hops=3)
    g4b = DynamicGraph()
    chain = [f"c{i}" for i in range(10)]
    for n_ in chain:
        g4b.add_node(n_, t=t)
    for i in range(9):
        g4b.add_edge(chain[i], chain[i + 1], t=t)
    eng4b.create_sos("bounded", "c0", t=t)
    eng4b.flood_to_convergence("bounded", g4b, t=t)
    ok(eng4b.hop_of("bounded", "c3") == 3, "Test K2: node at TTL cap reachable")
    ok(eng4b.hop_of("bounded", "c4") is None, "Test K2: beyond TTL cap unreachable")
    ok(eng4b.coverage("bounded", g4b) == 4 / 10,
       "Test K2: coverage limited by TTL (4/10)")

    # Test L: lost advertisement leaves a gap; later retransmit fills it
    eng5 = SosEngine()
    g5 = DynamicGraph()
    for n_ in "ABC":
        g5.add_node(n_, t=t)
    g5.add_edge("A", "B", t=t)
    g5.add_edge("B", "C", t=t)
    eng5.create_sos("loss", "A", t=t)
    ok(eng5.hear("loss", "B", 0, 1, t)[0] is True, "Test L: A->B delivered")
    ok(eng5.coverage("loss", g5) == 2 / 3, "Test L: C missing -> 2/3 coverage")
    ok(eng5.hear("loss", "C", 1, 1, t)[0] is True, "Test L: B->C retransmit adopts")
    ok(eng5.coverage("loss", g5) == 1.0, "Test L: gap recovered after retransmit")

    # expiry via time (lifespan), spec §41
    eng6 = SosEngine(default_lifespan=50.0)
    g6 = DynamicGraph()
    g6.add_node("A", t=t)
    eng6.create_sos("short", "A", t=t, lifespan=50.0)
    ok(eng6.is_active("short", t=t + 49), "lifespan: active at 49s")
    ok(not eng6.is_active("short", t=t + 51), "lifespan: expired past 50s")

    print(f"\nSosEngine selftest: {checks} checks PASSED")


if __name__ == "__main__":
    _test()