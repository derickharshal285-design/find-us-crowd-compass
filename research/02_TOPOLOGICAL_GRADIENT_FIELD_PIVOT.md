---
title: "02. The Topological Gradient Field Pivot"
tags:
  - project/find-us
  - architecture/gradient-field
  - math/graph-topology
created: 2026-09-18
updated: 2026-09-18
---

# 02. The Topological Gradient Field Pivot

> [!ABSTRACT]
> This document formalizes the mathematical and architectural transition from **Metric Pose-Graph Rebuilding** to **Topological Hop-Count Gradient Descent**. It proves why topological metrics are invariant to coordinate distortions, why RSSI fails as a potential function, and how the emergency itself acts as an implicit, self-calibrating spatial origin.

---

## 1. Mathematical Formalism: Why Vector-Chains Explode

### 1.1 The Legacy Vector-Chain Model
In the original Crowd Compass architecture, given a chain of nodes $v_0 \to v_1 \to v_2 \dots \to v_n$, the estimated relative coordinate of $v_0$ from the perspective of $v_n$ was:

$$\vec{P}_{n \to 0} = \sum_{i=1}^{n} \mathbf{R}(\theta_i) \cdot \vec{d}_i$$

Where:
* $\vec{d}_i$ is the 2D displacement vector measured at hop $i$, with distance error $\epsilon_{d,i} \sim \mathcal{N}(0, \sigma_d^2)$.
* $\theta_i$ is the relative compass/gyroscope heading, with orientation error $\epsilon_{\theta,i} \sim \mathcal{N}(0, \sigma_\theta^2)$.
* $\mathbf{R}(\theta_i)$ is the 2D rotation matrix:
  $$\mathbf{R}(\theta_i) = \begin{bmatrix} \cos \theta_i & -\sin \theta_i \\ \sin \theta_i & \cos \theta_i \end{bmatrix}$$

### 1.2 The Variance Catastrophe
Because the rotation matrices compound:
$$\Theta_k = \sum_{j=1}^k \theta_j$$
The angular variance accumulates linearly with hop depth $k$: $\operatorname{Var}(\Theta_k) = k \cdot \sigma_\theta^2$.
When projected through distance, the transversal positional uncertainty $\sigma_{\perp}^2$ explodes quadratically with distance and hop count:

$$\sigma_{\text{total}}^2 \approx \sum_{i=1}^n \sigma_{d,i}^2 + \sum_{i=1}^n \left( \sum_{j=i}^n \|\vec{d}_j\| \right)^2 \sigma_{\theta,i}^2$$

In a real smartphone environment:
* Consumer magnetometer error indoors/near metal: $\sigma_\theta \approx 15^\circ\text{ to } 30^\circ$ ($0.26\text{ to } 0.52\text{ rad}$).
* RSSI-derived distance error: $\sigma_d \approx 3\text{ to } 5\text{ meters}$.
* At **Hop 4**, total position error $\sigma_{\text{total}} > 35\text{ meters}$. The estimated coordinate vector points in a completely arbitrary direction.

---

## 2. The Topological Solution: Gradient Fields

Instead of embedding nodes in a continuous metric manifold $\mathbb{R}^2$, we treat the ad-hoc mesh as a discrete topological graph $G = (V, E)$, where:
* $V$ is the set of participating smartphones.
* $E$ is the set of active BLE bidirectional links: $(u, v) \in E \iff \text{link is viable}$.

### 2.1 The Emergency as the Graph Origin
When node $v_{\text{sos}} \in V$ triggers an emergency, it defines a scalar potential function $H: V \to \mathbb{N}_0$ representing the shortest path hop distance to $v_{\text{sos}}$:

$$H(v) = \operatorname{dist}_G(v, v_{\text{sos}}) = \min \{ k \mid (v_0, v_1, \dots, v_k) \text{ is a path}, v_0 = v_{\text{sos}}, v_k = v \}$$

By definition:
* $H(v_{\text{sos}}) = 0$
* For any neighbor $u \in \mathcal{N}(v)$, $|H(u) - H(v)| \le 1$

### 2.2 Discrete Gradient Descent
A responder node $v_r$ does not require coordinates. It only requires a descent trajectory:

$$\mathcal{P} = (v^{(0)}, v^{(1)}, \dots, v^{(m)})$$
such that:
$$v^{(0)} = v_r, \quad v^{(m)} = v_{\text{sos}}, \quad \text{and } H(v^{(t+1)}) < H(v^{(t)})$$

This is strictly **monotonic** and **finite**. It terminates in exactly $H(v_r)$ steps if a path exists.

```text
               [SOS: Hop 0]
                 /   |   \
           [Hop 1] [Hop 1] [Hop 1]
           /    \     |     /    \
       [Hop 2] [Hop 2] [Hop 2] [Hop 2]
          \       |     |       /
          [Hop 3] [Hop 3] [Hop 3]
                     |
            [Responder: Hop 3]
```

---

## 3. Why RSSI CANNOT Be the Gradient

A common fatal pitfall in peer-to-peer localization is asserting:
> *"Just walk in the direction of increasing signal strength (RSSI)."*

This fails catastrophically in multi-hop networks for two distinct reasons:

### 3.1 Logical vs. Physical Distance Inversion
Consider the topological scenario below:

```text
[SOS: Hop 0]
      │
  [Node B: Hop 1] ─────────────── [Node X: Hop 3]
      │                               ▲
  [Node C: Hop 2]                     │ (Physically 1.2 meters away)
      │                               │
[Responder: Hop 3] ───────────────────┘
```

* Node $X$ is physically right next to the Responder ($1.2\text{ meters}$).
* Node $X$'s signal strength is an overwhelming $-52\text{ dBm}$.
* Node $C$ is $7\text{ meters}$ away, blocked by three people, with an RSSI of $-84\text{ dBm}$.
* **If the responder follows RSSI gradients:** They will turn towards Node $X$. But Node $X$ is Hop 3! Walking toward $X$ takes the responder completely off the descent trajectory.
* **If the responder follows Hop gradients:** They query: *"Which neighbors advertise Hop 2?"* Only Node $C$ does. The responder moves toward $C$, correctly descending $3 \to 2 \to 1 \to 0$.

### 3.2 The Multi-Path & Human Attenuation Shadow
2.4 GHz RF propagation in a crowd obeys the Log-Normal Shadowing Model:

$$\operatorname{RSSI}(d) = P_0 - 10 n \log_{10}\left(\frac{d}{d_0}\right) - X_\sigma - L_{\text{body}}$$

Where:
* $n \approx 3.2\text{--}4.5$ (path loss exponent in crowded indoor/stadium spaces).
* $X_\sigma \sim \mathcal{N}(0, \sigma^2)$ is shadowing due to multipath ($\sigma \approx 6\text{--}10\text{ dB}$).
* $L_{\text{body}} \approx 15\text{--}25\text{ dB}$ is the direct attenuation caused by a human torso standing directly between two phones.

Because $L_{\text{body}}$ and $X_\sigma$ can alter RSSI by over $30\text{ dB}$, a phone $3\text{ meters}$ away can easily register a weaker signal than a phone $12\text{ meters}$ away that has line-of-sight across heads. 

> [!WARNING]
> **Cardinal Rule:**
> **Hop count provides the directional topology.**
> **RSSI is only a local hint to estimate when you are within arm's reach of that specific node.**

---

## 4. Solving the "Which Way to Walk" Problem

If the responder is at Hop 3, and their phone sniffs three different devices advertising Hop 2:

```text
               Hop 2 (Phone A)  [Left, 8m]
              /
Responder [Hop 3]
              \
               Hop 2 (Phone B)  [Right, 15m]
```

Which phone should the responder approach?

### 4.1 Solution Strategy: Local Relative Proximity Scoring
The responder doesn't need to choose the "perfect" node; **any valid Hop 2 node guarantees topological progress**. However, to optimize physical distance, the responder's phone calculates a **Local Target Weight**:

$$W(u) = \alpha \cdot \frac{1}{H(u)} + \beta \cdot \overline{\operatorname{RSSI}}(u) - \gamma \cdot \operatorname{Age}(u)$$

For all $u \in \mathcal{N}(\text{Responder})$ where $H(u) < H(\text{Responder})$.

### 4.2 Biological Shadowing as the Local Compass
To know which physical direction to take:
1. The responder holds their phone against their sternum.
2. The user rotates $360^\circ$ over 4 seconds.
3. The phone records RSSI samples of the lowest-hop beacon keyed to the phone's internal gyroscope azimuth $\phi \in [0, 360^\circ)$.
4. The user's torso acts as an RF attenuator ($15\text{--}20\text{ dB}$ loss). 
5. The **maximum signal strength occurs when the user faces directly toward the Hop-2 node**, because their body is behind the phone, providing zero shadowing.
6. The user's screen displays a simple directional cone: **"Walk forward in this heading."**

---

## 5. Tiny Packet Philosophy: The 28-Bit Wire Format

Because the network does not propagate coordinates or vector chains, the packet size is drastically reduced.

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          SOS_ID (12)          |  HOP (4)  | BARO_DIFF(6)|FLAGS|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

* **`SOS_ID` (12 bits):** Unique pseudorandom incident token (refreshed every 30 minutes, supports 4,096 simultaneous emergencies in the same stadium).
* **`HOP_COUNT` (4 bits):** Values $0\text{--}15$. Max 15 hops covers $> 300\text{--}450\text{ meters}$ across dense human gatherings.
* **`BARO_DIFF` (6 bits):** Two's complement signed integer ($\pm 31$). Represents elevation difference relative to victim in units of $0.5\text{ hPa}$ ($\sim 4\text{ meters}$ per step, covering $\pm 15$ stadium tiers).
* **`CONTROL_FLAGS` (6 bits):**
  * Bit 0: Emergency Type (0 = Medical, 1 = Threat/Security)
  * Bit 1: Visual Runway Activated (Screen/Strobe on Hop 1)
  * Bit 2: Cancellation / Resolved
  * Bits 3–5: Reserved for collision-avoidance backoff multiplier

**Total wire payload: 28 bits.**
This fits effortlessly into the 31-byte advertising payload of BLE Legacy Advertising (Bluetooth 4.0+) without requiring BLE 5.0 Extended Advertisements or connection handshakes.
