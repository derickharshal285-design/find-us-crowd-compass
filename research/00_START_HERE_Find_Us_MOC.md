---
title: "Find Us / Crowd Compass — Master Research Map of Content (MOC)"
tags:
  - project/find-us
  - research/crowd-compass
  - architecture/topological-mesh
  - status/active
created: 2026-09-18
updated: 2026-09-18
---

# 🧭 Find Us (Crowd Compass) — Master Research Map of Content (MOC)

> [!IMPORTANT]
> **Core Architectural Axiom:** 
> **Stop trying to solve global coordinates for emergency navigation in offline crowds.** 
> Abandon the global `(0,0)` anchor and vector stacking. Instead, use a decentralized mesh to form a **Topological Hop-Count Gradient Field** outward from the emergency target ($SOS = \text{Hop } 0$). Navigate by gradient descent (decreasing hop number) across macro-distances, and switch to biological shadowing or optical handoffs in the terminal 10 meters.

---

## 📑 Knowledge Base Index

### Core Architecture & Deep Dives
### 1. High-Level Overviews & Onboarding
* [[01_EXECUTIVE_SUMMARY_CONCISE]] — High-level summary of the Crowd Compass / Find Us architecture.
* [[08_PLAIN_ENGLISH_NAVIGATION_GUIDE]] — The simple, jargon-free guide: how every problem is solved using plain, visual ideas.
* [[10_MASTER_CHAT_QA_AND_ONBOARDING_REFERENCE]] — The permanent chat Q&A ledger, plain-English navigation engine from scratch, and dual-compartment encryption.

### 2. Core Physics & Mesh Routing
* [[02_TOPOLOGICAL_GRADIENT_FIELD_PIVOT]] — Why absolute distances fail and why we use a Topological Hop-Count Gradient Field.
* [[06_TINY_PACKET_SPECIFICATION]] — Baseline bit-level wire format specification for the 28–32 bit emergency payload.
* [[20_PACKET_V2_WIRE_FORMAT]] — Definitive 56-bit Packet v2 wire format specification (Age bucket, anti-spoofing 16-bit rolling MAC (amended per Doc 22), (7,4) Hamming FEC, and GAP budget).
* [[09_PROGRESSIVE_NAVIGATION_RESOLUTION]] — Step-by-step resolution of the core progression: from two adjacent phones up to multi-hop, dynamic churn, and outsider rescue.

### 3. Dynamic Mathematics & Kinematics
* [[07_RIGOROUS_CRITIQUE_AND_MATHEMATICAL_CORRECTIONS]] — Formal technical critique, SE(2) Lie group algebra, and trajectory alignment.
* [[11_DYNAMIC_RELATIVE_COORDINATE_MATH_AND_CALIBRATION]] — Mathematical blueprint for dynamic relative coordinates, inter-phone calibration, ego-centric gauge fixing, and spring-mass relaxation.
* [[12_THE_NEWCOMER_PROBLEM_WHY_SLAM_FAILS_AND_HOW_WE_FIX_IT]] — Why pure cooperative SLAM collapses when a newcomer arrives, and the 3-phase handover that fixes it.

