---
title: "15. Engineering Solutions for Real-World Failures"
tags:
  - fixes
  - engineering
  - ios-backgrounding
  - security
created: 2026-09-19
updated: 2026-09-19
---

# 15. Engineering Solutions for Real-World Failures

Following the brutal teardown in [[14_BRUTAL_REAL_WORLD_TEARDOWN_AND_CRITIQUE]], this document provides the concrete engineering fixes required to bridge the gap between theoretical math and real-world deployment.

---

## 🛠️ 1. Fixing PDR Chaos: Activity Recognition (AR) Gating
**The Problem:** Drunk walking, jumping, or putting the phone in a pocket causes Pedestrian Dead Reckoning (PDR) to hallucinate false displacement vectors, destroying the navigation graph.
**The Engineering Fix:**
* Both iOS (CoreMotion) and Android (ActivityRecognitionClient) have highly tuned neural nets for classifying user posture and motion.
* **The Rule:** The app must NEVER broadcast its 2-byte vector displacement unless:
  1. `Activity == WALKING` or `RUNNING`
  2. `Confidence Score > 0.8` (High)
  3. `Phone Posture == IN_HAND_NAVIGATING`
* If the user is in a mosh pit (`Activity == UNKNOWN` or `JUMPING`), the displacement vector is zeroed out (`0x0000`). The mesh falls back purely to the **Topological Hop Gradient** (which is immune to sensor noise).

---

## 🛠️ 2. Fixing iOS Background Throttling: The iBeacon Trojan Horse
**The Problem:** Apple iOS aggressively kills background Bluetooth scanning to save battery, severely fracturing the mesh graph if a large portion of the crowd uses locked iPhones.
**The Engineering Fix:**
* Apple makes an exception for its own proprietary protocol: **iBeacon**.
* iOS will actively wake up a backgrounded app (for about 10 seconds) if it detects an iBeacon UUID that the app is registered to monitor.
* **The Trojan Horse Strategy:** We format the unencrypted 8-byte Public Envelope of our mesh packet to masquerade as an iBeacon advertisement. 
* When a stranger's locked iPhone detects this "iBeacon," the OS wakes up the Crowd Compass app in the background. The app quickly reads the payload, increments the hop count, rebroadcasts it, and goes back to sleep. This bypasses Apple's strict background execution limits.

---

## 🛠️ 3. Fixing Hop-0 Spoofing: Truncated TOTP MACs
**The Problem:** A malicious actor with a high-gain antenna broadcasts a fake `Hop 0` packet, hijacking the Topological Gradient and leading your friends away from you.
**The Engineering Fix:**
* We implement **Outer-Envelope Authentication**. We cannot use a standard 32-byte HMAC because we only have 31 bytes total for BLE legacy ads.
* **The TOTP Solution:** Similar to Google Authenticator. The target generates a Hash-based Message Authentication Code (HMAC) using the shared secret group key and the current Unix Timestamp (divided by 30 seconds). 
* The target takes the first 2 bytes of this HMAC and appends it to the cleartext Public Envelope.
* Strangers forward the packet without knowing what the 2 bytes mean.
* When the searcher receives the packet, they generate the same 2-byte MAC using their shared key and current time. If it matches, they trust the `Hop 0`. If a prankster tries to spoof it, they won't know the key, the MAC will fail, and the searcher will drop the packet.

---

## 🛠️ 4. Fixing the "Torso Spin" Failure: The Hot/Cold Sequential Filter
**The Problem:** The searcher is packed like a sardine in a crowd and physically cannot do a $360^\circ$ torso sweep to find the signal peak.
**The Engineering Fix:**
* **Sequential RSSI Delta (Hot/Cold):** The app detects that the compass is not rotating (the user is stuck). It switches the UI to "Hot/Cold" mode.
* The user takes 2-3 steps forward in whatever direction they are facing. 
* The app calculates the temporal derivative of the signal strength ($\frac{d(RSSI)}{dt}$).
* If $\frac{d(RSSI)}{dt} > 0$ (signal getting stronger), the UI glows Green/Hot. Keep pushing forward.
* If $\frac{d(RSSI)}{dt} < 0$ (signal getting weaker), the UI flashes Red/Cold. The user knows they are walking away from the target and must turn around. 
* This removes the need for physical spinning at the cost of being slightly slower.

---

## 🛠️ 5. Fixing the Broadcast Storm: CSMA/CA Backoff
**The Problem:** 5,000 people realize they are lost at the exact same time after a concert, flooding the 3 BLE advertising channels and causing 100% packet loss.
**The Engineering Fix:**
* We implement **Carrier-Sense Multiple Access with Collision Avoidance (CSMA/CA)** at the application layer.
* **Listen Before Talk (LBT):** When a user hits "Find My Group," the phone does NOT transmit immediately. It listens silently for 3-5 seconds.
* If it hears a beacon from the group already in the mesh, it silently joins the gradient.
* If it hears nothing, it schedules a `DISCOVERY_PROBE`. But instead of sending it instantly, it rolls a random backoff timer (e.g., $100\text{ms} \times \text{Random}(1, 16)$). This staggers the 5,000 probes over a 2-second window, preventing spectrum collapse.
