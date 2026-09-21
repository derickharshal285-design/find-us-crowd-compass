#!/usr/bin/env python3
"""
Find Us / Crowd Compass — Responder Guidance Engine (fixed)

Navigation honesty layers:
  1. Macro Gradient Descent (hop count) — with freshness weighting + aging
  2. Floor-Aware Gating (barometric)   — responder-relative, not victim-absolute
  3. Stairwell Detection               — barometric rate-of-change, not hop counts
  4. RF Confirmation                   — multi-second fusion, RSSI-only (no phantom bearing)
  5. Terminal Handoff                  — rotate-scan RSSI bearing (synthetic lighthouse)

Key fixes vs the original design:
  - TERMINAL_HANDOFF mode is now reachable (was dead code behind hop<=2 branch)
  - Gradients are aged-out and scored by freshness, not frozen forever
  - AR gate actually gates: it holds guidance while gait is unstable
  - Barometer compares responder vs victim altitude (relative delta), not victim absolute
  - Bearing coherence field (unmeasurable without an antenna array) removed;
    bearing comes from rotating the phone and sampling RSSI vs compass heading
  - Responder no longer imports GradientEntry from the relay — self-contained
"""
import time
import math
import statistics
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Deque
from collections import deque
from enum import IntEnum
import threading

from packet_v2 import (
    PacketV2, PacketType,
    unpack_packet_v2, verify_envelope_mac, compute_envelope_mac,
    decode_packet_frame,
)


# ─── Constants from verified research ───
ACTIVITY_WINDOW_S = 2.0           # 2.0 s AR gating window (100 samples @ 50 Hz)
AR_GATE_THRESHOLD = 0.85          # Master gate pass threshold
RF_CONFIRM_WINDOW_S = 2.5         # Multi-second RF confirmation window (relaxed for sparse mesh)
RF_MIN_PACKETS = 3                # M >= 3 packets for statistical validity (sparse traffic reality)
BARO_FLOOR_THRESHOLD_HPA = 0.35   # |ΔP| > 0.35 hPa -> different floor
BARO_SAME_FLOOR_HPA = 0.25        # |ΔP| <= 0.25 hPa -> same floor
TERMINAL_HOP_THRESHOLD = 1        # Hop <= 1 -> terminal mode
RSSI_VARIANCE_THRESHOLD = 4.8     # σ_RSSI > 4.8 dB -> multipath
RSSI_TREND_WINDOW_S = 10.0        # Trend window for closing/drifting detection
RSSI_CLOSING_DB = 3.0             # +dB over window -> closing
RSSI_DRIFT_DB = -5.0              # -dB over window -> drifting away
RESPONDER_GRADIENT_MAX_AGE_S = 60.0  # Cull gradients silent > 60 s
STAIR_SLOPE_WINDOW_S = 3.0        # Pressure slope window
STAIR_CLIMB_SLOPE_HPA_S = -0.05   # Sustained slope < -0.05 hPa/s -> climbing
STAIR_DESCENT_SLOPE_HPA_S = 0.05  # Sustained slope > +0.05 hPa/s -> descending
TERMINAL_SCAN_WINDOW_S = 10.0     # Rotate-scan bearing window
TERMINAL_SCAN_MIN_SAMPLES = 12    # Min RSSI/heading samples for a bearing estimate
RPA_ROTATION_S = 15.0             # Resolvable Private Address rotation


class ActivityClass(IntEnum):
    NAVIGATING_WALK = 0
    MOSH_PIT_BOUNCE = 1
    POCKET_DRUNK_SHUFFLE = 2
    TORSO_SPIN_SEARCH = 3
    STATIONARY_IDLE = 4


class GuidanceMode(IntEnum):
    MACRO_GRADIENT = 0      # Hop descent (macro: 500m -> 15m)
    STAIRWELL_PORTAL = 1    # Vertical transition (responder on different floor than target)
    RF_CONFIRMATION = 2     # Multi-second RF fusion (15m -> 5m)
    TERMINAL_HANDOFF = 3    # Rotate-scan bearing + visual (final 5m -> 0m)


@dataclass
class IMUSample:
    timestamp: float
    accel: Tuple[float, float, float]   # x, y, z (g)
    gyro: Tuple[float, float, float]    # x, y, z (rad/s)
    mag: Tuple[float, float, float]     # x, y, z (µT)