### 4. Stress Tests & Reality Checks
* [[03_CRITICAL_PHYSICAL_HAZARDS]] — Deep-dive into physical constraints: Torso shielding, spectrum collapse, Z-axis, and waterbag human attenuation.
* [[04_TERMINAL_NAVIGATION_AND_RADICAL_STRESS_TESTS]] — Stress tests of the 5 candidate mechanisms for terminal navigation ($10\text{m} \to 0\text{m}$).
* [[05_PROBLEM_DEPENDENCY_AUDIT_12_SUBPROBLEMS]] — Rigorous breakdown of the 12 ordered sub-problems + identity rotation & adversarial trust.
* [[13_THE_VECTOR_DISPLACEMENT_REALITY_CHECK]] — Why hop-by-hop vector stacking fails (missing radio angles, stranger drift) and the Target-Displacement Shortcut Engine that solves it.
* [[14_BRUTAL_REAL_WORLD_TEARDOWN_AND_CRITIQUE]] — A zero-sugar-coating, worst-case-scenario teardown of the architecture's vulnerabilities (PDR chaos, iOS backgrounding, spoofing).
* [[15_ENGINEERING_SOLUTIONS_FOR_REAL_WORLD_FAILURES]] — Comprehensive engineering fixes for the critical failures identified in the teardown.
* [[16_TECHNICAL_NAVIGATION_EDGE_CASES_AND_HETEROGENEITY]] — Mathematical fixes for device antenna heterogeneity, pocket/purse pose misalignment (PCA), and multi-target group centroids.
* [[17_DATA_MULE_MESH_PARTITION_HEALING_FOR_FRAGMENTED_CROWDS]] — Delay-Tolerant Networking (DTN) and pedestrian store-and-forward muling to bridge disconnected crowd islands.
* [[18_BLE_ADVERTISING_TRANSPORT_REALITY]] — Independently verified physical transport facts: 31-byte legacy limits, channel hopping, and OS background constraints.
* [[19_ASYNC_SCHEDULE_MESH_OPERATING_MODEL]] — Asynchronous mesh operating model, iOS Service-UUID fix (23B budget), empirical OS wake rates, and critique of Doc 06.
* [[21_ASYNC_TRICKLE_MESH_DESIGN]] — Asynchronous Trickle mesh architecture: percolation breakdown analysis, sweep breaking point, and Epoch-Synchronized Burst Windows (ESBW) protocol redesign.
* [[22_ANTI_SPOOFING_ENVELOPE_MAC]] — Anti-spoofing envelope MAC decision matrix: black-hole attack model, 16-bit truncation mandate (0.15% forgery @100 msgs), and Doc 20 amendment.
* [[23_RF_CONFIRMATION_WALL_ALERTS]] — Multipath wall-alert fusion detector: single-sniff RSSI catastrophes vs multi-second statistical windows (94.73% accuracy, 0% FPR).
* [[24_STORM_BACKOFF_PROTOCOL]] — End-of-event discovery-probe storm: passive listen + CSMA/CA backoff + k=1 passive suppression (100% discovery in 60 s, 87.3% collision reduction).
* [[25_PDR_ACTIVITY_GATING_SPEC]] — Activity-Recognition Gated PDR: 5-stage sensor-fusion filter (posture, accel var, cadence, gyro, mag) eliminating 100% of mosh/pocket false vectors and restoring navigation lock to 100%.
* [[26_TERMINAL_HANDOFF_PROTOCOL]] — Terminal Handoff Protocol: Torso cardioid shadowing + 3-step Hot/Cold verification walk for near-field obstacle clearance and flip ambiguity resolution (<30° bias, 98.26% arrival).
* [[27_GHOST_GRADIENT_RESOLUTION]] — Ghost Gradient Resolution: Wire metadata, 16-bit MAC origin invariance, Epoch Cadence Delta Gating, and ETUI partition ingress arc navigation (0.0 false alerts, 0% misled rate, 0% FNR).
* [[28_MULTILEVEL_BARO_AND_STAIRWELL]] — Multi-Level Barometric Navigation & Stairwell Geometry: RF ceiling shadow trap resolution, floor-aware receiver gating, and cross-OS turnstile calibration (100% arrival, 0% ceiling entrapment, 0.244 floor MAFE).
* [[29_IMPLEMENTATION_BLUEPRINT_V1]] — Master Implementation Blueprint v1 (Vol 1: Research Complete): Canonical synthesis of B-01..B-10, bit tables, node state machines, responder guidance pseudocode, global failure mode matrix, and multi-year tech-risk register.
* `refimpl_spec.md` — Concise, machine-readable reference implementation specification (<250 lines) for autonomous build agents and engineering teams.

---

