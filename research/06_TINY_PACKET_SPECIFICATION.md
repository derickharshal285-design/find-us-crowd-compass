---
title: "06. Tiny Packet Wire Specification (28–32 Bit Protocol)"
tags:
  - project/find-us
  - protocol/spec
  - ble/packet-format
created: 2026-09-18
updated: 2026-09-18
---

# 06. Tiny Packet Wire Specification (28–32 Bit Protocol)

> [!NOTE]
> **Design Axiom:**
> In high-contention wireless environments, packet transmission success is inversely proportional to packet size. By stripping all floating-point coordinates, vector lists, and node identity strings, Crowd Compass packs the entire spatial state into a **compact 4-byte (32-bit) payload**.

---

## 1. Bit-Level Wire Format Layout

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          SOS_ID (12)          |  HOP (4)  | BARO_DIFF(6)|FLAGS| EPOCH |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### Field Definitions

| Field Name | Bit Width | Range / Format | Description |
| :--- | :---: | :---: | :--- |
| **`SOS_ID`** | 12 bits | `0x000` – `0xFFF` ($0\text{--}4095$) | Unique pseudorandom emergency session identifier. Ephemeral; generated at incident trigger. |
| **`HOP_COUNT`** | 4 bits | $0\text{--}15$ | Shortest path hop distance to origin. Origin sets $H = 0$. Relays increment $H \to H + 1$. Max 15 hops ($\sim 350\text{--}500\text{m}$). |
| **`BARO_DIFF`** | 6 bits | Signed int ($-32\text{ to } +31$) | Vertical pressure offset relative to target in units of $0.5\text{ hPa}$ ($\sim 4.2\text{ m}$ elevation per unit). Represents $\pm 15$ floors. |
| **`CONTROL_FLAGS`** | 6 bits | Bitmask flags | Operational command & status flags (see breakdown below). |
| **`EPOCH`** | 4 bits | $0\text{--}15$ modulo counter | Incremented every 5 seconds by `Hop 0`. Relays drop packets with stale epochs to prevent routing loops. |

**Total Payload Size: 32 bits (4.0 Bytes).**

---

## 2. Control Flags Bitmask (6 Bits)

```text
Bit 0: EMERGENCY_TYPE    (0 = Medical Incident, 1 = Security / Structural Threat)
Bit 1: VISUAL_RUNWAY     (1 = Activate Screen Strobe & Torch on Hop 1/Hop 0 devices)
Bit 2: SEVERE_URGENCY    (1 = Patient Unconscious / Non-Responsive)
Bit 3: ACK_RECEIVED      (1 = First responder has acknowledged and is actively inbound)
Bit 4: CANCEL_RESOLVED   (1 = Incident cancelled or patient secured; flush gradient)
Bit 5: RESERVED          (Reserved for future mesh expansion)
```

---

## 3. BLE Physical Encapsulation (GAP Advertisement)

The 4-byte payload is encapsulated within a standard **Bluetooth Low Energy (BLE 4.2/5.0+) Non-Connectable, Undirected Advertising PDU (`ADV_NONCONN_IND`)**:

```text
┌──────────────────────────────────────────────────────────────┐
│ BLE Advertising Packet (Max 31 Bytes GAP Payload)             │
├─────────────┬────────────────────────────────────────────────┤
│ Length (1B) │ AD Type (1B) : 0x01 (Flags: LE General Disc.)  │
├─────────────┼────────────────────────────────────────────────┤
│ Length (1B) │ AD Type (1B) : 0x16 (Service Data - 16-bit UUID│
├─────────────┼────────────────────────────────────────────────┤
│ 2 Bytes     │ Service UUID : 0xFC00 (Find Us Assigned UUID)   │
├─────────────┼────────────────────────────────────────────────┤
│ 4 Bytes     │ Find Us Payload (SOS_ID, HOP, BARO, FLAGS, EP) │
├─────────────┼────────────────────────────────────────────────┤
│ Remaining   │ 21 Bytes UNUSED (Available for FEC / Signatures)│
└─────────────┴────────────────────────────────────────────────┘
```

### Why Legacy Advertising is Mandatory
1. **Zero-Connection Overhead:** Does not require peer pairing, L2CAP channels, or GATT handshakes.
2. **Universal Compatibility:** Can be received and transmitted by 100% of smartphones produced since 2012 (iPhone 4S+, Android 4.3+).
3. **Background Sniffing:** Background OS policies on Android and iOS permit sniffing standardized Service UUID advertisements much more reliably than active connection establishment.

---

## 4. Node State Machine & Relay Pseudocode

```python
# Constants
K_REDUNDANCY_THRESHOLD = 3
T_JITTER_MIN_MS = 50
T_JITTER_MAX_MS = 250
COOLDOWN_MS = 2000
MAX_HOP_CAP = 15

class NodeState:
    def __init__(self, node_id, local_baro_hpa):
        self.node_id = node_id
        self.baro = local_baro_hpa
        self.active_emergencies = {} # sos_id -> {hop, epoch, last_seen}
        self.suppression_cache = {}  # (sos_id, hop) -> count

    def on_ble_packet_received(self, pkt):
        # 1. Parse fields
        sos_id = pkt.sos_id
        rx_hop = pkt.hop_count
        rx_epoch = pkt.epoch
        baro_diff = pkt.baro_diff
        flags = pkt.flags

        # 2. Check cancellation
        if flags.cancel_resolved:
            self.active_emergencies.pop(sos_id, None)
            return

        # 3. Epoch Freshness Check
        if sos_id in self.active_emergencies:
            current = self.active_emergencies[sos_id]
            if (rx_epoch - current['epoch']) % 16 > 8:
                # Stale epoch, drop
                return
            if rx_hop >= current['hop']:
                # Already have equal or better hop path, increment suppression counter
                key = (sos_id, rx_hop)
                self.suppression_cache[key] = self.suppression_cache.get(key, 0) + 1
                return

        # 4. New shorter path found!
        my_hop = rx_hop + 1
        if my_hop > MAX_HOP_CAP:
            return

        self.active_emergencies[sos_id] = {
            'hop': my_hop,
            'epoch': rx_epoch,
            'last_seen': time.now()
        }

        # 5. Schedule Inhibitory Rebroadcast
        self.schedule_inhibitory_relay(sos_id, my_hop, rx_epoch, baro_diff, flags)

    def schedule_inhibitory_relay(self, sos_id, hop, epoch, baro_diff, flags):
        key = (sos_id, hop)
        self.suppression_cache[key] = 1
        jitter_ms = random.uniform(T_JITTER_MIN_MS, T_JITTER_MAX_MS)

        # Wait during jitter window while listening
        sleep(jitter_ms)

        # Check suppression threshold
        if self.suppression_cache.get(key, 1) >= K_REDUNDANCY_THRESHOLD:
            # Suppress! Local neighborhood already well-covered
            return

        # Transmit 1 advertising burst on primary channels 37, 38, 39
        out_pkt = Packet(
            sos_id=sos_id,
            hop_count=hop,
            baro_diff=baro_diff,
            flags=flags,
            epoch=epoch
        )
        ble_broadcast(out_pkt)

        # Enter refractory cooldown
        sleep(COOLDOWN_MS)
```
