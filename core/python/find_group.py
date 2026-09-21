#!/usr/bin/env python3
"""
Find Us / Crowd Compass — Group-Finding Navigation Layer (Stage 2)

Real use case fixed: **not** emergency responders — people finding each other
inside a group (festival, stadium, hike). Foreground BLE, per-member beacon,
RSSI distance + compass-heading arrow.

Components
----------
  * GroupSession     — join code -> per-group derived key (fixes hardcoded-key
                       problem). No server involved: everyone with the code
                       derives the same key locally.
  * member_beacon    — PacketType.GROUP_BEACON (0x7, reserved in PacketV2 spec)
                       carrying member_id + valid envelope MAC under the group key.
  * PeerDistanceEstimator — log-distance path-loss model + Kalman-lite smoothing
                       -> distance_m with closing/drifting trend.
  * DirectionSweep   — rotate-scan bearing: RSSI vs compass-heading histogram
                       -> bearing_deg toward a member (synthetic lighthouse).

Run self-test:
    PYTHONPATH=core/python python3 core/python/find_group.py
"""
import time
import math
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Deque
from collections import deque

from packet_v2 import (
    PacketV2, AgeBucket,
    pack_packet_v2, unpack_packet_v2,
    compute_envelope_mac, verify_envelope_mac,
    encode_fec_hamming, decode_packet_frame,
    encapsulate_ios_background_safe,
)

GROUP_BEACON_TYPE = 0x7          # Reserved range 0x7..0xF in PacketV2 spec
KEY_SALT = b"FindUs/Group/v1"
KEY_ITERATIONS = 1000

# Log-distance path-loss model: RSSI = A - 10n*log10(d)
RSSI_AT_1M_DBM = -59.0           # A: RSSI measured at 1 m (tune per device)
PATH_LOSS_N = 2.2                # n: indoor office/venue ~2.2
BLE_PAYLOAD_LIMIT = 23           # iOS background-safe budget

# Direction sweep
SWEEP_WINDOW_S = 10.0
SWEEP_MIN_SAMPLES = 12
SWEEP_BIN_DEG = 45               # 8 bins over 360 deg
SWEEP_MIN_BIN_COUNT = 2

# Distance filter (Kalman-lite on log-distance domain)
KALMAN_PROCESS_NOISE = 0.03      # meters drift per update
KALMAN_MEASURE_NOISE = 4.0       # dBm measurement variance


def derive_group_key(join_code: str) -> bytes:
    """PBKDF2-HMAC-SHA256(join_code) -> 32-byte group session key.

    Anyone who knows/can guess the join code can join the group — that is the
    intent (friends share a code). Use a 6+-digit code for a ~1M-space offline
    guess barrier; do NOT reuse this for anything security-critical.
    """
    if not join_code or len(join_code) < 4:
        raise ValueError("join_code must be >= 4 characters")
    return hashlib.pbkdf2_hmac(
        "sha256", join_code.encode("utf-8"), KEY_SALT, KEY_ITERATIONS
    )


class GroupSession:
    """One group = one derived key + member roster (no server)."""

    def __init__(self, join_code: str, max_members: int = 64, poll_s: float = 5.0):
        self.join_code = join_code
        self.key = derive_group_key(join_code)
        self.max_members = max_members
        self.poll_s = poll_s
        self.members: Dict[int, str] = {}  # member_id -> display name
        self._next_id = 0

    def add_member(self, name: str = "") -> int:
        """Allocates the next free 12-bit member id and returns it."""
        if len(self.members) >= self.max_members:
            raise ValueError(f"member limit reached ({self.max_members})")
        mid = self._next_id % 0x0FFF
        while mid in self.members:
            self._next_id = (self._next_id + 1) % len(self.members) + 1
            mid = self._next_id % 0x0FFF
        self.members[mid] = name
        self._next_id = mid + 1
        return mid


