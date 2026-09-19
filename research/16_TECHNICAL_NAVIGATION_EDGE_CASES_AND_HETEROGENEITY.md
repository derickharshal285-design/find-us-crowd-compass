---
title: "16. Technical Navigation Edge Cases and Device Heterogeneity"
tags:
  - edge-cases
  - heterogeneity
  - device-pose
  - multi-target
created: 2026-09-19
updated: 2026-09-19
---

# 16. Technical Navigation Edge Cases and Device Heterogeneity

While we have secured the core topological routing and dynamic relative math, there are three lingering, highly technical navigation problems that arise from the fact that we are dealing with commodity consumer hardware (smartphones) rather than calibrated robotics sensors.

This document identifies these final edge cases and provides the mathematical and engineering fixes for each.

---

## 🛑 Problem 1: Device Heterogeneity (The Antenna Gain Mismatch)
**The Problem:**
An iPhone 15 Pro Max and a $100 budget Android phone have completely different Bluetooth antenna designs, casing materials, and transmit power (Tx) outputs. 
* If an iPhone receives a signal at $-80\text{ dBm}$, the target might be $15\text{m}$ away. 
* If the cheap Android receives the exact same $-80\text{ dBm}$ signal, the target might only be $5\text{m}$ away.
If we use raw RSSI for Micro-Navigation ($10\text{m} \to 0\text{m}$) without accounting for hardware, the relative coordinate map will warp, stretching and compressing distances based on what phone the person bought.

**The Fix: The "Two-Point Handshake Calibration"**
* We cannot hardcode lookup tables for 10,000 different Android models. We must calibrate dynamically.
* **The Solution:** We use a purely mathematical **Path Loss Exponent (PLE) Estimation**. 
* As a searcher walks toward a target, they record a time-series of RSSI values alongside their own PDR displacement (e.g., "I walked 2 meters, and RSSI changed from $-85$ to $-79$").
* By comparing the known physical distance walked (via pedometer) with the $\Delta \text{RSSI}$, the searcher's phone mathematically solves for the unknown antenna gain coefficient of the target's phone in real-time. The map scales itself correctly within 3-4 steps.

---

## 🛑 Problem 2: Device Pose Misalignment (The Purse/Pocket Problem)
**The Problem:**
Pedestrian Dead Reckoning (PDR) relies on the compass to know which way the user stepped. However, the compass measures the orientation of the *device*, not the *human*.
* If the user puts their phone sideways in a purse and walks North, the phone's compass might be pointing East. 
* If the app blindly trusts the compass, it thinks the user walked East. The displacement vector becomes mathematically rotated by $90^\circ$, completely corrupting the relative map.

**The Fix: Principle Component Analysis (PCA) on the Accelerometer**
* Human walking generates a very specific acceleration pattern (the forward/backward sway of a leg or purse).
* **The Solution:** We run a lightweight PCA algorithm over a 2-second window of accelerometer data to find the **Vector of Principal Variance**. 
* The axis with the highest variance is mathematically guaranteed to be the direction of human travel, regardless of how the phone is rotated in the pocket. 
* We calculate the offset angle between this PCA vector and the magnetometer North, yielding the **Pose Misalignment Angle ($\theta_{\text{offset}}$)**. We apply a rotation matrix $R(-\theta_{\text{offset}})$ to all PDR vectors before broadcasting them, perfectly aligning the phone's frame of reference with the human's frame of reference.

---

## 🛑 Problem 3: The Multi-Target "Centroid" Dilemma (Group Splitting)
**The Problem:**
The architecture assumes one Searcher finding one Target. But what if a group of 6 people goes to a festival, and they scatter into three pairs? 
* If everyone is broadcasting `Hop 0`, the gradient field becomes a chaotic terrain with three different "valleys" (sinks).
* A searcher following the gradient won't know *which* part of the group they are being routed to.

**The Fix: Bit-Masked Sub-Targeting & Centroid Gravity**
* We have 4 bytes (32 bits) in the payload. We allocate **3 bits for a `Member ID`** (supporting groups up to 8 people).
* The Public Envelope now looks like: `[GroupHash (16 bit) | MemberID (3 bit) | HopCount (5 bit) | TTL (8 bit)]`.
* **The Solution:** Instead of a single gradient, the mesh effectively multiplexes up to 8 parallel gradients. The searcher's app aggregates these gradients.
* The UI presents a **Multi-Target Heatmap**. The user can either select a specific `Member ID` to route to, or the app calculates the **Topological Centroid** (the geographic middle of the group based on intersecting hop gradients) and routes the user to a centralized meeting point that is equidistant for everyone.
