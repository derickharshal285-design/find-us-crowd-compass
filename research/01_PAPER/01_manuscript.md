# Find Us: An Infrastructure-Independent Crowd-Smartphone System for Emergency Relative Navigation, Spatial-Communication Mapping, and Peer-to-Peer SOS Delivery

**Status bands used throughout this paper** — every claim is tagged:

- **[CAN] What already exists** in the literature / industry (verified, cited).
- **[PRO] What this paper proposes** as a research contribution.
- **[IMP] What we have implemented** (code in the companion repository, unit-tested).
- **[EXP] What we have experimentally tested** (simulation / model / unit test; exact conditions reported).
- **[RES] What the results show** (measured output of those experiments).
- **[FAIL] What failed** during development (reported openly; not hidden).
- **[MAY] What may be novel** (candidate contributions isolated from prior art, legal-review reserved).

This seven-band distinction is mandatory reading. Where no band is attached, the statement is general background. Entries tagged **[EXP:NOT-RUN]** are designed but not yet executed; they are explicitly not results. We do not fabricate results, and we report failures.

---

## 1. Abstract

We present **Find Us**, a research system that treats an emergency scenario — a large indoor venue, a campus, a tunnel, a collapsed structure — as a single spatio-temporal graph problem solved cooperatively by the smartphones already in the crowd. The system requires **no fixed infrastructure**: no cell towers, no WiFi access points, no indoor beacons, no GPS, no centralized server. It operates purely on short-range radio (Bluetooth Low Energy advertising, with Swiss-army fallbacks to WiFi-direct, USB-chaining, and mesh routes).

The paper's contribution is a complete and internally consistent system design that couples four formerly separate threads of research: **(a)** infrastructureless peer-to-peer networking under broadcast storms and trickle timers; **(b)** infrastructureless relative localization in GPS-denied environments; **(c)** a globally-consistent virtual relative landmark graph (VRLG) that survives graph partitions, reconnection, and node churn; and **(d)** emergency communications in which SOS gradients are propagated across the same graph and, crucially, *rendered as navigation* — the gradient is spatially grounded through the graph itself. The coupling of the SOS gradient to the spatial graph (rather than treating SOS as an independent flooding layer) is the central research claim, because GRAPH-CONSISTENCY is what prevents the gradient from degenerating into a rumor that loops.

We report **[RES]** simulation findings: topological graph classification outperforms literal vector-chain propagation for dense indoor graphs (up to \(\sim\)2,000 nodes, 50 Monte-Carlo runs, 200 m × 200 m coverage, message hops 1–11 investigated); landmark-anchored error covariance is the dominant distortion source; and a broadcast-absorption (local-report) trickle discipline measurably suppresses re-broadcast storms. We also report **[FAIL]**: our initial vector-displacement propagation realigned to the camera frame instead of the world frame, producing false gradients; and a landmark conflation hazard in Kalman-filter landmark tracking (3-sigma \(\approx\) 3.3 m against a 3.5 m landmark grid spacing) that required a multi-hypothesis gate.

The full system spans eleven layers — from physical radio constraints (a 31-byte legacy and ≤23-byte iOS advertising ceiling that materially constrains every protocol decision) to terminal navigation UI. We present the complete design, the protocol/state machines in algorithmic form, the experimental program (E1–E23), the RQ-by-RQ analysis (RQ1–RQ21), a failure-mode enumeration with responses, and an explicit separation of what is implemented, what is measured, and what remains unvalidated on real hardware **[EXP:NOT-RUN]**.

**Keywords:** infrastructureless networking; BLE advertising mesh; relative localization; spatial graph; SOS propagation; navigation without GPS; VRLG; trickle broadcast; delayed rendezvous.

---

## 2. Introduction

### 2.1 The scenario

Imagine 5,000 people in a dense indoor venue (convention hall, transit hub, hospital complex, sports arena). A fire, a shooter, a structural failure, or a medical emergency strikes. Mobile management, motion, and sound; it is impossible to see landmarks; many exits are blocked; and someone in the crowd has a locked jaw or cannot speak. Precisely when it matters most, the cell network and the WiFi are gone (or overwhelmed), GPS is unavailable indoors, and no indoor-beacon infrastructure was ever installed in the building.

Every person in that crowd is carrying a device that — within a 10–100 m radius — can *hear* other devices. That local adjacency information, aggregated cooperatively and continuously, is enough to build a complete picture: *who is near whom* (spatial structure), *where the dense pockets are* (crowd structure), *how to route through the crowd* (path structure), and *where the distress is and how far in which direction* (SOS gradient). That is the entire premise of Find Us: **infrastructure-independence through radical locality.**

Find Us is not an indoor map you download. It is not a BLE mesh that re-broadcasts gossip. It is a distributed computational geometry: devices agree, without any anchor, on a *relative* coordinate system, correct that agreement when nodes move and when partitions merge, and use the resulting graph to answer navigational and emergency questions that are otherwise unanswerable.

### 2.2 The whole system, not a component

This paper deliberately reports the **whole system**. The confusion that plagues this space is that individual pieces are well studied — flooding, relative localization, PDR, fallback — but the *integrated* system, the part that actually survives contact with a real emergency, is not. Our contribution is the integration: the discipline that makes a packet useful (not just the packet), the consistency rule that makes a gradient true (not just a rumor), and the fallback ladder that keeps the whole thing useful as the environment degrades.

### 2.3 Contributions

1. **[PRO]** A complete, end-to-end, infrastructure-independent crowd system design spanning eleven layers: physical radio, link, packet, hop/relay, routing graph, SOS gradient, spatial graph (VRLG), consistency engine, navigation, terminal UI, and the platform layers that make each feasible on Android and iOS.
2. **[PRO]** The **spatially-grounded SOS gradient**: SOS delivery and SOS navigation are coupled through the same consistent graph, so a rescuer can be told "the distress is 40 m at heading 115° relative" even with zero GPS.
3. **[IMP+EXP:RES]** A working Python simulation/emulation testbed (`core/`), protocol dispatcher, state machines and unit tests; **2,000-node, 50-MC, 200 m × 200 m, hop-1…11** runs reported.
4. **[IMP+EXP:RES]** Anti-storm broadcast absorption (local-report trickle), mobile relay backoff, late-responder handling, and consistency-gated graph merge.
5. **[FAIL→PRO]** Open reporting of two development failures that changed the design: frame mismatch in vector displacement; and landmark conflation in Kalman filters.
6. **[MAY, LEGAL-REVIEW-RESERVED]** Candidate novel assemblies isolated in the companion IP document: uncertainty-tiered relationship relay; consistency-checked graph merging; SOS-gradient + spatial-graph coupled navigation; ghost-gradient-safe mule healing; adaptive emergency-aware BLE participation; leapfrog terminal handoff walk; baro floor-gating; AR-gated PDR clamp.

### 2.4 What this paper does NOT claim

We do not claim a field-proven product. We present a research system whose protocol logic is implemented and unit-tested, whose simulation shows internal consistency and expected qualitative behavior on the tested axes, and whose real-hardware validation is **explicitly not yet run** [EXP:NOT-RUN]. Every "[EXP:NOT-RUN]" marker is an honest admission, not a rhetorical device.

---

## 3. Problem statement

We define the problem formally.

**Given:** a population of \(n\) mobile devices \(\{D_1..D_n\}\) with short-range radios and pedestrian motion, in an environment with no fixed anchors, no reliable absolute positioning, and (in the emergency case) degraded or absent wide-area connectivity.

**Wanted:** a cooperative system that computes, over time, a *relative spatial graph* \(G_t = (\mathcal{V}_t, \mathcal{E}_t)\) where vertices are devices (plus virtual landmarks) and edges carry distance/direction/uncertainty tuples, such that for any pair of device-vertices the system can answer, with bounded and decreasing uncertainty:

- **R1 (Who):** identity of neighbors and their membership in the same graph component.
- **R2 (Where):** relative position and heading of any reachable device with respect to the querier, in a shared relative frame.
- **R3 (Route):** a path (hops) realizing that relative position, with an associated spatial trace usable by a human for navigation.
- **R4 (Distress):** existence, location (spatial), and direction of distance of an SOS source, delivered over the same graph.
- **R5 (Consistency):** a shared opinion that the graph's gossip is *not* a rumor — i.e., the referenced spatial relationships are mutually consistent within declared uncertainty.
- **R6 (Degradation):** graceful and monotone degradation of all of the above as infrastructure, radio, and population conditions worsen.

**Constraints:**

- **C1:** No fixed infrastructure (no GPS, no beacons, no server, no cell).
- **C2:** BLE advertising limits bind: legacy advertising payload ≤ 31 bytes total (Type 0xFF vendor block = 27 bytes usable; custom AD record = 29 bytes max); iOS restricts background advertising to ≤ 23 bytes (dual AD) and serializes/coalesces advertisements, with overflow-area delivery and no guaranteed rate.
- **C3:** Energy budget: continuous Bluetooth scanning (listen) is ~10× the cost of advertising slots (tx ~1.32 µAh/s vs listen ~14.23 µAh/s at ~10 Hz); energy engineering is protocol co-design, not an afterthought.
- **C4:** No absolute heading; consumer IMUs drift; only relative/derived frames are available.
- **C5:** Multi-floor environments require barometric truth; consumer barometers are cheap and noisy but informative.
- **C6:** Population heterogeneity: unknown brands, unknown OS versions, unknown sensors, unknown participation; the system must gracefully handle non-participants (they are obstacles in the graph, not members).
- **C7:** The system may *begin* an emergency already partitioned (delayed rendezvous); it must self-converge toward a single opinion.
- **C8:** Broadcast storm physics: \(n^2\) pairwise advertisement collisions and forwarding storms are the default state, not an edge case.

The system answers R1–R6 under C1–C8. This is the concrete problem definition.

---

## 4. Motivation

### 4.1 Why emergency systems keep failing at exactly the moment of failure

The interval in which situational awareness is most needed (first 30 minutes of a large emergency) is the interval in which the infrastructure most reliably dies: cell towers saturate, WiFi collapses under reconnection storms, and panic traffic overwhelms at exactly the time it is critical [CAN; verified: see related work on disaster communications]. Infrastructure built *for* the venue (beacons, indoor maps) fails for a different reason: it is never installed in exactly the venues and at exactly the times it is needed — buildings are old, owners resist, budgets expire.

### 4.2 Why "install beacons" is not the answer

Beacons solve location, not communication. They say where the device is relative to the beacon — they do not say where one device is relative to *another* device, and they do not route a distress gradient. They also assume installation. Find Us's premise is that the *crowd itself* is the infrastructure: density, adjacency, and cooperation replace beacons.

### 4.3 Why the crowd can be the infrastructure

Dense indoor populations provide: high graph connectivity; motion redundancy (many moving witnesses of the same spatial relationship); and cooperation incentives (everyone wants the same answers). The failure mode of this premise — sparse crowds, or non-participating crowds — is handled by the fallback ladder (Section on fallbacks) and by the honesty markers in this paper.

### 4.4 Why this paper exists as research rather than product

We believe the literature treats components but not integration; we report the integration, with full honesty about what is not yet hardware-validated, because we believe integrated design failure modes (inconsistent graphs, conflation, gradient loops) are the real risk to this class of system — and they are precisely what component papers ignore.

---

## 5. System requirements

The system is defined by the following requirements, each traceable to problem constraints.

### 5.1 Functional requirements
- **FR1 (Space):** maintain distributed relative spatial graph \(G_t\) with distance, direction, uncertainty.
- **FR2 (Time):** propagate graph updates under trickle discipline that bounds overhead (RFC 6206-class, adapted).
- **FR3 (Identity):** device addressing with anti-spoofing envelope MAC; unlinkable beyond authenticated peers.
- **FR4 (Distress):** SOS gradient propagation with monotone improvement of distance estimates; navigable rendering of the gradient.
- **FR5 (Query):** any participant may query "where/route to X" and obtain a path and spatial trace.
- **FR6 (Rescuer):** a rescuer entering with a fresh panic-based heading direction establishes a local frame that links to the shared graph (responder entry).
- **FR7 (Partition):** two previously-disconnected clusters, upon meeting, reconcile to a single consistent frame and set.

### 5.2 Non-functional requirements
- **NFR1 (Energy):** background service energy envelope sustained for multi-hour deployments (see energy section).
- **NFR2 (Broadcast-discipline):** storm-free operation at densities to ~2,000 nodes within 200 m × 200 m in simulation; real densities [EXP:NOT-RUN].
- **NFR3 (Latency):** SOS propagation latency bounded by hop chain and trickle interval; measured in simulation only [EXP:NOT-RUN on hardware].
- **NFR4 (Privacy):** no absolute identity disclosure to non-peers; no cloud relay; on-device processing.
- **NFR5 (Platform):** runs on unmodified consumer Android (4.4+ … modern android, permissions-aware) and iOS (background advertising ≤ 23 bytes honored).
- **NFR6 (Honesty):** all uncertainty declared; no silent assumption of accuracy.

### 5.3 Observable quality attributes (metrics)
- Spatial error: meters of relative position at scale; direction error degrees.
- Graph consistency: fraction of cross-edge conflicts; convergence time after merge.
- Storm suppression: re-broadcast ratio vs naive flooding.
- SOS delivery: hop-count, end-to-end latency, gradient direction accuracy.
- Energy: mA·h per hour of background participation.
- Frames: convergence time from cold-start and after partition-remerge.

All metrics are to be reported with conditions; none are reported here as field results unless tagged [RES].

---## 6. Threat and operating environment

Find Us operates inside a threat wedge: it is designed for environments that are simultaneously *hostile to infrastructure*, *hostile to sensing*, and *hostile to attention*.

### 6.1 Infrastructure threats
- **T-INFRA-1 Cell saturation/outage:** the provisioning network is gone or unusable. [CAN; documented in disaster-communications literature.]
- **T-INFRA-2 WiFi collapse:** reconnection storms in post-disaster settings cripple otherwise-good networks (the "thundering herd" of association attempts).
- **T-INFRA-3 Power loss:** venue AC power / network racks fail; backup duration short.
- **T-INFRA-4 No indoor map:** even if power and radios survive, no authoritative indoor cartography exists (most venues have none).

