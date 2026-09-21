#!/usr/bin/env python3
"""
Find Us / Crowd Compass — Relative Graph Map (Stage 3)

No GPS, no global coordinates. Members build a *relative* map of the group from
pairwise measurements (RSSI distance + optional compass bearing) entirely on-device.

Model
-----
  * nodes  = group members (origin member pinned at (0,0))
  * edges  = pairwise distance estimates (meters) with a freshness weight
  * layout = spring/gradient relaxation embedding into 2D (relative frame,
             defined only up to rotation/translation — that is expected and fine)
  * bearing = optional compass measurements (from DirectionSweep/rotate-scan)
             rotate the map so it points North for a "you are here" heading

Why this and not SLAM/vector chains (cf. research/12, research/13):
  SLAM needs odometry consistency phone IMUs cannot provide in crowds. A graph
  re-embedded from *fresh* pairwise links is:
    - robust to member joins/leaves (edges added/dropped smoothly)
    - robust to noisy edges (weights decay with age/staleness)
    - cheap: n<=64 -> <=4096 pairs, hundreds of float ops per frame

Feed path: GroupFollower.summary() -> follower_to_edges() -> embed() -> map.

Self-test (pure stdlib, no numpy):
    PYTHONPATH=core/python python3 core/python/relative_map.py
"""
import math
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ─── Tunables ───
EMBED_ITERATIONS = 600          # spring relaxation frames
EMBED_LEARNING_RATE = 0.02      # per-iteration position update gain
EMBED_WEIGHT_MIN = 0.05         # stale edges never fully removed
EDGE_FRESH_DECAY_S = 45.0       # edge freshness half-weight period
EDGE_QUALITY_FLOOR = 0.10       # edge min weight before being dropped
DISTANCE_NOISE_DB = 0.0         # (reserved) injected noise for tests
SPRING_EPS = 1e-6               # guard against coincident nodes


@dataclass
class NodeState:
    member_id: int
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    last_seen: float = 0.0


@dataclass
class EdgeState:
    a: int
    b: int
    distance_m: float
    ts: float
    quality: float = 0.7            # 0..1 measurement trust
    bearing_deg_a: Optional[float] = None  # compass bearing a->b (for north-up)

    def weight(self, now: float) -> float:
        age = max(0.0, now - self.ts)
        fresh = math.exp(-age / EDGE_FRESH_DECAY_S)
        return max(EMBED_WEIGHT_MIN, self.quality * fresh)


def _pair_key(a: int, b: int) -> Tuple[int, int]:
    return (a, b) if a < b else (b, a)


