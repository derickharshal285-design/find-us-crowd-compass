# FIND US — RESEARCH BLUEPRINT & LITERATURE / PRIOR-ART MAP

**Working title (v0.1):** *Find Us: A Distributed Infrastructure-Independent Smartphone Crowd System for Emergency Communication, Spatial Awareness, Relative Localization and Navigation*

**Document type:** Research blueprint — Phase 1 (system decomposition) and Phase 2 (research gap + prior-art map) of the master research program. Intended to feed the manuscript section-by-section. **Not** a finished paper.

**Date:** 2026-09-21
**Version:** 0.1

---

## 0. How to read this document

This blueprint is the honest, evidence-tagged foundation for the Find Us research program. Every layer of the system is decomposed below, marked with a **status-classification ladder**:

> THEORETICAL → MATHEMATICALLY DEFINED → SIMULATED → UNIT TESTED → INTEGRATION TESTED → REAL BLUETOOTH HARDWARE TESTED → REAL MULTI-PHONE TESTED → CONTROLLED CROWD TESTED → REAL-WORLD VALIDATED → NOT YET IMPLEMENTED

and with the **7-band distinction** that must appear everywhere in the final manuscript:

| Band | Meaning in Find Us |
|---|---|
| WHAT ALREADY EXISTS | Established technology / prior art (cited) |
| WHAT WE PROPOSE | Design meant to be validated |
| WHAT WE IMPLEMENT | Code that exists in this repository |
| WHAT WE EXPERIMENTALLY TEST | Simulated / unit-tested results from the research log |
| WHAT THE RESULTS SHOW | Concrete numbers, conditions attached |
| WHAT FAILED | Documented negative results |
| WHAT MAY BE NOVEL | Unclaimed combos — for scrutiny, not assertion |

**Integrity rules used here and in the manuscript:** nothing is elevated one ladder rung higher than the evidence supports; every `[EXPERIMENT REQUIRED]`, `[CITATION REQUIRED]`, `[IMPLEMENTATION VALIDATION REQUIRED]`, `[RESULTS REQUIRED]` marker is deliberate; no fabricated results; no invented citations.

---

## 1. Central research question (one line to challenge, not to assume)

> Can ordinary heterogeneous smartphones cooperate in a dense crowd to provide useful emergency communication, distributed spatial awareness, relative localization and emergency navigation *without depending fundamentally* on fixed infrastructure, continuous Internet connectivity, cellular service, or GPS?

The first clause is deliberately broad: **the entire Find Us system is the research subject**, not the navigation stage alone.

---

## 2. Phase 1 — Complete system decomposition

The system is decomposed into the layers used in the master instruction. For each layer: statement of the problem, the mechanism(s), current status per device in the repo, the evidence base, and the honest limits.

### 2.1 Communication architecture
- **Role:** phones already in a crowd discover each other and exchange tiny packets with no infrastructure. Range: BLE legacy advertising (31-byte AdvData ceiling; 27 usable data bytes for AD Type 0xFF, 29 for a custom AD type) and the iOS background-safe ceiling of **23 bytes** (31 − 4-byte Service-UUID AD − 4-byte AD header) [Doc 18].
- **Mechanisms:** discovery (advertise/scan), Dual-AD dual-advertisement structure (Service UUID `0xFC00` + Manufacturer Data), asynchronous push/lazy operation, RPA (resolvable private address) rotation to defeat iOS duplicate coalescing.
- **Status:** mathematically defined + partially simulated/wiki-documented. iOS background filter and 23-byte ceiling: derived from Apple CoreBluetooth constraints [Doc 18]; some numbers in `data/` artifacts are **modeled, not measured on hardware** `[EXPERIMENT REQUIRED]`.
- **Correctness guardrails:** "BLE mesh is not novel" — existing mesh and opportunistic systems are cited in §3. What Find Us adds is carrying and reasoning over *spatial relationship information*, not the relay transport itself `[CITATION REQUIRED per specific claim]`.

### 2.2 BLE networking / crowd mesh
- **Problem:** A→B→C→D phone-relay operation in a dense, moving crowd; collision, churn, partitions.
- **Mechanisms (all in `research/` docs, mostly simulated):**
  - *K=3 inhibitory Trickle suppression* (RFC 6206 adapted) — simulated 90.0–91.0% redundant-transmission reduction at ≤2,000 nodes.
  - *Adaptive jitter scaling* `T_max ∝ log₂ N` for >2,000-node flash mobs — simulated: 96.2% delivery at 1,000 nodes, 74.8% at 2,500.
  - *ESBW (Epoch-Synchronized Burst Windows)* — 15 s epochs / 10 s bursts / ~47 packets per window; restores coverage to 99.86% and delivery to 99.98% even at 70% background-locked iOS nodes (simulated).
  - *Cold-start storm avoidance* — 5 s passive listen, U(0,60 s) urgence backoff, K=1 discovery suppression — simulated 100% discovery in 60 s, 12.4% overall collision.
  - *Mode ladder:* NORMAL (low radio activity) → RELEVANT (increased activity) → SOS (high-priority participation) → NO LONGER RELEVANT (return to low power). **This adaptive BLE participation ladder is proposed; battery and latency trade-offs are `[EXPERIMENT REQUIRED]`.**