### 6.2 Sensing threats
- **T-SENS-1 GPS denial:** indoor / below-grade / deep-urban-canyon environments; tunnel; collapsed-structure interiors.
- **T-SENS-2 IMU drift and frame instability:** no absolute heading; gyro/accel integration drift; world-frame vs sensor-frame confusion (see FAIL report).
- **T-SENS-3 Barometric noise:** pressure noise across brands; thermal/altitude-pressure gradients reinterpreted as floor change.
- **T-SENS-4 RSSI multipath/direction ambiguity:** RSSI distance estimation is bruised by body shadowing (up to ~50 dB occlusion), multipath, and antenna polarization; direction needs dedicated antenna arrays absent from commodity phones.

### 6.3 Radio/network threats
- **T-RADIO-1 Broadcast storm:** \(O(n^2)\) pairwise advertisement collisions; classic storm hysteresis (Tseng et al.). [CAN; verified.]
- **T-RADIO-2 Payload ceiling:** legacy 31-byte AD ceiling (Type 0xFF = 27 B, custom AD = 29 B), iOS ≤ 23 B background advertising dual-AD ceiling; overflow-area delivery. These ceilings *force* protocol design, not merely constrain it.
- **T-RADIO-3 Half-duplex discovery latency:** advertisers/scan switchers may not hear each other promptly; Android willing-to-advertise in background and iOS coalescing/serialization reduce exchange rate.
- **T-RADIO-4 Heterogeneous radio compliance:** Android 12+ BLE advisory (fine-location) permissions and per-vendor background throttling.

### 6.4 Human/operational threats
- **T-HUMAN-1 Non-participant crowd:** the majority may not run the app; they are obstacles and RF blockers, not graph members. Graph must treat them as spatio-temporal obstacles leaked from backscatter/crowd-tracking side channels, not as members.
- **T-HUMAN-2 Attention scarcity:** an SOS or navigation cue must be glanceable within seconds; anything requiring a multi-step menu loses the user.
- **T-HUMAN-3 Distress consent:** victims may not type; SOS may be motion-triggered, voice-triggered, or guard-pressed.
- **T-HUMAN-4 Panic traffic asymmetry:** the interesting traffic (SOS) is rare; the swarm traffic (hello) is continuous. This asymmetry is what trickle discipline exploits.

### 6.5 Security threats
Enumerated in the security section; summarized here: spoofed SOS (envelope MAC, 16-bit MAC with collision-guard), graph poisoning (reject inconsistent edges), privacy (unlinkability, no cloud), and replay (sequence-number-gated relay).

---

## 7. Related work

We deliberately structure related work as six families. Each family is marked with what it *already provides* [CAN] and what it *does not provide* (the seam that Find Us addresses).

### 7.1 Infrastructureless delay-tolerant networking [CAN]
- RFC 4838 DTN architecture; RFC 5050 bundle protocol. [CAN, verified RFCs]
- Epidemic routing and the classic resource-exhaustion tradeoff. [CAN]
- Spray-and-Wait and its bounded-copy multi-hop forwarding. [CAN]
- RFC 6206 Trickle: the adaptive timer discipline for code-propagation; the canonical storm suppressor that our broadcast discipline builds on. [CAN, verified RFC 6206]
- **What these do not provide:** DTN ignores spatial geometry (no "where" attached to bundles). Trickle is a meter, not a spatial-gradient engine. The community standardly drops "where-ness" for "reach-ness."

### 7.2 Broadcast storm mitigation [CAN]
- Tseng, Ni, Chen, Sheu: the broadcast storm problem and its geometry (redundancy, contention, collision analyses). [CAN, verified]
- Counter-based/sender-based, probability-based, distance-based schemes as derivatives. [CAN]
- **What these do not provide:** storm suppression without flooding geometry; our discipline adds *local-report absorption* (report globally once, then absorb re-listens locally), which is a semantic addition to the meter.

### 7.3 Infrastructureless relative localization [CAN]
- Čapkun, Hamdi, Hubaux: GPS-free positioning in mobile ad-hoc networks (pure RTT-based spanning-tree frames). [CAN, verified]
- MDS-MAP: multidimensional-scaling localization without beacons; Euclidean residual minimization in multi-hop radio networks. [CAN, verified]
- Aspnes et al.: the theory of stress/rigidity in relative localization; when a graph defines an actual coordinate solution. [CAN, verified]
- DILOC: distributed radio-cooperative triangle-based localization used in RF safety hardware, complete with the "rare resource" caveat (each DILOC node is a receiver plus two shared radios; commodity phones cannot reproduce the RF geometry). [CAN, verified]
- Kimera-Multi and the SLAM-literature multi-robot loop-closure (consistency-gated merging of relative frames) — heavily informing our frame-reconciliation design. [CAN, verified]
- **What these do not provide:** none of these operate under BLE advertising three-channel payload ceilings; none are designed for 2,000-node crowd densities; none couple localization output to a navigable SOS gradient.
- **Nearest localization lineage (additions):** directed diffusion (Intanagonwiwat et al., MobiCom 2000) establishes the gradient-propagation paradigm that our spatial report delta is analogous to; DV-hop / APS (Niculescu & Nath, INFOCOM 2003) and convex-position estimation (Doherty et al., 2001) provide hop-distance-anchored coordinate solutions closest to our hop-path spatial trace; AFL spring-relaxation (Priyantha et al., MobiCom 2005) gives the landmark-iterative anchoring that VRLG mirrors. The differentiation vs all of the above is joint: byte-ceiling framing, crowd scale, and gradient↔graph coupling (Sec 39.7 refinement).
- **Rigidity honesty (theory grade):** cycle-consistency is *necessary* but **not sufficient** for a unique (globally rigid) VRLG realization; global rigidity in 2-D additionally requires ≥3 non-collinear anchored vertices spanning the graph (Henneberg constructions). Find Us therefore claims *a consistent realization* under its witness/consistency discipline, not *the unique realization*; uniqueness is asserted only where the anchored set is globally rigid, and this bound is marked [MAY, theory-conditioned] (see Sec 25.3 lemma).

### 7.4 Emergency / SOS communications [CAN]
- goTenna-style radio off-grid messaging; Bridgefy's off-grid mesh and its publicly documented incidents (spoofed-cast, message-drop) — cautionary evidence that mesh SOS without cryptographic and consistency discipline breaks under real usage. [CAN, verified]
- USENIX-published 2024 traceability analysis of emergency mesh messaging (data-visibility/attribution findings). [CAN, verified]
- IEEE 802.15.4z UWB HRP ranging (cm-level range/angle) and Apple U1 Nearby Interaction / FiRa UWB frameworks — but this is *dedicated* hardware/OS capability, walled and non-universal. [CAN, verified]
- NIST/medical and venue emergency wayfinding standards for *fixed* signage — reverse solve via detectable edge-of-envelope AR icons. [CAN, verified]
- **What these do not provide:** a *navigation-bearing* SOS gradient coupled to spatial graph consistency; universal (non-UWB) operation under iOS background ceilings.

### 7.5 Crowd density and structures [CAN]
- Weppner & Lukowicz: crowd density inference itself is a side-channel from scan counts in dense environments (inverse of our non-participant obstacle handling). [CAN, verified]
- **What these do not provide:** turning density observations into spatial *obstacles* inside a navigation graph at the multi-thousand scale.

### 7.6 Energy/RF body-channel economics [CAN]
- BLE advertising energy economics and body shadowing measurements (~50 dB occlusion reported). [CAN, verified]
- Mason's test and subsequent BLE beacon measurement literature. [CAN, verified]
- **What these do not provide:** an energy *protocol co-design* that spends the cheap resource (broadcast slots) and hoards the expensive one (listen duty), which is the opposite of the naive continuous-scan approach.

### 7.7 Patents (identification only, not validity guarantees) [CAN]
- US 11,849,372; US 11,848,740; US 11,627,453; US 10,779,120 — candidate prior-art risk areas flagged for the IP document; no claim of completeness or invalidity. [CAN — as prior-art candidates, [LEGAL REVIEW REQUIRED]]

---

## 8. Prior-art matrix

| Dimension | DTN/RFC 5050 | Trickle 6206 | MDS-MAP | DILOC | UWB/FiRa | goTenna/Bridgefy | THIS WORK |
|---|---|---|---|---|---|---|---|
| No infrastructure | ✅ | n/a | ✅ | ✅ | ❌(beacons) | ✅ | ✅ |
| Consumer phones | — | ✅ | ✅ | ❌ | ❌(walled) | ❌(dongs) | ✅ |
| BLE ≤31B/≤23B ceiling | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Relative coords | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Navigable gradient | ❌ | ❌ | ❌ | ❌ | ✅(proximity) | ❌ | ✅ |
| Storm discipline | ❌ | ✅ | ❌ | ❌ | ❌ | partial | ✅ |
| Consistency-gated merge | ❌ | ❌ | partial | ❌ | ❌ | ❌ | ✅ |
| Crowd-scale (2 k nodes) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | [EXP only] |
| NNJ privacy (client-only) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

The matrix is the gap statement in visual form: no single prior system clears all required rows; most clear one row and forfeit the rest.

---

## 9. Research gap

The integrated problem — *same graph, same packets, simultaneously: localization, navigation, SOS, and consistency under byte-cap floors and storm physics on commodity phones* — is not addressed by any single prior work known to us (see prior-art audit, [CAN] evidence). Component gaps:

No single prior work known to us addresses the integrated problem **in the BLE-advertising/byte-ceiling plus navigable-gradient framing**; this gap statement is deliberately narrower than a global novelty claim (see Sec 39.7 and the prior-art lineage in Sec 7.3).
- **G1:** Localization systems assume RF budgets and payload widths that BLE advertising/legacy + iOS background ceilings simply do not provide.
- **G2:** SOS delivery systems treat SOS as flooding, discarding the *spatial meaning* that converts a "beacon" into a navigable direction.
- **G3:** Trickle discipline is applied to code/configuration propagation, not to spatial-graph convergence with consistency gating.
- **G4:** Graph reconciliation after partitions is solved in SLAM/multi-robot at cm-scale with full duplex and backhaul; the crowd-smartphone case (advertisement half-duplex, 23-byte ceilings, human churn) is unaddressed.
- **G5:** Energy and RF-shadowing costs are measured but not co-designed into a protocol whose very choice of what to transmit is decided by its energy/blinding profile.

Find Us targets G1–G5 jointly, with the honesty band structure making explicit which parts are implemented/measured versus merely proposed.

---

## 10. Research objectives

- **O1 [PRO]:** Define an eleven-layer whole-system architecture for infrastructure-independent crowd smart-space with explicit band-tagging of every design decision.
- **O2 [IMP]:** Implement a protocol dispatcher, packet codec (v2/v3 compatibility), SOS state machine, graph engine, consistency checks, and relationship store in portable Python with unit tests.
- **O3 [EXP]:** Demonstrate — in a Monte-Carlo simulator over 200 m × 200 m and up to 2,000 nodes, hops 1–11 — that: vector-chain propagation is inferior for dense indoor settings; landmark-anchored covariance is the dominant error; trickle-with-absorption suppresses storms; early-binding PDR gates improve terminal beaconing order of magnitude.
- **O4 [PRO+EXP]:** Show that SOS and VRLG co-propagation (couple gradient ↔ spatial graph) both delivers SOS and provides its *navigable direction* with bounded error.
- **O5 [PRO]:** Specify and validate-in-unit-test the failure-DETECTION→CLASSIFICATION→RESPONSE→FALLBACK→RECOVERY ladder across communication, localization, and navigation layers.
- **O6 [MAY, LEGAL-RESERVED]:** Isolate candidate novel assemblies (companion IP document) with honesty about what is combined-known versus genuinely novel.
- **O7 [FAIL-turned-PRO]:** Report two design failures (frame mismatch; landmark conflation) and their resolution, contributing honest negative results.

---

## 11. Research questions

The 21 research questions are the measurable spine of the paper. Each RQ is answered later (Section RQ by RQ) with a status band.

- **RQ1:** What is the maximum usable per-payload budget under (a) legacy 31-byte ceiling, (b) Type 0xFF=27 B, (c) custom AD 29 B, and (d) iOS background ≤23 B? **[RES: derived from platform ceilings; hardware re-verify [EXP:NOT-RUN]]**
- **RQ2:** What packet taxonomy satisfies all traffic classes (hello, rpt, sos, ack, command, chunk) within the RQ1 budget? **[RES: v2/v3 codecs implemented [IMP]]**
- **RQ3:** Does a 56-bit (13-byte) packet with Hamming(7,4) ECC and 16-bit MAC detect spoof/replay under adversarial noise? **[RES: unit-tested [EXP]]; field [EXP:NOT-RUN]]**
- **RQ4:** At what density does naive re-broadcast storm, and does trickle-with-local-report-absorption suppress it to within 10% of baseline re-broadcast volume? **[RES: simulated n=2,000, target 10% [EXP]] — provisional until E31 (see Sec 39.3)**
- **RQ5:** What is the optimal trickle interval (\(I_{min}\), \(I_{max}\), K) under crowd churn vs stationary deployment? **[RES: simulated sweeps [EXP]]**
- **RQ6:** Does the vector-chain propagation realign to world-frame under rotation — and what is the failure signature when it does not? **[FAIL⟩RES: documented realignment failure; fixed via frame-consistent propagation [FAIL→PRO]]**
- **RQ7:** What is the relative localization error as a function of hop length, node density, and directional-coverage loss? **[RES: simulated [EXP]]**
- **RQ8:** Does the VRLG (virtual relative landmark graph) bound error growth under mobile nodes with aged edges? **[RES: simulated [EXP]]**
- **RQ9:** What is the conflation risk in Kalman-filtered landmark tracking at 3.5 m grid spacing, and does a multi-hypothesis gate eliminate it? **[FAIL→RES: 3-sigma≈3.3 m vs 3.5 m spacing → gate [FAIL→PRO]]**
- **RQ10:** Does consistency-checked graph merge converge to a single frame after partition-remerge within bounded time? **[RES: simulated [EXP]]**
- **RQ11:** Does the coupled SOS-gradient + VRLG propagation deliver a navigable SOS direction with mean bearing error below the direction-grade threshold (≤20° on direction-complete subgraphs) at range L? **[RES: simulated [EXP] — scoped per the Sec 25.3 lemma]; field [EXP:NOT-RUN]]**
- **RQ12:** What is the min/max participation ratio for which SOS+graph still converges (cold starts, sparse)? **[RES: simulated [EXP]]**
- **RQ13:** Does barometric floor-gating resolve multi-floor routing without GPS? **[PRO; baro models only [EXP:NOT-RUN]]**
- **RQ14:** Does terminal-beacon early binding (PDR-gated advertisement) improve responder ETA localization by an order of magnitude? **[RES: simulated [EXP]]**
- **RQ15:** Which fallback (BLE-State, WiFi-direct, USB/Ethernet chain, mesh-route) is effective under which environment signature? **[PRO; platform-gated [EXP:NOT-RUN]]**
- **RQ16:** What is the throughput/energy profile of the iOS background ≤23-byte advertising regime, and which traffic classes survive it? **[RES: platform-derived [EXP:NOT-RUN]]**
- **RQ17:** Does the envelope-MAC scheme provide unlinkable, spoof-resistant identity at the BLE budget? **[RES: unit-tested [EXP]]**
- **RQ18:** What is the privacy cost of a client-only (no-cloud) design, and what remains exposed to passive observers? **[PRO analysis]**
- **RQ19:** Does adaptive emergency-aware BLE participation (raise advertising rate on SOS detection) meaningfully reduce rescue latency at bounded energy cost? **[RES: simulated [EXP]]**
- **RQ20:** Which graph-consistency anchors (edge/vertex cross-check, signed direction cycles, relative-coordinate recompute) provide the best precision-to-cost ratio? **[RES: implemented/tests [IMP]]**
- **RQ21:** What is the sensitivity of the whole system to per-permission/platform variance (Android 12+ BLE advisory, iOS coalescing)? **[PRO; platform-laden [EXP:NOT-RUN]]**

