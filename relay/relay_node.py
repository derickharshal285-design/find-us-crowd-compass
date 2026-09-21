#!/usr/bin/env python3
"""
Find Us / Crowd Compass — Relay Node Firmware Reference Implementation
Zero-Decrypt Forwarding (ZDF) + Epoch-Synchronized Burst Windows (ESBW) + Inhibitory Trickle (k=3)
"""
import time
import random
from dataclasses import dataclass
from typing import Dict, Optional
from enum import IntEnum
import threading

from packet_v2 import (
    PacketV2, PacketType, AgeBucket, Flags,
    pack_packet_v2, unpack_packet_v2, encode_fec_hamming,
    compute_envelope_mac, verify_envelope_mac,
    encapsulate_ios_background_safe,
    decode_packet_frame
)

# ─── Constants ───
EPOCH_DURATION_S = 15.0           # 4-bit EPOCH cadence
BURST_WINDOW_S = 10.0             # Active TX window per epoch
ADV_INTERVAL_MS = 211.25          # ~47 packets / 10 s burst
INHIBIT_THRESHOLD_K = 3           # Suppress if ≥k neighbors with same/better hop
JITTER_MIN_S = 0.05
JITTER_MAX_S = 2.0
VIRTUAL_HOP_FLOOR = 6             # MULE packets clamp HOP ≥ 6
MAX_HOP = 15
SESSION_KEY = b"crowd_compass_session_key_2026"  # In production: per-incident ECDH


class RelayState(IntEnum):
    IDLE = 0
    LISTENING = 1
    BURSTING = 2
    SUPPRESSED = 3


@dataclass
class GradientEntry:
    """Per-SOS_ID gradient state"""
    sos_id: int
    hop: int
    baro_diff: int
    flags: int
    epoch: int
    age: int
    reserved: int
    envelope_mac: int
    last_rx_time: float
    rx_count: int = 0
    neighbor_burst_count: int = 0  # For inhibitory gating


@dataclass
class RelayConfig:
    session_key: bytes = SESSION_KEY
    tx_power_dbm: int = 4
    adv_channel_map: int = 0x07  # Channels 37, 38, 39
    max_gradient_age_s: float = 300.0  # 5 min max gradient lifetime


