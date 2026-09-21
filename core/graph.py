"""Block 2/5 — Dynamic graph engine (spec §63 Blocks 2 & 5, §18–21, §85).

Pure topology: nodes, edges, lifecycles, connected components, BFS hop
distance, next-hop sets, snapshots and graph update events (spec §66).
No Bluetooth, no geometry (ADR-003). Geometry lives in relationships.py.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Set, Tuple

from domain import (
    CapabilityProfile, EdgeId, EdgeLifecycle, EdgeState, GraphSnapshot,
    NodeId, NodeLifecycle, PeerState, edge_id, now,
)


class GraphEventKind(enum.Enum):
    NODE_DISCOVERED = "NodeDiscovered"
    NODE_UPDATED = "NodeUpdated"
    NODE_STALE = "NodeStale"
    NODE_EXPIRED = "NodeExpired"
    EDGE_CREATED = "EdgeCreated"
    EDGE_UPDATED = "EdgeUpdated"
    EDGE_STALE = "EdgeStale"
    EDGE_EXPIRED = "EdgeExpired"
    COMPONENT_SPLIT = "ComponentSplit"
    COMPONENT_MERGED = "ComponentMerged"
    ROUTE_CHANGED = "RouteChanged"


@dataclass
class GraphEvent:
    kind: GraphEventKind
    timestamp: float
    node: Optional[NodeId] = None
    edge: Optional[EdgeId] = None
    component: Optional[frozenset] = None
    detail: str = ""

    def __str__(self) -> str:  # for diagnostics (Block 9)
        name = self.kind.value
        target = self.edge or self.node or ""
        return f"[{self.timestamp:.1f}] {name} {target} {self.detail}".strip()


class DynamicGraph:
    """Dynamic communication graph G = (V, E) (spec §18)."""

    def __init__(
        self,
        node_stale_after: float = 30.0,
        node_expire_after: float = 120.0,
        edge_stale_after: float = 30.0,
        edge_expire_after: float = 120.0,
    ) -> None:
        self.node_stale_after = node_stale_after
        self.node_expire_after = node_expire_after
        self.edge_stale_after = edge_stale_after
        self.edge_expire_after = edge_expire_after
        self._nodes: Dict[NodeId, PeerState] = {}
        self._edges: Dict[EdgeId, EdgeState] = {}
        self.events: List[GraphEvent] = []
        self._last_components: List[frozenset] = []
        self._track_sources: Set[NodeId] = set()  # SOS origins to route-watch
        self._last_hop: Dict[NodeId, Dict[NodeId, int]] = {}

    # ---- events ----------------------------------------------------------

    def _emit(
        self, kind: GraphEventKind, t: float, node: Optional[NodeId] = None,
        edge: Optional[EdgeId] = None, component: Optional[frozenset] = None,
        detail: str = "",
    ) -> None:
        self.events.append(GraphEvent(kind, t, node, edge, component, detail))

    def clear_events(self) -> None:
        self.events.clear()

    # ---- nodes -----------------------------------------------------------

    def add_node(self, node_id: Any, t: Optional[float] = None,
                 capabilities: Optional[CapabilityProfile] = None) -> NodeId:
        nid = NodeId(str(node_id))
        t = t if t is not None else now()
        if nid not in self._nodes:
            self._nodes[nid] = PeerState(nid, NodeLifecycle.DISCOVERED,
                                         first_seen=t, last_seen=t,
                                         capabilities=capabilities)
            self._emit(GraphEventKind.NODE_DISCOVERED, t, node=nid)
        else:
            st = self._nodes[nid]
            old = st.lifecycle
            st.last_seen = t
            st.capabilities = capabilities or st.capabilities
            self._emit(GraphEventKind.NODE_UPDATED, t, node=nid,
                       detail=f"{old.value}->{st.lifecycle.value}")
        self._recompute_components(t)
        return nid

    def touch_node(self, node_id: Any, t: Optional[float] = None) -> None:
        nid = NodeId(str(node_id))
        if nid not in self._nodes:
            return
        t = t if t is not None else now()
        self._nodes[nid].last_seen = t
        self._refresh_lifecycles(t)

    def remove_node(self, node_id: Any, t: Optional[float] = None) -> bool:
        nid = NodeId(str(node_id))
        t = t if t is not None else now()
        if nid not in self._nodes:
            return False
        for eid in list(self._edges):
            if nid in self._edges[eid].endpoints:
                del self._edges[eid]
                self._emit(GraphEventKind.EDGE_EXPIRED, t, edge=eid,
                           detail="incident to removed node")
        del self._nodes[nid]
        self._emit(GraphEventKind.NODE_EXPIRED, t, node=nid,
                   detail="removed")
        self._recompute_components(t)
        self._check_routes(t)
        return True

    def expire_node(self, node_id: Any, t: Optional[float] = None) -> bool:
        nid = NodeId(str(node_id))
        t = t if t is not None else now()
        if nid not in self._nodes:
            return False
        if self._nodes[nid].lifecycle != NodeLifecycle.EXPIRED:
            self._nodes[nid].lifecycle = NodeLifecycle.EXPIRED
            self._emit(GraphEventKind.NODE_EXPIRED, t, node=nid)
        return True

    def has_node(self, node_id: Any) -> bool:
        return NodeId(str(node_id)) in self._nodes

    def get_node(self, node_id: Any) -> Optional[PeerState]:
        return self._nodes.get(NodeId(str(node_id)))

    def node_ids(self) -> List[NodeId]:
        return sorted(self._nodes)

    # ---- edges -----------------------------------------------------------

    def _edge_key(self, u: Any, v: Any) -> EdgeId:
        return edge_id(u, v)

    def add_edge(self, u: Any, v: Any, t: Optional[float] = None,
                 source: str = "transport") -> Optional[EdgeId]:
        u, v = NodeId(str(u)), NodeId(str(v))
        t = t if t is not None else now()
        for nid in (u, v):
            if nid not in self._nodes:
                self.add_node(nid, t=t)  # join-on-first-relationship (CP5)
        eid = self._edge_key(u, v)
        if eid in self._edges:
            st = self._edges[eid]
            resurrected = st.lifecycle == EdgeLifecycle.EXPIRED
            if resurrected:
                st.lifecycle = EdgeLifecycle.SEEN
            st.last_seen = t
            self._emit(GraphEventKind.EDGE_UPDATED, t, edge=eid,
                       detail=f"{st.lifecycle.value}->{st.lifecycle.value}")
            if resurrected:
                self._recompute_components(t)
                self._check_routes(t)
            return eid
        self._edges[eid] = EdgeState(eid, (u, v), EdgeLifecycle.SEEN,
                                     first_seen=t, last_seen=t, source=source)
        self._emit(GraphEventKind.EDGE_CREATED, t, edge=eid)
        self._recompute_components(t)
        self._check_routes(t)
        return eid

    def touch_edge(self, u: Any, v: Any, t: Optional[float] = None,
                   bidirectional: bool = False) -> bool:
        eid = self._edge_key(u, v)
        t = t if t is not None else now()
        st = self._edges.get(eid)
        if st is None:
            return False
        st.last_seen = t
        if bidirectional:
            st.last_bidirectional_exchange = t
        self._refresh_lifecycles(t)
        return True

    def expire_edge(self, u: Any, v: Any, t: Optional[float] = None) -> bool:
        eid = self._edge_key(u, v)
        t = t if t is not None else now()
        st = self._edges.get(eid)
        if st is None:
            return False
        if st.lifecycle != EdgeLifecycle.EXPIRED:
            st.lifecycle = EdgeLifecycle.EXPIRED
            st.last_seen = t
            self._emit(GraphEventKind.EDGE_EXPIRED, t, edge=eid)
        self._recompute_components(t)
        self._check_routes(t)
        return True

    def has_edge(self, u: Any, v: Any) -> bool:
        return self._edge_key(u, v) in self._edges

    def is_edge_live(self, u: Any, v: Any) -> bool:
        st = self._edges.get(self._edge_key(u, v))
        return st is not None and st.lifecycle != EdgeLifecycle.EXPIRED

    def get_edge(self, u: Any, v: Any) -> Optional[EdgeState]:
        return self._edges.get(self._edge_key(u, v))

    def edge_ids(self) -> List[EdgeId]:
        return sorted(self._edges)

    # ---- lifecycles (spec §19, §20: aging, soft/hard expiry) -------------

    def _refresh_lifecycles(self, t: float) -> None:
        for nid, st in self._nodes.items():
            # An EXPIRED node is NOT skipped: if it has since been freshly
            # touched (authenticated radio contact resumed), its age drops and
            # it is re-admitted (relationship memory, §23). A node that was
            # NOT re-touched stays EXPIRED because its age is still past the
            # hard threshold. Same rule for edges below.
            age = st.age(t)
            if age is None:
                continue
            new = NodeLifecycle.ACTIVE
            if age > self.node_expire_after:
                new = NodeLifecycle.EXPIRED
            elif age > self.node_stale_after:
                new = NodeLifecycle.STALE
            if new != st.lifecycle:
                old = st.lifecycle
                st.lifecycle = new
                kind = {NodeLifecycle.STALE: GraphEventKind.NODE_STALE,
                        NodeLifecycle.EXPIRED: GraphEventKind.NODE_EXPIRED,
                        NodeLifecycle.ACTIVE: GraphEventKind.NODE_UPDATED}[new]
                self._emit(kind, t, node=nid, detail=f"{old.value}->{new.value}")
                if new == NodeLifecycle.EXPIRED:
                    for eid in list(self._edges):
                        if nid in self._edges[eid].endpoints:
                            self._edges[eid].lifecycle = EdgeLifecycle.EXPIRED
                            self._emit(GraphEventKind.EDGE_EXPIRED, t,
                                       edge=eid, detail="incident node expired")
        for eid, st in self._edges.items():
            # EXPIRED edges are NOT revived here: explicit expiry (expire_edge,
            # or an endpoint node expiring) must stick until add_edge explicitly
            # re-arms the edge (SEEN) on a fresh received signal.
            if st.lifecycle == EdgeLifecycle.EXPIRED:
                continue
            age = st.age(t)
            if age is None:
                continue
            new = EdgeLifecycle.ACTIVE
            if age > self.edge_expire_after:
                new = EdgeLifecycle.EXPIRED
            elif age > self.edge_stale_after:
                new = EdgeLifecycle.AGING
            if new != st.lifecycle:
                old = st.lifecycle
                st.lifecycle = new
                kind = {EdgeLifecycle.AGING: GraphEventKind.EDGE_STALE,
                        EdgeLifecycle.EXPIRED: GraphEventKind.EDGE_EXPIRED,
                        EdgeLifecycle.ACTIVE: GraphEventKind.EDGE_UPDATED}[new]
                self._emit(kind, t, edge=eid, detail=f"{old.value}->{new.value}")
        self._recompute_components(t)
        self._check_routes(t)

    def refresh(self, t: Optional[float] = None) -> None:
        self._refresh_lifecycles(t if t is not None else now())

    # ---- connectivity (spec §85) ----------------------------------------

    def _live(self, nid: NodeId) -> bool:
        st = self._nodes.get(nid)
        return st is not None and st.lifecycle != NodeLifecycle.EXPIRED

    def _live_edges(self) -> Iterable[Tuple[EdgeId, EdgeState]]:
        for eid, st in self._edges.items():
            if st.lifecycle == EdgeLifecycle.EXPIRED:
                continue
            if not (self._live(st.endpoints[0]) and self._live(st.endpoints[1])):
                continue
            yield eid, st

    def neighbors(self, v: Any) -> Set[NodeId]:
        v = NodeId(str(v))
        out: Set[NodeId] = set()
        for _eid, st in self._live_edges():
            if st.endpoints[0] == v:
                out.add(st.endpoints[1])
            elif st.endpoints[1] == v:
                out.add(st.endpoints[0])
        return out

    def connected_components(self) -> List[Set[NodeId]]:
        seen: Set[NodeId] = set()
        comps: List[Set[NodeId]] = []
        for nid in self._nodes:
            if not self._live(nid) or nid in seen:
                continue
            stack = [nid]
            seen.add(nid)
            comp: Set[NodeId] = set()
            while stack:
                cur = stack.pop()
                comp.add(cur)
                for nb in self.neighbors(cur):
                    if nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
            comps.append(comp)
        return comps

    def is_reachable(self, a: Any, b: Any) -> bool:
        a, b = NodeId(str(a)), NodeId(str(b))
        if a == b:
            return self._live(a)
        seen = {a}
        stack = [a]
        while stack:
            cur = stack.pop()
            for nb in self.neighbors(cur):
                if nb == b:
                    return True
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        return False

    def hop_distance(self, source: Any) -> Dict[NodeId, int]:
        """hop(s, v) via BFS on the unweighted live graph (spec §85, §63 Block 5)."""
        source = NodeId(str(source))
        hops: Dict[NodeId, int] = {}
        if not self._live(source):
            return hops
        hops[source] = 0
        frontier = [source]
        while frontier:
            nxt: List[NodeId] = []
            for cur in frontier:
                h = hops[cur]
                for nb in self.neighbors(cur):
                    if nb not in hops:
                        hops[nb] = h + 1
                        nxt.append(nb)
            frontier = nxt
        return hops

    def next_hops(self, v: Any, source: Any) -> Set[NodeId]:
        """nextHops(v, s) = neighbors(v) with hop == hop(v)-1 (spec §85)."""
        v = NodeId(str(v))
        hops = self.hop_distance(source)
        if v not in hops:
            return set()
        h = hops[v]
        if h <= 0:
            return set()
        return {nb for nb in self.neighbors(v) if hops.get(nb) == h - 1}

    # ---- components / route change events (spec §66) ----------------------

    def _recompute_components(self, t: float) -> None:
        new = [frozenset(c) for c in self.connected_components()]
        prev = self._last_components or []
        self._last_components = new
        if not prev:
            return
        # split: a previous component's nodes now live in >=2 new components
        prev_to_new: Dict[FrozenSet, Set[FrozenSet]] = {}
        for pc in prev:
            hits = set()
            for nc in new:
                if pc & nc:
                    hits.add(nc)
            if len(hits) >= 2:
                prev_to_new[pc] = hits
        for pc, hits in prev_to_new.items():
            self._emit(GraphEventKind.COMPONENT_SPLIT, t, component=pc,
                       detail=f"into {len(hits)} components")
        # merge: a new component contains nodes from >=2 previous components
        for nc in new:
            olds = {pc for pc in prev if pc & nc}
            if len(olds) >= 2:
                self._emit(GraphEventKind.COMPONENT_MERGED, t, component=nc,
                           detail=f"from {len(olds)} components")

    def _check_routes(self, t: float) -> None:
        for src in self._track_sources:
            new_hop = self.hop_distance(src)
            old_hop = self._last_hop.get(src)
            self._last_hop[src] = new_hop
            if old_hop is None:
                continue
            all_nodes = set(new_hop) | set(old_hop)
            for nid in all_nodes:
                if new_hop.get(nid) != old_hop.get(nid):
                    self._emit(GraphEventKind.ROUTE_CHANGED, t, node=src,
                               detail=f"node {nid}: {old_hop.get(nid)}->{new_hop.get(nid)}")
                    break

    def track_routes_to(self, source: Any) -> None:
        """Register an SOS origin so route changes emit ROUTE_CHANGED events."""
        self._track_sources.add(NodeId(str(source)))
        self._last_hop[NodeId(str(source))] = self.hop_distance(source)

    # ---- snapshot (spec §63 Block 2) --------------------------------------

    def to_snapshot(self, t: Optional[float] = None) -> GraphSnapshot:
        t = t if t is not None else now()
        comps = [sorted(c, key=str) for c in self.connected_components()]
        snap = GraphSnapshot(
            generated_at=t,
            nodes={k: (v, v.capabilities.name if v.capabilities else None)
                   for k, v in self._nodes.items()},
            edges={k: st.lifecycle.value for k, st in self._edges.items()},
            components=comps,
        )
        return snap


# ---- selftest: spec §84 Tests A–D (+ G, H hop/route primitives) -----------

def _test() -> None:
    checks = 0

    def ok(cond: bool, name: str) -> None:
        nonlocal checks
        checks += 1
        assert cond, name
        print(f"  PASS {name}")

    t0 = 1000.0
    g = DynamicGraph()

    # Test A: add nodes and edges
    for n in "ABCDE":
        g.add_node(n, t=t0)
    g.add_edge("A", "B", t=t0)
    g.add_edge("B", "C", t=t0)
    g.add_edge("C", "D", t=t0)
    g.add_edge("D", "E", t=t0)
    ok(g.has_node("A") and g.has_node("E"), "Test A: nodes added")
    ok(g.has_edge("A", "B") and g.has_edge("D", "E"), "Test A: edges added")
    ok(g.is_reachable("A", "E"), "Test A: A reachable to E")

    # Test B: remove a node, unrelated edges survive
    g.remove_node("C", t=t0)
    ok(not g.has_node("C"), "Test B: node C removed")
    ok(g.has_edge("A", "B"), "Test B: unrelated edge A-B survives")
    ok(g.has_edge("D", "E"), "Test B: unrelated edge D-E survives")
    ok(not g.is_reachable("A", "E"), "Test B: path through C is gone")

    # Test C: split one graph into two components
    g.add_edge("B", "C", t=t0)
    g.add_edge("C", "D", t=t0)  # re-join -> one component
    comps = g.connected_components()
    ok(len(comps) == 1, "Test C: reconnected single component")
    split_before = [GraphEventKind.COMPONENT_SPLIT in [e.kind for e in g.events]]
    g.expire_edge("B", "C", t=t0)
    comps = g.connected_components()
    ok(len(comps) == 2, "Test C: graph split into two components")
    ok(any(e.kind == GraphEventKind.COMPONENT_SPLIT for e in g.events),
       "Test C: COMPONENT_SPLIT event emitted")

    # Test D: reconnect two components
    g.add_edge("B", "C", t=t0)
    ok(len(g.connected_components()) == 1, "Test D: two components reconnect")
    ok(any(e.kind == GraphEventKind.COMPONENT_MERGED for e in g.events),
       "Test D: COMPONENT_MERGED event emitted")

    # hop distances (spec §85) across the reconnected chain
    hops = g.hop_distance("A")
    ok(hops["A"] == 0 and hops["B"] == 1 and hops["C"] == 2 and
       hops["D"] == 3 and hops["E"] == 4, "hop BFS A..E = 0..4")
    nexts = g.next_hops("C", "A")
    ok(nexts == {"B"}, "nextHops(C,A) = {B}")

    # Test G (route change on relay removal)
    g.track_routes_to("A")
    before = g.hop_distance("A")
    ok(before["E"] == 4, "Test G: initial route E hop=4")
    g.expire_edge("C", "D", t=t0)
    after = g.hop_distance("A")
    ok("E" not in after, "Test G: relay removed -> no route to E")
    ok(any(e.kind == GraphEventKind.ROUTE_CHANGED for e in g.events),
       "Test G: ROUTE_CHANGED emitted")

    # lifecycle aging (spec §19)
    g2 = DynamicGraph(node_stale_after=5, node_expire_after=10,
                      edge_stale_after=5, edge_expire_after=10)
    g2.add_node("X", t=0.0)
    g2.add_node("Y", t=0.0)
    g2.add_edge("X", "Y", t=0.0, source="sensor")
    g2.refresh(t=3.0)
    ok(g2.get_node("X").lifecycle.value == "ACTIVE", "aging: fresh -> ACTIVE")
    g2.refresh(t=7.0)
    ok(g2.get_node("X").lifecycle.value == "STALE", "aging: STALE after timeout")
    ok(g2.get_edge("X", "Y").lifecycle.value == "AGING", "aging: edge AGING")
    g2.refresh(t=40.0)
    ok(g2.get_node("X").lifecycle.value == "EXPIRED", "aging: EXPIRED")
    ok(len(g2.connected_components()) == 0, "aging: no components after expiry")

    # relationship memory (§23): X re-signals after hard expiry and comes back
    # (per-endpoint liveness: Y must be re-heard too before the link is live)
    g2.add_edge("X", "Y", t=40.0, source="radio")
    g2.touch_node("X", t=40.0)
    g2.touch_node("Y", t=40.0)
    g2.touch_edge("X", "Y", t=40.0, bidirectional=True)
    ok(g2.get_node("X").lifecycle.value == "ACTIVE",
       "memory: re-signaling node re-admitted after expiry")
    ok(g2.get_edge("X", "Y").lifecycle.value == "ACTIVE",
       "memory: its edge is live again")
    ok(g2.is_reachable("X", "Y"), "memory: connectivity restored")

    print(f"\nDynamicGraph selftest: {checks} checks PASSED")


if __name__ == "__main__":
    _test()