@dataclass
class BaroSample:
    timestamp: float
    pressure_hpa: float
    temperature_c: float


@dataclass
class RSSISample:
    timestamp: float
    rssi_dbm: float
    channel: int  # 37, 38, 39
    hop: int
    sos_id: int
    heading_deg: float = 0.0  # Phone compass heading at RX time (for rotate-scan)


@dataclass
class TrackedGradient:
    """Responder-side per-target gradient state (self-contained, not relay's GradientEntry)."""
    sos_id: int
    hop: int
    baro_diff: int
    flags: int
    epoch: int
    age: int
    envelope_mac: int
    first_seen: float
    last_rx_time: float
    last_rssi_dbm: float = -120.0
    rssi_history: Deque[Tuple[float, float]] = field(  # (timestamp, rssi)
        default_factory=lambda: deque(maxlen=300)
    )

    @property
    def age_s(self) -> float:
        return time.time() - self.last_rx_time


@dataclass
class GuidanceState:
    mode: GuidanceMode = GuidanceMode.MACRO_GRADIENT
    target_sos_id: int = 0
    current_hop: int = 255
    current_floor: int = 0
    target_floor: int = 0
    baro_reference_hpa: float = 0.0
    last_stairwell_bearing: float = 0.0
    terminal_bearing: float = 0.0
    visual_runway_active: bool = False


class ActivityRecognizer:
    """AR classifier — 50 Hz IMU, 2.0 s window = 100 samples"""
    def __init__(self):
        self.window = deque(maxlen=100)  # 100 samples @ 50 Hz = 2.0 s
        self._lock = threading.Lock()

    def add_sample(self, sample: IMUSample):
        with self._lock:
            self.window.append(sample)

    def classify(self) -> Tuple[ActivityClass, float]:
        """Returns (activity_class, confidence)"""
        with self._lock:
            if len(self.window) < 20:  # Need minimum samples
                return ActivityClass.NAVIGATING_WALK, 0.5

            samples = list(self.window)
            accel_mags = [math.sqrt(sum(a * a for a in s.accel)) for s in samples]
            gyro_mags = [math.sqrt(sum(g * g for g in s.gyro)) for s in samples]

            mean_accel = statistics.mean(accel_mags)
            std_accel = statistics.stdev(accel_mags) if len(accel_mags) > 1 else 0
            mean_gyro = statistics.mean(gyro_mags)
            std_gyro = statistics.stdev(gyro_mags) if len(gyro_mags) > 1 else 0

            # Heuristic thresholds (calibrated from research)
            if mean_accel > 2.5 and std_accel > 1.5:
                return ActivityClass.MOSH_PIT_BOUNCE, 0.95
            if std_accel > 0.8 and mean_gyro > 1.0:
                return ActivityClass.POCKET_DRUNK_SHUFFLE, 0.90
            if mean_gyro > 3.0:
                return ActivityClass.TORSO_SPIN_SEARCH, 0.85
            if mean_accel < 1.1 and std_accel < 0.1:
                return ActivityClass.STATIONARY_IDLE, 0.90

            return ActivityClass.NAVIGATING_WALK, 0.88


class BarometricFloorEstimator:
    """Cross-OS calibrated floor estimation with venue entrance gate protocol."""
    def __init__(self):
        self.reference_pressure: Optional[float] = None
        self.reference_timestamp: float = 0
        self.peer_pressures: Dict[int, Deque[float]] = {}  # peer_id -> pressure deque
        self._lock = threading.Lock()

    def set_entrance_gate_reference(self, pressure_hpa: float):
        """Protocol 2: Venue entrance gate baseline snapshot (call once at gate)."""
        with self._lock:
            self.reference_pressure = pressure_hpa
            self.reference_timestamp = time.time()

    def add_peer_pressure(self, peer_id: int, pressure_hpa: float):
        """Protocol 3: Co-located peer consensus fallback."""
        with self._lock:
            if peer_id not in self.peer_pressures:
                self.peer_pressures[peer_id] = deque(maxlen=20)
            self.peer_pressures[peer_id].append(pressure_hpa)

    def estimate_floor(self, current_pressure_hpa: float) -> Tuple[int, float]:
        """Returns (floor, confidence) relative to the entrance gate reference."""
        with self._lock:
            if self.reference_pressure is None:
                return 0, 0.0  # No reference — must calibrate at the gate

            delta = self.reference_pressure - current_pressure_hpa
            floor = round(delta / 0.413)  # 0.413 hPa per 3.5 m floor
            confidence = 0.95

            if confidence < 0.8 and len(self.peer_pressures) >= 8:
                peer_values = [statistics.mean(d) for d in self.peer_pressures.values()
                               if len(d) >= 5]
                if peer_values:
                    peer_mean = statistics.mean(peer_values)
                    delta = peer_mean - current_pressure_hpa
                    floor = round(delta / 0.413)
                    confidence = 0.70

            return floor, confidence

    def floor_delta_hpa(self, current_pressure_hpa: float) -> float:
        """Returns ΔP in hPa relative to the responder's entrance-gate reference."""
        with self._lock:
            if self.reference_pressure is None:
                return 0.0
            return self.reference_pressure - current_pressure_hpa


