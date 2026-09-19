---
title: "05. Problem Dependency Audit: All 12 Sub-Problems Analyzed"
tags:
  - project/find-us
  - audit/dependency-chart
  - research/problem-decomposition
created: 2026-09-18
updated: 2026-09-18
---

# 05. Problem Dependency Audit: All 12 Sub-Problems Analyzed

> [!IMPORTANT]
> This document audits the **12 foundational sub-problems** (plus #13 MAC Rotation and #14 Trust) defined in the Crowd Compass Dependency Chart.
> For each sub-problem in strict dependency order, this audit establishes:
> 1. **The Proposed Mechanism** (Legacy Vector-Chain vs. Pivoted Gradient Field).
> 2. **The Smallest Concrete Failure Point**.
> 3. **What Must Be Tested / Measured to Trust It**.
> 4. **Architectural Verdict & Status**.

---

```
                       [1. No Shared Origin]
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       [2. Two-Phone Relation]         [3. Spatial Relays]
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
                    [4. Vector-Chain Composition]
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
          [5. Staleness]              [6. Conflicting Paths]
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
                     [7. Dynamic Mesh Topology]
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
        [8. New Device Joins]        [9. Outward Group Growth]
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
                  [10. Private Frame vs. Outsider]
                                 │
                                 ▼
                     [11. SOS Spatial Context]
                                 │
                                 ▼
                [12. Responder Locates the Target]
```

---

## Sub-Problem 1: No Shared Coordinate Origin

* **Why it exists:** GPS is blocked indoors or in dense crowds. Phone A and Phone B initialize arbitrary local `(0,0)` origins that have zero physical relationship.
* **1. Proposed Mechanism:**
  * *Legacy:* Establish an anchor phone that declares itself `(0,0)`; all other phones express coordinates relative to that anchor.
  * *Pivoted (Gradient Field):* **Discard global coordinates entirely.** The SOS beacon itself becomes `Hop 0`. All other devices define their spatial position simply as the integer shortest-path distance $H \in \mathbb{N}_0$ to that specific emergency.
* **2. Smallest Concrete Failure Point:**
  * Two separate emergencies happen simultaneously ($SOS_A$ and $SOS_B$). If packets do not carry distinct `SOS_ID` tags, hop counters from both incidents collide, creating an inconsistent multi-origin potential field.
* **3. What Must Be Tested / Measured:**
  * Multi-incident isolation: Verify that a 12-bit `SOS_ID` allows phones to independently track up to 8 concurrent gradient fields with zero cross-talk in simulation.
* **4. Verdict:** **SOLVED BY PIVOT.** Origin is dynamic, ephemeral, and anchored to the crisis itself.

---

## Sub-Problem 2: Establishing Raw Spatial Relationship Between Two Adjacent Phones

* **Why it exists:** When A and B are in direct BLE range, what do they measure: distance, direction, both, and how?
* **1. Proposed Mechanism:**
  * *Legacy:* Use Bluetooth 5.1 Angle-of-Arrival (AoA) for bearing and RSSI path-loss for metric distance.
  * *Pivoted (Gradient Field):* **Discrete Link Viability + Torso Shadowing.** We only test if packet reception rate (PRR) exceeds threshold ($> 60\%$) to declare an active edge. Bearing is resolved locally via the user's biological torso rotation (Synthetic Lighthouse) rather than multi-antenna AoA arrays.
* **2. Smallest Concrete Failure Point:**
  * AoA APIs are completely locked down by Apple and Google on iOS/Android; standard consumer phones do not expose I/Q raw phase samples to third-party apps.
* **3. What Must Be Tested / Measured:**
  * Measure torso shadowing attenuation (dB differential) across 20 different phone models and user body types. Verify $\ge 15\text{ dB}$ front-to-back dip.
* **4. Verdict:** **PIVOT CONFIRMED.** Do not rely on AoA hardware that OS vendors do not expose.

---

## Sub-Problem 3: Spatial Information Traveling Through Relays

* **Why it exists:** Direct BLE range is $< 10\text{ meters}$ in a crowd. Spatial relationship information must hop through intermediate phones C, D, E.
* **1. Proposed Mechanism:**
  * *Legacy:* Each intermediary appends its relative displacement vector $\vec{v}_i$ to the message payload.
  * *Pivoted (Gradient Field):* **Topological Increment.** When relay $v$ receives a packet with `HOP = k`, it checks if this is the lowest hop seen for that `SOS_ID`. If yes, it caches `my_hop = k + 1` and rebroadcasts `[SOS_ID, k+1]` using an inhibitory Trickle window.
* **2. Smallest Concrete Failure Point:**
  * Rebroadcasting stale hop information after the target moves, causing "count-to-infinity" routing loops.
* **3. What Must Be Tested / Measured:**
  * Sequence number freshness: Ensure each SOS burst increments an `epoch_seq` (4 bits) so relays immediately drop stale hop tiers from previous epochs.
* **4. Verdict:** **HIGHLY FEASIBLE.** Tiny constant payload replaces unbounded vector concatenation.

---

## Sub-Problem 4: Vector-Chain Composition

* **Why it exists:** When multiple local vectors are stacked end-to-end ($\vec{V}_{\text{total}} = \vec{v}_1 + \vec{v}_2 + \dots$), do they reconstruct a usable position?
* **1. Proposed Mechanism:**
  * *Legacy:* Trigonometric matrix multiplication and floating-point summation across hops.
  * *Pivoted (Gradient Field):* **ELIMINATE VECTOR STACKING COMPLETELY.** Instead of computing $\vec{P} = \sum \vec{v}_i$, the network builds a scalar hop field $H: V \to \mathbb{N}_0$. The responder performs gradient descent across physical nodes.
* **2. Smallest Concrete Failure Point:**
  * In the legacy approach: $10^\circ$ compass error per hop accumulates to $40^\circ$ error over 4 hops, placing the estimated target $50\text{ meters}$ away in the wrong quadrant.
* **3. What Must Be Tested / Measured:**
  * Simulation comparison: Compounding trigonometric variance vs. topological descent success rate in dense cluttered graphs.
* **4. Verdict:** **FATAL IN LEGACY; BYPASSED BY GRADIENT FIELD.**

---

## Sub-Problem 5: Relationship Staleness

* **Why it exists:** People in a crowd constantly sway, walk, and shift. A vector measured 90 seconds ago is invalid.
* **1. Proposed Mechanism:**
  * *Legacy:* Dead reckoning decay timers and covariance inflation matrices.
  * *Pivoted (Gradient Field):* **Rapid Epoch Decay (TTL + Wall-Clock Expiry).** Hop field gradients expire after $10\text{--}15\text{ seconds}$ unless refreshed by a new heartbeat from `Hop 0`. Relays only store the latest epoch.
* **2. Smallest Concrete Failure Point:**
  * If the victim's phone dies or is dropped, the mesh continues circulating an obsolete gradient field.
* **3. What Must Be Tested / Measured:**
  * Gradient dissipation latency: Measure how quickly an obsolete gradient evaporates from a 1,000-node network when the source stops broadcasting (target $< 5\text{ seconds}$).
* **4. Verdict:** **MANAGEABLE.** Ephemeral state prevents ghost gradients.

---

## Sub-Problem 6: Conflicting Redundant Paths

* **Why it exists:** A responder receives Hop 2 from Path A (via 2 fast relays) and Hop 4 from Path B (via 4 slow relays). Which is correct?
* **1. Proposed Mechanism:**
  * *Legacy:* Complex pose-graph optimization, non-linear least squares, or Kalman filtering to reconcile conflicting vectors.
  * *Pivoted (Gradient Field):* **Minimum Hop Wins (Dijkstra Principle).**
    $$\operatorname{Hop}_{\text{current}} = \min(\operatorname{Hop}_{\text{current}}, \operatorname{Hop}_{\text{received}} + 1)$$
    If a node hears Hop 1 and Hop 3, it is topological distance 2 from the target. The longer path is discarded.
* **2. Smallest Concrete Failure Point:**
  * A long-range spurious RF "wormhole" (e.g., reflection off a high metal arena ceiling) causes a single packet to jump 50 meters, falsely tagging a far node as Hop 1.
* **3. What Must Be Tested / Measured:**
  * Filtering outlier links: Require $k \ge 2$ packet receptions before accepting an ultra-low hop value from a new transmitter.
* **4. Verdict:** **CLEAN MATHEMATICAL RESOLUTION.** Discard graph solvers; use min-operator.

---

## Sub-Problem 7: Dynamic Mesh Membership

* **Why it exists:** Bystanders constantly turn their phones off, walk away, put phones in bags, or background the app.
* **1. Proposed Mechanism:**
  * *Legacy:* Continuous neighbor-table heartbeats, distributed routing table maintenance (AODV/DSR style).
  * *Pivoted (Gradient Field):* **Stateless Managed Flooding with Inhibitory Suppression.** Nodes do not maintain routing tables or track neighbor identities. They simply sniff raw BLE advertising packets and rebroadcast if their local redundancy count $c < 3$.
* **2. Smallest Concrete Failure Point:**
  * A sudden crowd partition (e.g., crowd splits into two aisles separated by a physical barricade), creating a disconnected subgraph.
* **3. What Must Be Tested / Measured:**
  * Partition recovery via "data mules": When a user walks across the gap, does store-and-forward bridge the two subgraphs within 30 seconds?
* **4. Verdict:** **EXTREMELY ROBUST.** Stateless protocols thrive in high-churn environments.

---

## Sub-Problem 8: A New Device Joining an Existing Spatial Frame

* **Why it exists:** A user turns on their phone midway through the event. How do they calibrate without restarting the whole mesh?
* **1. Proposed Mechanism:**
  * *Legacy:* Request the shared coordinate matrix from neighbors; run coordinate transformation.
  * *Pivoted (Gradient Field):* **Instant Passive Sniffing.** The joining device passively listens to BLE advertising channels 37/38/39 for 500 ms. If it hears `[SOS: 1842, Hop 3]`, it immediately knows its exact topological status: `Hop 4`. Zero handshakes, zero onboarding latency.
* **2. Smallest Concrete Failure Point:**
  * Device joins during a quiet cycle of the inhibitory suppression window and assumes no emergency exists.
* **3. What Must Be Tested / Measured:**
  * Time-to-first-detection: Verify $> 99\%$ of newly activated devices sniff the active emergency within $\le 1.5\text{ seconds}$.
* **4. Verdict:** **ZERO-COST JOIN.**

---

## Sub-Problem 9: Group Growing Outward From Its Origin

* **Why it exists:** As the crowd expands across a 100,000-capacity festival, hop counts grow ($1 \to 2 \to 5 \to 12$). Does the spatial structure degrade?
* **1. Proposed Mechanism:**
  * *Legacy:* Compounding covariance matrices explode to infinity at the perimeter; the edge is mathematically unusable.
  * *Pivoted (Gradient Field):* **Strict Bounded Inaccuracy.** At Hop 10, the topological error is still zero—you are exactly 10 hops away. The only physical degradation is propagation latency ($\sim 10 \times 150\text{ ms} = 1.5\text{ seconds}$).
* **2. Smallest Concrete Failure Point:**
  * Max hop limit exceeded: If the crowd spans 40 hops, a 4-bit hop field overflows.
* **3. What Must Be Tested / Measured:**
  * Cap maximum TTL to 15 hops (covers $\sim 300\text{--}450\text{ meters}$). For larger venues, scale payload to 5 bits (31 hops).
* **4. Verdict:** **RADICAL IMPROVEMENT OVER VECTOR CHAINS.**

---

## Sub-Problem 10: Private Group Frame vs. An Outsider

* **Why it exists:** A private group of friends has an internal map. A medic who just arrived has zero access to their internal reference.
* **1. Proposed Mechanism:**
  * *Legacy:* Complex cryptographic key exchange and coordinate alignment handshakes.
  * *Pivoted (Gradient Field):* **Universal Public Channel for SOS.** Normal social friend-finding can live in private encrypted sub-graphs. But when an SOS is flagged, the packet is broadcast on the unencrypted public emergency namespace. The incoming medic sniffs the exact same scalar hop gradient as everyone else.
* **2. Smallest Concrete Failure Point:**
  * Malicious bad actor triggers a fake SOS to disrupt the medic.
* **3. What Must Be Tested / Measured:**
  * Emergency rate-limiting and cryptographic signature from venue ticketing app (e.g., ticket QR code proves legitimate attendee).
* **4. Verdict:** **SOLVED BY DESIGN.**

---

## Sub-Problem 11: SOS Carrying Enough Spatial Context Beyond the Private Group

* **Why it exists:** A generic message saying *"I need help"* has zero spatial utility. The packet must carry its own navigation context without bloating.
* **1. Proposed Mechanism:**
  * *Legacy:* Compress 2D polygon bounding boxes or relative vector strings into payload.
  * *Pivoted (Gradient Field):* **The 28-Bit Self-Contained Gradient Frame:**
    `[SOS_ID: 12b][HOP: 4b][BARO_DIFF: 6b][STATUS: 6b]`.
    Every single packet contains the complete spatial and vertical context required for gradient descent.
* **2. Smallest Concrete Failure Point:**
  * Barometric sensor calibration offset between different smartphone vendors (Apple vs. Samsung vs. Google).
* **3. What Must Be Tested / Measured:**
  * Cross-vendor barometric baseline variance under identical ambient conditions.
* **4. Verdict:** **OPTIMAL WIRE EFFICIENCY.**

---

## Sub-Problem 12: Responder Locating an SOS Target (The Ultimate Test)

* **Why it exists:** The medic enters the venue with no prior context, in a noisy, moving, packed crowd, and must physically reach the patient.
* **1. Proposed Mechanism:**
  * *Complete Integrated 3-Stage Pipeline:*
    1. **Stage 1 (Macro):** Topological gradient descent ($N \to 1$) with barometric floor guidance.
    2. **Stage 2 (Local):** Biological torso shadowing sweep for line-of-bearing.
    3. **Stage 3 (Terminal):** Optical screen/torch strobe handoff ("Look Up Runway").
* **2. Smallest Concrete Failure Point:**
  * Target is unconscious and trampled on the ground under a dense sea of standing bodies; screen and torch are blocked from view.
* **3. What Must Be Tested / Measured:**
  * Terminal bystander audio-haptic prompt: The app on bystander phones immediately adjacent to the victim sounds a localized tone: *"Medical emergency directly at your feet."*
* **4. Verdict:** **THE COMPLETE ARCHITECTURAL SOLUTION.**

---

## Parallel Sub-Problems (Lower Layer)

### Sub-Problem 13: Device Identity Continuity (MAC Address Rotation)
* **Mechanism:** OS-level Bluetooth MAC address rotation (every 15 min) breaks node identity.
* **Gradient Field Advantage:** **The Gradient Field is completely agnostic to MAC addresses.** Nodes do not route *to* a specific MAC address; they broadcast *from* an emergency ID. Whether Phone B changes its MAC address three times during an emergency is completely irrelevant—it still relays `[SOS_ID, Hop 2]`.
* **Verdict:** **PROBLEM COMPLETELY EVAPORATES.**

### Sub-Problem 14: Trust & Adversarial Input
* **Mechanism:** Rogue participant injects fake `Hop 0` or false `Hop 1` to misdirect responders.
* **Countermeasure:** Event-ticket asymmetric signing (ECDSA secp256r1 token generated during venue entry) or proof-of-work rate limiting.
* **Verdict:** Deferred to security transport layer; does not impede spatial topology.