## 🔬 Autonomous Research Engine (Autoresearch)
* `research-state.yaml` — Central state machine tracking hypotheses, metrics, and loop progress.
* `research-log.md` — Timestamped decision log and hypothesis trajectory.
* `findings.md` — Synthesized research narrative and verified empirical conclusions.
* `literature/survey.md` — Academic literature review (DTN routing, RFC 6206 Trickle, 2.4 GHz human shadowing, BLE mesh specifications, smartphone PDR drift).
* `experiments/` — Simulated experimental protocols, empirical results, and ablation studies:
  * `[[experiments/H1-topological-gradient-vs-vector-chain/analysis|H1: Topological Gradient vs. Vector-Chain Compounding Error]]`
  * `[[experiments/H2-inhibitory-protocol-vs-spectrum-collapse/analysis|H2: Inhibitory Trickle Suppression vs. Spectrum Collapse]]`
  * `[[experiments/H3-biological-shadowing-directional-resolution/analysis|H3: Human Body Torso Shadowing for Local Directionality]]`
  * `[[experiments/H9_DATA_MULE_PARTITION_HEALING/RESULTS|H9: Data Mule Partition Healing & Ghost Gradient Characterization]]`
* `to_human/` — Visual reports and executive summaries:
  * `[[to_human/PROGRESS_REPORT|Latest Progress Report]]`
  * [Interactive Simulation Dashboard](to_human/dashboard.html)
* `paper/` — Monograph draft: *Topological Hop Gradients and Biological Shadowing for Emergency Localization in Denied Smartphone Meshes*.

---

## 🗺️ Architectural Topology at a Glance

```mermaid
flowchart TD
    subgraph S1["Level 0: Emergency Target"]
        SOS["🚨 SOS Target (Hop 0)<br/>Barometer Reference P_0"]
    end

    subgraph S2["Level 1: Topological Gradient Field (Macro Layer)"]
        H1["Hop 1 Devices (Ring 1)"]
        H2["Hop 2 Devices (Ring 2)"]
        H3["Hop 3 Devices (Ring 3)"]
        H4["Hop 4 Devices (Ring 4)"]
        RESP["🏃 Responder Enters at Hop 4"]
    end

    subgraph S3["Level 2: Inhibitory Protocol (Anti-Collapse)"]
        TRICKLE["Trickle-Suppression Window<br/>k-redundancy threshold = 3<br/>Jitter: 50–250 ms"]
    end

    subgraph S4["Level 3: Terminal Localization (Micro Layer: Last 10m)"]
        SHADOW["Synthetic Lighthouse<br/>(Torso Biological Shadowing: 15–20 dB Attenuation)"]
        OPTICAL["Visual Runway<br/>(Screen Strobe / Flashlight on Hop 1)"]
    end

    SOS -->|BLE Adv (Tiny Payload: 28 bits)| H1
    H1 -->|Suppressed Rebroadcast| H2
    H2 -->|Suppressed Rebroadcast| H3
    H3 -->|Suppressed Rebroadcast| H4
    
    RESP -->|1. Follow Decreasing Hop Count| H3
    H3 -->|2. Follow Decreasing Hop Count| H2
    H2 -->|3. Follow Decreasing Hop Count| H1
    H1 -->|4. Switch to Terminal Layer| SHADOW
    SHADOW -->|5. Look Up & Identify| OPTICAL
    OPTICAL --> SOS

    TRICKLE -.->|Regulates Transmission| H1
    TRICKLE -.->|Regulates Transmission| H2
    TRICKLE -.->|Regulates Transmission| H3
```

---

## ⚡ Quick Reference: Why Old vs. New?

| Design Axis | The Original Vector-Chain Approach | The Pivoted Gradient Field Approach |
| :--- | :--- | :--- |
| **Spatial Model** | Continuous 2D/3D Euclidean coordinate space ($x, y, z$) | Discrete topological hop distance field ($\mathbb{N}_0$) |
| **Reference Origin** | Arbitrary anchor phone `(0,0)`; requires pre-shared session | The SOS emitter itself dynamically establishes `Hop 0` |
| **Relay Mechanics** | Each node appends vector $(\Delta x, \Delta y, \theta)$; payload bloats | Payload is immutable size (~28 bits): `[SOS_ID][HOP][BARO]` |
| **Compounding Error** | Exponential: $5^\circ$ compass + 2m distance error explodes in 4 hops | **Zero compounding coordinate error**: topology is discrete |
| **Outsider / Medic Entry** | Unusable: medic has no shared coordinate reference | Instant: medic reads incoming hop packets and follows $N \to 0$ |
| **Terminal Resolution** | Assumes math points to a coordinate dot | Uses Torso Shadowing + Optical Strobing in the last 10m |