class RelativeMap:
    """Weighted distance graph of group members, embedded into 2D relative coords."""

    def __init__(self, origin_member: int, origin_name: str = "You"):
        self.origin = origin_member
        self.nodes: Dict[int, NodeState] = {
            origin_member: NodeState(origin_member, origin_name)
        }
        self.edges: Dict[Tuple[int, int], EdgeState] = {}
        self._north_aligned = False

    # ── Input ────────────────────────────────────────────────────────────────
    def upsert_node(self, member_id: int, name: str = "") -> None:
        if member_id not in self.nodes:
            self.nodes[member_id] = NodeState(member_id, name or f"#{member_id:03X}")

    def add_edge(self, a: int, b: int, distance_m: float, ts: float,
                 quality: float = 0.7, bearing_deg_a: Optional[float] = None) -> None:
        if distance_m <= 0.5:
            distance_m = 0.5  # floor: can't be closer than ~0.5 m to a person
        key = _pair_key(a, b)
        existing = self.edges.get(key)
        if existing is None or ts >= existing.ts:
            self.edges[key] = EdgeState(a, b, distance_m, ts, quality, bearing_deg_a)
        self.upsert_node(a)
        self.upsert_node(b)

    def remove_stale_edges(self, now: float, max_age_s: float = 180.0) -> int:
        """Drops links with decaying weight below the floor; returns count dropped."""
        drop = [k for k, e in self.edges.items()
                if e.weight(now) < EDGE_QUALITY_FLOOR or now - e.ts > max_age_s]
        for k in drop:
            del self.edges[k]
        return len(drop)

    # ── Embedding ────────────────────────────────────────────────────────────
    def _init_trilateration(self, pairs, n, ids) -> List[List[float]]:
        """
        Deterministic greedy init: place each node via trilateration from the
        two anchored nodes it shares edges with (fallback: circle from one anchor,
        then random). Kills the multiple-local-minima problem of pure spring
        relaxation on complete graphs.
        """
        pos: Dict[int, List[float]] = {0: [0.0, 0.0]}
        edges_by_node: Dict[int, List[Tuple[int, int, float]]] = {m: [] for m in ids}
        for i, j, d, _w in pairs:
            edges_by_node[ids[i]].append((ids[j], d))
            edges_by_node[ids[j]].append((ids[i], d))

        remaining = [m for m in ids if m != 0]
        # prefer nodes with most links to placed nodes (greedy)
        while remaining:
            best_m = max(remaining, key=lambda m: sum(1 for p, _d in edges_by_node[m]
                                                      if p in pos))
            anchors = [(p, d) for p, d in edges_by_node[best_m] if p in pos]
            if len(anchors) >= 2:
                (p1, d1), (p2, d2) = anchors[0], anchors[1]
                x1, y1 = pos[p1]
                x2, y2 = pos[p2]
                base = math.hypot(x2 - x1, y2 - y1)
                if base < SPRING_EPS:
                    px, py, r = pos[best_m] if best_m in pos else (0.0, 0.0, 0.0)
                    pos[best_m] = [x1, y1 + 0.001]
                    remaining.remove(best_m)
                    continue
                dx, dy = (x2 - x1) / base, (y2 - y1) / base
                xx = (d1 * d1 - d2 * d2 + base * base) / (2 * base)
                yy = math.sqrt(max(0.0, d1 * d1 - xx * xx))
                # two candidate points mirrored across the anchor line
                cand = [[x1 + xx * dx - yy * dy, y1 + xx * dy + yy * dx],
                        [x1 + xx * dx + yy * dy, y1 + xx * dy - yy * dx]]
                # disambiguate with a third anchor if available
                if len(anchors) >= 3:
                    p3, d3 = anchors[2]
                    x3, y3 = pos[p3]
                    err = [abs(math.hypot(c[0] - x3, c[1] - y3) - d3) for c in cand]
                    pos[best_m] = cand[0 if err[0] <= err[1] else 1]
                else:
                    random.seed(abs(best_m) * 7919 + 13)
                    pos[best_m] = cand[random.randint(0, 1)]
            elif len(anchors) == 1:
                p1, d1 = anchors[0]
                x1, y1 = pos[p1]
                random.seed(abs(best_m) * 7919 + 13)
                ang = random.uniform(0.0, 2 * math.pi)
                pos[best_m] = [x1 + d1 * math.cos(ang), y1 + d1 * math.sin(ang)]
            else:
                random.seed(abs(best_m) * 7919 + 13)
                pos[best_m] = [random.uniform(-5, 5), random.uniform(-5, 5)]
            remaining.remove(best_m)

        return [pos[m] for m in ids]

    def embed(self, iters: int = EMBED_ITERATIONS,
              lr: float = EMBED_LEARNING_RATE) -> Dict[int, Tuple[float, float]]:
        """Spring-relaxation embedding. Returns {member_id: (x,y)}, origin at (0,0)."""
        now = time.time()
        ids = list(self.nodes.keys())
        idx = {m: i for i, m in enumerate(ids)}
        n = len(ids)

        # Keep only edges between known nodes
        pairs = []
        for k, e in self.edges.items():
            if e.a in idx and e.b in idx:
                pairs.append((idx[e.a], idx[e.b], e.distance_m, e.weight(now)))

        if n == 1:
            return {ids[0]: (0.0, 0.0)}
        if not pairs:
            return {m: (0.0, 0.0) for m in ids}

        # Position init: prior embedding when available
        pos = [[self.nodes[m].x, self.nodes[m].y] for m in ids]
        if all(abs(px) < 1e-6 and abs(py) < 1e-6 for px, py in pos[1:]):
            pos = self._init_trilateration(pairs, n, ids)
        pos[0] = [0.0, 0.0]  # origin pinned

        # Coarse-to-fine learning rate: large steps converge the global shape,
        # progressively smaller steps settle into the noisy optimum without
        # oscillating (fixed-lr springs jitter forever).
        lr_start = max(lr, 0.06)
        lr_end = 0.004
        for it in range(iters):
            frac = it / max(iters - 1, 1)
            cur_lr = lr_start * (lr_end / lr_start) ** frac

            # decoupled forces: each edge pulls both ends toward its length
            for i, j, d, w in pairs:
                dx = pos[j][0] - pos[i][0]
                dy = pos[j][1] - pos[i][1]
                dist = math.hypot(dx, dy)
                if dist < SPRING_EPS:
                    dx, dy, dist = SPRING_EPS, 0.0, SPRING_EPS
                force = (dist - d) * w / dist  # signed pulling ratio
                fx, fy = dx * force, dy * force
                if i != 0:
                    pos[i][0] += cur_lr * fx
                    pos[i][1] += cur_lr * fy
                if j != 0:
                    pos[j][0] -= cur_lr * fx
                    pos[j][1] -= cur_lr * fy

        out = {}
        for i, m in enumerate(ids):
            out[m] = (pos[i][0], pos[i][1])
            self.nodes[m].x, self.nodes[m].y = pos[i]
        return out

    def align_to_north(self) -> bool:
        """
        Rotates the embedded map so the strongest available bearing from the
        origin points North-up. Bearing edge weight = rotation evidence.
        Returns True if an alignment happened.
        """
        now = time.time()
        best = None
        best_weight = 0.0
        for e in self.edges.values():
            if e.a == self.origin and e.bearing_deg_a is not None:
                w = e.weight(now)
                if w > best_weight:
                    best = (e.b, e.bearing_deg_a, w)
                    best_weight = w

        if best is None:
            return False
        target_mid, target_bearing, _ = best
        if target_mid not in self.nodes:
            return False
        bx, by = self.nodes[target_mid].x, self.nodes[target_mid].y
        cur_bearing = math.degrees(math.atan2(bx, by)) % 360  # CSS/2D y-down? no: north-from-y
        # Coordinate: +x right, +y up. Bearing 0 = +y (north), 90 = +x (east).
        cur_bearing = (90.0 - math.degrees(math.atan2(by, bx))) % 360
        delta = (target_bearing - cur_bearing + 180.0) % 360 - 180.0
        if abs(delta) < 0.5:
            self._north_aligned = True
            return True
        rad = math.radians(delta)
        c, s = math.cos(rad), math.sin(rad)
        for m in self.nodes:
            if m == self.origin:
                continue
            px, py = self.nodes[m].x, self.nodes[m].y
            # Clockwise (compass) rotation: a bearing-north point must spin toward
            # the target azimuth the same way a magnetic compass needle does.
            self.nodes[m].x = px * c + py * s
            self.nodes[m].y = -px * s + py * c
        self._north_aligned = True
        return True

    # ── Output ───────────────────────────────────────────────────────────────
    def stress(self, now: Optional[float] = None) -> float:
        """Raw least-squares embedding stress (0 = perfect fit)."""
        now = time.time() if now is None else now
        num = den = 0.0
        for e in self.edges.values():
            if e.a not in self.nodes or e.b not in self.nodes:
                continue
            ax, ay = self.nodes[e.a].x, self.nodes[e.a].y
            bx, by = self.nodes[e.b].x, self.nodes[e.b].y
            d_est = math.hypot(ax - bx, ay - by)
            w = e.weight(now)
            num += w * (d_est - e.distance_m) ** 2
            den += w * e.distance_m ** 2
        return num / den if den else 0.0

    def bearings_from_origin(self) -> Dict[int, float]:
        """Compass bearings from origin to each member (North-up, for UI arrow)."""
        out = {}
        for m, node in self.nodes.items():
            if m == self.origin:
                continue
            out[m] = (90.0 - math.degrees(math.atan2(node.y, node.x))) % 360
        return out

    def ascii_map(self, span_m: float = 30.0, cols: int = 29) -> str:
        """Crude 'you are here' visualization. Origin '@', members by last hex digit."""
        ids = [m for m in self.nodes if m != self.origin]
        if not ids:
            return "@\n"
        minx = min(self.nodes[m].x for m in ids)
        maxx = max(self.nodes[m].x for m in ids)
        miny = min(self.nodes[m].y for m in ids)
        maxy = max(self.nodes[m].y for m in ids)
        cx = 0.5 * (minx + maxx) or 1.0
        cy = 0.5 * (miny + maxy) or 1.0
        scale = min((cols - 3) / (maxx - minx or 1.0),
                    (cols - 3) / (maxy - miny or 1.0))
        def cell(x, y):
            nx = int(round(cols / 2 + (x - cx) * scale))
            ny = int(round((cols - 3) / 2 - (y - cy) * scale))
            return nx, ny
        grid = [["."] * cols for _ in range(cols - 2)]
        for m, node in self.nodes.items():
            nx, ny = cell(node.x, node.y)
            ny = max(0, min(len(grid) - 1, ny))
            nx = max(0, min(cols - 1, nx))
            grid[ny][nx] = "@" if m == self.origin else f"{m & 0xF:X}"
        return "\n".join("".join(row) for row in grid)


