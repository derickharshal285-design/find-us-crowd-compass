---
title: "04. Terminal Navigation & Radical Architecture Stress Tests"
tags:
  - project/find-us
  - architecture/terminal-navigation
  - stress-tests/physics-engine
  - stress-tests/synthetic-lighthouse
  - stress-tests/acoustic-ripple
created: 2026-09-18
updated: 2026-09-18
---

# 04. Terminal Navigation & Radical Architecture Stress Tests

> [!ABSTRACT]
> Macro mesh navigation safely guides a responder from $500\text{ meters}$ down to the immediate vicinity of the emergency ($\sim 10\text{--}15\text{ meters}$, Hop 1). However, at Hop 1, BLE radio waves become chaotic, with multipath and human crowding obscuring whether the victim is standing $2\text{ meters}$ in front, behind, or to the side.
> 
> Here we systematically evaluate **five radical concepts** for terminal localization, isolate their smallest concrete failure points, and select the survivable architecture.

---

## The 5 Radical Architecture Stress Tests

```text
┌────────────────────────┬───────────────────────────────┬────────────────────────────────┐
│ Radical Concept        │ Core Mechanism                │ Smallest Concrete Failure Point│
├────────────────────────┼───────────────────────────────┼────────────────────────────────┤
│ 1. The Physics Engine  │ 2D mass-spring "rubber band"  │ FLIP AMBIGUITY: Graph folds    │
│    (Graph Rigidity)    │ simulation from noisy RSSI    │ 180° inverted; wrong direction │
├────────────────────────┼───────────────────────────────┼────────────────────────────────┤
│ 2. The RF Cocktail     │ Match static BSSID/beacon     │ TEMPORAL VOLATILITY: In crowds,│
│    (Fingerprinting)    │ signal similarity vector      │ moving wearables skew signature│
├────────────────────────┼───────────────────────────────┼────────────────────────────────┤
│ 3. Synthetic Lighthouse│ Rotate phone against torso;   │ CONCRETE MULTIPATH: Strong wall│
│    (Torso Shadowing)   │ use body as 20 dB shield      │ reflections create phantom dip │
├────────────────────────┼───────────────────────────────┼────────────────────────────────┤
│ 4. Acoustic Ripple     │ Microsecond phase-shift of    │ OS SCHEDULING JITTER: iOS/     │
│    (Ultrasound Time)   │ high-frequency audio chirps   │ Android audio buffer lags >20ms│
├────────────────────────┼───────────────────────────────┼────────────────────────────────┤
│ 5. "Look Up" Runway    │ Silent screen & LED strobe on │ THE POCKET VETO: Screen locked │
│    (Optical Handoff)   │ Hop 1 bystander phones        │ in pocket; OS background blocks│
└────────────────────────┴───────────────────────────────┴────────────────────────────────┘
```

---

## Stress Test 1: The Physics Engine (The "Rubber Band" Graph Rigidity)

### The Mechanism
Phones act as nodes in a 2D mass-spring physics engine. An observed pairwise RSSI is mapped to a resting spring length $L_0 = f(\text{RSSI})$. The simulation runs Verlet integration on the phone CPU until the network reaches mechanical equilibrium.

### The Smallest Concrete Failure: The Flip Ambiguity
Distance measurements are symmetric: $\operatorname{dist}(A, B) = \operatorname{dist}(B, A)$. 
* In graph theory, distance matrices can produce isometric embeddings with **reflectional symmetry** (chirality inversion).
* Without an external global orientation anchor (like a calibrated magnetic north common to all devices), the spring-mass relaxation can collapse into an inverted mirror image.
* **The Fatal Consequence:** The solver settles into a mathematically perfect local energy minimum, but the generated arrow points $180^\circ$ away from the real victim.

### Verdict: REJECT AS PRIMARY; ACCEPT AS LOCAL RELAXATION ONLY
Graph rigidity requires Laman graphs with high degree ($\ge 3$ non-collinear anchors per sub-cluster). In an ad-hoc emergency crowd, graph density is too sparse and non-uniform to guarantee chirality resolution.

---

## Stress Test 2: The RF Cocktail (Environmental Fingerprinting)

### The Mechanism
When the victim hits SOS, their phone scans the local ambient 2.4/5.0 GHz spectrum, creating a fingerprint vector:
$$\vec{F}_{\text{target}} = \left[ (BSSID_1, \text{RSSI}_1), (BSSID_2, \text{RSSI}_2), \dots \right]$$
As the responder approaches, their phone continually scans and computes the Cosine Similarity or Euclidean Distance between $\vec{F}_{\text{responder}}$ and $\vec{F}_{\text{target}}$.

### The Smallest Concrete Failure: Temporal Wearable Volatility
In a stadium or festival, $80\%\text{--}90\%$ of detected BLE/Wi-Fi devices are consumer smartwatches, fitness bands, and mobile hotspots.
* People dance, walk to concessions, or rotate their bodies.
* Within 5 minutes, $60\%$ of the BSSIDs present during the original SOS have moved or dropped below receiver threshold.
* Furthermore, mobile operating systems (iOS and Android) randomize their advertising MAC addresses every 15–20 minutes.

### Verdict: RESTRICTED COMPONENT ONLY
Fingerprinting works **only** if the app can strictly isolate static venue infrastructure (e.g., permanent enterprise APs with static BSSIDs or fixed stadium DMX lighting bridges). As a pure peer-to-peer crowd mechanism, it is too volatile.

---

## Stress Test 3: The Synthetic Lighthouse (Biological Torso Shadowing)