- **Density evidence used:** naive flooding at 5,000 nodes → 97.7% collision (simulated); percolation cliff between 30% and 50% background-locked nodes (simulated).
- **Status:** SIMULATED. No real multi-phone BLE measurement in repo `[REAL BLUETOOTH HARDWARE TESTED: gap]`.

### 2.3 Packet & protocol design
- **Packet v2 (Packet v2 wire format, Doc 20/22):**
  - Raw payload **56 bits (7 bytes)**; expands to **13 bytes** under nibble-wise systematic Hamming (7,4) FEC.
  - Fields: `SOS_ID`, `HOP`, `BARO_DIFF` (6-bit two's complement @ 0.5 hPa/LSB, ±135 m), `FLAGS`, `EPOCH` (4-bit), `PKT_TYPE` (4-bit), `AGE` (2-bit), `ENVELOPE_MAC` (**16-bit**, at `[55:40]`).
  - MAC: HMAC-SHA256 over origin invariants `(SOS_ID || EPOCH || PKT_TYPE)` keyed by incident-session key, truncated to 16 bits.
  - Dual-AD-compatible; Packet v2 fits the 23-byte iOS background ceiling with 10 B slack.
- **Why 16-bit MAC:** simulation — 8-bit MAC defeated; 12-bit fails 2.4% (100-msg epoch); 16-bit → 0.15–0.18% forgery acceptance; only width with >5× margin under the <1% target [Doc 22].
- **Status:** MATHEMATICALLY DEFINED + SIMULATED + UNIT TESTED (canonical vector `17a53ee2998f42` round-tripped across 100,000 randomized cases, packet_v2.py). Actual over-the-air BER/retransmission behavior `[EXPERIMENT REQUIRED]`.
- **Protocol v3 codec (implemented `core/protocol.py`):** 35-byte header, 8-byte auth tag, message types HEARTBEAT/ADVERTISEMENT/SOS/SOS_UPDATE/RELAY/RELATIONSHIP/CAPABILITY/JOIN(1–8), measurement blocks with explicit-null rule. **Note:** this codec and the simulation Packet v2 differ in framing; consolidate before the manuscript (see §5 "open conflicts").

### 2.4 SOS / emergency propagation
- **Concept:** SOS origin = Hop 0; neighbors = Hop 1; gradient radiates outward. **Hop count is topology, not physical distance** (a permanently documented distinction).
- **State model (defined in repo):** SOS ID, event version/sequence, hop, last-heard, expiry, origin invariant, per-event gradient; multiple simultaneous events supported.
- **Ghost-gradient resolution (Doc 27 / exp_013):** when data mules carry cached Hop-0 packets over a 200 m dead zone, naive store-and-forward bursts create 331.7–11,207.5 false Hop-1 alerts and mislead 46–100% of searchers. Multi-layer decision rule (16-bit MAC origin invariance + EPOCH cadence delta gating `ΔEpoch ≥ 2` + `MULE_STORE_FORWARD` flag + frozen-epoch detector) → 0.0 false alerts, 0.0% misled, 94–100% partition healing delivery, 0.00% FNR on co-located live targets (simulated).
- **One design to surface in the paper as a question, not an answer:** whether hop-count-only propagation is sufficient when the gradient is one of *several* simultaneous events `[EXPERIMENT REQUIRED]`.

### 2.5 Sensing system
- **Available-sensor heterogeneity modeled explicitly** (Phone A: BLE+IMU+compass; B: BLE+IMU; C: BLE+UWB; D: BLE-only; E: BLE+camera).
- **Per-sensor status:**
  - BLE RSSI: proximity hint only, NOT a distance metre and NOT the routing gradient. Supported by body-shadowing literature; in-repo simulations assume RSSI noise but **no real-crowd RSSI dataset** `[EXPERIMENT REQUIRED]`.
  - IMU/PDR: AR-gated (5-stage, 2.0 s window @50 Hz) — simulated 100% false-vector suppression, 9.86× drift reduction. Real IMU data `[EXPERIMENT REQUIRED]`.
  - Magnetometer/compass: an *orientation aid*, not a crowd-usable global compass; drift/magnetic interference `[EXPERIMENT REQUIRED]`.
  - Barometer: 6-bit BARO_DIFF for floors; cross-OS factory bias ±2.0 hPa documented; Entrance-Gate Baseline Snapshot restores ±1-floor to 100% / MAFE 0.244 (simulated).
  - BLE direction finding (AoA/AoD), UWB, Wi-Fi, camera, acoustic: **research options**; hardware/API availability must be probed per device and platform; not core requirements. Acoustic terminal guidance already assessed as unviable in >110 dB SPL concert noise (documented negative result).

### 2.6 Relative localization
- **Model:** relationship B→A = vector + uncertainty + timestamp + source; distance alone insufficient for direction.
- **Vector-displacement reality check (Doc 13/07):** is SE(2) composition mathematically sound, but *orientation frames differ across phones*; composing raw local vectors without frame alignment is wrong. Mirror-flip/rank-deficient ambiguity documented; co-motion turning constraints proposed to break it.
- **Implemented:** `core/relationships.py` `compose()` — propagates weakest-hop `tier` and quadrature `bearing_uncert_deg`; RelationshipStore soft/hard expiry (60 s / 300 s); source-tagged merge. `core/direction.py` — DirectionSweep, BearingFusion (reciprocal boost), StationarityGate, OobSideband; 21 selftest checks; cross-language (Kotlin/Swift) parity. **Gaps:** bearing estimates derive from torso-shadowing models `[EXPERIMENT REQUIRED]`; uncertainty calibration against ground truth `[EXPERIMENT REQUIRED]`.

### 2.7 VRLG / dynamic spatial graph
- **Model:** `G(t) = (V, E(t))`; edges carry distance, bearing, vector, uncertainty, timestamp, source, confidence, validity; composition `A→C ≈ (A→B)+(B→C)` **with uncertainty propagation**.
- **Status:** MATHEMATICALLY DEFINED + PARTIALLY SIMULATED/UNIT TESTED (compose tier/uncertainty propagation exists). **VRLG is not an established invention; novelty is a research question** (see §3 IP-adjacent). Loop closure / consistency mechanisms not yet computationally tested for find-us use `[EXPERIMENT REQUIRED]`.

### 2.8 Graph consistency
- **Proposal:** `V_AB + V_BC + V_CA ≈ 0`; loop error as a detector for bad measurements, sensor failures, malicious information, drift, staleness.
- **Status:** THEORETICAL → MATHEMATICALLY DEFINED. Robotics prior art (PCM, loop-odometry consistency) is highly relevant; **in-repo experiment absent** `[EXPERIMENT REQUIRED]`.

### 2.9 Dynamic topology
- **States:** join, leave, move, disappear, fail, relay fails, network splits, reconnects, components merge, responder enters late.
- **In repo:** SOS graph handles partition healing (mules, ghost-gradient suppression); graph lifecycle (DISCOVERED→ACTIVE→STALE→EXPIRED); edge aging. Simulation scenarios for split/reconnect partially modeled.
- **Gaps:** late-responder frame acquisition beyond SOS hop learning; consistent spatial-frame merging after two separate components meet (a core open problem, see §5).

### 2.10 Anchor / reference-frame problem
- **Decision:** no permanent anchor; SOS event is a temporary logical reference; relative relationships are primary. A local `(0,0)` may be useful internally but must not be assumed known by later entrants.
- **Remaining research:** frame alignment, coordinate transformation, graph merging, temporary anchors, dynamic references — THEORETICAL `[EXPERIMENT REQUIRED]`.

### 2.11 Navigation
- **Mechanism:** multi-stage — (macro) discrete hop-gradient descent + baro floor gating; (local) torso-shadowing bearing + 3-step walk ambiguity clearance; (terminal) optical strobe runway + localized audio-haptic prompts.
- **Simulated evidence (H1):** topological descent achieves 100.0% arrival from hops 1–11 in 200×200 m venue (50 Monte Carlo runs) vs vector-chain >10.9 m error. Terminal handoff: arrival ≤5 m 88.4% (blocked) / up to 98.3% (bias <30°).
- **Honest status:** SIMULATED geometry/mobility models; **no human-in-the-loop physical navigation trial** `[EXPERIMENT REQUIRED]`.
- **Routing-objective separation:** shortest-path vs lowest-uncertainty vs fewest-hops vs most-stable vs energy — deliberately NOT collapsed into one score; a single-score model requires justification `[CITATION REQUIRED / EXPERIMENT REQUIRED]`.

### 2.12 Terminal localization
- **Ladder:** coarse (topology) → medium (relative graph) → local (higher-resolution sensing) → terminal (UWB / BLE DF / acoustic / optical / camera / signal patterns — research options; acoustic assessed as unviable at concert SPL — documented negative).
- **Status:** partially simulated (torso scan + strobe runway); real-device terminal tests `[EXPERIMENT REQUIRED]`.

### 2.13 Z-axis / multi-floor
- **Mechanism:** BARO_DIFF floor gating; floor-aware receiver routing to stairwells; entrance-gate baro calibration.
- **Simulated evidence (B-10):** RF ceiling shadow trap (100% trapped / 0% arrival under naive 2D descent) resolved to 0% trap / 100% arrival via floor-aware gating; MAFE 0.244 floors calibrated. **Real-building pressure measurements `[EXPERIMENT REQUIRED]`.**

### 2.14 Communication fallback
- **Ladder (proposed, not assumed):** BLE → local Wi-Fi capability → Internet gateway/backend when available → SMS when cellular available.
- **Critical honesty note for the manuscript:** Internet/SMS are **fallback augmentation, not infrastructure-free claims**. Core system must be investigated with degraded/absent Internet/cellular.

### 2.15 Positioning fallback
- **Ladder (research hypothesis to test, not a conclusion):** high-quality ranging/direction → BLE DF/proximity → BLE+IMU → IMU/compass → topological guidance → terminal localization.

### 2.16 Security
- **Implemented/simulated:** 16-bit envelope MAC (anti-forgery), incident session keys (HKDF), ZDF (zero-decrypt forwarding) so strangers relay without keys, black-hole/flood/replay analysis (0.5% rogues mislead 88–100% without MAC; 16-bit MAC → 0.15–0.18% acceptance).
- **Documented caveat:** light-model insider-forgery caveat documented (ADR-010); full threat model (Sybil, identity spoofing under RPA rotation, selective forwarding, location poisoning) is **RED/unresolved** `[EXPERIMENT REQUIRED]`.

### 2.17 Privacy
- **Mechanism:** ephemeral incident-scoped identities, RPA rotation (~15 min default; defeating duplicate coalescing), minimal location exposure, event-scoped disclosure, sto Erection limits, resident privacy-versus-utility tradeoffs.
- **Reality check from prior art:** MAC randomization alone does not guarantee privacy (USENIX Security 2024; CCS 2022) — the paper must scope privacy claims carefully.

### 2.18 Battery / energy
- **Modeled figures (simulated / literature-anchored):** ZDF relay drawing <1.4 mAh/day bystander budget; H6 dual-compartment frame. Peer-reviewed phone measurements (advertise ~1.32 µAh/s @10 Hz; listen ~14.23 µAh/s) exist in literature to anchor the energy model. **In-repo battery numbers are model estimates, not device measurements** `[EXPERIMENT REQUIRED]`.

### 2.19 Android implementation
- **Status:** Kotlin engine (Android app scaffold): Direction/CompatTier/EngineSelfTest parity; BLEManager with RSSI-sample hook; compile pending (no toolchain here). Android BLE permissions/background behavior documented as constraints `[CITATION REQUIRED at claim time — platform docs version-dependent]`.

### 2.20 iOS implementation
- **Status:** Swift engine parity sources; iOS background constraints (CoreBluetooth service-UUID filter, no wildcard/Type-0xFF-only scanning, 23-byte Dual-AD ceiling) documented from platform research [Doc 18]. **No iOS build/device run** `[IMPLEMENTATION VALIDATION REQUIRED]`.
- **Design principle settled:** platform-independent protocol layer + platform-specific transports.

### 2.21 Scalability
- **Simulated scales:** 10 → 50 → 100 → 500 → 1,000 → 5,000 → 10,000 nodes in various simulations (storms, gradient, trickle). 50,000-node efficiency **not** demonstrated `[RESULTS REQUIRED]`.
- **Methodology position for manuscript:** real devices (small N) + simulation (large N) + network models; extrapolation claims must carry justification.

### 2.22 Failure analysis
- **In-repo:** an 18+ failure-mode matrix (Doc 29) covering kinematic mosh chaos, pocket compass drift, near-field bystander blockage, iOS background throttling, percolation collapse, black-hole spoofs, multipath bounce overrides, discovery storms, ghost gradients, multi-deck ceiling traps, cross-OS baro offsets, channel BER, etc., mapped to mechanisms and verified simulated numbers.
- **For every failure the paper must present:** WHAT FAILED / WHY / DETECTED HOW / SYSTEM ACTION / FALLBACK / INFORMATION LOST / RECOVERY.

---

## 3. Phase 2 — Research gap and prior-art map

### 3.1 Method
Literature and patent survey conducted 2026-09-21. All citations below were verified live in this session (web search performed, URLs/DOIs observed in tool output). **No citation below is fabricated.** Items whose author lists could not be fully captured are flagged. Where a claim is ours rather than a source's, it is marked accordingly.

(Bibliography is maintained in `research/paper/ip/` appendix and `literature/` for the manuscript's References section.)

### 3.2 Verified prior-art clusters

**A. BLE mesh / phone mesh / opportunistic communication**
1. HosseinKhani, Z., Gómez, C., Nabi, M. (2025). *Mobile Bluetooth Mesh Networks: Performance Evaluation of a Novel Concept.* IEEE Sensors Journal. https://doi.org/10.1109/jsen.2025.3545249 — current phone-BLE mesh measurement work; confirms live active area.
2. RFC 4838 *Delay-Tolerant Networking Architecture* (Cerf et al., 2007). https://www.rfc-editor.org/rfc/rfc4838.html
3. RFC 5050 *Bundle Protocol Specification* (Scott & Burleigh, 2007). https://www.rfc-editor.org/rfc/rfc5050.html
4. Vahdat, A., Becker, D. *Epidemic Routing for Partially-Connected Ad Hoc Networks.* Duke CS. https://cseweb.ucsd.edu/~vahdat/papers/epidemic.pdf
5. Spyropoulos, T., Psounis, K., Raghavendra, C.S. (2005). *Spray and Wait.* SIGCOMM 2005 Wksp. https://conferences.sigcomm.org/sigcomm/2005/paper-SpyPso.pdf
6. *Mesh Messaging in Large-scale Protests: Breaking Bridgefy.* IACR ePrint 2021/214. https://eprint.iacr.org/2021/214 — real deployed BLE mesh security analysis.
7. Albrecht, M., et al. (2022). *Breaking Bridgefy, again: Adopting libsignal is not enough.* USENIX Security 2022. https://www.usenix.org/system/files/sec22-albrecht.pdf
8. TU München. *Survey of Mesh Networking Messengers* (NET-2021-05-1) — Briar, Serval, FireChat, Bridgefy, etc. (author list not captured).

**B. Broadcast storms / suppression**
9. Levis, P., et al. (2011). *The Trickle Algorithm.* RFC 6206. https://www.rfc-editor.org/rfc/rfc6206.html
10. Tseng, Y.-C., Ni, S.-Y., Chen, Y.-S., Sheu, J.-P. (2002). *The Broadcast Storm Problem in a Mobile Ad Hoc Network.* Wireless Networks 8:153–167. https://doi.org/10.1023/A:1013763825347

**C. Anchor-free / relative / distributed localization**
11. Čapkun, S., Hamdi, M., Hubaux, J.-P. (2001). *GPS-free positioning in mobile ad-hoc networks.* HICSS-34. https://doi.org/10.1109/hicss.2001.927202
12. Shang, Y., Ruml, W., Zhang, Y., Fromherz, M. (2003). *Localization from Mere Connectivity* (MDS-MAP). MobiHoc 2003. https://www.cs.unh.edu/~ruml/papers/mobihoc03.pdf
13. Aspnes, J., et al. (2006). *A Theory of Network Localization.* IEEE TMC. https://www.cs.yale.edu/homes/aspnes/papers/loc-tmc-final.pdf
14. Moore, D., Leonard, J., Rus, D., Teller, S. (2004). *Robust distributed network localization with noisy range measurements.* SenSys 2004. https://doi.org/10.1145/1031495.1031502
15. Khan, U.A., Kar, S., Moura, J.M.F. (2009). *DILOC … Minimal Number of Anchor Nodes.* IEEE TSP 57(5):2000–2016. https://doi.org/10.1109/tsp.2009.2014812
16. Patwari, N., et al. (2003). *Relative location estimation in wireless sensor networks.* IEEE TSP. https://doi.org/10.1109/tsp.2003.814469 — CRB for cooperative relative localization. *(key for honesty: RSSI-only accuracy bounds)*
17. Patwari, N., et al. (2005). *Locating the nodes: cooperative localization in wireless sensor networks.* IEEE Signal Processing Magazine. https://doi.org/10.1109/msp.2005.1458287
18. García-Fernández, Á.F., Svensson, L., Särkkä, S. (2017). *Cooperative Localization Using Posterior Linearization Belief Propagation.* IEEE TVT. https://doi.org/10.1109/tvt.2017.2734683

**D. RM channel instability / body shadowing (the "RSSI is not ground truth" anchor)**
19. Cotton, S.L., Scanlon, W.G. (2009). *An experimental investigation into the influence of user state and environment on fading characteristics in wireless body area networks at 2.45 GHz.* IEEE TWC 8(1):6–12. https://doi.org/10.1109/t-wc.2009.070788
20. Cotton, S.L., McKernan, A., Ali, A.J., Scanlon, W.G. (2011). *Off-body communications channels at 2.45 GHz.* EuCAP 2011. https://ieeexplore.ieee.org/document/5782245 — body rotation degrades received power up to ~50 dB.
21. Cotton, S.L., Yoo, S.K., Doone, M.G. (2014). *Shadowed κ-µ fading.* IEEE AP-S 2014. https://doi.org/10.1109/aps.2014.6904689

**E. Surveys / PDR / localizability**
22. Zafari, F., Gkelias, A., Leung, K.K. (2019). *A Survey of Indoor Localization Systems and Technologies.* IEEE COMST. https://doi.org/10.1109/comst.2019.2911558
23. Harle, R. (2013). *A Survey of Indoor Inertial Positioning Systems for Pedestrians.* IEEE COMST. https://doi.org/10.1109/surv.2012.121912.00075
24. Liu, Y., Yang, Z., Wang, X., Jian, L. (2010). *Location, Localization, and Localizability.* JCST 25(2):274–297. https://doi.org/10.1007/s11390-010-9324-2 — error-accumulation in cooperative localization.
25. Savvides, A., Park, H., Srivastava, M.B. (2003). *The n-Hop Multilateration Primitive.* MONET 8:443–451. https://doi.org/10.1023/A:1024544032357; and Savvides et al., *On the Error Characteristics of Multihop Node Localization*, IPSN 2003. https://doi.org/10.1007/3-540-36978-3_21

**F. Multi-robot / distributed map merging + consistency (VRLG's closest algorithmic family)**
26. Mangelson, J.G., Dominic, D., Eustice, R.M., Vasudevan, R. (2018). *Pairwise Consistent Measurement Set Maximization for Robust Multi-Robot Map Merging* (PCM). ICRA 2018. https://doi.org/10.1109/icra.2018.8460217
27. Tian, Y., et al. *Kimera-Multi: Robust, Distributed, Dense Metric-Semantic SLAM for Multi-Robot.* arXiv:2106.14386. https://ar5iv.labs.arxiv.org/html/2106.14386
28. *Robust Loop Closure Selection Based on Inter-Robot and Intra-Robot … Consistency* (2023). Remote Sensing 15(11):2796. https://www.mdpi.com/2072-4292/15/11/2796 (author list not captured)

**G. UWB / BLE direction finding / barometry**
29. IEEE Std 802.15.4z-2020 (HRP-UWB). https://standards.ieee.org/ieee/802.15.4z/10230/
30. FiRa Consortium, *UWB Secure Ranging in FiRa* (2022). URL observed in survey. UWB ~100 m LOS; BLE used for discovery — "why not just UWB?" section support.
31. Apple. *Nearby Interaction* framework (UWB application surface). https://developer.apple.com/documentation/nearbyinteraction — intent/session-scoped; not generic mesh ranging.
32. Bluetooth SIG. *Bluetooth Direction Finding* technical overview (CTE AoA/AoD; I/Q sample prerequisite). URL observed.
33. Muralidharan, K., Khan, A.J., Misra, A., Balan, R.K., Agarwal, S. (2014). *Barometric phone sensors: more hype than hope!* HotMobile 2014. https://doi.org/10.1145/2565585.2565596
34. *Pressure-Pair-Based Floor Localization System Using Barometric Sensors on Smartphones.* PMC6720727. https://pmc.ncbi.nlm.nih.gov/articles/PMC6720727/ (author list not captured)

**H. Emergency / rescue mesh systems & field evidence**
35. Ramanathan, R., et al. (2019). *Long-Range Short-Burst Mobile Mesh Networking* (goTenna). IEEE SECON Wksp. https://doi.org/10.1109/sahcn.2019.8824803
36. *Lost in the woods: forest vegetation … most affects the connectivity of mesh radio networks for public safety* (2022). PMC9728932. https://pmc.ncbi.nlm.nih.gov/articles/PMC9728932/ — full mesh connectivity only 32.6% of the time; vegetation-dominated. *(support for "mesh connectivity is variable; design for it")*
37. Kuo, T.-W., et al. (2022). *Using Smartphones for Indoor Fire Evacuation.* IJERPH 19(10):6061. https://www.mdpi.com/1660-4601/19/10/6061 — infrastructure-dependent (BLE-beacon) guidance; contrast target.

**I. BLE energy on phones**
38. Siva, J., Yang, J., Poellabauer, C. (2019). *Connection-less BLE Performance Evaluation on Smartphones.* Procedia CS 155. https://doi.org/10.1016/j.procs.2019.08.011 — scan energy ≫ advertise.
39. García-Alonso, J., et al. (2020). *Using BLE Advertisements for Detection of People Temporal Proximity Patterns.* Mobile Information Systems 2020:8506323. https://doi.org/10.1155/2020/8506323 — transmit ~1.32 µAh/s @10 Hz; listen ~14.23 µAh/s.

**J. Crowd-density / co-location sensing from BLE scans**
40. Weppner, J., Lukowicz, P. (2013). *Bluetooth based collaborative crowd density estimation.* PerCom 2013. https://doi.org/10.1109/percom.2013.6526732
41. Weppner, J., et al. (2014). *Participatory Bluetooth Scans Serving as Urban Crowd Probes.* IEEE Sensors J. https://doi.org/10.1109/jsen.2014.2360123

**K. Security / privacy (randomization not privacy)**
42. Wu, J., et al. (2024). *Finding Traceability Attacks in the Bluetooth Low Energy Specification and Its Implementations.* USENIX Security 2024. https://www.usenix.org/system/files/usenixsecurity24-wu-jianliang.pdf
43. Zhang, Y., Lin, Z. (2022). *When Good Becomes Evil: Tracking Unattended Smart Devices at Scale.* ACM CCS. https://doi.org/10.1145/3548606.3559372
44. Piro, C., Shields, C., Levine, B.N. (2006). *Detecting the Sybil Attack in Mobile Ad hoc Networks.* SecureComm 2006 (verified via search citation).
45. Liu, Y., Bild, D.R., Dick, R.P., Mao, Z.M., Wallach, D.S. (2015). *The Mason Test: A Defense Against Sybil Attacks in Wireless Networks Without Trusted Authorities.* IEEE TMC. https://doi.org/10.1109/tmc.2015.2398425 (verified via search citation).

**L. Patents (prior-art landscape, all observed in survey tool output)**
46. US 11,849,372 (2023). *System and method for location determination using mesh routing.* — mesh-relayed location estimate; server/centralized, payment context.
47. US 11,848,740 (2023). *Signal bouncing local mesh network to locate entities in remote areas.* — fixed "bouncer" transceivers; requires deployable infrastructure.
48. US 11,627,453 (2023). *Emergency communication over non-persistent peer-2-peer network.* — UE ad-hoc mesh anchored to PE/backhaul; no relative localization.
49. US 10,779,120 (2020). *Peer-to-peer geolocation system.* — P2P location into shared ledger (anti-tamper).

**Flagged for the manuscript:** items #8, #28, #34, #36 and two #L patents need author-list confirmation on download before formal citation.

### 3.3 Gap synthesis (honest)

Across the verified literature:
- **Anchor-free relative localization over plain phone-to-phone BLE (legacy advertising) with no anchors, no convex-hull prerequisite, and uncertainty explicitly propagated** — related work goes through the infrastructure-free positioning line (Čapkun; Shang; DILOC; Patwari CRB) and BLE-mesh messaging (Bridgefy; TU München survey), but the intersection "uncentralized, heterogeneous-sensor spatial *relationship* propagation on legacy-AD phones guiding an SOS responder *late-entering* a running crowd graph" is **not established prior art** in the works found. This is a gap — and the honest caveat is that absence-of-evidence ≠ novelty; a patent search by counsel is required.
- **Consistency-checked map merging applied to human crowd RF measurements** — prior art (PCM, Kimera-Multi) is on visual/LiDAR SLAM with rich odometry and loop closures; porting to sparse, noisy, drifting human phone measurements is an open research question.
- **Uncertainty propagation in multi-hop spatial composition on phones** — prior art establishes that naive multi-hop accumulation fails (Savvides; Liu; Patwari); the Find Us claim must be an explicit uncertainty model, not a tacit one.
- **Adaptive emergency-aware BLE participation ladder + battery budget** — energy asymmetry (scan ≫ advertise) is literature-anchored; the *emergency dual-mode budget model* is a defensible contribution only after measurement.
- **Late-responder spatial acquisition under RPA-rotating identities** — identity continuity under randomization is a documented privacy-vs-utility tension; a mesh-identity scheme stable for minutes but private over time is an open problem.

**Research gap statement (candidate, to be refined in Phase 2.5):** *No verified system combines (i) infrastructure-free phone-to-phone BLE relaying, (ii) propagation of heterogeneous relative spatial relationships with explicit uncertainty, (iii) consistency-checkable dynamic spatial graphs, and (iv) late-entering responder guidance for emergency navigation, under realistic background-OS constraints.* Separately, every one of these exists; their simultaneous, low-energy operation on commodity phones is the unoccupied space Find Us investigates.

---

## 4. The 7-band mapping (current snapshot)

| Band | Content (with evidence tags) |
|---|---|
| **WHAT ALREADY EXISTS** | BLE legacy/extended AD ceilings, Trickle (RFC 6206), DTN (RFC 4838/5050), epidemic/spray routing, antenna-free relative localization (Čapkun/MDS/DILOC/CRB), body-shadowing channel models (Cotton), PDR drift surveys, PCM/Kimera-Multi graph consistency, UWB (802.15.4z), BLE RPA mechanics, phone-BLE energy asymmetry. |
| **WHAT WE PROPOSE** | Full system as a research program: adaptive BLE participation ladder; uncertainty-carrying relationship propagation; consistency-checked VRLG; floor-aware gating + entrance-gate baro calibration; AR-gated PDR; ghost-gradient-safe partition healing; terminal handoff stack; fallback ladders. |
| **WHAT WE IMPLEMENT** | Protocol v3 codec; Packet v2 (sim); SOS engine; graph/relationships engine incl. compose tier+uncertainty; direction layer (DirectionSweep/BearingFusion/StationarityGate/OobSideband); compat layer (MeasurementSource, NavTier); Kotlin + Swift parity sources; relay_node/guidance_engine/find_group executables; simulation suite (scenario_relative_vector_nav §57.26). |
| **WHAT WE EXPERIMENTALLY TEST** | Simulated: gradient descent vs vector chains (H1), storm/collision suppression (H2/H5/B-06), torso shadowing (H3/B-08), barrier/RF-bleed (H4), DF/encryption budget (H6), PDR chaos (H7, AR gating), packet v2 FEC roundtrips, ESBW async recovery (B-03), anti-spoof MAC width (B-04), multipath wall discrimination (B-05), ghost-gradient (B-09), multi-floor baro (B-10), storm backoff (B-06), compat/direction parity (B-12; unit tests 13/13 + regression 91/91). |
| **WHAT THE RESULTS SHOW** | (conditions attached) gradient 100% descent in-sim; 97.7%→~12% collision regimes; 99.86%/99.98% ESBW recovery; MAC 16-bit 0.15–0.18% forgery; AR gating 100% false-vector suppression; ghost gradient 0.0 false alerts; floor gating 0% trap/100% arrival; baro MAFE 0.244 calibrated. |
| **WHAT FAILED** | Naive vector chaining (>10.9 m compounding error); synchronous flooding myth (async reality 1.51% coverage); unmitigated async trickle; RSSI-as-distance; acoustic terminal guidance in loud crowds (!110 dB SPL); raw cross-OS baro (0.0% floor accuracy uncalibrated); 12-bit MAC (2.4%). |
| **WHAT MAY BE NOVEL** | Candidate list in §3.3 + §5 — presented as candidates for scrutiny, not claims. |

---

## 5. Open conflicts, unresolved problems, and risk register

**Cross-cutting integrity issues to resolve before full drafting:**
1. **Protocol v3 codec vs Packet v2 framing** differ (35-byte header vs 13-byte FEC packet). Must reconcile and present ONE transport profile `[CITATION/IMPLEMENTATION REQUIRED]`.
2. **Simulation-is-not-measurement:** every headline number in findings.md is simulated or modeled. The manuscript **must not** present them as hardware results.
3. **Frame alignment / graph re-merge** remains THEORETICAL — do not assert solved.
4. **VRLG novelty** is unproven; needs patent counsel search, not an assertion.
5. **iOS/Android real-device parity** is compiled-but-untested `[IMPLEMENTATION VALIDATION REQUIRED]`.
6. **50,000-node simulation** not demonstrated `[RESULTS REQUIRED]`.
7. **Deterministic "guaranteed delivery"** claims prohibited until measured.

**Risk register (drawn from Doc 29 TR-01…TR-06 concept, kept honest):**
- TR-01 Real-body torso-shadowing bearing accuracy at scale (currently simulated).
- TR-02 Background-OS BLE behavior differences across Android OEMs / iOS versions.
- TR-03 BLE 5.1 AoA/AoD + UWB device availability for the terminal layer.
- TR-04 Cross-OS barometer bias + thermal drift in real venues.
- TR-05 Packet collision / percolation at >10,000 concurrent nodes.
- TR-06 Battery: dual-role (scan+advertise+relay) duty-cycle model vs real drain.

---

## 6. Next steps (phases 3–8)

- **Phase 3:** RQ hierarchy — refine the 20+ candidate RQs into a testable hierarchy mapped to hypotheses and experiments (input: `docs/RESEARCH_QUESTIONS.md`, §1 question above).
- **Phase 4:** Complete system architecture — reconcile protocol v3 vs v2; architecture document with transport/engines separation.
- **Phase 5:** Mathematical/system models — G(t), edge composition with uncertainty, loop-consistency error, energy budget, baro floor gating, percolation.
- **Phase 6:** Experimental program — expand E1–E23 into testable designs (objective/hypothesis/variables/metrics/statistics), splitting simulated vs real-hardware.
- **Phase 7:** IP candidate map — see separate document `ip/00_ip_analysis.md`.
- **Phase 8+:** detailed outline → drafting → review → citation verification → result insertion.

*End of blueprint v0.1. Authored from repo state dated 2026-09-21 (research B-01…B-12, docs 00–29, refimpl_spec).*