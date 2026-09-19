---
title: "09. Progressive Navigation Resolution: Stepping Down the Core Questions"
tags:
  - navigation/step-by-step
  - architecture/progressive-resolution
  - core-questions/answers
created: 2026-09-18
updated: 2026-09-18
---

# 09. Progressive Navigation Resolution: Stepping Down the Core Questions

> [!IMPORTANT]
> **Focusing Strictly on Navigation (Z-Axis set aside):**
> This document systematically answers the core progressive chain of questions you identified:
> * How do two phones establish a relationship?
> * What is in that relationship?
> * How does that relationship travel through 1 hop, 2 hops, 3 hops?
> * What happens when someone moves or leaves?
> * How does a new person join without resetting to zero?
> * How does an external responder get a directional arrow with zero prior history?

---

## The Baseline: What Can an Ordinary Phone Actually Measure?

Before connecting two phones, we must be brutally honest about what a phone's hardware can and cannot measure:

```text
┌───────────────────────────┬─────────────────────────────────────────────────────────────┐
│ Sensor                    │ What It Actually Gives Us                                   │
├───────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Bluetooth Radio (BLE)     │ 1. Presence: "Device X is within 5–15 meters."              │
│                           │ 2. RSSI: Very noisy signal strength (blurry distance).      │
│                           │ ❌ NO DIRECTION: A single phone antenna CANNOT tell angle.  │
├───────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Accelerometer (IMU)       │ Step detection (user took a step ≈ 0.7 meters).             │
├───────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Gyroscope (IMU)           │ Turning rate (user turned 45° left). Very accurate short-term│
├───────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Magnetometer (Compass)    │ Heading relative to North. Wobbles 15°–30° indoors near rebar│
└───────────────────────────┴─────────────────────────────────────────────────────────────┘
```

---

## Step 1: Two Adjacent Phones ($A \leftrightarrow B$)

```text
     Phone A  ◄────── 5 to 10 meters ──────►  Phone B
        📱                                       📱
```

### 1.1 What do they actually measure?
* **Distance:** Rough distance only. They sniff each other's BLE advertisements. An RSSI of $-65\text{ dBm}$ means roughly $3\text{--}5\text{ meters}$; $-85\text{ dBm}$ means roughly $10\text{--}15\text{ meters}$.
* **Direction:** **Neither phone knows where the other is facing or what direction the other is standing.** 
  * If Phone A and Phone B are both sitting still, all they know is: *"We are neighbors within arm's reach."*

### 1.2 How do they get DIRECTION between each other?
There are only two ways an ordinary phone can find the direction of another phone without special antennas:
1. **The Motion Method (Walking):**
   * Phone A stands still. Phone B takes 5 steps.
   * Phone B's accelerometer measures its own displacement vector: $\Delta \vec{x}_B = [3.5\text{m forward}]$.
   * If Phone A's signal strength gets stronger during those 5 steps, Phone B was walking toward Phone A. If it gets weaker, Phone B walked away.
2. **The Torso Shadowing Method (Spinning on the spot):**
   * User B holds their phone to their chest and spins $360^\circ$.
   * User B's own body absorbs $18\text{ dB}$ of Bluetooth signal when their back is turned.
   * When User B faces Phone A, the signal peaks. User B's screen locks the heading: *"Phone A is at your 1 o'clock."*

---

## Step 2: Three Phones ($A \leftrightarrow C \leftrightarrow B$)

```text
   Phone A ────────────── Phone C ────────────── Phone B
      📱                      📱                      📱
   (Victim)                (Relay)                (Searcher)
   
   [A and B CANNOT hear each other. Only C can hear both.]
```

### 2.1 The Problem:
Phone B wants to know where Phone A is. But Phone B only has a radio connection to Phone C.

### 2.2 How does the information travel?
There are two ways to answer this, depending on what the user is doing:

#### Route A: The Macro / Emergency Way (Topological Gradient Field)
* **What C transmits:** Phone C does **not** send a complex geometric vector. 
* Phone A broadcasts: `[SOS, Hop 0]`.
* Phone C receives it, increments the counter, and broadcasts: `[SOS, Hop 1]`.
* Phone B receives it and sees: `[SOS, Hop 1]`.
* **What B knows:** Phone B knows Phone A is exactly **2 hops away through Phone C**.
* Phone B moves toward Phone C. When B reaches C, B is now at Hop 1 and can detect A directly!

#### Route B: The Private Group Map Way (Relative Geometric Vectors)
* If A, B, and C are friends who want a private radar screen:
* Phone C knows: *"Phone A is 6m to my North."*
* Phone C knows: *"Phone B is 8m to my East."*
* Phone C sends a tiny packet to Phone B containing: `Vector_CA = [-8m East, +6m North]`.
* Phone B subtracts its own position from that vector:
  $$\vec{P}_{B \to A} = \vec{P}_{C \to A} - \vec{P}_{C \to B}$$
* Phone B's screen displays: *"Friend A is roughly 10 meters Northwest of you."*

---

## Step 3: Multi-Hop Chaining ($A \leftrightarrow C \leftrightarrow D \leftrightarrow B$)

```text
Phone A ─────── Phone C ─────── Phone D ─────── Phone B
   📱               📱               📱               📱
 (Hop 0)          (Hop 1)          (Hop 2)          (Hop 3)
```

### 3.1 Why the Old Vector-Chain Broke:
If every phone tried to chain vectors ($\vec{V}_{AC} + \vec{V}_{CD} + \vec{V}_{DB}$):
* Phone C has a $15^\circ$ compass error.
* Phone D has a $20^\circ$ compass error.
* Phone B has a $15^\circ$ compass error.
* When you add them end-to-end, the errors multiply by the distance! By Hop 3, Phone B calculates that Phone A is in the parking lot, when Phone A is actually near the stage.

### 3.2 How the Hop Gradient Solves This:
* Phone A: `Hop 0`.
* Phone C: `Hop 1`.
* Phone D: `Hop 2`.
* Phone B: `Hop 3`.
* **The Error is Zero:** Phone B is objectively 3 hops away. There are no angles to multiply, no compasses to wobble, and no coordinates to distort.
* Phone B simply walks toward whichever neighbor advertises `Hop 2` (Phone D). Once at Phone D, Phone B walks toward `Hop 1` (Phone C).

---

## Step 4: When Someone Leaves or Moves (Node C Disappears)

```text
Phone A ─────── [Phone C Leaves!] ─────── Phone D ─────── Phone B
   📱                   ❌                     📱               📱
```

### 4.1 What happens to the spatial information?
1. **Heartbeat & Expiry (TTL):** Every hop packet has a rolling timestamp/epoch (refreshed every 5 seconds).
2. When Phone C walks away or turns off, Phone D stops hearing `Hop 1` from C.
3. Phone D's cache expires C after 8 seconds.
4. **Local Mesh Healing:**
   * Phone D looks for any other neighbor who hears Phone A.
   * If Phone D finds Phone E (who hears A at Hop 1), the path instantly re-routes through E:
     $$A \longrightarrow E \longrightarrow D \longrightarrow B$$
   * If no other neighbor exists, Phone D increments its hop count to indicate the path broke, and uses **Store-and-Forward** (holding the last known direction until a new walking person passes by).

---

## Step 5: When People Move (Dead Reckoning & Step Updates)

```text
       Start at (0,0) ──► Takes 10 steps East ──► New Position (+7m, 0m)
```

### 5.1 The Rule: Keep Movement Local!
* A phone **never** broadcasts every step to the crowd. If 10,000 phones broadcasted every footstep, the radio channels would crash in 2 seconds.
* **Each phone tracks its own movement silently:**
  * Phone B counts its own steps using its accelerometer.
  * Gyroscope tracks when User B turns corners.
* If User B is tracking Friend A, User B's phone updates Friend A's relative arrow on the screen **purely inside User B's own memory**:
  $$\text{New Arrow} = \text{Old Target Vector} - \text{My Own Steps Taken}$$