```text
       Target Transmitter (Hop 0/1)
                   📱
                   ▲
                   │  2.4 GHz Direct Wave
                   │
                   📱  Phone Held Against Sternum
              ╭─────────╮
              │  Chest  │  [Zero Torso Attenuation: RSSI = -68 dBm]
              │  (You)  │
              ╰─────────╯
                   ▲
                   │  Turn 180° Away
                   │
              ╭─────────╮
              │  Back   │  [20 dB Torso Attenuation: RSSI = -88 dBm]
              │  (You)  │
              ╰─────────╯
                   📱  Phone Shielded by Torso
```

### The Mechanism
A single smartphone antenna is omnidirectional ($\sim 0\text{ dBi}$ gain). However, human tissue has high water content and absorbs $15\text{--}25\text{ dB}$ of $2.4\text{ GHz}$ energy.
* When the responder holds the smartphone firmly flat against their sternum, the phone's antenna is shielded from behind by the user's $30\text{ cm}$-wide torso.
* The user plus phone forms a **directional cardioid receiver**.
* When the user rotates in a complete circle ($360^\circ$ over 3–5 seconds), the phone's gyroscope correlates azimuth $\phi \in [0, 360^\circ)$ with sampled beacon RSSI.
* The maximum RSSI corresponds to the front-facing direction toward the emitter (zero body blockage). The minimum RSSI ($180^\circ$ opposite) corresponds to maximum body absorption.

### The Smallest Concrete Failure: Severe Multipath in Metallic Enclosures
In an enclosed room surrounded by corrugated steel walls or heavy metal staging, the reflected multipath wave from behind the responder can be stronger than the direct wave blocked by multiple bodies.
* In an open stadium or grass field, multipath is low ($< -10\text{ dB}$ relative to direct path), and torso shadowing achieves an angular accuracy of $\pm 25^\circ$.
* In a metallic shipping container, angular error degrades to random noise.

### Verdict: ADOPT AS PRIMARY LOCAL DIRECTIONAL MECHANISM
Biological shadowing is the only zero-hardware method that gives an ordinary single-antenna smartphone directional bearing to an RF beacon in an ad-hoc crowd.

---

## Stress Test 4: The Acoustic Ripple (Ultrasonic Phase-Shift)

### The Mechanism
Nodes emit an inaudible high-frequency acoustic chirp ($18\text{--}21\text{ kHz}$) from the loudspeaker. Neighboring phones record via the microphone and compute Time Difference of Arrival (TDOA) to achieve centimeter-scale acoustic ranging.

### The Fatal Flaw: OS Audio Buffer Scheduling Jitter
1. **Operating System Latency:**
   * Modern smartphone OSs (iOS AudioUnit and Android AAudio/AudioTrack) process audio in hardware buffers (typically 256 to 1024 frames).
   * A single buffer cycle introduces $5.8\text{ to } 23.2\text{ milliseconds}$ of scheduling jitter, compounded by power-saving CPU frequency scaling.
   * Sound travels at $343\text{ m/s}$ ($0.343\text{ mm/\mu s}$). A $10\text{ millisecond}$ OS scheduling delay translates to a **3.43-meter ranging error**!
2. **Concert Acoustic Environment:**
   * A live music concert features high-SPL sound reinforcement ($100\text{--}115\text{ dB}$ SPL) with rich harmonic distortion extending past $20\text{ kHz}$ from cymbals, synthesizers, and crowd screams.
   * The phone's microphone automatic gain control (AGC) instantly clamps input gain to prevent clipping, completely burying a micro-chirp in the noise floor.

### Verdict: REJECT AS CORE ARCHITECTURE
Acoustic ranging is unusable in concert venues and cannot survive mobile OS scheduling jitter without dedicated real-time DSP hardware.

---

## Stress Test 5: The "Look Up" Runway (Visual Mesh Handoff)

### The Mechanism
When the responder reaches **Hop 1** (within $10\text{--}15\text{ meters}$ of the target), the responder's phone broadcasts an encrypted BLE command: `TRIGGER_RUNWAY(SOS_ID)`.
* Phones within Hop 1 that have line-of-sight immediately turn their displays to maximum brightness neon green or pulse their LED torch in a synchronized strobing pattern ($4\text{ Hz}$).
* The responder stops looking at the screen, looks up at the crowd, and immediately spots the illuminated cluster.

### The Smallest Concrete Failure: The "Pocket Veto" & OS Permissions
1. **The Pocket Veto:** $75\%\text{--}85\%$ of bystander phones in a crowd are locked inside pockets or bags. Turning on a screen or flashlight inside a pocket is useless and drains battery.
2. **OS Privacy Locks:** iOS and Android strictly prohibit background applications from waking the screen or turning on the LED flashlight without explicit user interaction (camera/torch permission).

### Architectural Solution: Ambient Light Sensor Gating + Notification Banner
1. The app queries the phone's **Ambient Light Sensor (ALS)**. If ALS $< 5\text{ lux}$ (inside pocket/purse), the strobe command is suppressed.
2. If ALS $> 20\text{ lux}$ (phone is being held in hand or used):
   * On Android: A high-priority system overlay displays a flashing full-screen emergency banner.
   * On iOS: A high-priority Critical Alert notification banner vibrates and illuminates the lock screen.
3. The victim's own phone (which initiated the SOS) is explicitly overridden to maximum screen brightness and rear torch pulse, because the user voluntarily hit the SOS button.

### Verdict: ADOPT AS WINNING TERMINAL IDENTIFICATION LAYER
When combined with Biological Shadowing to face the correct section, the visual strobe allows instant human recognition within the final 10 meters.