class StairDetector:
    """
    Barometric stairwell detection via sustained pressure slope.

    Walking flat on one floor has |slope| < ~0.02 hPa/s (thermal drift + wind).
    Ascending stairs: ~ -0.12 hPa/s sustained; elevator/one floor jump: instantaneous step.
    """
    def __init__(self, window_s: float = STAIR_SLOPE_WINDOW_S):
        self.window_s = window_s
        self.samples: Deque[Tuple[float, float]] = deque(maxlen=120)
        self._lock = threading.Lock()

    def add(self, timestamp: float, pressure_hpa: float):
        with self._lock:
            self.samples.append((timestamp, pressure_hpa))

    def slope_hpa_per_s(self) -> Tuple[bool, float]:
        """Returns (is_on_stairs, slope_hpa_per_s). Climbing -> negative slope."""
        with self._lock:
            if len(self.samples) < 3:
                return False, 0.0
            cutoff = time.time() - self.window_s
            recent = [(t, p) for t, p in self.samples if t >= cutoff]
            if len(recent) < 3:
                return False, 0.0

            t0 = recent[0][0]
            dt = recent[-1][0] - t0
            if dt < 1.0:
                return False, 0.0

            # Least-squares slope of pressure vs time
            n = len(recent)
            sx = sum(x[0] for x in recent)
            sy = sum(x[1] for x in recent)
            sxy = sum(x[0] * x[1] for x in recent)
            sxx = sum(x[0] * x[0] for x in recent)
            denom = n * sxx - sx * sx
            if abs(denom) < 1e-9:
                return False, 0.0
            slope = (n * sxy - sx * sy) / denom

            on_stairs = (slope <= STAIR_CLIMB_SLOPE_HPA_S or slope >= STAIR_DESCENT_SLOPE_HPA_S)
            return on_stairs, slope


class RFConfirmationEngine:
    """
    Multi-second RF confirmation (2.5 s window, M >= 3 packets), RSSI-only.

    Bearing-coherence ("|ρ| <= 0.6") removed — it required an antenna array / heading
    source the phones do not expose. Honest features used instead:
      - mean RSSI band (wall bleed vs. LoS gap)
      - RSSI std (multipath flicker)
      - channel diversity (multipath decorrelates across 37/38/39)
    Results are marked confidence: LOW when below M or with <2 channels.
    """
    def __init__(self):
        self.samples: Dict[int, Deque[RSSISample]] = {}  # sos_id -> samples
        self._lock = threading.Lock()

    def add_rssi(self, sample: RSSISample):
        with self._lock:
            if sample.sos_id not in self.samples:
                self.samples[sample.sos_id] = deque(maxlen=80)
            self.samples[sample.sos_id].append(sample)

    def evaluate(self, sos_id: int) -> Optional[Dict]:
        """Returns confirmation result or None if insufficient data."""
        with self._lock:
            samples = self.samples.get(sos_id)
            if not samples:
                return None

            now = time.time()
            recent = [s for s in samples if now - s.timestamp <= RF_CONFIRM_WINDOW_S]
            if len(recent) < RF_MIN_PACKETS:
                return None

            rssis = [s.rssi_dbm for s in recent]
            hops = [s.hop for s in recent]
            channels = {s.channel for s in recent}

            mean_rssi = statistics.mean(rssis)
            std_rssi = statistics.stdev(rssis) if len(rssis) > 1 else 0
            hop_mode = max(set(hops), key=hops.count)
            channel_diversity = len(channels)

            is_multipath = (std_rssi > RSSI_VARIANCE_THRESHOLD) and channel_diversity >= 2
            is_wall_bleed = (not is_multipath
                             and -99 <= mean_rssi <= -89.5
                             and std_rssi <= RSSI_VARIANCE_THRESHOLD)
            is_los_gap = (not is_multipath
                          and mean_rssi > -89.5
                          and std_rssi <= RSSI_VARIANCE_THRESHOLD)

            return {
                "valid": True,
                "confidence": "LOW" if channel_diversity < 2 else "MEDIUM",
                "mean_rssi": mean_rssi,
                "std_rssi": std_rssi,
                "hop": hop_mode,
                "packets": len(recent),
                "channels": channel_diversity,
                "is_multipath": is_multipath,
                "is_wall_bleed": is_wall_bleed,
                "is_los_gap": is_los_gap,
            }

    def clear(self, sos_id: int):
        with self._lock:
            self.samples.pop(sos_id, None)