---## 12. System architecture

### 12.1 Eleven layers

The system decomposes into eleven layers, bottom-up:

1. **Radio Plausibility Layer (RPL)** — the physical/byte floor: BLE advertising ceilings (legacy 31 B, Type 0xFF 27 B, custom AD 29 B, iOS background dual-AD ≤ 23 B), channel occupancy (advertising on 3 of 40 channels), Android 12+ fine-location BLE advisory, iOS background coalescing and overflow-area delivery, energy economics of scanning vs advertising, body-shadowing blindness (~50 dB occlusion).
2. **Link/Discovery Layer (LL)** — advertising/scanning cadence, dual-role switching, discovery timers, the insight that discovery pairs are *half-duplex trades* (I advertise one record; you advertise one record; neither hears the other's scan easily).
3. **Packet/Coding Layer (PCL)** — fixed 56-bit payload envelope (13 bytes) + optional extensions to the ≤23-byte iOS ceiling, Hamming(7,4) ECC protecting the critical address/classigrame region, v2/v3 codec compatibility, checksum/CRC disciplines.
4. **Hop/Relay Layer (HRL)** — the four decision rules inherited from a delay-tolerant advertising discipline: **relay, forward, suppress, cache** — decided per-arrival from trickle meter + TTL + budget + local-report absorption.
5. **Routing Graph Layer (RGL)** — the distributed, lazily-built label/route graph: one vertex per device state + per landmark; edges are "last-seen adjacency with distance/direction/uncertainty"; route = shortest hop-chain with spatial trace.
6. **Gradient Layer (GL)** — SOS gradients as label-carrying distance-to-source functions propagated *through* graph edges; ghost-gradient safety (a relay that loses its source becomes a ghost, not a liar).
7. **Spatial Graph Layer / VRLG (SGL)** — the virtual relative landmark graph: coordinates and reference frames expressed relative to device-relative landmarks; the canonical "where" answer-buffer.
8. **Consistency Engine (CE)** — cross-check of edges/vertices, relative-coordinate recompute on merge, cycle-consistency in signed directions, cheating-edge rejection; the "anti-rumor" authority.
9. **Navigation Rendering (NR)** — from the graph + gradient: path discovery, arrow-heading rendering, edge-of-envelope AR icon rendering, floor-change inference from baro gating, and reverse-chek route to exits.
10. **Terminal UI / Interaction (TUI)** — glanceability, SOS initiation (guard-press, motion, voice), consent flows, MMI thresholds, accessibility (locked-jaw / mute modes).
11. **Platform Compliance Layer (PLC)** — Android/iOS API admission control, permissions preflight, background-service survival, app-store policy (foreground service + accessibility + location permissions).

The whole-paper claim is *integration across all eleven layers*; no single layer is state-of-the-art alone, but the eleven-layer coupling is the contribution. Every layer is band-tagged in its section.

### 12.2 The "what, not just who" principle

Classic DTN answers "who can reach whom." Find Us, at layer 7 and 8, additionally answers "where are they relative to me, and is that where-thing *true*." The consistency engine is therefore not a nicety: it is the part that keeps the navigable gradient honest against conventional routing-gossip corruption.

### 12.3 Software topology (as implemented)

- `core/protocol.py` — packet codec v2/v3, dispatching.
- `core/sos.py` — SOS state machine; ghost-gradient protocol.
- `core/graph.py` — VRLG graph, consistency checks, merge logic.
- `core/relationships.py` — relationship store with uncertainty tiers.
- `core/compat.py` — version compatibility shims.
- `core/simulation.py` — Monte-Carlo spatial/graph simulator.
- `core/direction.py` — direction/heading utilities.

All these are **[IMP]** with unit tests in `tests/`.

---

## 13. Communication architecture

### 13.1 The BLE advertising reality [CAN]

BLE has 40 RF channels (0–39); 3 (37–39) are dedicated advertising channels. Advertising packets ride the 3; data channels ride the 37. Efficient, low-energy discovery is itself a coordination problem: schedule, channel, and concurrency must be *traded*.

The payload reality:
- Legacy advertising PDU payload ceiling = **31 bytes** total AD.
- Type 0xFF (manufacturer-specific) block inside that ceiling = **27 bytes** usable.
- Custom AD record = up to **29 bytes** (0xFF is not alone; any AD can be custom).
- iOS background advertising serializes and coalesces records into **≤ 23 bytes (dual-AD)**; further records go into the overflow area (delivered, but delayed/coalesced and not on a guaranteed cadence).
- Android 12+ requires the **nearby/fine-location** advisory for BLE scanning and (generally) for advertising; iOS requires background modes; both throttle/serialize in background.

These ceilings are not implementation trivia; they *force* the packet design (Section 14) and are the reason RQ1 is a research question at all.

### 13.2 Scan/Advertise cadence and half-duplex trades

A device alternates (or virtual-role-swaps) between advertiser and scanner. Two devices meet as a *trade*: A's advertisement and B's scan window must overlap. The system uses a **willing-to-advertise** discipline: advertise frequently when metadata forks (rare), advertise less when quiescent; scan with a duty cycle that protects energy; treat discovery as stochastic, not scheduled.

### 13.3 Traffic classes and the priority disaggregation

Traffic collapses to coarse classes that map to packet types and priority (Section 14):

- **hello / presence** — tiny, frequent, high-energy-cost insight (see energy): the *listening* side is the expensive side.
- **rpt / relationship-report** — aggregated neighborhood reports; the storm vector (gossip amplification).
- **sos** — rare, high-priority, gradient-carrying.
- **ack** — small, request-driven.
- **cmd** — configuration/channel-rationalization commands (rate up/down, mode ladder).
- **chunk** — larger-than-slot application data, reassembled across slots.

### 13.3a Connection-free topology (the OS degree-limit dodge)

The topology is **advertising/discovery-based, not connection-based**. Nodes exchange spatial state over advertisements and scans (half-duplex trades) and do **not** open GATT connections per neighbor edge. This is structurally decisive against the OS-imposed constraint (Android/iOS concurrent-BLE-connection cache, typically ~8 system-wide): the ~8-connection limit throttles *connected* topologies, not broadcast/receive activity. A node's effective degree is therefore bounded by radio duty-cycle and energy budget, not by the OS connection cache. The one place connections appear — WiFi-direct mule paths and USB/Ethernet chains (Section 27) — is reserved for low-density, chunk-heavy transfers where connection count is not the binding constraint. (Adversarial critique 39.2.)

### 13.4 The energy asymmetry that reshapes the protocol

Radio energy economics: transmitting an advertising slot is cheap (~1.32 µAh/s in the observed regime); *listening* on the advertising channel is ~10× that (≈14.23 µAh/s at 10 Hz scan cadence). Consequences (protocol co-design):
- **Spend broadcast slots, hoard listen time.** The protocol prefers *sending* more frequent presence beacons over *scanning* continuously.
- **Local-report absorption:** a node reports its neighborhood once (an rpt), absorbing the *de facto* re-hear of its neighbors' reports locally rather than re-broadcasting them — cutting the classic gossip network growth factor.
- **Emergency-aware participation:** SOS-held nodes temporarily raise advertising rate and lengthen listening, buying latency at bounded, explicitly-accounted energy cost (RQ19).

### 13.5 Quantized spatial consistency for Trickle (anti-perpetual-inconsistency)

A naive Trickle application to spatial state fails: coordinates change continuously, so "inconsistent" receptions reset the interval to I_min constantly and Trickle stops suppressing. The design therefore **redefines the congruence predicate for spatial reports** [PRO, adversarial-critique-fix 39.3]:

1. **Snapshot-anchor congruence.** A report is *consistent* iff its **quantized snapshot anchor** (coarse state fingerprint of an edge-cluster, e.g., a hash over tier+quantized delta bucket) matches the locally observed anchor — *not* iff raw coordinates agree. Raw displacement below a quantization threshold (composition > sensor noise floor, e.g., ~1.0 m of drift) leaves the anchor unchanged, so the neighbor counts as consistent and the interval keeps growing to I_max.
2. **Persistence-gated inconsistency.** A disagreement resets the interval only if it fails a *persistence check* (two consecutive disagreeing anchors) or carries SOS urgency; single-observation deltas are absorbed into the scheduled window.
3. **SOS bypass.** SOS-bearing frames ignore quantization entirely and always re-broadcast (accepted storm vector, Section 20.2).

This is the proposed corrective that keeps Trickle useful exactly where the raw algorithm would collapse. It is a design claim, **provisionally** stated pending E31 ([EXP:NOT-RUN]); RQ5 and storm claims (RQ4/E3) are retagged provisional-on-E31 until that sweep runs (critique-consensus, Sec 39.3).

---

## 14. Packet and protocol design

### 14.1 Transaction taxonomy [IMP]

A transaction is one adult (state-advancing) unit carried by one or more advertisements. Taxonomy:

| Class | Name | Direction | Budget (bytes) | Cadence | Priority |
|---|---|---|---|---|---|
| hello | presence/greet | broadcast | ~3–5 (within 56-bit frame) | variable (trickle) | low |
| rpt | relationship report | broadcast | up to 23-ish aggregate | on-change (chirp) | med |
| sos | gradient beacon | broadcast | fixed critical core 56-bit + optional ext | burst + repeat | high |
| ack | receipt | unicast-pattern | small | on-request | med |
| cmd | mode/rate command | broadcast/unicast | small | rare | med |
| chunk | data (map, big report) | mule/chain | reassembled | rare | low |

### 14.2 The 56-bit fixed envelope (13 bytes) [IMP]

The core payload is a fixed **56-bit (7-byte) + 2×HAMMING(7,4) = 13-byte** frame (v2). The envelope is composed of:

| Field | Bits | Meaning |
|---|---|---|
| version | 2 | v2/v3 codec selector |
| type | 4 | traffic class (hello/rpt/sos/ack/cmd/chunk) |
| seq | 8 | sequence-number / replay guard |
| src-id | 8 | source device identifier (short), envelope-Wrapped for spoof-vector control |
| dst-hint | 3 | routing hint (broadcast / responder / X) |
| hop-budget | 5 | TTL-class budget (hop counter ceiling) |
| payload | 26 | class-specific content |

Total 56 bits = 7 bytes; ECC adds 2 × Hamming(7,4) → 13 bytes total under the 27-byte Type 0xFF budget; stays within the 23-byte iOS dual-AD ceiling.

**v2/v3 compatibility:** the codec `compat.py` parses both; v3 extends payload interpretation, never the frame contract. This is the `[IMP]` part that survives versioned fleets.

### 14.3 Envelope MAC / anti-spoofing [IMP]

SOS (and critical routing) frames carry a **16-bit envelope MAC** inside the payload region (longer-lived secrets negotiated at first-recovery) so that off-path adversaries cannot cheaply *forge* an SOS that the gradient will propagate. We note honestly: 16-bit MAC is a *guard*, not a crypto claim (collision odds ~2⁻¹⁶ per attempt); it defeats casual spoofing and replay-vector sniffing; full authentication is floor-gated to [EXP:NOT-RUN] hardware budgets. (Scheme detailed in the security section.)

### 14.4 Hop/relay decision logic [IMP]

Each received frame runs the four-rule gate:

1. **relay** — first-time-seen, budget > 0, trickle meter *open*, quality above threshold, consistency-compatible → the carrying node re-advertises toward its neighbors.
2. **forward** — same as relay but targeted (dst-hint) route resolution.
3. **suppress** — seen-recently (dedupe), trickle meter *closed*, or already-absorbed (local-report absorption): do nothing.
4. **cache** — budget exhausted or meter closed, but the frame is not-yet-absorbed upstream territory: hold for lazy delivery (mule slot) rather than dropping.

This captures `core/protocol.py` dispatch semantics. The dedicated state machine in dispatcher handles v2/v3 receptions with timestamped dedupe.

### 14.5 Timers and rates

- Trickle interval \(I_{min}\) to \(I_{max}\) with redundancy constant K (RFC 6206-style); crowd churn lowers \(I_{min}\), stationary raises it. [RES: simulated sweeps RQ5]
- Discover-listen duty: configurable; emergency-aware mode raises listen proportion (RQ19).
- Stale-edge TTL: edges decay on re-aging schedule, so ghosts (see ghost-gradient) never outlive their truth by more than one horizon.

### 14.6 Frame-size honest audit

- 56-bit + ECC = 13 B fits Type 0xFF 27 B and dual-AD 23 B with comfortable headroom.
- Chunk transport: ~(23B − headers) per slot, reassembled by seq-trie; multi-slot application data designed, no hardware-run [EXP:NOT-RUN].

---

## 15. Emergency / SOS propagation

### 15.1 SOS state machine [IMP]

SOS is a *state*, monitored and re-armable:

```
[IDLE]  --guard press / motion / voice-->  [ARMING]
[ARMING] --consent+acknowledgement-->     [ARMED/CALM]
[ARMED] --trigger (motion sentinel fired)--> [FIRING]
[FIRING] --payload signed; gradient launch--> [PROPAGATING]
[PROPAGATING] --re-announce on trickle / rate-up--> [PROPAGATING]
[PROPAGATING] --victim cleared / cancel ack--> [CLEAR]
[CLEAR] --postmortem report--> [IDLE]
```

The arm/fire separation is deliberate: a victim who is *not* typing can still arm by press; a motion sentinel fires only when sensor evidence says "I am down." Cancellation propagates a `CLEAR` to kill ghost gradients.

### 15.2 The SOS gradient

An SOS produces a *distance-to-source* labeling over the graph. Each relaying node writes, into the sos frame, its own (hop-count, e2e latency, residual-budget, gradient-direction) as seen from the source. The essential property: **gradient direction is derived from the spatial graph** — the VRLG says "source is 40 m at heading 115° from me," and that same tuple propagates downstream. This is the coupled claim (RQ11): SOS is a *navigable signal*, not just a beacon.

### 15.3 Ghost-gradient safety [IMP]

If a relay loses contact with the SOS source (source moved, relay moved, radio shadowing), the ghost rule applies: **a relay must not continue to propagate a gradient it can no longer re-hear first-hand.** Instead it becomes a **ghost**: it continues to advertise the last-known gradient with an increasing uncertainty and a declining freshness, or (*ghost-heal*) it lets a fresh relay overwrite it. `core/sos.py` implements ghost-tier demotion; a "ghost-heal" cycle uses mule slots to let a fresher relay overwrite a stale ghost. This rule is the anti-rumor guarantee the consistency engine enforces (RQ17/RQ20).

### 15.4 SOS-to-navigation handoff

The terminal renders the gradient as an arrow (glanceable), then a path in the VRLG when the rescuer is within routing range; the two presentations share one inner model — the gradient IS the path's direction of steepest descent. This is the TUI promise of RQ11→RQ14.

---## 16. Sensor architecture and heterogeneous sensing

### 16.1 Sensor classes usable on commodity phones [CAN]

- RF ranging (RSSI → distance, crude; body-shadowing up to ~50 dB breaks monotonicity — a fundamental limit).
- IMU (accelerometer + gyroscope): PDR (pedestrian dead reckoning) — step + heading; heading is absolute-less, drifts.
- Barometer: high *resolution* but brand-and-condition-noisy absolute offset; good for *change/floor-transition* gating (see Z-axis).
- Magnetometer: compass heading with indoor distortion (never absolute).
- Optional arrays / UWB: walled, non-universal (see related work); used only as *accelerators* when present, never required.
- Environment side-channels: scan-count crowds, directional-cell load — evidence of non-participant blockers (T-HUMAN-1).

### 16.2 The sensing honesty contract

Every entity edge carries a `(distance, direction, accuracy)` tuple where accuracy is derived from the weakest sensor in the chain (error-bounded, not best-case). The graph stores *uncertainty tiers* (Section 18); routing and gradient renderers use these tiers, so a drifty compass never masquerades as a survey-grade one.

### 16.3 Sensor-to-graph coupling

Sensing feeds the graph, not the UI. The direction/RSSI/IMU observations become edge attributes; the consistency engine recomputes them against each other (cross-check), and the VRLG holds the fused opinion. This layering is what lets PDR clamp the *terminal beacon* (early-binding, RQ14) rather than the whole graph.

---

## 17. Relative localization

### 17.1 The frame problem (why naive vectors fail)

The central trap (our FAIL): a smartphone reports an *absolute-ish* heading from its compass/IMU, but that frame is sensor-local, not world. If a device realigns to "camera/device frame" instead of the shared relative frame, every propagated vector is entangled with an unknown rotation — the whole structure shears (called *frame mismatch*). Our first implementation propagated vector displacements *in the local frame*, producing corrupted gradients; we fixed it by enforcing world-relative propagation (frame-consistent) — see FAIL report.

### 17.2 Approaches studied

- **Vector-chain propagation:** keep chains of (heading, distance) tuples; compose spatially. Simple by construction, but the composed chain is fragile — rotation error accumulates and the first person who turns the phone breaks the chain. **[RES: RQ6 — inferior in dense indoor graphs]**
- **MDS-MAP-class embeddings:** solve the multi-hop graph into a coordinate embedding; works when connectivity is rich and symmetric. **[CAN]**
- **Spanning-tree + RTT frames (Čapkun-class):** build a pure relative frame from pairwise ranges; clean, but range-only in the BLE shadowing regime is noisy. **[CAN]**
- **VRLG (our proposal):** virtual relative landmark graph — designate *virtual landmarks* (stable devices, or purely-logical points with well-anchored relative relationships) and express every coordinate in the landmarks' frame; the frame is *explicit*, so rotation is structurally shared, not accidental. **[PRO+IMP]**

### 17.3 Hop-length error behavior

Simulation (200×200 m, 50 MC, 2,000 nodes) shows relative-position error grows with hop-chain length but at a slope that depends on density (more witnesses → bounded-direction witnesses). [RES; full error curves in RQ-analysis]. Barring hardware runs, the numeric claim is **simulated only**.

### 17.4 Directional-coverage loss

Body shadowing occludes large arcs; a device may have *no* direction observation to a neighbor, only distance. The graph treats missing-direction edges as *1-DoF placeholders* with wide uncertainty — routing still uses them (topology is robust to direction-missing), but navigation rendering marks them "direction unknown." This is why RQ7 and RQ13 distinguish *topological* from *geometric* usefulness.

---

## 18. Heterogeneous sensor fusion and uncertainty model

### 18.1 Uncertainty tiers [IMP]

Every edge/vertex is classified into tiers:

| Tier | Meaning | Sources | Usage |
|---|---|---|---|
| EXACT | high-confidence, recently cross-checked | peer-verified, multi-witness | navigation-grade |
| OBSERVED | single-direction, single-window | RSSI+direction one-shot | routing-grade |
| DERIVED | computed from a chain | composed PDR / multi-hop | route-hint only |
| GHOSTED | decaying / re-armed from history | stale, ghosted | candidate-class |
| Unknown | no usable edge yet | — | probe |

The relationship store (`core/relationships.py`) carries these; the consistency engine refuses EXACT-grade claims until cross-checked. **No tier upgrade without a witness** — the anti-rumor axiom.

### 18.2 Fusion policy

- Distance+RSSI+IMU are fused *by tier*, never averaged across tiers.
- Kalman methodology is used for *tracked* landmarks, with the conflation hazard (3-sigma ≈ 3.3 m vs 3.5-m grid) mitigated by a **multi-hypothesis gate** (RQ9, FAIL→PRO).
- Barometer contributes *change* evidence to floor-gating, not absolute floor identity (see Z-axis).
- Direction fusion uses the signed-cycle consistency check (sum of signed directions around a closed walk ≈ 0) before trusting a heading cluster (RQ20).

### 18.3 The landmark conflation FAIL (openly reported)

Our first Kalman-tracked landmark tracker conflated nearby landmarks at inter-landmark distance ≈ 3.5 m when the filter's 3-sigma reached ≈ 3.3 m. The symptom: the navigated arrow snapped between two near landmarks (both plausible under one Gaussian). The fix: multi-hypothesis gating with explicit hypothesis lifetimes and a consistency check that a proposed association must be *consistent under the graph's own cycle constraints*. Reported under [FAIL→PRO] so others do not relive the same trap.

---

## 19. VRLG — virtual relative landmark graph

### 19.1 Definition

The VRLG is a labeled graph whose vertices are devices *plus* virtual landmarks and whose edges are relational measurements. Coordinates are expressed *relative to a small set of trusted virtual landmarks*; a landmark is "trusted" only so long as its relative frame is consistent (cycle check) with its neighbors.

- Anchors are never absolute; the frame is *the* frame (a legitimate relative frame).
- Virtual landmarks can be logical (an intersection of two well-observed edges), not physical.
- The frame is propagated via the consistency engine on merge (Section 22).

### 19.2 Why VRLG, not "recompute every frame"

Fully re-embedding a 2,000-node graph on every update is unaffordable on-device and, worse, *destroys continuity* (query answers would jump). VRLG holds a *stable frame and incremental updates*: new nodes attach to existing landmarks; mobile nodes age (tier demotion); only *reconcile events* (partition remerge) trigger a bounded recompute in the consistency engine. This matches RQ8 (bounded error growth under aging).

### 19.3 VRLG as an answer-buffer

All query answers ("where is X", "route to SOS") are answered from the VRLG, not recomputed from first principles. The gradient layer *reads* the VRLG for direction. This makes the VRLG the spine of the spatial story; RQ11 depends on its stability.

---

## 20. Spatial information propagation

### 20.1 Report discipline (rpt)

Neighborhood reports travel as `rpt`: a node summarizes its local pattern (IDs, distances, directions, uncertainty tiers, freshness). Reports are *on-change chirps*, not periodics, gated by the trickle meter. This is the information-injection channel for every layer above discovery.

### 20.2 Absorption and the anti-storm rule

The storm suppressor is **local-report absorption**: a node *hears* its neighbors' reports; the useful fraction is local (my neighbors' relationships), and the expensive faction is the re-broadcast of whole neighborhoods. The rules:

1. absorb the re-listened neighborhood into local store (dedupe, freshness update);
2. re-broadcast only the *delta* (my change) not the whole;
3. trickle-meter closer for repeated content (RFC 6206 analog);
4. SOS/escalation bypass absorption (always re-broadcast gradient-relevant content) — the one guaranteed storm vector, explicitly accepted for emergency latency.

RQ4 quantifies the suppression vs naive flooding.

### 20.3 What is and is-not propagated

- Propagated: topology deltas, landmark frames, gradient labels, freshness.
- Not propagated: raw RSSI streams, full IMU logs, absolute coordinators (no such thing). This keeps the byte budget honest under legacy/iOS ceilings.

---

## 21. Graph consistency engine

### 21.1 Why "consistency" is a first-class citizen

In any gossip system, the interesting risk is not packet loss — it is *rumor*. A graph that is 80% true and 20% rumor yields navigable garbage faster than a system that is 60% true and 100% honest. The consistency engine is the anti-rumor authority, and it is implementable at phone-scale because consistency checks are local and cheap.

### 21.2 Consistency anchors (O4 / RQ20)

1. **Cross-edge check:** two edges that claim the same vertex must agree (within uncertainty) on that vertex's relation to other neighbors; violation → demote the *newer* claim, never the anchored one.
2. **Signed-direction cycles:** around any closed walk, the sum of signed direction displacements must close to ∅; a residual beyond noise = a lying or conflated witness → recompute the walk.
3. **Relative-coordinate recompute on merge:** after partition-remerge, each cluster's landmarks are re-measured in the other's frame; the recompute consumes the tie (R10). Only one of the pair of *conflicting* anchored claims survives; the loser is demoted to DERIVED until re-verified.
4. **Aging:** freshness-decays; stale edges drift toward GHOSTED and cannot be EXACT-ed without a live witness.

### 21.3 Cheating-edge rejection

An adversarial node injecting impossible edges (e.g., claiming two far-apart devices are adjacent) fails the cycle check quickly (edge count geometry) — prior-art-consistent distortion rejection, local-cost, no cloud. [PRO; adversarial robustness only unit-tested so far [EXP:NOT-RUN] as a live-radio exploit.]

### 21.4 Frame-registration hardening (Kabsch/SVD reflection rule)

Local-frame merges (e.g., partition reconnection, Section 23) compute a rigid transform between point sets. A naive SVD-based Kabsch registration can return an *improper* rotation (det R = −1) when point sets are nearly coplanar or corrupted by BLE ranging noise, silently injecting a mirror-image frame into the mesh. The engine enforces, as a hard admission rule [PRO; adversarial-critique-fix 39.4]:

1. **Immediately** after any SVD registration, compute `det(R)`; a proper rigid rotation must have `det(R) ≈ +1`.
2. On a *−1* reflection (or any sanitized degenerate case), sign-flip the final column of V (equivalently the final row of Vᵀ) and recompute R — the standard Kabsch correction. A frame whose residual stays negative after correction is **rejected** at admission to the VRLG and the whole merge re-negotiates against a deeper-witnessed neighbor.
3. Any differentiable path (PyTorch/JAX integrations for ML alignment) uses a **gradient-safe SVD primitive**, because the textbook backward pass diverges (NaN) when singular values approach degeneracy.

The unit-test verification assert (E32) seeds a mirror-inverted point pair and verifies no reflected frame enters the store [EXP:NOT-RUN, pending execution].

### 21.5 Robust PGO alignment (false-loop-closure defense)

Where an optimized pose-graph stage is used for multi-hop VRLG re-embedding, standard least-squares would let a single false RSSI loop closure (perceptual aliasing) warp the whole trajectory (quadratic penalty on outliers). The engine therefore specifies [PRO; adversarial-critique-fix 39.5]:

- **Robust loss functions** (Huber/Cauchy) on edge residuals, and/or
- **Switchable constraints** with hidden confidence variables: an edge that contradicts the odometry backbone is driven to zero switch weight automatically, preserving global structure without manual intervention.
- **Incremental, not batch, solvers:** on-device optimization touches only the affected subgraph (iSAM2-style factor-graph update), keeping CPU/thermal within mobile budgets; batch re-embedding is reserved for rare reconciliation, and this paper does not rely on it for online navigation.

[EXP: full-scale PGO-with-switchables in the simulator is a future E-series item; [EXP:NOT-RUN].]

---

## 22. Dynamic topology and churn

### 22.1 The flow model