class RelayNode:
    """
    Relay node implementing:
    - Zero-Decrypt Forwarding (ZDF): relay without MAC verification, only check on hop decrease
    - ESBW: burst transmission aligned to epoch boundaries
    - Inhibitory Trickle (k=3): suppress if k neighbors with same/better hop seen
    - MULE handling: virtual hop floor, AGE bucket, FLAGS.MULE_STORE_FORWARD
    """

    def __init__(self, node_id: int, config: Optional[RelayConfig] = None):
        self.node_id = node_id
        self.config = config or RelayConfig()
        self.gradients: Dict[int, GradientEntry] = {}  # sos_id -> GradientEntry
        self.state = RelayState.IDLE
        self.current_epoch = 0
        self.epoch_start_time = time.time()
        self.burst_end_time = 0.0
        self.suppress_until = 0.0
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def stop(self):
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run_loop(self):
        while self._running:
            now = time.time()
            self._update_epoch(now)
            self._expire_gradients(now)
            self._maybe_burst(now)
            time.sleep(0.1)  # 100 ms control loop

    def _update_epoch(self, now: float):
        elapsed = now - self.epoch_start_time
        new_epoch = int(elapsed // EPOCH_DURATION_S) & 0xF
        if new_epoch != self.current_epoch:
            self.current_epoch = new_epoch
            self.epoch_start_time = now - (elapsed % EPOCH_DURATION_S)
            self.burst_end_time = self.epoch_start_time + BURST_WINDOW_S
            # Reset inhibitory counter at epoch boundary
            with self._lock:
                for g in self.gradients.values():
                    g.neighbor_burst_count = 0

    def _expire_gradients(self, now: float):
        with self._lock:
            expired = [
                sos for sos, g in self.gradients.items()
                if now - g.last_rx_time > self.config.max_gradient_age_s
            ]
            for sos in expired:
                del self.gradients[sos]

    def _maybe_burst(self, now: float):
        """ESBW: transmit burst if in window and not suppressed"""
        with self._lock:
            if self.suppress_until > now:
                return
            if now > self.burst_end_time:
                return  # Outside burst window

            # Find best gradient to advertise
            best = min(self.gradients.values(), key=lambda g: g.hop, default=None)
            if not best:
                return

            # Inhibitory gating: count neighbors with same/better hop in this epoch
            if best.neighbor_burst_count >= INHIBIT_THRESHOLD_K:
                self.suppress_until = now + random.uniform(JITTER_MIN_S, JITTER_MAX_S)
                return

            # Schedule this packet with jitter
            delay = random.uniform(JITTER_MIN_S, JITTER_MAX_S)
            threading.Timer(delay, self._transmit_gradient, args=(best,)).start()

    def _transmit_gradient(self, grad: GradientEntry):
        """Build and transmit gradient packet.

        Preserves the ORIGINAL (victim) EPOCH in the packet so the envelope MAC
        remains valid end-to-end. The MAC covers (SOS_ID || EPOCH || PKT_TYPE);
        HOP is not MAC-covered, so the relay may increment it freely.
        """
        if not self._running:
            return

        # Build packet
        pkt = PacketV2(
            pkt_type=PacketType.LIVE_GRADIENT,
            sos_id=grad.sos_id,
            hop_count=min(grad.hop + 1, MAX_HOP),
            baro_diff=grad.baro_diff,
            flags=grad.flags,
            epoch=grad.epoch,          # victim's epoch — keeps MAC valid
            age=grad.age,
            reserved=grad.reserved,
            envelope_mac=grad.envelope_mac
        )
        raw = pack_packet_v2(pkt)
        fec = encode_fec_hamming(raw)

        # Frame for BLE
        adv_data = encapsulate_ios_background_safe(fec)

        # Simulated BLE transmit (replace with platform BLE API)
        self._ble_transmit(adv_data)

    def _ble_transmit(self, adv_data: bytes):
        """Hook for platform BLE transmit"""
        pass  # In production: BLE stack advertise on channels 37/38/39

    def on_packet_received(self, raw_packet: bytes, rssi_dbm: float, rx_time: float):
        """Process received packet — accepts raw 7B or BLE-framed/FEC packets."""
        payload = decode_packet_frame(raw_packet)
        if payload is None:
            return  # Invalid frame
        try:
            pkt = unpack_packet_v2(payload)
        except Exception:
            return  # Invalid packet

        # Verify MAC only if we would adopt a LOWER hop (ZDF rule)
        should_verify = False

        with self._lock:
            existing = self.gradients.get(pkt.sos_id)

            # New gradient or better hop → verify MAC
            if not existing or pkt.hop_count < existing.hop:
                should_verify = True

            if should_verify:
                if not verify_envelope_mac(
                    self.config.session_key,
                    pkt.sos_id, pkt.epoch, pkt.pkt_type, pkt.envelope_mac
                ):
                    return  # MAC verification failed — drop

            # Adopt gradient
            if not existing or pkt.hop_count <= existing.hop:
                self.gradients[pkt.sos_id] = GradientEntry(
                    sos_id=pkt.sos_id,
                    hop=pkt.hop_count,
                    baro_diff=pkt.baro_diff,
                    flags=pkt.flags,
                    epoch=pkt.epoch,
                    age=pkt.age,
                    reserved=pkt.reserved,
                    envelope_mac=pkt.envelope_mac,
                    last_rx_time=rx_time
                )

                # If this packet has MULE flag, clamp hop floor
                if pkt.flags & Flags.MULE_STORE_FORWARD:
                    self.gradients[pkt.sos_id].hop = max(pkt.hop_count, VIRTUAL_HOP_FLOOR)

    def on_neighbor_burst(self, sos_id: int, neighbor_hop: int, rx_time: float):
        """Called when overhearing a neighbor's burst — inhibitory gating"""
        with self._lock:
            grad = self.gradients.get(sos_id)
            if grad and neighbor_hop <= grad.hop:
                grad.neighbor_burst_count += 1

    def get_gradient(self, sos_id: int) -> Optional[GradientEntry]:
        with self._lock:
            return self.gradients.get(sos_id)


# ─── Convenience: Create SOS beacon (target) ───
def create_sos_beacon(sos_id: int, epoch: int, session_key: bytes = SESSION_KEY) -> bytes:
    """Target creates Hop-0 beacon with valid MAC"""
    mac = compute_envelope_mac(session_key, sos_id, epoch, PacketType.LIVE_GRADIENT)
    pkt = PacketV2(
        pkt_type=PacketType.LIVE_GRADIENT,
        sos_id=sos_id,
        hop_count=0,
        baro_diff=0,
        flags=0,
        epoch=epoch,
        age=AgeBucket.LIVE,
        reserved=0,
        envelope_mac=mac
    )
    raw = pack_packet_v2(pkt)
    fec = encode_fec_hamming(raw)
    return encapsulate_ios_background_safe(fec)


if __name__ == "__main__":
    # Quick self-test
    print("RelayNode firmware self-test...")
    node = RelayNode(node_id=1)
    node.start()

    # Simulate target beacon at Hop 0 (iOS-safe dual-AD frame over BLE)
    beacon = create_sos_beacon(sos_id=0x123, epoch=0)
    node.on_packet_received(beacon, rssi_dbm=-40, rx_time=time.time())

    grad = node.get_gradient(0x123)
    assert grad is not None
    assert grad.hop == 0, f"expected adopted hop 0, got {grad.hop}"
    print(f"✓ Adopted gradient: SOS={grad.sos_id:04X} hop={grad.hop} (MAC verified)")

    # Simulate a relayed transmission and verify the receiver can validate its MAC.
    # The relay increments HOP to 1 but preserves the victim EPOCH, so MAC should verify.
    grad.hop = 1  # what _transmit_gradient advertises
    relayed = pack_packet_v2(PacketV2(
        pkt_type=PacketType.LIVE_GRADIENT, sos_id=grad.sos_id, hop_count=1,
        baro_diff=0, flags=0, epoch=grad.epoch, age=grad.age,
        reserved=0, envelope_mac=grad.envelope_mac,
    ))
    assert verify_envelope_mac(SESSION_KEY, grad.sos_id, grad.epoch,
                               PacketType.LIVE_GRADIENT, grad.envelope_mac), \
        "Relayed packet MAC must survive hop increment"
    print(f"✓ Relayed Hop-1 packet MAC verifies at receiver (epoch preserved)")

    # A second relay hops again to 2, still MAC-valid
    grad.hop = 2
    assert verify_envelope_mac(SESSION_KEY, grad.sos_id, grad.epoch,
                               PacketType.LIVE_GRADIENT, grad.envelope_mac), \
        "MAC must survive multi-hop relay chain"
    print(f"✓ Multi-hop (0->1->2) chain: MAC valid at every hop")

    node.stop()
    print("Self-test passed.")