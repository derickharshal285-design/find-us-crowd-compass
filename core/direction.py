"""Phone-to-phone direction for the relative vector graph.

There is no BLE4/5 phone-to-phone angle hardware, so the legacy path
reconstructs the world bearing to a neighbor by rotating the handset for a few
seconds: the RSSI-vs-heading pattern peaks when the phone faces the neighbor
(synthetic lighthouse, per stage-2 find_group.DirectionSweep). Self-located, no
neighbor data, no wire changes -> backward compatible by construction.

Optional refinements, strictly additive:
  * a stationary peer sharing its reciprocal world bearing over the OOB peer
    channel tightens the estimate (BearingFusion weighted circular mean);
  * state-gating (StationarityGate) keeps the sweep honest while walking.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Deque, List, Optional, Tuple

# Log-distance model constants (shared with stage-2 find_group).
RSSI_AT_1M_DBM = -59.0
PATH_LOSS_N = 2.2

BAND_NEAR_M = 5.0
BAND_MEDIUM_M = 20.0

SWEEP_WINDOW_S = 10.0
SWEEP_MIN_SAMPLES = 12
SWEEP_BIN_DEG = 45
SWEEP_MIN_BIN_COUNT = 2


def wrap360(deg: float) -> float:
    return math.fmod(deg, 360.0) % 360.0


def opposite(bearing: float) -> float:
    return wrap360(bearing + 180.0)


def rssi_to_meters(rssi_dbm: float, a_dbm: float = RSSI_AT_1M_DBM,
                   n: float = PATH_LOSS_N) -> float:
    """Log-distance RSSI -> meters (clamped so near-field never goes <= 0)."""
    if rssi_dbm >= a_dbm:
        return max(0.5, math.pow(10.0, (a_dbm - rssi_dbm) / (10.0 * n)))
    return math.pow(10.0, (a_dbm - rssi_dbm) / (10.0 * n))


def meters_to_band(distance_m: float) -> str:
    if distance_m < BAND_NEAR_M:
        return "NEAR"
    if distance_m < BAND_MEDIUM_M:
        return "MEDIUM"
    return "FAR"


def _circular_mean(pairs: List[Tuple[float, float]]) -> Tuple[float, float]:
    """(bearing_deg, weight) pairs -> (mean_deg, resultant_length r 0..1)."""
    s, c, wsum = 0.0, 0.0, 0.0
    for b, w in pairs:
        rad = math.radians(b)
        s += w * math.sin(rad)
        c += w * math.cos(rad)
        wsum += w
    if wsum <= 0:
        return 0.0, 0.0
    r = math.hypot(s, c) / wsum
    mean = math.degrees(math.atan2(s / wsum, c / wsum)) % 360.0
    return mean, r


def confidence_to_sigma_deg(confidence: float) -> float:
    """Map a DirectionSweep confidence onto a bearing uncertainty (degrees)."""
    c = max(0.0, min(1.0, confidence))
    return 5.0 + 90.0 * (1.0 - c)


class SweepEstimate:
    __slots__ = ("detected", "bearing_deg", "confidence", "samples",
                 "occupied_bins")

    def __init__(self, detected: bool, bearing_deg: float,
                 confidence: float, samples: int = 0,
                 occupied_bins: int = 0) -> None:
        self.detected = detected
        self.bearing_deg = wrap360(bearing_deg)
        self.confidence = confidence
        self.samples = samples
        self.occupied_bins = occupied_bins

    def sigma_deg(self) -> Optional[float]:
        return confidence_to_sigma_deg(self.confidence) if self.detected else None


class DirectionSweep:
    """Productized rotate-scan bearing estimator (stage-2 model, core library).

    Feeds (rssi_dbm, heading_deg, ts) samples while the handset rotates; the
    histogram of mean RSSI per 45-deg heading bin peaks toward the neighbor.
    """

    def __init__(self, sweep_window_s: float = SWEEP_WINDOW_S,
                 bin_deg: int = SWEEP_BIN_DEG) -> None:
        self.samples: Deque[Tuple[float, float, float]] = deque(maxlen=400)
        self.sweep_window_s = sweep_window_s
        self.bin_deg = int(bin_deg)
        self.min_samples = SWEEP_MIN_SAMPLES
        self.min_bin_count = SWEEP_MIN_BIN_COUNT

    def add_sample(self, rssi_dbm: float, heading_deg: float, ts: float) -> None:
        self.samples.append((ts, rssi_dbm, wrap360(heading_deg)))

    def estimate(self, now: Optional[float] = None) -> SweepEstimate:
        cutoff = (now if now is not None else _wall_now()) - self.sweep_window_s
        recent = [(t, r, h) for t, r, h in self.samples if t >= cutoff]
        if len(recent) < self.min_samples:
            return SweepEstimate(False, 0.0, 0.0, samples=len(recent))

        n_bins = 360 // self.bin_deg
        bins_sum = [0.0] * n_bins
        bins_cnt = [0] * n_bins
        for _, r, h in recent:
            idx = int(((h % 360.0) + self.bin_deg / 2.0) // self.bin_deg) % n_bins
            bins_sum[idx] += r
            bins_cnt[idx] += 1
        for i in range(n_bins):
            if bins_cnt[i]:
                bins_sum[i] /= bins_cnt[i]

        peak = max(range(n_bins), key=lambda i: bins_sum[i])
        if bins_cnt[peak] < self.min_bin_count:
            return SweepEstimate(False, 0.0, 0.0, samples=len(recent),
                                 occupied_bins=sum(1 for c in bins_cnt if c))

        # Confidence = angular spread contrast of the RSSI pattern, clamped.
        spread = max(bins_sum) - min(bins_sum)
        confidence = min(1.0, max(0.0, spread / max(10.0, abs(spread))))
        bearing = (peak * self.bin_deg) % 360.0
        return SweepEstimate(True, bearing, confidence,
                             samples=len(recent),
                             occupied_bins=sum(1 for c in bins_cnt if c))


class BearingFusion:
    """Weighted circular fusion of bearing evidence (sweep + OOB reciprocity)."""

    @staticmethod
    def fuse(pairs: List[Tuple[float, float]]) -> Tuple[Optional[float],
                                                        Optional[float]]:
        """(bearing_deg, weight) -> (mean_deg, sigma_deg); None when empty."""
        if not pairs:
            return None, None
        mean, r = _circular_mean(pairs)
        if r <= 1e-9:
            return None, 90.0
        sigma = math.degrees(math.sqrt(max(0.0, -2.0 * math.log(min(1.0, r)))))
        sigma = max(5.0, min(90.0, sigma))
        return mean, sigma

    @staticmethod
    def reciprocal_boost(self_bearing: Optional[float],
                         peer_bearing_to_me: Optional[float],
                         weight_self: float = 2.0,
                         weight_peer: float = 1.0
                         ) -> Tuple[Optional[float], Optional[float]]:
        pairs: List[Tuple[float, float]] = []
        if self_bearing is not None:
            pairs.append((self_bearing, weight_self))
        if peer_bearing_to_me is not None:
            pairs.append((opposite(peer_bearing_to_me), weight_peer))
        return BearingFusion.fuse(pairs)


class StationarityGate:
    """Detects when the handset is still, from accelerometer-magnitude variance."""

    def __init__(self, window: int = 20, variance_threshold: float = 0.10) -> None:
        self.samples: Deque[float] = deque(maxlen=window)
        self.variance_threshold = variance_threshold

    def add_accel(self, magnitude_g: float) -> None:
        self.samples.append(magnitude_g)

    def is_stationary(self) -> bool:
        if len(self.samples) < 4:
            return False
        mean = sum(self.samples) / len(self.samples)
        var = sum((x - mean) ** 2 for x in self.samples) / len(self.samples)
        return var <= self.variance_threshold


class OobSideband:
    """Bearing-reciprocity sideband (text frame, not the legacy BLE wire).

    Parity with the Kotlin/Swift CompatTier ports: a peer shares the bearing it
    measures *back to us*, and BearingFusion folds it into the sweep estimate.
    """

    PREFIX = "FINDUS/OOB/1\n"

    @staticmethod
    def serialize(peer_bearing_to_me_deg: float) -> str:
        return OobSideband.PREFIX + str(peer_bearing_to_me_deg)

    @staticmethod
    def parse(raw: str) -> Optional[float]:
        if not raw.startswith(OobSideband.PREFIX):
            return None
        try:
            v = float(raw[len(OobSideband.PREFIX):].strip())
        except ValueError:
            return None
        if not math.isfinite(v) or not 0.0 <= v < 360.0:
            return None
        return v


def route_metrics(graph: dict, origin: str, target: str
                  ) -> dict:
    """Min-hops / min-meters / min-uncertainty paths over an edge dict.

    graph = { (a, b): (meters, bearing_deg, sigma_deg) } (undirected).
    Returns each metric's path + cost. Simple Dijkstra over three cost fields.
    """
    adj: dict = {}
    for (a, b), (d, _, s) in graph.items():
        adj.setdefault(a, []).append((b, d, s))
        adj.setdefault(b, []).append((a, d, s))

    def dijkstra(cost_field: str) -> Tuple[list, float]:
        import heapq
        best = {origin: 0.0}
        parent: dict = {}
        pq = [(0.0, origin)]
        while pq:
            cu, u = heapq.heappop(pq)
            if u == target:
                break
            if cu > best.get(u, math.inf):
                continue
            for v, d, s in adj.get(u, []):
                step = {"hops": 1.0, "meters": d, "uncert": s * s}[cost_field]
                nv = cu + step
                if nv < best.get(v, math.inf):
                    best[v] = nv
                    parent[v] = u
                    heapq.heappush(pq, (nv, v))
        if target not in best:
            return [], math.inf
        path = [target]
        u = target
        while u != origin:
            u = parent[u]
            path.append(u)
        path.reverse()
        return path, round(best[target], 2)

    hops_path, hops = dijkstra("hops")
    meters_path, meters = dijkstra("meters")
    uncert_path, uncert = dijkstra("uncert")

    def path_meters(path: List[str]) -> float:
        total = 0.0
        for i in range(len(path) - 1):
            key = (path[i], path[i + 1])
            d = graph.get(key, (0.0, 0.0, 0.0))[0]
            total += d
        return round(total, 2)

    return {
        "min_hops": (hops_path, hops),
        "min_meters": (meters_path, meters),
        "min_uncertainty": (uncert_path, uncert),
        "hops_path_meters": path_meters(hops_path),
    }


def _wall_now() -> float:
    import time
    return time.time()


def _test() -> None:
    checks = 0

    def ok(cond: bool, name: str) -> None:
        nonlocal checks
        checks += 1
        assert cond, name
        print(f"  PASS {name}")

    # 1. Geometry helpers.
    ok(wrap360(370.0) == 10.0, "wrap360")
    ok(opposite(10.0) == 190.0, "opposite bearing")
    ok(rssi_to_meters(-59.0) < 2.0 and rssi_to_meters(-80.0) > rssi_to_meters(-59.0),
       "rssi_to_meters monotonic")
    ok(meters_to_band(3.0) == "NEAR" and meters_to_band(10.0) == "MEDIUM"
       and meters_to_band(40.0) == "FAR", "distance bands")

    # 2. Sweep recovers the lighthouse bearing (peak at 120 deg).
    sweep = DirectionSweep()
    ts = 1000.0
    for deg in range(0, 360, 15):
        sep = abs(((deg - 120 + 540) % 360) - 180)
        sig = -55.0 - sep * 0.5
        sweep.add_sample(sig, float(deg), ts)
        ts += 0.05
    est = sweep.estimate(now=ts + 0.01)
    ok(est.detected and abs(est.bearing_deg - 120.0) <= 22.5,
       f"sweep recovers 120 deg (got {est.bearing_deg:.1f})")
    ok(est.confidence > 0.0, "sweep confidence positive")
    ok(sweep.estimate(now=ts + 20.0).detected is False,
       "stale sweep reports not-detected")

    # 3. Fusion: agreeing evidence tightens sigma; contradiction blows up.
    mean, sigma = BearingFusion.fuse([(90.0, 1.0), (95.0, 1.0)])
    ok(abs(mean - 92.5) < 3.0, f"fusion mean ~92.5 (got {mean:.1f})")
    ok(sigma is not None and sigma < 30.0, f"fusion sigma tight ({sigma:.1f})")
    mean2, sigma2 = BearingFusion.fuse([(10.0, 1.0), (350.0, 1.0)])
    ok(abs(mean2 - 359.99) < 1.0 or abs(mean2 - 0.0) < 1.0,
       "fusion wraps across 0 deg")
    _, rbad = _circular_mean([(0.0, 1.0), (180.0, 1.0)])
    ok(rbad < 0.05, "antipodal evidence -> confidence collapses")

    # 4. Reciprocal boost: peer shares its bearing back to me.
    me_b, me_s = BearingFusion.reciprocal_boost(90.0, 265.0)  # 265 -> 85
    ok(abs(me_b - 87.5) < 3.0, f"reciprocal boost mean {me_b:.1f}")
    selfonly, _ = BearingFusion.reciprocal_boost(90.0, None)
    ok(abs(selfonly - 90.0) < 1e-6, "self-only falls back to sweep")

    # 5. Stationarity gate.
    gate = StationarityGate(window=8, variance_threshold=0.10)
    for _ in range(8):
        gate.add_accel(1.0)
    ok(gate.is_stationary(), "still handset is stationary")
    for i in range(8):
        gate.add_accel(1.0 + (0.5 if i % 2 else -0.5))
    ok(not gate.is_stationary(), "shaking handset is not stationary")

    # 5b. OOB bearing-reciprocity sideband (Kotlin/Swift parity).
    ok(OobSideband.parse(OobSideband.serialize(84.5)) == 84.5,
       "OOB sideband round-trips")
    ok(OobSideband.parse("X/OTHER/1\n5.0") is None,
       "foreign OOB frame rejected")
    ok(OobSideband.parse("FINDUS/OOB/1\n999.0") is None,
       "out-of-range OOB bearing rejected")

    # 6. Vector-graph route metrics: physically-shorter path beats min-hops.
    graph = {
        # Arm 1 (2 hops, long): A-B-C
        ("A", "B"): (31.6, 115.0, 10.0),
        ("B", "C"): (32.0, 115.0, 10.0),
        # Arm 2 (3 hops, short): A-D-E-C  (total 20 m)
        ("A", "D"): (5.0, 90.0, 10.0),
        ("D", "E"): (5.0, 90.0, 10.0),
        ("E", "C"): (10.0, 90.0, 10.0),
    }
    m = route_metrics(graph, "A", "C")
    hops_path, hops_cost = m["min_hops"]
    meters_path, meters_cost = m["min_meters"]
    ok(hops_cost == 2.0 and hops_path == ["A", "B", "C"],
       f"min-hops = {hops_path} ({hops_cost})")
    ok(meters_cost == 20.0 and meters_path == ["A", "D", "E", "C"],
       f"min-meters = {meters_path} ({meters_cost})")
    ok(meters_cost < m["hops_path_meters"],
       f"vector graph prefers physically-shorter route: "
       f"{meters_cost:.0f}m vs {m['hops_path_meters']:.0f}m")

    print(f"-" * 50)
    print(f"direction layer: {checks} checks PASSED")


if __name__ == "__main__":
    _test()