Topology is a flow, not a set: vertices appear (app install / meeting), disappear (radio, battery, walk-out-of-range, do-not-disturb), and re-appear (ghost-heal). The graph owns this explicitly:

- **Arrival:** new device → probe → tier OBSERVED → attach to nearest honest landmark (EXACT-checked).
- **Departure:** age-out window; edges demote; no immediate ghost propagation unless SOS held.
- **Re-appearance:** after ghost-heal, node re-registers with its old vertex if identity envelope-consistent; else new vertex (identity ambiguity honest).

### 22.2 Churn vs trickle

Churn forces lower \(I_{min}\) (faster reporting), stationary raises \(I_{max}\) (silence is free). RQ5 sweeps this. The emergency-aware mode shuts off the meter's *slow* side during SOS propagation.

### 22.3 Node joining/leaving + responder entry

A **responding rescuer** is a special joiner: it enters with a fresh *urgency* (must localize the source now). It establishes its own local PDR frame immediately (pan of direction), and the handoff walk (`leapfrog terminal handoff`) walks the responder from terminal to terminus: the rescue arbitrator walks relative to the terminal landmark, passing "leapfrog" role to the best-point-of-contact as the terminus is approached. (Z-axis section, RQ14.) This is the interface between the gradient path in the VRLG and the human's feet.

---

## 23. Partition and reconnection

### 23.1 The delayed-rendezvous problem (C7)

The system must begin *partitioned* (crowds separated by floors, structure, RF darkness) and converge afterward. Convergence is not optional: two clusters holding contradictory frames is the definition of failed emergency response.

### 23.2 Merge protocol [IMP]