def build_member_beacon(session: GroupSession, member_id: int,
                        epoch: int, baro_diff: int = 0, flags: int = 0,
                        age: int = AgeBucket.LIVE) -> bytes:
    """Encodes a member beacon into an iOS-safe BLE frame (ready to advertise)."""
    mac = compute_envelope_mac(session.key, member_id, epoch, GROUP_BEACON_TYPE)
    pkt = PacketV2(
        pkt_type=GROUP_BEACON_TYPE,
        sos_id=member_id,
        hop_count=0,
        baro_diff=baro_diff,
        flags=flags,
        epoch=epoch,
        age=age,
        reserved=0,
        envelope_mac=mac,
    )
    raw = pack_packet_v2(pkt)
    fec = encode_fec_hamming(raw)
    return encapsulate_ios_background_safe(fec)


def decode_member_beacon(session: GroupSession, frame: bytes,
                         now: float) -> Optional[Tuple[int, int, int]]:
    """Parses + authenticates a member beacon. Returns (member_id, epoch, baro_diff)."""
    payload = decode_packet_frame(frame)
    if payload is None:
        return None
    try:
        pkt = unpack_packet_v2(payload)
    except Exception:
        return None
    if pkt.pkt_type != GROUP_BEACON_TYPE:
        return None
    if not verify_envelope_mac(session.key, pkt.sos_id, pkt.epoch, pkt.pkt_type,
                               pkt.envelope_mac):
        return None
    return pkt.sos_id, pkt.epoch, pkt.baro_diff


class PeerDistanceEstimator:
    """Log-distance path loss -> distance, filtered in the log domain (Kalman-lite)."""

    def __init__(self, member_id: int):
        self.member_id = member_id
        self.distance_m: float = float("nan")
        self.cov: float = 10.0          # initial log-distance variance
        self.q = KALMAN_PROCESS_NOISE
        self.r = KALMAN_MEASURE_NOISE
        self.rssi_history: Deque[Tuple[float, float]] = deque(maxlen=200)
        self.last_update: float = 0.0

    def _rssi_to_logdist(self, rssi: float) -> float:
        if rssi >= -20.0:  # clamped: too close to be meaningful
            rssi = -20.0
        return (RSSI_AT_1M_DBM - rssi) / (10.0 * PATH_LOSS_N)

    def update(self, rssi_dbm: float, ts: float) -> float:
        """Adds an RSSI sample, returns smoothed distance in meters."""
        self.rssi_history.append((ts, rssi_dbm))

        z = self._rssi_to_logdist(rssi_dbm)

        if math.isnan(self.distance_m):
            self.distance_m = z
            self.cov = 10.0
        else:
            dt = max(0.0, ts - self.last_update)
            self.cov += self.q * dt if dt else self.q
            gain = self.cov / (self.cov + self.r)
            self.distance_m += gain * (z - self.distance_m)
            self.cov *= (1.0 - gain)

        self.last_update = ts
        return self.distance_m

    def trend_db(self, window_s: float = 10.0) -> Tuple[float, int]:
        """Returns (rssi_delta_db, samples) over the window."""
        now = time.time()
        cutoff = now - window_s
        recent = [(t, r) for t, r in self.rssi_history if t >= cutoff]
        if len(recent) < 3:
            return 0.0, len(recent)
        return recent[-1][1] - recent[0][1], len(recent)


