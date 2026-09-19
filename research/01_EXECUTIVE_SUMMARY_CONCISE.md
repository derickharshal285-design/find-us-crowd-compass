---
title: "01. Executive Summary: The Architectural Pivot"
tags:
  - project/find-us
  - architecture/executive-summary
  - research/spatial-mesh
created: 2026-09-18
updated: 2026-09-18
---

# 01. Executive Summary: The Architectural Pivot

> [!NOTE]
> **Elevator Summary:**
> In a stadium of 50,000 people where cellular networks are jammed, GPS is blocked by concrete, and no infrastructure exists, an emergency victim presses SOS. 
> The legacy approach attempted to compute a precise metric coordinate $(x, y)$ by chaining local vector measurements $(d, \theta)$ through peer phones. **That approach fundamentally breaks** due to exponential angular error accumulation, lack of a common coordinate origin $(0,0)$, and the "Outsider" problem (an incoming responder has no shared history).
> 
> The breakthrough architecture is **The Topological Hop-Count Gradient Field**:
> 1. The SOS beacon establishes **Hop 0**.
> 2. Surrounding devices broadcast discrete hop tiers (**Hop 1, Hop 2, Hop 3...**).
> 3. An external responder performs **Gradient Descent in physical space** by simply walking toward lower hop tiers ($N \to N-1$).
> 4. **Crucial Correction:** Hop count provides the spatial topological gradient; **RSSI is NOT the gradient** (RSSI varies wildly with body orientation and multipath). Bluetooth signal strength serves only as an ephemeral local proximity check.
> 5. Terminal resolution (the last 10 meters) is handed off to **Biological Shadowing** (human torso attenuation) and **Optical Strobing**.

---

## 1. The Core Paradigm Shift

```
ORIGINAL PARADIGM (Geometric Navigation):
"Where exactly is the victim in Euclidean space?"
(Requires: Shared (0,0) anchor + vector chaining + angle-of-arrival + continuous graph optimization)
❌ Compounding math error, bloated packets, uninterpretable by outsiders.

NEW PARADIGM (Topological Navigation):
"How many mesh hops away from the SOS am I?"
(Requires: Discrete hop count + tiny 28-bit payload + local step decisions)
✅ Zero global coordinate error, tiny payload, immediate onboarding for outsiders.
```

---

## 2. The Three-Layer Architecture

Instead of forcing a single phone sensor to solve the whole 500-meter journey:

```text
┌──────────────────────────────────────────────────────────┐
│ 1. GLOBAL / MACRO MESH LAYER (500m down to 15m)          │
│    - Decentralized Hop Gradient Field (Hop N → Hop 0)     │
│    - Inhibitory Trickle routing to prevent Spectrum Storm │
│    - Relative Barometric Delta for Z-axis (Floor ±N)     │
└──────────────────────────┬───────────────────────────────┘
                           │ Hand-off at Hop 1 / Hop 2
                           ▼
┌──────────────────────────────────────────────────────────┐
│ 2. LOCAL DIRECTIONAL LAYER (15m down to 5m)              │
│    - Synthetic Lighthouse: Biological Torso Shadowing     │
│      (Rotate phone against chest; 15–20 dB torso dip      │
│       reveals true bearing of lowest-hop emitter)        │
│    - Coarse RSSI differential across motion (Hot / Cold)  │
└──────────────────────────┬───────────────────────────────┘
                           │ Hand-off at Hop 0 / Hop 1 (Final 10m)
                           ▼
┌──────────────────────────────────────────────────────────┐
│ 3. TERMINAL IDENTIFICATION LAYER (Last 5 meters)         │
│    - Optical Visual Runway: Target screen/torch strobes  │
│    - Pocket-aware proximity alert                        │
│    - Acoustic chirp (secondary fallback in quiet zones)   │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Why the Gradient Field Eliminates the Hardest Problems

1. **Eliminates the Anchor Problem:**
   The network does not need a pre-surveyed anchor beacon or arbitrary `(0,0)` origin. The emergency itself creates the origin: $\text{Target} \equiv 0$. All spatial topology radiates outward as concentric rings of hop numbers.
2. **Compresses the Wire Payload to ~28 Bits:**
   Because nodes do not append floating-point vectors, headings, or covariance matrices, the emergency packet needs only:
   * `SOS_ID`: 12 bits (4,096 concurrent incidents)
   * `HOP_COUNT`: 4 bits (0–15 hops, covering up to 450m in dense crowds)
   * `BAROMETRIC_DELTA`: 6 bits (relative floor indicator: $\pm 32$ levels in 0.5hPa steps)
   * `STATUS_FLAGS`: 6 bits (medical, security, fire, cancellation)
   * **Total: 28 bits.** This fits inside a single standard BLE Non-Connectable Advertising PDU with massive forward error correction overhead.
3. **Solves the "Outsider" Medic Case:**
   A responder arriving from outside the venue does not need to synchronize an internal map. As soon as the responder's phone sniffs BLE advertising packets on channels 37/38/39, it observes `Hop 5`. Walking in any direction either increments or decrements the observed hop count. The responder simply follows the descent: $5 \to 4 \to 3 \to 2 \to 1 \to 0$.

---

## 4. The 4 Fatal Traps Solved in this Research

* **Trap A (Using RSSI as the Gradient):**
  * *Why it fails:* An irrelevant node at Hop 3 standing 1 meter away will register $-55\text{ dBm}$, while the correct Hop 2 node behind a person registers $-82\text{ dBm}$. Following RSSI leads you into blind dead-ends.
  * *The Fix:* **Hop count is the sole routing gradient.** RSSI is used strictly locally to detect when you are physically closing in on a specific chosen node.
* **Trap B (Spectrum Collapse):**
  * *Why it fails:* If 10,000 phones receive an SOS and rebroadcast immediately on the 3 primary BLE advertising channels, the channel contention probability hits 99.8%. The mesh deafens itself.
  * *The Fix:* **Inhibitory Routing (RFC 6206 Trickle variant).** If a node receives $k \ge 3$ redundant copies of the same `[SOS_ID, HOP_COUNT]` within a randomized jitter window ($50\text{--}250\text{ ms}$), it completely suppresses its rebroadcast.
* **Trap C (The Z-Axis Concrete Barrier):**
  * *Why it fails:* In a multi-deck stadium, a target at Hop 1 might be physically 3 meters away vertically through a reinforced concrete slab, but 200 meters away via stadium ramps.
  * *The Fix:* **Barometric Differential ($\Delta P$).** Every modern smartphone has a barometric sensor accurate to $0.05\text{ hPa}$ ($~0.4\text{ meters}$). The SOS packet broadcasts the victim's reference pressure $P_{\text{target}}$. The responder compares $P_{\text{local}} - P_{\text{target}}$ to instruct "GO DOWN ONE LEVEL" before horizontal descent.
* **Trap D (The "Which Way" Walking Problem):**
  * *Why it fails:* At Hop 3, there are multiple Hop 2 nodes in different directions. Hop count doesn't tell you to turn $30^\circ$ left.
  * *The Fix:* **Biological Shadowing (The Torso Lighthouse).** The human body absorbs $15\text{--}25\text{ dB}$ of 2.4 GHz energy. Holding the phone to the sternum and turning $360^\circ$ turns the human body into a directional cardioid antenna, identifying the line of bearing to the next hop tier without AoA hardware.