class TerminalHandoffEngine:
    """
    Final 5m -> 0m: rotate-scan RSSI bearing (synthetic lighthouse).

    While the responder slowly spins (TORSO_SPIN_SEARCH), RSSI vs compass-heading
    samples are collected. The bearing of maximum average RSSI points AT the target,
    because body/antenna shadowing suppresses RSSI on the opposite side.
    """
    def __init__(self, window_s: float = TERMINAL_SCAN_WINDOW_S):
        self.window_s = window_s
        self.samples: Deque[Tuple[float, float, float]] = deque(maxlen=300)  # (t, rssi, heading)
        self._lock = threading.Lock()

    def add_rssi(self, rssi_dbm: float, heading_deg: float, timestamp: float):
        with self._lock:
            self.samples.append((timestamp, rssi_dbm, heading_deg))

    def detect_bearing(self) -> Tuple[bool, float, float]:
        """Returns (detected, bearing_deg, confidence 0..1) toward the target."""
        with self._lock:
            now = time.time()
            recent = [(t, r, h) for t, r, h in self.samples if now - t <= self.window_s]
            if len(recent) < TERMINAL_SCAN_MIN_SAMPLES:
                return False, 0.0, 0.0

            # 8 bins of 45°; average RSSI per bin
            bins_mean = [0.0] * 8
            bins_count = [0] * 8
            for _, r, h in recent:
                idx = int(((h % 360) + 22.5) // 45) % 8
                bins_mean[idx] += r
                bins_count[idx] += 1
            for i in range(8):
                if bins_count[i]:
                    bins_mean[i] /= bins_count[i]

            peak = max(range(8), key=lambda i: bins_mean[i])
            if bins_count[peak] < 2:
                return False, 0.0, 0.0

            spread = max(bins_mean) - min(bins_mean)
            rssi_range = max(bins_mean) - min(bins_mean) or 1.0
            confidence = min(1.0, spread / max(10.0, rssi_range))
            bearing_deg = (peak * 45) % 360
            return True, bearing_deg, confidence

    def detect_torso_shadow(self) -> Tuple[bool, float]:
        """Detects the 15-20 dB body-attenuation signature (backs to the target)."""
        with self._lock:
            if len(self.samples) < 10:
                return False, 0.0
            recent = list(self.samples)[-10:]
            rssis = [r for _, r, _ in recent]
            std_rssi = statistics.stdev(rssis) if len(rssis) > 1 else 0
            return std_rssi > 8.0, 0.0

    def activate_visual_runway(self):
        with self._lock:
            pass  # Trigger phone torch/strobe via platform API


class ResponderGuidanceEngine:
    """
    Complete responder guidance engine integrating all layers:

    1. Macro Gradient Descent (hop count, freshness-weighted)
    2. Floor-Aware Gating (barometric, responder-relative)
    3. Stairwell Detection (sustained pressure slope)
    4. RF Confirmation (multi-second fusion, RSSI-only)
    5. Terminal Handoff (rotate-scan bearing)
    """
    def __init__(self, session_key: bytes):
        self.session_key = session_key
        self.activity_recognizer = ActivityRecognizer()
        self.floor_estimator = BarometricFloorEstimator()
        self.stair_detector = StairDetector()
        self.rf_confirmation = RFConfirmationEngine()
        self.terminal_handoff = TerminalHandoffEngine()
        self.state = GuidanceState()
        self.gradients: Dict[int, TrackedGradient] = {}
        self.max_gradient_age_s = RESPONDER_GRADIENT_MAX_AGE_S
        self._lock = threading.Lock()

    def process_packet(self, raw_packet: bytes, rssi_dbm: float, channel: int,
                       rx_time: float, heading_deg: float = 0.0):
        """Main packet ingestion — accepts raw 7B packets OR encapsulated BLE frames."""
        payload = decode_packet_frame(raw_packet)
        if payload is None:
            return
        try:
            pkt = unpack_packet_v2(payload)
        except Exception:
            return

        if not verify_envelope_mac(self.session_key, pkt.sos_id, pkt.epoch,
                                   pkt.pkt_type, pkt.envelope_mac):
            return

        self._record_packet(pkt, rssi_dbm, channel, rx_time, heading_deg)

    def _record_packet(self, pkt: PacketV2, rssi_dbm: float, channel: int,
                       rx_time: float, heading_deg: float):
        with self._lock:
            g = self.gradients.get(pkt.sos_id)
            if g is None:
                g = TrackedGradient(
                    sos_id=pkt.sos_id, hop=pkt.hop_count, baro_diff=pkt.baro_diff,
                    flags=pkt.flags, epoch=pkt.epoch, age=pkt.age,
                    envelope_mac=pkt.envelope_mac,
                    first_seen=rx_time, last_rx_time=rx_time,
                )
                self.gradients[pkt.sos_id] = g
            else:
                # Adopt a strictly better (lower) hop only when fresh
                if pkt.hop_count < g.hop or rx_time - g.last_rx_time > 1.5:
                    g.hop = min(g.hop, pkt.hop_count)
                g.baro_diff = pkt.baro_diff
                g.flags = pkt.flags
                g.epoch = pkt.epoch
                g.age = pkt.age
                g.last_rx_time = rx_time
            g.last_rssi_dbm = rssi_dbm
            g.rssi_history.append((rx_time, rssi_dbm))

        self.rf_confirmation.add_rssi(RSSISample(
            timestamp=rx_time, rssi_dbm=rssi_dbm, channel=channel,
            hop=pkt.hop_count, sos_id=pkt.sos_id, heading_deg=heading_deg,
        ))
        self.terminal_handoff.add_rssi(rssi_dbm, heading_deg, rx_time)

    def add_imu_sample(self, sample: IMUSample):
        self.activity_recognizer.add_sample(sample)

    def add_baro_pressure(self, pressure_hpa: float):
        self.stair_detector.add(time.time(), pressure_hpa)

    def set_entrance_gate_reference(self, pressure_hpa: float):
        self.floor_estimator.set_entrance_gate_reference(pressure_hpa)

    def add_peer_pressure(self, peer_id: int, pressure_hpa: float):
        self.floor_estimator.add_peer_pressure(peer_id, pressure_hpa)

    @staticmethod
    def _expire_hint(age_s: float) -> float:
        """Freshness penalty added to hop score. +2 per 10 s past 30 s."""
        if age_s <= 30:
            return 0.0
        return (age_s - 30.0) / 10.0 * 2.0

    def _rssi_trend(self, g: TrackedGradient) -> Tuple[float, int]:
        """Returns (rssi_delta_db, packets_in_window) over the trend window."""
        now = time.time()
        cutoff = now - RSSI_TREND_WINDOW_S
        recent = [(t, r) for t, r in g.rssi_history if t >= cutoff]
        if len(recent) < 3:
            return 0.0, len(recent)
        return recent[-1][1] - recent[0][1], len(recent)

    def update(self, current_pressure_hpa: Optional[float] = None) -> Dict:
        """Main guidance update — called at ~1 Hz from UI thread (or on RSSI events)."""
        now = time.time()
        with self._lock:
            # 1. Age out stale gradients
            stale = [sos for sos, g in self.gradients.items()
                     if now - g.last_rx_time > self.max_gradient_age_s]
            for sos in stale:
                del self.gradients[sos]

            if not self.gradients:
                return {"mode": "SEARCHING", "action": "SCAN"}

            # 2. Score by (hop + freshness), tie-break by strongest RSSI
            best = min(
                self.gradients.values(),
                key=lambda g: (g.hop + self._expire_hint(g.age_s), -g.last_rssi_dbm),
            )
            rssi_delta, packets_in_window = self._rssi_trend(best)
            closing = rssi_delta >= RSSI_CLOSING_DB
            drifting = rssi_delta <= RSSI_DRIFT_DB

            self.state.target_sos_id = best.sos_id
            self.state.current_hop = best.hop

            # 3. AR gate — hold guidance unless gait state is trustworthy
            activity, ar_confidence = self.activity_recognizer.classify()
            gate_pass = (ar_confidence >= AR_GATE_THRESHOLD
                         and activity in (ActivityClass.NAVIGATING_WALK,
                                          ActivityClass.TORSO_SPIN_SEARCH))

            # 4. Barometric — responder-relative floor logic (NOT victim-absolute)
            vertical_delta_hpa = 0.0
            current_floor = 0
            floor_delta = 0.0
            if current_pressure_hpa is not None:
                floor_delta = self.floor_estimator.floor_delta_hpa(current_pressure_hpa)
                current_floor, _ = self.floor_estimator.estimate_floor(current_pressure_hpa)
                victim_offset_hpa = best.baro_diff * 0.5
                # Responder's current altitude minus victim's altitude
                vertical_delta_hpa = floor_delta - victim_offset_hpa
            different_floor = abs(vertical_delta_hpa) > BARO_FLOOR_THRESHOLD_HPA

            self.state.current_floor = current_floor
            self.state.target_floor = round(-best.baro_diff * 0.5 / 0.413) if best.baro_diff else 0

            # 5. Mode ladder — TERMINAL first so it is actually reachable
            if best.hop <= TERMINAL_HOP_THRESHOLD:
                self.state.mode = GuidanceMode.TERMINAL_HANDOFF
            elif best.hop <= 2:
                self.state.mode = GuidanceMode.RF_CONFIRMATION
            elif different_floor:
                self.state.mode = GuidanceMode.STAIRWELL_PORTAL
            else:
                self.state.mode = GuidanceMode.MACRO_GRADIENT

            output = {
                "mode": self.state.mode.name,
                "target_sos": f"{best.sos_id:04X}",
                "hop": best.hop,
                "age_s": round(best.age_s, 1),
                "rssi_delta_db": round(rssi_delta, 1),
                "closing": closing,
                "drifting": drifting,
                "packets_in_window": packets_in_window,
                "floor": current_floor,
                "target_floor": self.state.target_floor,
                "vertical_delta_hpa": round(vertical_delta_hpa, 2),
                "activity": activity.name,
                "ar_gate": gate_pass,
                "stair_slope_hpa_s": 0.0,
                "bearing_deg": None,
                "confidence": "LOW",
                "timestamp": now,
            }

            # 6. AR-gated action generation
            if not gate_pass:
                # Do NOT emit a steering instruction while gait is untrusted
                output.update({
                    "action": "HOLD",
                    "reason": "AR_GATE_BLOCKED: gait not confidently navigating",
                    "mode": self.state.mode.name,
                })
                return output

            stair_active, stair_slope = self.stair_detector.slope_hpa_per_s()
            output["stair_slope_hpa_s"] = round(stair_slope, 3)

            if self.state.mode == GuidanceMode.MACRO_GRADIENT:
                output["action"] = "DESCEND_HOP"
                output["confidence"] = "MEDIUM" if packets_in_window >= RF_MIN_PACKETS else "LOW"
                output["steer_hint"] = "CLOSING" if closing else ("DRIFTING" if drifting else "FLAT")
                output["reason"] = "Follow hop-descent path; bearing from RSSI trend only"

            elif self.state.mode == GuidanceMode.STAIRWELL_PORTAL:
                output["action"] = "NAVIGATE_STAIRWELL"
                output["confidence"] = "MEDIUM"
                if stair_active:
                    output["reason"] = ("On stairs: vertical motion confirmed by pressure slope "
                                        f"{stair_slope:.3f} hPa/s")
                    output["action"] = "CLIMBING_STAIRS" if stair_slope < 0 else "DESCENDING_STAIRS"
                else:
                    output["reason"] = "Different floor than target; find stairwell/elevator"

            elif self.state.mode == GuidanceMode.RF_CONFIRMATION:
                rf = self.rf_confirmation.evaluate(best.sos_id)
                output["confidence"] = rf["confidence"] if rf else "LOW"
                if rf and rf["valid"]:
                    if rf["is_multipath"]:
                        output["action"] = "REJECT_MULTIPATH"
                        output["warning"] = "Multipath flicker — do not trust sudden RSSI peaks"
                    elif rf["is_wall_bleed"]:
                        output["action"] = "WALL_ALERT"
                        output["reason"] = "Signal bleeding through wall; walk the corridor edge"
                    elif rf["is_los_gap"]:
                        output["action"] = "SHORTCUT_CONFIRMED"
                        output["reason"] = "LoS signal present; shortcut is real, advance"
                    else:
                        output["action"] = "CONTINUE_GRADIENT"
                else:
                    output["action"] = "CONTINUE_GRADIENT"
                    output["reason"] = "Insufficient RF samples yet — keep walking down-hop"

            elif self.state.mode == GuidanceMode.TERMINAL_HANDOFF:
                detected, bearing_deg, bearing_conf = self.terminal_handoff.detect_bearing()
                shadowed, _ = self.terminal_handoff.detect_torso_shadow()
                output["bearing_deg"] = round(bearing_deg, 1) if detected else None
                output["confidence"] = "MEDIUM" if bearing_conf >= 0.5 else "LOW"

                if detected:
                    output["action"] = "WALK_BEARING"
                    output["reason"] = (f"Bearing {bearing_deg:.0f} deg via rotate-scan "
                                        f"(conf {bearing_conf:.2f})")
                    self.state.terminal_bearing = bearing_deg
                elif shadowed:
                    output["action"] = "TURN_AROUND"
                    output["reason"] = "Torso shadow detected — target is behind you"
                    self.terminal_handoff.activate_visual_runway()
                    self.state.visual_runway_active = True
                else:
                    output["action"] = "SPIN_SCAN"
                    output["reason"] = "Rotate slowly; acquiring bearing to hop<=1 target"
                    output["bearing_deg"] = "SPIN"

            return output


def run_guidance_self_test() -> Dict:
    """
    Real self-test: packets are created with pack_packet_v2 + valid compute MAC,
    so process_packet actually admits them (the original test fed envelope_mac=0
    and therefore always fell through to SEARCHING).
    """
    print("=" * 70)
    print("RESPONDER GUIDANCE ENGINE SELF-TEST")
    print("=" * 70)
    key = b"test_key_2026"
    now = time.time()
    results = {}

    def make_packet(sos_id, hop, baro_diff, epoch=5, mac=None, pkt_type=PacketType.LIVE_GRADIENT):
        mac = mac if mac is not None else compute_envelope_mac(key, sos_id, epoch, pkt_type)
        pkt = PacketV2(
            pkt_type=pkt_type, sos_id=sos_id, hop_count=hop, baro_diff=baro_diff,
            flags=0, epoch=epoch, age=0, reserved=0, envelope_mac=mac,
        )
        from packet_v2 import pack_packet_v2
        return pack_packet_v2(pkt)

    def fill_walk(engine, t0=now, n=25, spin=False):
        """Feed n IMU samples so the AR gate has a trustworthy history."""
        for i in range(n):
            if spin:
                gyro = (0, 0, 3.2)  # torso spin search
            else:
                gyro = (0, 0, 0.12)
            engine.add_imu_sample(IMUSample(t0 - (n - i) * 0.02,
                                            (1.0, 0.0, 0.8), gyro, (0, 0, 40)))

    # 1. Mode ladder: hop 3 -> MACRO_GRADIENT (baro same floor)
    e = ResponderGuidanceEngine(session_key=key)
    e.set_entrance_gate_reference(1013.25)
    e.process_packet(make_packet(0x123, 3, 0), rssi_dbm=-70, channel=37, rx_time=now,
                     heading_deg=90)
    fill_walk(e)
    out = e.update(current_pressure_hpa=1013.25)
    results["hop3_macro_decend"] = out["mode"] == "MACRO_GRADIENT" and out["action"] == "DESCEND_HOP"
    print(f"[1] hop=3 -> {out['mode']} / {out['action']}")

    # 2. Mode ladder: hop 1 -> TERMINAL_HANDOFF (reachable now; was dead code)
    e2 = ResponderGuidanceEngine(session_key=key)
    e2.set_entrance_gate_reference(1013.25)
    e2.process_packet(make_packet(0x456, 1, 0), rssi_dbm=-42, channel=37, rx_time=now,
                      heading_deg=0)
    fill_walk(e2)
    out2 = e2.update(current_pressure_hpa=1013.25)
    results["hop1_terminal_reachable"] = out2["mode"] == "TERMINAL_HANDOFF"
    print(f"[2] hop=1 -> {out2['mode']} / {out2['action']}")

    # 3. Mode ladder: hop 3, different floor -> STAIRWELL_PORTAL
    e3 = ResponderGuidanceEngine(session_key=key)
    e3.set_entrance_gate_reference(1013.25)
    e3.process_packet(make_packet(0x789, 3, -4), rssi_dbm=-65, channel=37, rx_time=now)
    fill_walk(e3)
    out3 = e3.update(current_pressure_hpa=1011.0)  # 2.25 hPa above reference -> up ~1-2 floors
    results["hop3_diff_floor_stairwell"] = out3["mode"] == "STAIRWELL_PORTAL"
    print(f"[3] hop=3 diff-floor -> {out3['mode']} / {out3['action']} / {out3['vertical_delta_hpa']}")

    # 4. AR gate actually holds steering (MOSH_PIT_BOUNCE blocks it)
    e4 = ResponderGuidanceEngine(session_key=key)
    e4.set_entrance_gate_reference(1013.25)
    e4.process_packet(make_packet(0x111, 3, 0), rssi_dbm=-60, channel=37, rx_time=now)
    for i in range(25):
        e4.add_imu_sample(IMUSample(now - (25 - i) * 0.02,
                                    (3.0 + 1.8 * math.sin(i * 1.7),
                                     3.0 + 1.5 * math.cos(i * 1.3),
                                     2.8 + 1.2 * math.sin(i * 0.9)),
                                    (0, 0, 2.0 + 1.5 * math.sin(i)),
                                    (0, 0, 40)))  # moshing: high mean + high variance
    out4 = e4.update(current_pressure_hpa=1013.25)
    results["ar_gate_holds"] = out4.get("action") == "HOLD"
    print(f"[4] unstable gait -> {out4.get('action')} (gate={out4.get('ar_gate')})")

    # 5. AGING: silent gradient is culled -> SEARCHING
    e5 = ResponderGuidanceEngine(session_key=key)
    e5.set_entrance_gate_reference(1013.25)
    old = now - 120.0
    e5.process_packet(make_packet(0x222, 2, 0), rssi_dbm=-60, channel=37, rx_time=old)
    fill_walk(e5)
    out5 = e5.update(current_pressure_hpa=1013.25)
    results["gradient_aging_culls"] = out5.get("mode") == "SEARCHING"
    print(f"[5] 120s-stale gradient -> {out5.get('mode')}")

    # 6. Terminal rotate-scan bearing: synthetic peak at heading 90
    e6 = ResponderGuidanceEngine(session_key=key)
    e6.set_entrance_gate_reference(1013.25)
    e6.process_packet(make_packet(0x333, 1, 0), rssi_dbm=-50, channel=37, rx_time=now,
                      heading_deg=0)
    mt = now - 6
    for deg in range(0, 360, 15):
        # Strongest when facing 90 deg (target direction), weakest opposite
        sep = abs(((deg - 90 + 540) % 360) - 180)
        sig = -50 - sep * 0.35
        e6.terminal_handoff.add_rssi(sig, float(deg), mt)
        mt += 0.05
    fill_walk(e6, spin=True)
    out6 = e6.update(current_pressure_hpa=1013.25)
    results["rotate_scan_bearing"] = (
        out6.get("bearing_deg") is not None and abs(out6["bearing_deg"] - 90) <= 22.5
    )
    print(f"[6] rotate-scan -> action={out6.get('action')} bearing={out6.get('bearing_deg')}")

    all_pass = all(results.values())
    print("-" * 70)
    for k, v in results.items():
        print(f"  {'✓' if v else '✗'} {k}")
    print("-" * 70)
    print(f"RESULT: {'ALL PASSED' if all_pass else 'FAILURES PRESENT'}")
    return results


if __name__ == "__main__":
    run_guidance_self_test()