* The network is only pinged when a major event occurs (an SOS or periodic 30-second refresh).

---

## Step 6: A New Person Joins ($X$ Joins the Crowd)

```text
Existing Mesh: [A: Hop 0] ── [C: Hop 1] ── [D: Hop 2]
                                                │
                                                ▼ (X walks up with phone)
                                            [New User X]
```

### 6.1 Does User X need to find an anchor or start at zero?
**NO.** User X does not need to know where the original anchor was.
1. User X turns on their phone.
2. User X's phone passively listens to the Bluetooth airwaves for 500 milliseconds.
3. User X hears Phone D broadcasting: `[SOS, Hop 2]`.
4. User X instantly knows: *"I am at Hop 3 relative to that emergency."*
5. **Onboarding latency: 0.5 seconds. Handshakes required: ZERO.**

---

## Step 7: When the Network Splits and Reconnects (Data Mules)

```text
Cluster 1 (Stage Area)                     Cluster 2 (Concessions)
[A: Hop 0] ── [B: Hop 1]                   [E: Hop ?] ── [F: Hop ?]
             \                                 ▲
              \                                │
               ▼                               │
          [Person M walks from Cluster 1 to Cluster 2]
```

1. There is a 50-meter dead zone between the stage and the food stands.
2. Phone M is standing near Cluster 1 and caches the SOS packet: `[SOS 47, Hop 1, Timestamp 21:05]`.
3. Person M walks over to the food stands to buy water.
4. The moment Person M gets within Bluetooth range of Cluster 2, Phone M broadcasts the cached packet.
5. Cluster 2 immediately learns that an emergency exists at the stage, and how old the alert is.
6. **Physical human walking bridges network gaps for free.**

---

## Step 8: The External Responder / Medic (The Full Navigation Flow)

This is the ultimate test of the whole system. A medic arrives from outside the stadium with no prior friends group, no shared map, and no cellular connection.

Here is the exact sequence on the medic's screen:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. GATE ENTRANCE (400 meters away)                                          │
│    Medic's screen: "EMERGENCY DETECTED: HOP 6"                              │
│    Medic walks toward the concourse. Number drops: 6 → 5 → 4.               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. VENUE CONCOURSE (50 meters away)                                         │
│    Medic's screen: "APPROACHING TARGET: HOP 2"                              │
│    Medic enters Section 104. Number drops: 2 → 1.                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. SECTION 104 (15 meters away - The Which Way Problem)                     │
│    Medic's screen prompts: "HOLD PHONE TO CHEST AND TURN 360°"              │
│    Medic spins on the spot.                                                 │
│    Medic's body shields Bluetooth signals until medic faces the victim.     │
│    Screen compass locks: "BEARING: 30° LEFT (ROW G)"                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. ROW G (Last 5 meters in the crowd)                                       │
│    Screen prompts: "LOOK UP: VISUAL RUNWAY ACTIVATED"                       │
│    Victim's phone strobes neon green and rear LED flash pulses.             │
│    Medic spots the flashing light in the crowd. Patient secured!            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Summary: How We Answered All 28 Sub-Questions

| Question Theme | The Exact Answer We Landed On |
| :--- | :--- |
| **How do 2 phones relate?** | Rough distance via BLE signal; direction via torso rotation or walking motion. |
| **What travels through relays?** | Discrete hop counts and emergency IDs (4 bytes total); NOT large vector lists. |
| **How do relationships compose?** | Topologically: $Hop_{\text{new}} = \min(Hop_{\text{neighbors}}) + 1$. Minimum hop always wins. |
| **What happens when nodes move?** | Dead reckoning tracks movement locally on each phone; no network flood. |
| **What happens when relays leave?** | Rolling 8-second expiry caches; mesh re-routes through alternate neighbors. |
| **How does a new device join?** | Passive listening; sniffs neighbor hop tier and increments by 1 instantly. |
| **Do we need Cartesian (X,Y) maps?** | **NO.** Topological hop gradients + local torso direction replace (X,Y) maps entirely. |