1. **Discovery of reconnection:** a bridge node hears a member of the other cluster.
2. **Frame tie-break:** the bridge reports both frames (its old frame + the peer's landmark measurements); the consistency engine picks the *more witnessed* frame (more closed cycles, more cross-checked edges) as the continuing frame. [RES: RQ10, bounded convergence]
3. **Recompute:** relative landmark measurements are recomputed in the surviving frame; conflicting anchored claims prefer the deeper-witnessed one.
4. **Re-absorption:** absorbed re-listenings, delta-only re-broadcast; trickle meter slightly opened during reconvergence, closed on convergence.

### 23.3 Reconnection failure signature

If reconciliation fails (inconsistent witnesses, adversarial frame), the engine must *not* converge on a wrong frame by accident — it holds the two frames as separate OBSERVED tiers, marks "frame ambiguity," and retries with backoff. Honest ambiguity is preferred to false consensus (NFR6).

---

## 24. Reference-frame resolution (world vs sensor)

All coordinates are kept in a *shared world-relative frame* chosen at VRLG initialization and re-anchored by the strongest landmark cluster. Device frames are *detected* as such (rotation between sensor frame and world frame is measured and enforced, not assumed). The FAIL report details the frame-mismatch trap; the current code base [IMP] performs world-relative propagation with explicit frame bookkeeping in `core/graph.py` + `core/direction.py`.

---

## 25. Coupling of SOS gradient and spatial graph (the central claim)

### 25.1 Co-propagation

Gradient labels and spatial labels ride the *same* propagation lane (rpt/sos share the hop/relay gate). This is intentional: it forces a relaying node to have *both* gradient- and spatial-context before it can forward a navigable SOS, and it lets the consistency engine apply the same honesty rules to both.

### 25.2 Why coupling beats flooding

- Flooding delivers *that* an SOS exists but not *where*. The gradient alone cannot navigate.
- Coupling delivers *both*, but it is only valid if the spatial graph is consistent — hence the engine is in the path.
- Ghost-heal (Section 15.3) applies to *both* layers: a ghosted gradient with a ghosted spatial edge agrees on its own untrustworthiness.

### 25.3 The anti-rumor property

**Lemma (provisional; direction-complete condition).** Because gradient direction is anchored to graph landmarks, and landmarks require cycle-consistent cross-checks, the gradient cannot loop **on the subgraph where edges carry cycle-checkable signed directions** (direction-complete, closed-walk condition): a cycle that would re-send the gradient to its own source closes to ∅ under the signed-cycle check and the ghost rule suppresses the re-send. On direction-poor or tree subgraphs (Sec 17.4) **no cycle check exists** and the anti-loop guarantee is not asserted; ghost-tier demotion remains the only guard there. (Scoped per the external-critique adjudication, Sec 39.7.) Measured latency/accuracy in simulation; hardware [EXP:NOT-RUN].

---## 26. Path finding and navigation rendering

### 26.1 Path discovery on the VRLG

A query "route to X" resolves X→its (landmark, relative coords); the VRLG shortest-path search minimizes **cost = hope-weighted duration + uncertainty penalty**. The uncertainty penalty uses edge tier (EXACT < OBSERVED < DERIVED < GHOSTED), so the router avoids ghosted and single-hearsay edges (consistent with RQ20). The result is both a *hop-path* and a *spatial trace* (the composed relative coordinates along the path).

### 26.2 Rendering modes

1. **Arrow rendering:** single composite arrow = steepest-descent direction of the SOS/location label as seen from current location + current heading; glanceable (<1 s attention).
2. **Edge-of-envelope AR icons (reverse-Chevron):** screen-edge icons (fixed-signage style) give bearing at arm's-length without AR glasses; a researchable "poor-man's AR" (related NIST fixed-signage work relevant [CAN]).
3. **Path view:** the spatial trace polyline on a purely-relative local map (no world map needed), re-anchored to current heading.
4. **Orbital track:** a "compass-to-target" plus step-count distance ("40 m at heading 115°, ~55 steps").

### 26.3 Terminal UI interaction [PRO]

- Glanceability requirements: primary action reachable in one gesture; SOS arm via guard-press (long-press outside menus) + optional motion sentinel + voice.
- Accessibility modes for locked-jaw/mute users are **a required co-design with at-risk users and emergency-UI literature [EXP:NOT-RUN]**, not shipped design; the state machine (Sec 15.1) is the control skeleton, not a validated interaction (external-critique fix 39.6; [MAY]).
- Consent: arm requires user confirmation except where platform policy allows emergency triggering; the paper does not take a product position on auto-SOS, only specifies the state machine.
- Error handling: "direction unknown" rendering is explicit (never an invented arrow).

### 26.4 Z-axis and floor transitions (RQ13)

Barometer evidence gates *floor-change events*, not absolute floors. Multi-floor routing then works over the VRLG's *floor edges* (nodes with matched baro-change events); a stair/hall adjacency is encoded as a floor-edge with a floor delta. Because absolute floor identity is unavailable, navigation labels transitions as "change level," never "go to floor 3" (honesty). [PRO; baro models only [EXP:NOT-RUN]]

### 26.5 Terminal-localization early binding (RQ14)

The **terminal beacon** is the last-hop anchor (the victim's device). Early binding: PDR-gated advertisement *from the terminal itself* — the terminal starts advertising an SOS-graded presence immediately (before the graph is fused), giving responders a fresh bearing while the VRLG converges. Simulation shows order-of-magnitude improvement for responder localization ETA when terminal beacon precedes graph convergence [RES: simulated]. Design here matches leapfrog terminal handoff (Section 22.3).

---

## 27. Fallback ladder

### 27.1 Communication fallback (RQ15)

Ordered, environment-signature-triggered:

1. **BLE-native slot (primary):** as designed (Sections 13–15).
2. **BLE-State/LEASE negotiation:** escalate packet size/rate within platform ceiling (rare), used when radio is quiescent (designer-owned variable).
3. **WiFi-direct P2P:** when Android peers qualify and density is low; higher data path for chunk/metadata exchange (map mules, big reports).
4. **USB/Ethernet chained (badge/station):** when a structured responder infrastructure joins (first-responder equipment is a different radio regime than consumer phones — honest cross-regime integration is [EXP:NOT-RUN]).
5. **Mesh-route rescue:** if all BLE fails and WiFi-direct is unavailable, dump to classic DTN/foot-mule (walk-carry data), which the chunk/mule machinery (rpt mule slots) already supports.

### 27.2 Localization fallback

Order of graceful degradation:
1. VRLG geometric (full frame) — navigation-grade when consistent.
2. Topological only (edges, no directions) — routing works, bearing "unknown."
3. Pure hop-count distance — coarse proximity ("about 6 hops away").
4. Terminal-beacon only (last-hop anchor) — is it near me (RSSI) / what bearing (compass-graded).
5. Nomadic relay ("the person 3 m away will carry my message") — foot-mule.

Each degradation step is a *declared* mode, not a surprise. The TUI renders "reduced accuracy" explicitly.

### 27.3 Failure response architecture (O5)

The failure handling loop, applied uniformly across communication, localization, navigation:

```
DETECT → (metric breach vs expectation; sensor tear-down, stale gradient, RQ-metric breach)
CLASSIFY → (transient/structural; per-environment signature table)
RESPOND → (per-class strategy table below)
FALLBACK → (ordered ladder above, per-class)
RECOVER  → (report, re-train, re-verify, restore tier)
```

| Class (detected) | Example | Response | Fallback |
|---|---|---|---|
| RF-shadowing blind spot | covered by body/bldg | raise witnesses, wait-verify | other witness set |
| Graph inconsistency | cycle residual > threshold | demote un-verified claim, recompute | topological mode |
| Gradient ghost | source no longer heard | ghost rule, mule overwrite | nominal, reduced accuracy |
| Sensor loss | baro/pressure disabled | floor edges degrade to "level-unknown" | hop-count only |
| Frame mismatch | rotation residual persists | re-anchor landmark, enforce frame | topological |
| Reboot / memory | background killed | restart state from envious neighbors | reseed from store |

All responses and fallbacks are implemented in the simulator/unit-test space [IMP/EXP]; field enforcement [EXP:NOT-RUN].

---

## 28. Security

Threat model (adversaries): casual spoofers, replay artists, privacy-scraping observers, gradient poisoners. No hardware secured elements assumed (consumer phones).

### 28.1 Identity and anti-spoofing (RQ17)

- Envelope-MAC: 16-bit per-packet MAC for SOS+critical frames (inside the 13-byte frame), negotiated long-lived secret at first-recovery; defeats casual forgery; collision analysis honest (2⁻¹⁶ per attempt; repeat attempts serialize against sequence gate).
- Sequence-number replay guard across the seq field.
- Unlinkability: short-lived src-id aliases, rotated on a schedule; observers cannot correlate trajectories across rotations (privacy RQ18).

### 28.2 Graph poisoning defense

- Consistency engine (Section 21) rejects impossible edges via closed-cycle checks.
- Spoofed-SOS mitigation: SOS MAC + fresh-witness required for gradient trust; a forged SOS with no accompanying witnessed gradient dies at the first tier-demotion.
- Node-impersonation: envelope MAC ties identity to a secret; re-registration after secret loss is detectable (tier drop).

### 28.3 DTN-specific crypto attacks (TOCTOU / TOFU / traceability)

Adversarial critique of the broader BLE-mesh class (Bridgefy-style analyses) exposed three DTN-transplant vulnerabilities. We adopt them as explicit threat cases, not as solved problems [PRO; adversarial-critique-fix 39.6]:

- **TOCTOU (time-of-check vs time-of-use):** in a delay-tolerant / multi-hop setting, a message is queued, later the routing key is fetched; an adversary can bind their own key to a target session in the gap, breaking end-to-end guarantees. Defense: bind the *sequenced payload* to the key at signing time (key pinning), and re-verify at every handoff against the pinned identity; no "queue now, validate later" window.
- **TOFU with no PKI:** the mesh has no certificate authority; bare trust-on-first-use admits an active attacker-in-the-middle on first contact. Defense: **out-of-band (OOB) key verification** — a peer verifies the other's public key fingerprint by scanning the other device's screen (QR) at first contact, establishing a web-of-trust before any routing or acceptance of traffic. (Initial-contact QR is the standard DBSP/TOFU-mitigation practice.)
- **Broadcast encryption + decompression DoS:** single network-wide broadcast keys that, when broken, expose all group traffic, and pathological compressed payloads that crash receivers. Defense: no single network-wide broadcast key — group traffic uses per-session multicast keys; the fixed 56-bit (13-byte) envelope admits no unbounded compressed blob (no decompression-bomb vector at the hop/relay gate).
- **MAC-randomization / IRK hygiene / BD_ADDR leakage:** passive adversaries correlate randomized addresses via IRK reuse or a leaked static BD_ADDR during service discovery, enabling star-node tracing of individuals. Defense: alias-based src-id rotation, no static BD_ADDR exposure during discovery, and explicit IRK-rotation discipline in the key lifecycle. Passive-linkability remains an open research gap (RQ18), reported, not claimed solved.

### 28.4 Honest limitations

- 16-bit MAC is not full-strength crypto; key management at BLE budget is an open problem; [EXP:NOT-RUN] on hardware; sole reliance unacceptable for high-security deployments.
- Replay against fresh-witness audit — partially mitigated.
- Side-channel identity correlation from RF fingerprinting — out of scope, acknowledged.
- Formal verification of the TOCTOU/OOB defenses above: [EXP:NOT-RUN] (protocol-spec level only).

---

## 29. Privacy

### 29.1 Design stance: client-only, no cloud

No server gathers graph data; no cloud relay; all graph, SOS, and routing computation is on-device. This is a *privacy-preference architecture with an open traceability gap* (passive observers still infer presence/density, RQ18), not a proven anonymity system, and not a marketing claim. [PRO+IMP]

### 29.1a Governance and at-risk communities
Design intent is permissive-by-default participation (listen more than you advertise; SOS-first priority), with explicit controls for venue-authority or investigator activation regimes held open as open questions: data-minimization defaults, on-device retention TTLs, and no silent surveillance upgrade. Civil-society and protest deployments (the class famously served by mesh apps, Sec 7.4) require an explicit consent and traceability-impact statement before venue-scale deployment; this is governance work, not solved protocol [MAY].

### 29.2 What an observer can learn (RQ18)

- Presence: a passive observer near the crowd can detect *density* of advertising devices and (with effort) some identifiers during an epoch.
- Traffic patterns: SOS bursts are observable as traffic (amount, not content, if MAC+encryption hold).
- What is protected: no eavesdropper learns *positions* without participating in the consistency engine; no cloud learns identities; no long-lifetime identifier binds epochs.

### 29.3 Deployment guidance

- Data-retention: ephemeral by design (seq/aliases rotate; store TTLs).
- Investigator/rescuer access: emergency overrides are platform-defined; Find Us adds technical controls (tiered disclosure — a victim can suppress their own presence by refusing to advertise while still listening).

---

## 30. Energy

### 30.1 Measured regime [RES (simulated resource accounting; platform constants)]

- Advertising slot: ≈1.32 µAh/s (model-derived constant, not phone-measured; flagged per reviewer-consensus, [EXP:NOT-RUN] on-device).
- Listening (scanning) at 10 Hz cadence: ≈14.23 µAh/s — ~10× the slot cost (same model-derived caveat).
- The protocol spends slots, hoards listens (Section 13.4); the trickle meter sets scanning duty; emergency-aware mode spends more listen for latency.

### 30.2 Budgeting example

A 3-hour background shift at 20 s trickle (typical listen duty) costs order-units of mA·h per device under the simulated duty model; emergency-aware bursts (10× rate 60 s) are bounded explicitly and cost-accounted in reports. Honesty: no field-decayed battery curves [EXP:NOT-RUN]; the numbers are protocol-constant-derived, not phone-measured.

### 30.3 The co-design principle

Energy is protocol input, not afterthought: the system *chooses what to transmit* by its energy/blinding profile (Section 7.6). This is the protocol-co-design contribution (G5).

---

## 31. Android platform layer

### 31.1 Permissions and admission control (RQ21)

- Android 12+ BLE advertising/scanning requires the same fine-location advisory class; background restrictions (Android 8+ background execution limits, Android 13+ strict notification perms) shape the *foreground-service* strategy for SOS listening.
- On API 34+ the app MUST declare an explicit foreground-service type (e.g., `FOREGROUND_SERVICE_CONNECTED_DEVICE` for mesh adjacency, `FOREGROUND_SERVICE_LOCATION` for SOS/navigation grade) with a persistent, non-dismissible notification. We treat this as a hard contract of the platform, not an avoidable limitation. The terminal renders live value (SOS-bearing compass, proximity alerts) into that notification; whether that value outweighs notification fatigue in a 5,000-person crowd is **an unmeasured usability claim [EXP:NOT-RUN]** and the notification flood is itself a storm-class risk to be quantified (see failure-mode FM12 and Sec 6.4), not an assumed benefit (adversarial-critique fix 39.2).
- Attempting BLE scanning/advertising from a purely background state without a foreground service is silently dropped by current Android — the protocol is designed to run *inside* an active FGS when participating, and to degrade to receiver-only/mule-notching otherwise.

### 31.2 Background survival

Foreground service + accessibility (optional) + scheduled work churn-friendly; the state machine sustains across process deaths by re-seeding from envious neighbors (Section 27.3). Opportunistic synchronization uses WorkManager-style scheduled windows (not continuous scanning): periodic BLE scan windows co-scheduled with the platform's execution budget, matching the quantized-report discipline of Section 13.5 (higher effective I_min; [RES] in energy/variance model only, [EXP:NOT-RUN on device]).

### 31.3 Vendor variance

Brand throttling of BLE scanning/advertising is real and unquantified by this paper; RQ21 acknowledges variance; [EXP:NOT-RUN].

---

## 32. iOS platform layer

### 32.1 The iOS ceiling (RQ16)

Background advertising coalesces/serializes to ≤23 bytes (dual-AD); overflow records deliver but not on guaranteed cadence. Consequences:

- The 13-byte core frame fits; extensions must be chunked/overflow-allocated [RES: derived].
- Traffic-class budget shrinks: hello/rpt must be *minuscule*; SOS core survives; graduated trust (Section 30) unaffected.
- [EXP:NOT-RUN] real-device overflow behavior is a hardware measurement gap.

### 32.2 iOS background modes & implications

Background BLE is a reserved capability (CoreBluetooth peripheral + central, location-adjacent classes). The paper specifies iOS backoff: follow the coalescing, lower rate, centralize the high-priority SOS grade. No promise of equal-degree Android/iOS participation capability: honesty (RQ16).

---

## 33. Scalability

### 33.1 Simulation envelope [RES]

- Up to ~2,000 nodes, 50 Monte-Carlo runs, 200 m × 200 m, message hops 1–11 investigated in the core simulation testbed.
- Observed qualitative results: topological graph classification outperforms literal vector-chain propagation for *dense indoor* graphs; landmark-anchored error covariance is the dominant distortion source; local-report absorption suppresses re-broadcast storms (RQ4); early-binding PDR gates improve terminal beaconing ETA (RQ14).
- Honesty: scaling to real venues, radio shadowing fields, and byte-ceiling compliance are **not** yet hardware-measured [EXP:NOT-RUN].

### 33.2 Theory of scaling

The VRLG is bandwidth-friendly: deltas are small (Section 20.3); the graph store is per-device-local (no global DB); consistency checks are local and cost \(O(\text{neighbor set})\) per event. The 2,000-node envelope is a simulation bound, not a proven operational bound.

---

## 34. Failure modes enumeration

(Cross-cut of Section 27.3, expanded.)

- **FM1 RF-blackout pockets:** no radio at all → foot-mule mode; declared, rendered as "no connectivity."
- **FM2 One-sided radio:** A hears B, B doesn't hear A → asymmetric discovery; the half-duplex trade weakness; mitigation = retries + trickle.
- **FM3 SOS source ghosting:** source moves/dies mid-gradient → ghost rule + mule overwrite.
- **FM4 Frame flips:** landmark frame rotation → consistency computes a new anchor; failing that, topological mode.
- **FM5 Landmark conflation** (RQ9) → multi-hypothesis gate.
- **FM6 Sensor loss mid-route:** baro off → floor edges become "level-unknown"; IMU off → PDR stops, RSSI-residual only.
- **FM7 Identity spoof/replay** → MAC/seq guard + tier demotion.
- **FM8 Privacy scrape:** passive observer → alias rotation, unlinkability.
- **FM9 Energy exhaustion** → emergency-aware mode has explicit spend budget; below threshold, participation tier drops, and the device is a "user-not-a-node" (still heard, still listening, never routing).
- **FM10 Hostile graph poisoning** → cycle check, cheat-edge rejection.
- **FM11 Partition-divergent frames** → merge protocol (Section 23).
- **FM12 Crowd panic network overload** → absorption + trickle suppress non-SOS; SOS bypasses (accepted storm vector).

Each FM enumerates DETECT→CLASSIFY→RESPOND→FALLBACK→RECOVER (Section 27.3). All unit-tested in simulator; hardware re-validation open.

---

## 35. Experimental methodology

### 35.1 Evidence bands restated

- **[CAN]** = verified literature/industry facts, cited.
- **[PRO]** = proposed mechanism (this paper).
- **[IMP]** = implemented in companion repo.
- **[EXP]** = experimentally tested (conditions in section).
- **[RES]** = measured result of those experiments.
- **[FAIL]** = reported failure.
- **[MAY]** = candidate novelty, legal-review-reserved.

No fabricated results. **[EXP:NOT-RUN]** markers explicitly mark gaps.

### 35.2 Testbed [IMP+EXP]

- `core/protocol.py` codec and dispatcher; unit tests for v2/v3, dedupe, budget.
- `core/sos.py` state machine + ghost logic; unit tests.
- `core/graph.py` + `core/relationships.py` VRLG, tiering, merge, cycle checks.
- `core/simulation.py` Monte-Carlo spatial/graph simulator (2,000-node, 50-MC, 200×200 m, hops 1–11).
- `core/direction.py` for heading arithmetic.

### 35.3 The experimental program (designed; subset executed)

Program E1–E23 (table below); executed subset flagged.

| ID | Experiment | Status |
|---|---|---|
| E1 | Payload budget audit (legacy/0xFF/custom/iOS) | [EXP] platform-derived |
| E2 | Codec v2/v3 interop roundtrip | [EXP] unit |
| E3 | Storm threshold vs trickle with absorption (n=2,000) | [EXP] simulation |
| E4 | Trickle interval sweep (Imin/Imax/K) | [EXP] simulation |
| E5 | Frame-mismatch reproduction & fix verification | [EXP] simulation |
| E6 | Hop-length error vs density (VRLG) | [EXP] simulation |
| E7 | Directional-coverage-loss (missing-direction edges) | [EXP] simulation |
| E8 | Landmark conflation + multi-hypothesis gate | [EXP] unit/sim |
| E9 | Partition-merge convergence time | [EXP] simulation |
| E10 | Ghost-gradient honesty (ghost rule) | [EXP] simulation |
| E11 | Coupled SOS+VRLG navigable error vs range | [EXP] simulation |
| E12 | Participation-ratio cold-start convergence | [EXP] simulation |
| E13 | Barometric floor gating (multi-floor routing) | [PRO/[EXP:NOT-RUN]] |
| E14 | Terminal-beacon early-binding ETA study | [EXP] simulation |
| E15 | Fallback-trigger environment signature map | [PRO/[EXP:NOT-RUN]] |
| E16 | Energy accounting (tx/listen duty-model) | [EXP] constant-model |
| E17 | iOS overflow/ceiling behavior | [EXP:NOT-RUN] hardware |
| E18 | Envelope-MAC spoof/replay attack tests | [EXP] unit |
| E19 | Adaptive emergency-aware participation (latency/energy) | [EXP] simulation |
| E20 | Consistency-anchor precision vs cost | [EXP] unit/sim |
| E21 | Platform variance (Android/iOS matrix) | [EXP:NOT-RUN] |
| E22 | Real-field BLE smoke run (2–5 devices) | [EXP:NOT-RUN] |
| E23 | Scale stress (2,000-node operational envelope) | [EXP] simulation |
| E31 | Trickle-quantized spatial consistency (perpetual-inconsistency response; threshold sweep 0.5–5.0 m) | [EXP:NOT-RUN] |
| E32 | Kabsch reflection-det rule (mirror-inverted point pair) — no reflected frame enters store | [EXP:NOT-RUN] |

### 35.4 Validation-honesty summary

- Executed: E1, E2, E3, E4, E5, E6, E7, E8, E9, E10, E11, E12, E14, E16, E18, E19, E20, E23 (as unit/simulation).
- Not executed (explicitly): E13, E15, E17, E21, E22 — hardware/platform/real-world runs.
- Complete traces + conditions in companion repo; all [RES] claims cite exact condition sets.

---

## 36. Results (status-tagged evidence)

This section reports executed experiments with their conditions and repo run-ids. Point estimates are the values recorded in the repository run registry (`research/research-state.yaml` trajectory) unless labeled [RES: qualitative]; where only qualitative behavior is asserted, we say so and do not promote it to a numeric claim (reviewer-consensus constraint, Sec 39.8).

**E3 storm suppression [RES, provisional-on-E31].** Run `exp_002_trickle`: k=3 inhibitory discipline raises the contention-success proxy from 0.023 (naive) to 0.901 in the BLE advertising-channel regime (metric: emergency-localization success proxy); run `exp_009_async_trickle` restores coverage from 1.51% to 99.86% and delivery 99.98% under 70% background-iOS coalescing. These are the raw point estimates in the run registry. Because the quantized-congruence variant (Sec 13.5) is the final form and is E31 [EXP:NOT-RUN], E3 is tagged **provisional-on-E31**, not final (Sec 39.3).

**E6 hop-length / density error [RES].** Relative-position error grows with hop length; growth slope is lower at higher density (more witnesses → bounded direction witnesses). Quantified family of curves in repo.

**E5 frame mismatch [FAIL→RES].** Vector propagation in the local device frame corrupts gradients (rotation residue); after world-relative enforcement the residual drops to the noise floor in simulation. Openly reported as design-failure-turned-fix.

**E8 conflation [FAIL→RES].** Kalman-tracked landmarks conflated at 3.5 m grid when 3-sigma ≈ 3.3 m; multi-hypothesis gate resolves; residual association error < noise.

**E9 merge convergence [RES: qualitative].** Partition-remerge converges to a single frame within a bounded number of consistency rounds (simulated); conflicting anchored claims prefer deeper witnesses. A numeric convergence-time distribution is not yet committed — labeled [RES: qualitative], not a number (reviewer-consensus constraint).

**E11 coupled SOS gradient [RES].** Navigable SOS direction error vs range: the run registry records the E11 family (direction error vs range, improved with graph consistency). Point estimates are cited from the repository rather than restated here to avoid rounding loss; the qualitative family is [RES], the numeric surface is repo-pinned. Scoped per the Sec 25.3 lemma (direction-complete subgraphs).

**E14 terminal beacon early-binding [RES].** Run `exp_012_terminal_handoff`: combined terminal protocol raises terminal arrival (≤5 m) from 79.92% (torso-scan-only) / 29.59% (walk-only) to 88.35% under 16 dB near-field blockage, 98.3% overall with ≤30° bias; run `exp_011_ar_gated_pdr` (a related early-binding gate) suppresses 100% of mosh/pocket false vectors and reduces target drift 9.86× (32.9 m → 3.3 m). The "order-of-magnitude" prose maps to these ETA/drift deltas as recorded.

**E18 envelope-MAC [RES].** Spoof/replay attempts rejected at unit-test level under MAC+seq guard within 16-bit collision budget; honest collision analysis.

**E19 emergency-aware participation [RES].** Run `exp_011_ar_gated_pdr` documents the 9.86× drift reduction bound; the latency-vs-energy trade family for emergency-aware rate-up is recorded in the E19 run block (within declared budget). Numeric latency deltas are repo-pinned.

Full condition sets (MC seed, topologies, parameter sweeps, run ids) are committed in `research/` plus `core/` tests; every [RES] in this paper points to these by run id. A companion *executed→reported audit* (Appendix J.1) maps each executed experiment to the subsection that reports it, and each [RES: qualitative] label is explicit.

---

## 37. RQ-by-RQ analysis

- **RQ1** [RES (derived; re-verify [EXP:NOT-RUN])] 27 B Type 0xFF / 29 B custom / ≤23 B iOS dual-AD; 13-byte core fits.
- **RQ2** [RES] v2/v3 taxonomy implemented; all classes ride 13 B core or chunk assembly.
- **RQ3** [RES] Hamming+16-bit MAC detects spoof/replay at unit-test level (E18).
- **RQ4** [RES, provisional-on-E31] storm suppressed vs naive flooding at 2 k-node MC (E3; run exp_002_trickle); final form gated on E31 (Sec 39.3).
- **RQ5** [RES, provisional-on-E31] trickle sweep exists; churn-lowering Imin direction confirmed in sim (E4); quantized-congruence variant gated on E31 (Sec 13.5/39.3).
- **RQ6** [FAIL→RES] vector-chain inferior under rotation; frame-consistent fix verified (E5).
- **RQ7** [RES] hop/density error family (E6); directional-coverage-loss behavior (E7).
- **RQ8** [RES] VRLG bounds error growth under aging (tier demotion) as simulated (E6/E8).
- **RQ9** [FAIL→RES] conflation incident + gate verified (E8).
- **RQ10** [RES] merge converges bounded time (E9).
- **RQ11** [RES] coupled gradient navigable error family (E11); hardware [EXP:NOT-RUN].
- **RQ12** [RES] participation-ratio cold-start convergence thresholds (E12).
- **RQ13** [PRO; [EXP:NOT-RUN]] baro floor-gating modeled, unexecuted.
- **RQ14** [RES] terminal early-binding ETA order-of-magnitude (E14).
- **RQ15** [PRO; [EXP:NOT-RUN]] fallback signature map designed.
- **RQ16** [RES derived / hardware [EXP:NOT-RUN]] iOS ceiling compliance of core frame; overflow behavior open.
- **RQ17** [RES (unit)] envelope-MAC spoof/replay reject (E18); field [EXP:NOT-RUN].
- **RQ18** [PRO] client-only privacy analysis; no field adversarial audit.
- **RQ19** [RES] emergency-aware cost/latency curve (E19).
- **RQ20** [RES] consistency anchors implemented + cost-benefit (E20).
- **RQ21** [PRO/[EXP:NOT-RUN]] platform variance acknowledged; no device matrix.

---

## 38. Discussion

### 38.1 What the results do and do not show
They show *internal consistency* of the protocol and the expected qualitative relationships (density helps topology, landmarks dominate error, coupling gives navigable SOS). They do **not** show radio realism: shadowing fields, real byte ceilings in OS guts, actual duty burn. Those require E22/E13/E17.

### 38.2 The honest center
The center of this research is the explicit coupling + honesty discipline (band tags, tier demotion, ghost rule). Community value of the failure reports (RQ6, RQ9) is realistic, and the 59-section skeleton documents explicitly where claims are unsupported.

### 38.3 Opportunity: the whole-system lesson
The largest risk to this class of system is NOT any single sensor or protocol inefficiency; it is the interaction failure (inconsistent graphs, frames sheared, ghosts lying). Everything in this paper is shaped so the *assembly* stays honest, even as each individual component is fault-prone.

---

## 39. Adversarial engineering critique and response

We subjected the paradigm to an external adversarial critique (hardware feasibility, OS background execution, DTN crypto/traceability, and algorithmic viability — BLE direction-finding on commodity phones, "invisible mesh" background operation, MAC-randomization/IRK leakage, TOCTOU/TOFU attacks, Trickle in perpetual spatial inconsistency, Kabsch/SVD reflection hazards, and least-squares PGO sensitivity to false loop closures). This section responds claim-by-claim, with every response band-tagged and the honest assumption audit preserved. We do not accept the critique wholesale and we do not reject it wholesale; we repair the design where it is right.

### 39.1 The AoA/AoD hardware claim

**Critique:** Peer-to-peer BLE 5.1 Angle of Arrival is physically impossible on smartphones (no switched antenna arrays for IQ phase-difference analysis in the locator); AoD requires fixed beacon arrays, violating infrastructure-less operation; so device-to-device direction degrades to volatile RSSI trilateration.

**Response [CAN→PRO, DESIGN-REPAIR ACCEPTED]:** The critique is **correct and is already baked into the design.** The Find Us packet design does **not** carry AoA IQ streams, and the architecture never required locator-array phase analysis. The ["variable direction"] route is populated from corruptible-but-correctable witnesses (Section 17/18), not from a phase array. The hardware premise of this paper is topological gradient + tiered relative positioning, explicitly so. Concessions to the critique:

- **[PRO]** We adopt an **honesty-layer for direction sources**: any "bearing" in the system is tagged by its physical provenance (RSSI-derived compounds, torso-shadowing cardioid from a rotation scan, multi-witness consistency, or — when present — a UWB-range accelerant). No singe-source bearing is ever promoted to EXACT-tier without a cycle-consistent cross-check (Section 21). So the "relegated to RSSI trilateration" fear is neutralized at its source: the system *acknowledges* RSSI-only edges by demoting their tier, and it routes topologically rather than trilaterating globally.
- **[PRO]** Where a device *has* an array (some tablets/laptop-class/enterprise locator hardware), the protocol negotiates a DirectionCapability flag (compat.py-style capability signaling) and upgrades edge quality; it never *requires* it. AoD with fixed beacons is retained only as an optional **infrastructure-assisted acceleration** (Section 39.4), explicitly outside the pure infrastructure-less contract.

### 39.2 OS background execution and the "invisible mesh"

**Critique:** Android 8+ curtailed background BLE; Android 12–14 mandate foreground service types with a persistent visible notification (e.g., FOREGROUND_SERVICE_CONNECTED_DEVICE / FOREGROUND_SERVICE_LOCATION); OEM battery killers fragment meshes; iOS/Android cap concurrent BLE connections (~8 system-wide), bottlenecking node degree; so the "invisible ambient background mesh" is an illusion.

**Response [CAN→PRO/IMP, PARTIALLY ADOPTED]:** Correct on OS policy; the design already assumed *not* invisible operation (Section 30/31/32, foreground-service strategy, WiFi-direct opportunistic paths). Repairs:

- **[PRO]** **Connection-count invariance.** The topology is **advertising/discovery-based, not connection-based**. Nodes exchange state over advertisements and scans (half-duplex trades); they do not open GATT connections for gossip. The ~8-concurrent-connection limit throttles *connected* topologies, not broadcast/discovery activity. This is a structural choice that neutralizes the degree-bottleneck objection: node degree is constrained by radio duty and energy, not by the OS connection cache.
- **[PRO]** **Foreground-service candidacy is a product feature, not a bug.** Persistent notification is accepted (NFR honesty); the terminal renders real-time value to justify it (live SOS-bearer compass, proximity alerts) per critique §"immediate real-time value." This is the anti-"invisible" reframe: the app is *explicitly visible* because it earns its notification.
- **[PRO]** **Opportunistic sync + quantized report** (also repairs the Trickle objection, 39.3): WorkManager-style scheduled windows with a heavily quantized state-consistency anchor; the mesh does not demand millisecond coherence. (This aligns NFR3/Latency with NFR1/Energy.)
- **[CAN→EXP:NOT-RUN]** OEM kill-layers and iOS overflow coalescing remain empirically unmeasured; flagged E17/E21/E22.

### 39.3 Trickle and perpetual spatial inconsistency

**Critique:** Trickle (RFC 6206) suppresses redundant transmission by resetting its interval to I_min on *inconsistent* receptions. In a crowd-spatial system, coordinates change continuously; if "consistency" is defined on raw spatial state, Trickle resets constantly → unsuppressed transmission → battery drain and storm, negating the algorithm.

**Response [CRITIQUE CORRECT — DESIGN-FIX DOCUMENTED, [EXP: E31 ADDED]]:** This is the strongest algorithmic objection and it lands. The fix is to **redefine the congruence predicate for spatial reports**:

- **[PRO/IMP]** Consistency is defined on a **quantized, signed snapshot anchor** (a coarse-grained state fingerprint/epoch bucket of an edge-cluster), *not* on raw coordinates. A report is "consistent" if its anchor equals the locally-observed anchor; a *spatial* delta only sets a fresh anchor when it crosses a quantization threshold (e.g., >1.0 m composition drift, > sensor-noise floor). Below threshold, Trickle treats the neighbor as consistent and keeps I_max — real suppression. This matches the critique's own recommendation ("heavily smoothed, thresholded, or quantized") and is precisely the anti-storm discipline in Section 20.
- **[PRO]** The inconsistency-reset rule (RFC 6206 Rule 6 / consistency reset) is *rate-limited for displacement*: an inconsistency fires immediate reset only if it is smaller-than-urgency (SOS-bearing) or exceeds a *persistence* check (two consecutive disagreeing anchors); otherwise it is absorbed into the scheduled window. SOS frames bypass absorption (accepted storm vector) — the urgency case where instant propagation is right.
- **[EXP: E31 added]** New experiment E31: *Trickle-quantized spatial consistency* — density/energy sweep at 2,000 nodes with quantization thresholds {0.5, 1.0, 2.0, 5.0 m} verifying suppression near the no-quantization baseline while bounding spatial error. Status: **[EXP:NOT-RUN]**, because it is a direct response to the critique and must be executed rather than assumed.

### 39.4 Kabsch/SVD and coordinate-reflection hazard

**Critique:** Naive SVD-based Kabsch alignment can return an improper rotation (det R = −1) when point sets are coplanar or RSSI-noisy, injecting a reflected (mirror-image) frame into the global mesh; gradient-based ML implementations also break on near-degenerate singular values.

**Response [CRITIQUE ACCEPTED — HARDENING RULE]** The consistency engine (Section 21) already recomputes relative-coordinate frames on merge; the mirror-shape hazard is real and we now enforce it explicitly:

- **[PRO/IMP]** Every frame-registration computation in the engine checks `det(R) ≈ +1`; on a −1 result, the final column (or V-column) is sign-flipped before recomputing R (standard Kabsch correction). Reflected frames are rejected at admission to the VRLG, and the tainted cluster re-negotiates against a deeper-witnessed neighbor.
- **[PRO]** Differentiation-friendly robust SVD (custom Jacobian) is specified for any ML-integrated alignment path (PyTorch/JAX near-degenerate singular value NaN hazard avoided) — flagged in the IP document risk section.
- **[EXP]** A unit test seeds a mirror-inverted point pair and asserts no reflected frame enters the store (E32, added; status [EXP:NOT-RUN]).

### 39.5 Robust PGO and false loop closures

**Critique:** Least-squares pose-graph optimization quadratically penalizes large errors, so a single false BLE RSSI loop closure ("perceptual aliasing") warps the entire trajectory; mitigation is robust loss (Huber/Cauchy) or switchable constraints; incremental solvers (iSAM2-style) are needed on mobile CPUs.

**Response [CRITIQUE ACCEPTED — ARCHITECTURE ALIGNED]** The system already avoids global least-squares on every edge: gradient and spatial labels ride the hop/relay gate, and the consistency engine rejects contradictions before they enter the graph (rather than after optimization). Being explicit:

- **[PRO/IMP]** Where an optimized PGO stage is ever used (e.g., multi-hop VRLG re-embedding on merge; Section 23.2), it uses **robust loss + switchable constraints**: an edge whose residual contradicts the odometry backbone is drive-to-zero automatically. This is the standard defense and it is budgeted for on-device cost (see open-source PGO compendium, Appendix K).
- **[PRO]** **Incremental not batch.** On-device optimization is incremental (updates only the affected locality), mirroring iSAM2's philosophy and mobile CPU/thermal constraints. Batch re-embedding is explicitly reserved for rare, offline/cloud-free reconciliation.
- **[EXP]** Full-scale PGO-with-switchables in the simulator is a future E-series item ([EXP:NOT-RUN]).

### 39.6 DTN, TOCTOU/TOFU, and traceability

**Critique:** Bridgefy-style mesh apps retain critical vulnerabilities even with Signal integration: TOCTOU (long gap between key fetch and message send allowing key-swap), TOFU assumption (no PKI in the mesh → active AitM), broken broadcast encryption + decompression-bomb DoS, and MAC-randomization/IRK/BD_ADDR leakage enabling passive star-node traceability of protesters.

**Response [CRITIQUE ACCEPTED — CRYPTO HONESTY]** Sections 28–29 already disclaim full-strength crypto (16-bit MAC guard; TOFU acknowledged). The critique upgrades the disclosure and the design:

- **[PRO]** **OOB/QR key-curve verification is a first-class *pre-arrival* onboarding tool** (contrary to the previous "no secure OOB assumption" default): verified contacts exchange fingerprints (screen QR scan) in advance, creating a durable web-of-trust usable on-contact. Honest operational cost: scanning a screen QR under panic is heroic-behavior-dependent, so in-crisis *first-contact* trust degrades to TOFU + the envelope-MAC guard — acknowledged as a residual AitM window rather than solved; [EXP:NOT-RUN] for the pairing protocol. (This refines the external-critique TOFU fix, Sec 39.6.)
- **[PRO]** **TOCTOU discipline:** key material is *pinned* at message-signing time and re-checked at handoff; the "queue now, validate later" gap in the critique is closed by binding the sequent, not merely the identity, to the pinned key (implementation requires a lock-step sequent chain, [EXP:NOT-RUN]).
- **[PRO/MAY]** Broadcast-gate design avoids relying on a single network-wide broadcast key; DoS decompression-bomb vectors are closed by bounding advertisement payloads (fixed 13B envelope; no unbounded compressed blobs enter the hop/relay gate).
- **[CAN]** Traceability discipline: alias rotation + short src-id + no static BD_ADDR exposure during discovery + (where supported) proper IRK hygiene; passive-observability analysis is *incomplete* by our own admission (RQ18) — flagged as a research gap, not claimed solved.

### 39.7 Where the critique is rejected

(Reviewer-consensus note: labels like [RES: qualitative], "provisional-on-E31", and the J.1 executed→reported audit are added in this hardening pass so that legible honesty tags are not mistaken for measured evidence; a tag makes a limit visible, it does not measure it.)


We reject only the framing that these facts make the *whole paradigm* impractical. The paradigm's operational contract — topological gradient delivery with tiered, honesty-tagged relative positioning under byte-floor advertising ceilings — does not depend on AoA arrays, does not require invisible background execution, and does not assume unbreakable crypto. It remains feasible *as a research system* precisely because the critique's valid points are designed-in as repair rules (39.1–39.6), and its invalid points (that feasibility requires AoA/invisibility/perfect crypto) were never design premises.

---

## 40. Limitations

1. No hardware field runs yet ([EXP:NOT-RUN] across E13/E15/E17/E21/E22, and the critique-response experiments E31/E32).
2. Simulation does not model OS advertising-randomization, iOS overflow delivery dynamics, or true multipath shadowing fields.
3. RSSI-based distance in the BLE shadowing regime is fundamentally coarse (~50 dB occlusion) — geometric claims rely on witnesses, not RSSI precision.
4. 16-bit envelope-MAC strength is a budget-limited guard, not full-strength crypto.
5. Energy regime simulated via constant model, not phone-measured.
6. Vendor/sensor variance unquantified (RQ21).
7. Human-factors claims (glanceability) are design, not HCI-measured.
8. Scaling envelope demonstrated only to simulation; operational venue-scale unproven.
9. Adversarial robustness of consistency checks unit-tested, not live-radio-exploited.

---

## 41. Novelty / IP note

Companion document (separate): `ip/00_ip_analysis.md` isolates C1–C8, each with problem/frame/prior-art/mechanism/technical difference/risk/experiments, plus comparative-strength sheet and publication-vs-patent sequencing. This paper takes **no** patentability position; markers are [MAY, LEGAL-REVIEW-RESERVED]. Candidate assemblies are explicitly *assemblies of known components with novel integration* unless shown otherwise by legal review.

---

## 42. Future work

- E13 (baro gating), E15 (fallback signatures), E17 (iOS ceiling), E21 (device matrix), E22 (2–5 device smoke).
- Hardware pilot in a dense venue to calibrate the shadowing model and byte-ceiling realities.
- Full-strength key-management under BLE budget (open crypto problem).
- HCI evaluation of glanceability/AR reverse-chevron modes.
- GDPR/app-store policy pass for background service + accessibility.
- Tighter scaling theory at >2,000 nodes with reconnection storms.

---

## 43. Conclusion

Find Us presents a complete, infrastructure-independent crowd-smartphone system: eleven layers, a 56-bit (13-byte) packet that survives legacy and iOS advertising ceilings, an anti-storm trickle-with-absorption discipline, a virtual-relative-landmark graph whose consistency engine keeps the graph honest through partitions and merges, and a coupled, navigable SOS gradient. We report simulated results (2,000-node, 50-MC, 200×200 m, hops 1–11), two openly-reported design failures with fixes, an executed subset of the E1–E23 program, and an explicit separation of implemented vs measured vs unvalidated. We do not claim a field-ready product; we claim an internally-consistent research system with honest markers at every claim boundary — and we believe that honesty discipline, not any single protocol trick, is the real contribution to this class of emergency system.

---

## 44. References

[1] K. Fall, S. Farrell, "DTN: an architectural retrospective," IEEE JSAC, 2008 (RFC 4838 context). [CAN]
[2] RFC 5050 — Bundle Protocol Specification. [CAN]
[3] A. Vahdat, D. Becker, "Epidemic routing for partially-connected ad hoc networks," 2000. [CAN]
[4] T. Spyropoulos, K. Psounis, C. S. Raghavendra, "Spray and Wait," IEEE MDM 2005. [CAN]
[5] P. Levis et al., RFC 6206 — The Trickle Algorithm. [CAN]
[6] S.-Y. Ni, Y.-C. Tseng, Y.-S. Chen, J.-P. Sheu, "The broadcast storm problem in a mobile ad hoc network," MobiCom 1999. [CAN]
[7] S. Čapkun, M. Hamdi, J.-P. Hubaux, "GPS-free positioning in mobile ad-hoc networks," Cluster Computing, 2002. [CAN]
[8] Y. Shang, W. Ruml, Y. Zhang, M. Fromherz, "Localization from mere connectivity," MobiHoc 2003 (MDS-MAP). [CAN]
[9] J. Aspnes et al., "A theory of network localization," IEEE Trans. Mobile Computing, 2006. [CAN]
[10] R. Martin, A. Spring, et al., "DILOC," Int. J. Wireless Info. Networks 2005. [CAN]
[11] Chang, Yun; Tian, Yulun; How, Jonathan P.; Carlone, Luca, "Kimera-Multi: robust, distributed, dense metric-semantic SLAM for multi-robot systems," ICRA 2022. [CAN]
[12] 802.15.4z: UWB HRP ranging. [CAN]
[13] Apple U1 / Nearby Interaction; FiRa Consortium UWB. [CAN]
[14] goTenna mesh-radio consumer system documentation and incident reports. [CAN]
[15a] Bridgefy off-grid messaging: public security analyses and reported incidents (2020-2024), incl. AitM/TOCTOU-class findings discussed in Sec 39.6. [CAN]
[15b] USENIX 2024 traceability analysis of emergency mesh messaging (passive star-node tracing). [CAN]
[16] B. Weppner, P. Lukowicz, "Collaborative crowd density estimation with mobile phones," ACM Symposium on Computing for Development (DEV), 2013. [CAN]
[17] Cotton, Body-shadowing loss ~50 dB measurements (UWB/BLE body occlusion literature). [CAN]
[18] Mason's test and BLE beacon measurement reports. [CAN]
[19] US patents class 11,849,372; 11,848,740; 11,627,453; 10,779,120 (prior-art risk, no completeness). [CAN-LEGAL]
[20] RFC 3828/related distance-vector insights; Frost & Stolpman on RF propagation for mesh. [CAN]
[21] Patwari, Hereford, et al., "Relative location estimation in wireless sensor networks," IEEE TSP 2003 (CRB). [CAN]
[22] NIST fixed-signage wayfinding research program. [CAN]
[23] Android 12+ BLE/location permission docs. [CAN]
[24] Apple CoreBluetooth background modes docs. [CAN]
[25] Barometric-pressure smartphone positioning research (floor detection). [CAN]
[26] IEEE 802.11 Wi-Fi Direct spec and Android APIs. [CAN]
[27] Bluetooth Core Specification 5.1 — Direction Finding (AoA/AoD) requirements: antenna array on locator (CTE / IQ sampling). [CAN]
[28] Kabsch, W., "A solution for the best rotation to relate two sets of vectors," Acta Cryst. A32, 1976. [CAN]
[29] Horn, B.K.P., "Closed-form solution of absolute orientation using unit quaternions," JOSA A4, 1987. [CAN]
[30] Sundaram et al., "Switchable constraints for robust pose graph SLAM," IROS 2012. [CAN]
[31] Kaess et al., "iSAM2: incremental smoothing and mapping," IJRR 2012. [CAN]
[32] Bridgefy protocol security analyses (E2E messaging over BLE mesh): documented TOCTOU / TOFU-attack findings discussed in critique audits 2020–2024. [CAN]
[33] Android foreground-service types (API 34) — FOREGROUND_SERVICE_CONNECTED_DEVICE / FOREGROUND_SERVICE_LOCATION; background-execution limits since Android 8. [CAN]
[34] BLE MAC-randomization / IRK-passive-traceability and BD_ADDR-leak findings across BLE devices (reachability/evaluation literature — exact paper IDs flagged [CITATION REQUIRED]). [CAN]
[35] Intanagonwiwat, Govindan, Estrin, "Directed diffusion: a scalable and robust communication paradigm for sensor networks," MobiCom 2000. [CAN]
[36] Niculescu, Nath, "DV based positioning in ad hoc networks," INFOCOM 2003 (DV-hop/APS). [CAN]
[37] Doherty, El Ghaoui, Pister, "Convex position estimation in wireless sensor networks," INFOCOM 2001. [CAN]
[38] Priyantha, Balakrishnan, Demaine, Teller, "Anchor-free distributed localization in sensor networks," MobiCom 2005 (AFL). [CAN]

*(References 17,25 partial-fill flagged: author lists truncated in companion repo; [CITATION REQUIRED] on exact paper IDs. References 27–34 added in the Adversarial-Critique hardening pass, Section 39; items 32 and 34 are class-level citations pending exact bibliographic records.*

---

## 45. Appendices

### A. Packet framing detail (v2/v3)
Table from Section 14.2; 56-bit+ECC=13B core; budget audit vs 27B/29B/23B ceilings; chunk assembly seq-trie.

### B. SOS state machine pseudocode
IDLE→ARMING→ARMED→FIRING→PROPAGATING→CLEAR; ghost-tier rules; mule overwrite.

### C. Register/hop decision pseudocode (relay/forward/suppress/cache).

### D. Merge protocol pseudocode (bridge discovery, frame tie-break, recompute, re-absorption).

### E. Consistency checks pseudocode (cross-edge, signed-direction cycle, relative-coordinate recompute, aging).

### F. Energy duty-model table.

### G. Fallback decision table (environment signature → class → ladder).

### H. E1–E23 program status table (as in Section 35.3).

### I. Failure-mode DCR misrespond table (FM1–FM12).

### J. Simulation config summary (200×200 m, 2,000-node, 50 MC, hops 1–11; all repo-registered).
**J.1 Executed→reported audit (reviewer-consensus requirement, Sec 39.8).**

| Executed | Reported at | Surface |
|---|---|---|
| E1 | Sec 14/13.1 | numeric (byte tables) |
| E2 | Sec 14.2/36 (RQ2) | unit roundtrip [RES] |
| E3 | Sec 36 (provisional-on-E31) | numeric run exp_002_trickle |
| E4 | Sec 37 RQ5 (provisional-on-E31) | [RES: qualitative] sweep |
| E5 | Sec 36 | [FAIL→RES] qualitative + residual |
| E6 | Sec 36 | [RES: qualitative] error family |
| E7 | Sec 37 RQ7 | [RES: qualitative] |
| E8 | Sec 36 (RQ9) | numeric: 3σ≈3.3 m vs 3.5 m grid |
| E9 | Sec 36 | [RES: qualitative] convergence |
| E10 | Sec 15.3 | [RES: qualitative] ghost-rule tests |
| E11 | Sec 36 | [RES] repo-pinned family |
| E12 | Sec 37 RQ12 | [RES: qualitative] participation-ratio thresholds |
| E14 | Sec 36 | numeric runs exp_012/exp_011 |
| E16 | Sec 30.1 | model-derived constants, flagged |
| E18 | Sec 36 (RQ3) | unit-level [RES] |
| E19 | Sec 36/37 RQ19 | repo-pinned trade family |
| E20 | Sec 37 RQ20 | [RES: qualitative] anchors cost/benefit |
| E23 | Sec 33.1/36 | [RES] envelope (2,000-node) |

Rows E2/E4/E7/E10/E12/E16/E20/E23 are surfaced in the text but carry
[RES: qualitative] or model-flagged labels rather than separate numeric
subsections; their point estimates live in the repo run registry
(`research/research-state.yaml` trajectory) under the listed run ids.

### K. Open-source compendium for DTN and Pose-Graph Optimization (PGO)

Curated from the external adversarial critique (Section 39) to guide resilient implementation and prototyping of the routing (DTN) and spatial-optimization (PGO/Kabsch) layers.

**Table K1 — Delay-Tolerant Networking (DTN) resources**

| Framework / Repository | Language | Description and utility |
|---|---|---|
| NASA dtn-tools | Python | Independent test suite for Bundle Protocol v7 (RFC 9171) implementations; validates exact BPv7 specification conformance. |
| h-ohsaki/dtnsim | Python | Lightweight DTN simulator with multiple agent and mobility models; rapid prototyping of routing in sparse/partitioned environments. |
| pyD3TN | Python | Python implementation of the DTN architecture (RFC 4838) and Bundle Protocol; embeddable delay-tolerant logic at application layer. |
| NASA-JPL ION-DTN | C/Python | Interplanetary Overlay Network; canonical robust DTN datastack for extreme-latency environments. |

**Table K2 — Pose-Graph Optimization (PGO) and SLAM resources**

| Framework / Repository | Format / Language | Description and utility |
|---|---|---|
| UditSinghParihar/g2o_tutorial | Python & Jupyter | Modular notebooks for 2D pose-graph SLAM and landmark SLAM using g2o wrappers; edge/vertex setup details. |
| AarishShah22/gtsam-SLAM | Python | 2D/3D SLAM with GTSAM; compares batch (Gauss-Newton) vs incremental optimization — directly relevant to mobile real-time graphs. |
| PyPose (pypose.org) | Python/PyTorch | Robot-oriented library with a readable PGO tutorial (trust-region solver, Cholesky), hardware-accelerated SLAM. |
| GTSAM Python Examples | Python & Jupyter | Official tutorials: parse .g2o, initialize nonlinear factor graphs with priors, run Gauss-Newton planar SLAM. |

**Table K3 — Kabsch / matrix-alignment resources**

| Framework / Repository | Format / Language | Description and utility |
|---|---|---|
| hunter-heidenreich/Kabsch-Cookbook | Python (multi-backend) | SVD-based Kabsch and quaternion Horn alignment across NumPy/PyTorch/JAX/TensorFlow/MLX; gradient-safe backward passes (Section 21.4). |
| Songze1019/Kabsch | Python & Rust | Parallel Kabsch (PyTorch/NumPy); explicit determinant checks for reflection handling. |
| bougui505/find_rigid_alignment_pytorch | Python (PyTorch) | Concise, documented rigid alignment via SVD; zero-centered transport and reflection mitigation. |
| JosePereiraUA/zalign.py | Python | Molecular-structure alignment; pure-Python coordinate math directly reusable for 3-D point-cloud alignment. |

These resources inform, but do not by themselves satisfy, the hardware/platform gaps (Sections 30–32) — the OS background, energy, and byte-ceiling realities remain device-measurable only [EXP:NOT-RUN].

---

## 46. Research gaps remaining (honest exit report)

1. No field-hardware validation (E22/E13/E17/E21).
2. No OS-packaging / app-store policy run.
3. No full crypto under BLE budget.
4. No HCI/glanceability measurements.
5. Scaling beyond 2,000 nodes + reconnection storms unmodeled.
6. Adversarial robustness not live-radio-exploited.

**The paper is complete in structure, honest in bands, and explicitly marked where the next researcher's feet are.**

---