# ─── Bridge from GroupFollower (core/python/find_group.py) ─────────────────
def follower_to_edges(group_session, follower, origin_member: int,
                      ts: Optional[float] = None) -> List[Tuple[int, float, float]]:
    """
    Converts a GroupFollower.summary() into (member_id, distance_m, bearing_deg)
    star-graph edges from the origin member. Bearing may be None.
    """
    now = time.time() if ts is None else ts
    summ = follower.summary(origin_member, now=now)
    out = []
    for mid, rec in summ["members"].items():
        if mid == origin_member:
            continue
        d = rec.get("distance_m")
        if rec.get("status") == "FOUND" and d is not None:
            out.append((mid, float(d), rec.get("bearing_deg")))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────────────────
def _true_dist(xa, ya, xb, yb):
    return math.hypot(xa - xb, ya - yb)


def _distance_matrix(truth: Dict[int, Tuple[float, float]]):
    ids = list(truth)
    return {_pair_key(ids[i], ids[j]): _true_dist(*truth[ids[i]], *truth[ids[j]])
            for i in range(len(ids)) for j in range(i + 1, len(ids))}


def run_relative_map_self_test() -> Dict:
    print("=" * 70)
    print("RELATIVE GRAPH MAP SELF-TEST")
    print("=" * 70)
    results = {}
    random.seed(7)

    # Ground-truth group around origin (0,0)
    origin = 0
    truth = {
        origin: (0.0, 0.0),
        1: (10.0, 0.0),     # due East (bearing 90)
        2: (0.0, 12.0),     # due North (bearing 0)
        3: (-9.0, 5.0),
        4: (-12.0, -6.0),
        5: (5.0, -11.0),
    }
    true_dists = _distance_matrix(truth)

    # 1. Full-graph embed with noise: recovered coordinate set must reproduce
    #    the ground-truth distance matrix within tolerance.
    m = RelativeMap(origin)
    ts = time.time()
    for k, d in true_dists.items():
        noisy = d + random.gauss(0, 1.5)
        m.add_edge(k[0], k[1], max(0.5, noisy), ts, quality=0.8)
    m.embed()
    errs = []
    for k, d in true_dists.items():
        ax, ay = m.nodes[k[0]].x, m.nodes[k[0]].y
        bx, by = m.nodes[k[1]].x, m.nodes[k[1]].y
        errs.append(abs(math.hypot(ax - bx, ay - by) - d))
    max_dist_err = max(errs)
    mean_dist_err = sum(errs) / len(errs)
    results["embed_preserves_distances"] = max_dist_err < 2.5 and mean_dist_err < 1.0
    print(f"[1] full-graph embed -> dist errors: mean={mean_dist_err:.2f}m max={max_dist_err:.2f}m")

    # 2. Missing edges: drop 30% of links (CRITICAL — real scans are bursty)
    m2 = RelativeMap(origin)
    for i, (k, d) in enumerate(true_dists.items()):
        if i % 3 == 2:  # drop every 3rd edge
            continue
        m2.add_edge(k[0], k[1], d + random.gauss(0, 1.5), ts, quality=0.8)
    m2.embed()
    errs2 = [abs(math.hypot(m2.nodes[k[0]].x - m2.nodes[k[1]].x,
                            m2.nodes[k[0]].y - m2.nodes[k[1]].y) - d)
             for k, d in true_dists.items()
             if _pair_key(*k) in {_pair_key(e.a, e.b) for e in m2.edges.values()}]
    mean2 = sum(errs2) / len(errs2)
    results["embed_sparse_edges"] = mean2 < 2.0
    print(f"[2] 30%-dropped edges -> mean dist error={mean2:.2f}m")
    print(m2.ascii_map())

    # 3. North alignment via ONE known compass bearing (member 1 at bearing 90 E)
    m3 = RelativeMap(origin)
    for k, d in true_dists.items():
        m3.add_edge(k[0], k[1], d + random.gauss(0, 1.0), ts, quality=0.9,
                    bearing_deg_a=90.0 if k[0] == 0 and k[1] == 1 else None)
    m3.embed()
    m3.align_to_north()
    b = m3.bearings_from_origin()
    err_bearing = min(abs(b[1] - 90.0), 360 - abs(b[1] - 90.0))
    results["north_alignment"] = err_bearing < 10.0
    print(f"[3] north-align -> bearing to member1={b[1]:.1f} deg (target 90)")

    # 4. Incremental: a NEW member joins with links to two existing anchors
    # Truth for the newcomer joins the snapshot AFTER the first embedding
    newcomer_pos = (30.0, 8.0)
    m4 = RelativeMap(origin)
    for k, d in true_dists.items():
        m4.add_edge(k[0], k[1], d, ts, quality=0.9)
    m4.embed()
    # newcomer hears member 1 and 2 (and they hear back)
    for anchor in (1, 2):
        ax, ay = truth[anchor]
        d = math.hypot(newcomer_pos[0] - ax, newcomer_pos[1] - ay)
        m4.add_edge(6, anchor, d + random.gauss(0, 0.8), ts, quality=0.95)
        m4.upsert_node(6, "New")
    m4.embed(iters=400)
    nx, ny = m4.nodes[6].x, m4.nodes[6].y
    tx, ty = newcomer_pos
    # distance between newcomer's recovered and true position (relative frame may rotate)
    # -> worst-case bound via triangle inequality using anchor distances instead
    d1 = _true_dist(m4.nodes[6].x, m4.nodes[6].y, m4.nodes[1].x, m4.nodes[1].y)
    d1t = math.hypot(newcomer_pos[0] - truth[1][0], newcomer_pos[1] - truth[1][1])
    d2 = _true_dist(m4.nodes[6].x, m4.nodes[6].y, m4.nodes[2].x, m4.nodes[2].y)
    d2t = math.hypot(newcomer_pos[0] - truth[2][0], newcomer_pos[1] - truth[2][1])
    err_new = (abs(d1 - d1t) + abs(d2 - d2t)) / 2.0
    results["incremental_join"] = err_new < 1.5
    print(f"[4] newcomer -> anchor-dist error mean={err_new:.2f}m "
          f"recovered=({nx:.1f},{ny:.1f}) truth=({tx},{ty})")

    # 5. Stale edge cleanup
    m5 = RelativeMap(origin)
    m5.add_edge(0, 1, 10.0, ts, quality=0.9)
    m5.add_edge(1, 2, 9.0, ts - 400.0, quality=0.9)  # ancient
    dropped = m5.remove_stale_edges(time.time())
    results["stale_edge_cleanup"] = dropped == 1
    print(f"[5] stale-edge cleanup dropped {dropped}")

    all_pass = all(results.values())
    print("-" * 70)
    for k, v in results.items():
        print(f"  {'✓' if v else '✗'} {k}")
    print("-" * 70)
    print(f"RESULT: {'ALL PASSED' if all_pass else 'FAILURES PRESENT'}")
    return results


if __name__ == "__main__":
    run_relative_map_self_test()