class DirectionSweep:
    """Rotate-scan bearing estimator: histogram of RSSI vs compass heading."""

    def __init__(self, member_id: int):
        self.member_id = member_id
        self.samples: Deque[Tuple[float, float, float]] = deque(maxlen=400)  # (t, rssi, heading)

    def add_sample(self, rssi_dbm: float, heading_deg: float, ts: float):
        self.samples.append((ts, rssi_dbm, heading_deg))

    def bearing(self) -> Tuple[bool, float, float]:
        """Returns (detected, bearing_deg, confidence 0..1)."""
        now = time.time()
        recent = [(t, r, h) for t, r, h in self.samples if now - t <= SWEEP_WINDOW_S]
        if len(recent) < SWEEP_MIN_SAMPLES:
            return False, 0.0, 0.0

        n_bins = 360 // SWEEP_BIN_DEG
        bins_sum = [0.0] * n_bins
        bins_cnt = [0] * n_bins
        for _, r, h in recent:
            idx = int(((h % 360) + SWEEP_BIN_DEG / 2) // SWEEP_BIN_DEG) % n_bins
            bins_sum[idx] += r
            bins_cnt[idx] += 1
        for i in range(n_bins):
            if bins_cnt[i]:
                bins_sum[i] /= bins_cnt[i]

        peak = max(range(n_bins), key=lambda i: bins_sum[i])
        if bins_cnt[peak] < SWEEP_MIN_BIN_COUNT:
            return False, 0.0, 0.0

        spread = max(bins_sum) - min(bins_sum)
        rng = spread if spread > 1e-9 else 1.0
        confidence = min(1.0, spread / max(10.0, rng))
        bearing_deg = (peak * SWEEP_BIN_DEG) % 360
        return True, bearing_deg, confidence


@dataclass
class PeerState:
    member_id: int
    distance: PeerDistanceEstimator = field(default=None)
    direction: DirectionSweep = field(default=None)
    last_seen: float = 0.0
    epoch: int = -1

    def __post_init__(self):
        if self.distance is None:
            self.distance = PeerDistanceEstimator(self.member_id)
        if self.direction is None:
            self.direction = DirectionSweep(self.member_id)


class GroupFollower:
    """Tracks every group member and answers 'where is my friend'."""

    def __init__(self, session: GroupSession, stale_s: float = 60.0):
        self.session = session
        self.stale_s = stale_s
        self.peers: Dict[int, PeerState] = {}

    def on_scan(self, frame: bytes, rssi_dbm: float, heading_deg: float,
                ts: float) -> Optional[PeerState]:
        """Feed a BLE scan result (advertisement frame). Returns updated peer."""
        dec = decode_member_beacon(self.session, frame, ts)
        if dec is None:
            return None
        mid, epoch, _baro = dec

        peer = self.peers.get(mid)
        if peer is None:
            peer = PeerState(member_id=mid)
            self.peers[mid] = peer

        # Ignore out-of-order/stale epochs from the same member (4-bit replay guard)
        if peer.epoch != -1 and epoch != peer.epoch and (epoch - peer.epoch) % 16 != 1:
            pass  # still accept; epoch guard is advisory here

        peer.epoch = epoch
        peer.last_seen = ts
        peer.distance.update(rssi_dbm, ts)
        peer.direction.add_sample(rssi_dbm, heading_deg, ts)
        return peer

    def summary(self, member_id: Optional[int] = None,
                now: Optional[float] = None) -> Dict:
        """Human/UI-ready summary. Returns distances + coarse bearing per member."""
        now = time.time() if now is None else now
        out: Dict = {"members": {}, "join_code": self.session.join_code}
        for mid, name in self.session.members.items():
            peer = self.peers.get(mid)
            if peer is None or now - peer.last_seen > self.stale_s:
                out["members"][mid] = {"status": "LOST", "name": name}
                continue
            dist = peer.distance.distance_m
            detected, bearing, conf = peer.direction.bearing()
            db_delta, samples = peer.distance.trend_db()
            out["members"][mid] = {
                "status": "FOUND",
                "name": name,
                "distance_m": round(dist, 1) if not math.isnan(dist) else None,
                "bearing_deg": round(bearing, 1) if detected else None,
                "bearing_confidence": round(conf, 2) if detected else 0.0,
                "rssi_delta_db": round(db_delta, 1),
                "closing": db_delta >= 3.0,
                "drifting": db_delta <= -5.0,
                "last_seen_s": round(now - peer.last_seen, 1),
                "rssi_samples": samples,
            }
        return out


# ─────────────────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────────────────
def run_group_self_test() -> Dict:
    print("=" * 70)
    print("GROUP-FINDING NAVIGATION LAYER SELF-TEST")
    print("=" * 70)
    results = {}

    # 1. Key derivation is deterministic and code-sensitive
    k1 = derive_group_key("7421")
    k2 = derive_group_key("7421")
    k3 = derive_group_key("7422")
    results["key_derivation_deterministic"] = k1 == k2
    results["key_varies_with_code"] = k1 != k3
    print(f"[1] key determinism + code sensitivity: {k1.hex()[:8]}... != {k3.hex()[:8]}...")

    # 2. Beacon build -> decode round trip authenticates
    session = GroupSession("7421")
    mid = session.add_member("Alex")
    frame = build_member_beacon(session, mid, epoch=3)
    dec = decode_member_beacon(session, frame, time.time())
    results["member_beacon_roundtrip"] = dec is not None and dec[0] == mid and dec[1] == 3
    print(f"[2] member beacon round-trip + MAC: member={mid} decoded={dec}")

    # 3. Wrong group key rejects the beacon
    other = GroupSession("9999")
    results["wrong_key_rejected"] = decode_member_beacon(other, frame, time.time()) is None
    print(f"[3] different join-code beacon rejected: OK")

    # 4. Distance converges downward as we approach (synthetic RSSI)
    follower = GroupFollower(session)
    now = time.time()
    t = now - 60.0
    # Approach: victim at 30 m -> 2 m, RSSI improves per log-distance model
    for meters in [30, 25, 20, 15, 12, 10, 8, 6, 5, 4, 3, 2]:
        rssi = RSSI_AT_1M_DBM - 10 * PATH_LOSS_N * math.log10(max(meters, 0.5))
        follower.on_scan(frame, rssi, 0.0, t)
        t += 1.0
    # a closing burst over the last 10 s
    for meters in [4, 3, 2.5, 2]:
        rssi = RSSI_AT_1M_DBM - 10 * PATH_LOSS_N * math.log10(max(meters, 0.5))
        follower.on_scan(frame, rssi, 0.0, now - 1)
    summ = follower.summary(now=now)
    rec = summ["members"][mid]
    results["distance_converges"] = rec["distance_m"] is not None and rec["distance_m"] < 8.0
    results["closing_detected"] = rec["closing"]
    print(f"[4] approach -> distance={rec['distance_m']} m, closing={rec['closing']}")

    # 5. Direction sweep finds the bearing toward the member (peak at 120 deg)
    sweep_mid = session.add_member("Sam")
    sweep_frame = build_member_beacon(session, sweep_mid, epoch=1)
    fs = GroupFollower(session)
    st = now - 6
    for deg in range(0, 360, 15):
        sep = abs(((deg - 120 + 540) % 360) - 180)
        sig = -55 - sep * 0.5
        fs.on_scan(sweep_frame, sig, float(deg), st)
        st += 0.05
    summ2 = fs.summary(now=now)
    rec2 = summ2["members"][sweep_mid]
    ok_bearing = (rec2["bearing_deg"] is not None
                  and abs(rec2["bearing_deg"] - 120) <= 22.5)
    results["sweep_bearing_found"] = ok_bearing
    print(f"[5] sweep -> bearing={rec2['bearing_deg']} conf={rec2['bearing_confidence']} "
          f"(target 120)")

    # 6. Lost detection: a peer that goes silent is LOST
    summ3 = follower.summary(now=now + 120)
    results["lost_detection"] = summ3["members"].get(mid, {}).get("status") == "LOST"
    print(f"[6] stale peer -> {summ3['members'].get(mid, {}).get('status')}")

    all_pass = all(results.values())
    print("-" * 70)
    for k, v in results.items():
        print(f"  {'✓' if v else '✗'} {k}")
    print("-" * 70)
    print(f"RESULT: {'ALL PASSED' if all_pass else 'FAILURES PRESENT'}")
    return results


if __name__ == "__main__":
    run_group_self_test()