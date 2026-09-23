# Research Findings: Find Us (Crowd Compass)

## Research Question
Can an ad-hoc smartphone mesh provide actionable emergency navigation using only a distributed hop-distance gradient and local biological shadowing, without global coordinates, anchor nodes, or metric vector chains?

---

## Current Understanding

The fundamental insight of this research is that **metric coordinates are an unnecessary and actively harmful abstraction for offline emergency navigation**. 

When 50,000 people gather in a concrete stadium:
1. **The Origin Dilemma is Solved by the Crisis:** We do not need a pre-existing anchor or a shared `(0,0)` grid. The emergency emitter dynamically instantiates itself as **Hop 0**. All spatial relationships radiate outward as discrete topological contours ($H \in \mathbb{N}_0$).
2. **Topological Monotonicity:** A responder does not need an azimuth vector from $200\text{ meters}$ away. They only need to decrease their observed hop count ($N \to N-1$). In our simulations across 2,000-node dense graphs, greedy gradient descent achieved a **100.0% arrival rate**, whereas vector chaining accumulated $>10.9\text{ meters}$ of error, creating an unsearchable crowd perimeter.
3. **Decoupling Hop Count from RSSI:** RSSI varies by $>25\text{ dB}$ simply from people turning around or body blockage. Using RSSI as the routing gradient leads responders into false local minima. **Hop count is the sole routing gradient; RSSI is strictly an ephemeral local proximity hint.**
4. **The Three-Tier Localization Pipeline:**
   * **Macro Layer ($500\text{m} \to 15\text{m}$):** Discrete Hop Gradient Descent + Barometric Floor Offset ($\Delta P$).
   * **Local Directional Layer ($15\text{m} \to 5\text{m}$):** Synthetic Lighthouse via Biological Torso Shadowing ($15\text{--}20\text{ dB}$ body attenuation yields a $13^\circ\text{--}18^\circ$ bearing cone).
   * **Terminal Layer (Final $5\text{m}$):** Optical Visual Runway (Hop 1 bystander screen/torch strobing with ALS pocket-veto gating).

---

## Key Results

### 1. Vector-Chain Compounding vs. Topological Monotonicity (Experiment H1)
* **Topological Monotonicity:** Achieved **100.0% descent success** from Hop 1 through Hop 11 across 50 Monte Carlo trials in a $200\text{m} \times 200\text{m}$ venue.
* **Vector-Chain Error:** Grew continuously: $2.58\text{m}$ at Hop 1, $5.87\text{m}$ at Hop 4, and $10.92\text{m}$ at Hop 11. At Hop 1, the angular error ratio was $51.2\%$.

### 2. Spectrum Collapse vs. Inhibitory Relay (Experiment H2)
* **Naive Flooding Collapse:** In a 5,000-node stadium, naive uncoordinated rebroadcast produced $15,000\text{ pkts/sec}$ with a **$97.7\%$ packet collision rate**, completely muting the emergency.
* **Inhibitory Suppression:** The Trickle-based inhibitory protocol ($k=3$, jitter $50\text{--}250\text{ms}$) eliminated **$90.0\%\text{ to } 91.0\%$ of all redundant transmissions**, cutting packet rate down to $1,494\text{ pkts/sec}$.

### 3. Biological Torso Shadowing (Experiment H3)
* **Single-Antenna Directionality:** Holding the phone against the sternum and rotating $360^\circ$ achieved a mean angular bearing error of **$13.2^\circ\text{ to } 18.1^\circ$**, with **$83.5\%\text{ to } 96.5\%$ of estimates within a $\pm 30^\circ$ walking cone**.
* **Gain Over Baseline:** Delivered a **$4.64\times\text{ to } 7.04\times$ improvement** over an unshielded omnidirectional smartphone (which had $83^\circ\text{--}93^\circ$ error, pure random chance).

### 4. Obstacle Shadows & RF Bleed Override (Experiment H4)
* **The Detour Penalty:** In non-convex spaces with stage barriers, naive hop descent incurs a mean detour of **$122.58\text{ meters}$** to reach a target physically only **$13.34\text{ meters}$ away** ($10.09\times$ detour multiplier).
* **RF Bleed Override:** Faint direct RF bleed packets (< -90 dBm) trigger a "WALL BARRIER DETECTED" alert on responder phones, prompting physical barrier inspection before a 100-meter walk around the concourse.

### 5. Adaptive Jitter Scaling for Mass Flash Mobs (Experiment H5)
* **Scalability to 10,000 Nodes:** Dynamically scaling the Trickle jitter window ($T_{\max} \propto \log_2 N \approx 1,240\text{ms}$) increases packet delivery from $32.8\%$ to **$96.2\%$ at 1,000 nodes** (+63.4% gain) and from $12.3\%$ to **$74.8\%$ at 2,500 nodes** (+62.5% gain). Coupling this with density-dependent relay probability $p_{\text{relay}} \propto 1/N$ preserves channel health up to 10,000 devices.

### 6. Data Mule Partition Healing & Ghost Gradient Characterization (Experiment H9)
* **Threshold Density:** Delay-Tolerant Networking (DTN) store-and-forward muling across a $200\text{m}$ dead zone achieves $\ge 90\%$ discovery delivery within a 5-minute search window at **$\ge 2.0\text{ mules/min}$ ($94.0\%$ success, median latency $180.0\text{ s}$)**, reaching $100.0\%$ at $\ge 4.0\text{ mules/min}$.
* **The Ghost Gradient Discovery:** Raw unmitigated cache-bursting triggers an epidemic of false Hop-1 alerts ($378.7$ alerts at $0.5\text{ mules/min}$ to $10,997.4$ alerts at $16\text{ mules/min}$), corrupting up to $66.1\%$ of nodes in the destination island. Resolving this requires the `MULE_STORE_FORWARD` control flag and Epoch delta gating ($\Delta \text{Epoch} \ge 2$) to demote delayed transmissions from active live gradients to temporal traces.

### 7. BLE Advertising Transport Revalidation & Asynchronous Model (B-01)
* **The iOS Background Filter Reality:** Revalidated Apple Core Bluetooth constraints. Background scanning `scanForPeripherals(withServices:)` strictly requires explicit Service UUID filtering; wildcard scanning is unsupported and Type-0xFF (Manufacturer Data) only advertisements are discarded by baseband without waking the app.
* **The Dual-AD Structural Fix:** Injected a 4-byte 16-bit Service UUID AD structure (`AD Type 0x03`, UUID `0xFC00`), establishing the **23-Byte iOS Background-Safe Wire Ceiling** ($31 - 4 - 4 = 23\text{ B}$).
* **Empirical Wake & Discovery Bounds:** Locked iOS devices exhibit effective discovery rates of **$0.033\text{ to } 0.125\text{ Hz}$** ($8\text{--}30\text{ s}$ per discovery) due to ~10% duty cycle and duplicate coalescing (`AllowDuplicates` ignored). Android PendingIntent wake latency ranges from $50\text{ ms to } 3\text{ s}$ in moving crowds (Significant Motion Detection aborts Doze), but can reach $9\text{--}30\text{ min}$ in stationary deep Doze.
* **Wire Budget & FEC Validation (`data/byte_budget_model.json`):**
  * Doc 06 32-bit baseline: 4B raw $\to$ 7B under Hamming(7,4) (slack: +16B iOS mode) $\to$ 12B under shortened RS(16,8) (slack: +11B iOS mode) $\to$ 16B under full-block RS(16,8) (slack: +7B iOS mode).
  * Doc 06 + 8b Age + 16b Envelope MAC (7B raw): Fits in a single RS block ($7 + 8 = 15\text{ B}$), retaining **+8B slack in 23B iOS mode**.
  * Doc 06 + 8b Age + 32b Envelope MAC (9B raw): Exceeds 8-byte RS block boundary ($9 > 8$), forcing 2 blocks ($25\text{ B}$ shortened, $32\text{ B}$ full block) which **overflows iOS safe capacity (-2B)**. Confirms 16-bit MAC protocol mandate.
* **Paradigm Shift:** Overturned Doc 06's 150ms synchronous flooding assumption. Find Us is formalized as an **Asynchronous Push/Lazy Mesh** with $10\text{--}30\text{ s}$ per background hop and rotating Resolvable Private Addresses (RPA) to bypass iOS duplicate coalescing.

### 8. Async Trickle Phase Transition & ESBW Rescue (B-03)
* **The Synchronous Myth:** Idealized synchronous H2 replication gave $99.97\%$ coverage, $99.98\%$ responder delivery, $p_{95} = 1.83\text{ s}$.
* **The Unmitigated Async Reality:** With realistic $10\text{--}30\text{ s}$ background wakes, unmitigated async trickle collapses to **$1.51\%$ coverage, $0.22\%$ responder delivery** — the gradient dies at Hop 1. Naive async BLE is NOT a usable mesh.
* **Percolation Cliff:** Background-locked sweep ($0/30/50/70/90\%$) shows a catastrophic phase transition between $30\%$ and $50\%$ locked nodes; above 50% the alive subgraph falls below the 2D percolation threshold ($\lambda_c \approx 4.512$) and delivery → 0.
* **ESBW Mitigation (verified):** Epoch-Synchronized Burst Windows (15.0 s epochs, 10 s burst window, ~47 packets/window) + Gossip Re-Warming + Inhibitory $k{=}3$ gating restore coverage to **$99.86\%$**, responder delivery to **$99.98\%$** even at 70% background-locked; $p_{50}=287\text{ s}$, $p_{95}=442\text{ s}$. Suppression rate 34.74% (no spectrum collapse).

### 9. Anti-Spoofing Envelope MAC: 16-bit Mandate (B-04)
* **Black-Hole Attack Lethality:** With no MAC, a mere **0.5% of rogues mislead 88–100% of responders**; 8-bit truncation still misleads **11%** at 5% rogue (memoryless) and accepts **31.6–32.4%** of forgeries over a 100-message epoch budget.
* **The 16-bit Line:** 12-bit fails (2.4% @100 msgs); **16-bit achieves 0.15–0.18%** — the only width with >5× margin under the <1% hard target.
* **Packet v2 Amendment (via Doc 22):** `ENVELOPE_MAC` **8 → 16 bits**; payload 48→56 b (6→7 B native, 13 B Hamming-coded); still **10 B under** the 23 B iOS mode-C ceiling. No architecture breakage.

### 10. Multipath Wall Alerts & RF Confirmation Layer (B-05)
* **The Single-Sniff Dilemma:** Overhearing a $-85\text{ dBm}$ packet from Hop 0 cannot distinguish a direct line-of-sight window gap (Position A) from a specular multipath reflection off a distant stadium metal bleacher or roof truss (Position C). Naive single-packet heuristics trigger false shortcuts ($78.9\%$) or false wall alerts ($100.0\%$).
* **Multi-Carrier Fading & Coherence Discriminants:** In a multi-carrier BLE system (channels 37, 38, 39), distant metal multipath exhibits severe frequency-selective variance ($s_R = 5.55\text{ dB}$) and discordant bearing coherence ($\rho = -0.934$), whereas true concrete wall bleed is faint ($-92.88\text{ dBm}$), low-variance ($s_R = 2.86\text{ dB}$), and orthogonal ($\rho \approx 0.009$).
* **The 2.0s Multi-Second Rule:** A 2.0-second observation window ($M \ge 4$ packets) achieves **$94.73\%$ multi-class accuracy**, **$100.0\%$ multipath bounce rejection** ($0.00\%$ false alarms), and **$84.20\%$ Wall Alert sensitivity (TPR)** with **$0.00\%$ False Positive Rate (FPR)**. (Doc 23.)

### 11. End-of-Event Probe Storm: Backoff + Suppression Mandatory (B-06)
* **Naive cold-start collapse:** 1,250 simultaneous groups probing at rescue time → 98.6% burst collision, **only 77.8% discovery in 5 min** (22% of groups go undiscovered).
* **5 s passive listen alone fails** (79.3%; lockstep persists). **CSMA/CA urgency backoff → 100% @5 min**, 94.5% @60 s.
* **Chosen protocol:** backoff + **passive discovery suppression (k=1)** → **100% discovery in 60 s, 90.9% in 30 s**, overall collision 12.4%, **87.3% fewer collisions than the H2 baseline**, ~5× fewer probe packets. (Doc 24.)

### 12. Activity-Recognition Gated PDR & Kinematic Chaos Suppression (B-07)
* **The Kinematic Divergence Trap:** In dense festival crowds, unmitigated Pedestrian Dead Reckoning (PDR) registers violent jumping, bass bouncing ($>1.5\text{--}3.5\text{ g}$ shocks, $6.4\text{ Hz}$), and pocket swaying as forward footsteps. In a 120s festival mission, ungated PDR emits **$25.0$ false displacement vectors** per mission, accumulating **$32.94\text{ m}$ mean / $75.13\text{ m}$ peak drift error** and destroying searcher navigation lock in **$34.0\%$ of missions** ($66.0\%$ arrival rate, confirming H7).
* **The 5-Stage AR Gating Filter:** A deterministic $2.0\text{ s}$ window ($100$ samples @ $50\text{ Hz}$) pipeline verifies: (1) Navigating posture (pitch $20^\circ\text{--}65^\circ$, roll $\le 28^\circ$); (2) Dynamic accel variance band ($0.35\text{--}4.20\text{ m}^2/\text{s}^4$); (3) Harmonic cadence band ($1.10\text{--}2.40\text{ Hz}$, autocorrelation $\rho_{xx} \ge 0.42$); (4) Gyro rotational stability ($\sigma_\omega \le 0.80\text{ rad/s}$); (5) Magnetometer field stability ($\sigma_m \le 12.5\text{ }\mu\text{T}$). If any gate fails, displacement is strictly clamped to `0x0000`.
* **Empirical Verification (`data/ar_gated_pdr.json`):**
  * **$100.0\%$ False Vector Suppression:** Eliminates all $25.0$ false vectors ($0.00\text{ m}$ emitted during mosh/pocket/spin/idle states; $0.00\%$ FPR across 4,000 non-walking windows).
  * **$14.5\times$ Heading Accuracy:** Emitted heading error drops from $45.50^\circ$ to **$3.14^\circ$**.
  * **$9.86\times$ Target Drift Reduction:** Cumulative drift collapses from $32.94\text{ m}$ to **$3.34\text{ m}$**.
  * **$100.0\%$ Navigation Lock:** Restores searcher arrival rate to **$100.0\%$** via AR Gated Fusion.
  * **Ablation Proof:** Demonstrates that posture gating is uniquely required to kill pocket drift ($88.8^\circ$ misalignment), while accel variance and cadence kill mosh pit bouncing. (Doc 25.)

### 13. Terminal Handoff & Ambiguity Resolution Protocol (B-08)
* **The Near-Field Waterbag Breakdown:** In the final 15m terminal zone, human obstacles within $1.2\text{ m}$ cast $16\text{ dB}$ near-field knife-edge shadows that distort single-antenna torso cardioid patterns (Doc 14 Issue #2). Under direct line-of-sight blockage ($|\Delta \theta_B| \le 25^\circ$, $N=747$), pure torso scanning degrades to **$21.92^\circ$ mean / $59.22^\circ$ $p_{90}$ error**, with **$5.49\%$ catastrophic reflection flips** ($>90^\circ$) and arrival within $5\text{ m}$ falling to **$79.92\%$**.
* **Failure of Pure Gradient Walk:** A pure Hot/Cold 3-step walk ($2.1\text{ m}$) without a directional prior provides only a 1D hemisphere sign check with zero lateral steering ($\text{SNR} = -19.2\text{ dB}$ on lateral probe), yielding an unacceptably wide **$60.18^\circ$ mean error** and only **$33.78\%$ terminal arrival success**.
* **Combined Handoff Protocol Resolution (`data/terminal_handoff.json`, 5,000 trials):**
  * **Hypothesis + Verification + Clearance:** Uses torso scan for coarse prior $\hat{\theta}_{\text{cand}}$, tests via 3-step walk slope $\hat{g} = \frac{d\text{RSSI}}{dr}$, and flips $180^\circ$ if $\hat{g} < -0.4\text{ dB/m}$ and $\Delta \text{RSSI} < -1.0\text{ dB}$. Crucially, advancing $2.1\text{ m}$ physically steps past the $1.2\text{ m}$ bystander obstacle, clearing the near-field shadow ($A_B \to 0\text{ dB}$) and allowing an unblocked micro-check that clamps residual angular bias strictly $< 30^\circ$.
  * **Direct Blockage Regime ($N=747$):** Mean error collapses from $21.92^\circ$ down to **$13.67^\circ$** ($1.60\times$ improvement), $p_{90}$ error halved to **$30.01^\circ$**, flips cut to **$2.54\%$**, and terminal arrival ($\le 5\text{ m}$) restored to **$88.35\%$** (median miss distance $0.95\text{ m}$).
### 14. Ghost Gradient Resolution & Multi-Layer Partition Healing (B-09)
* **The Ghost Gradient Catastrophe (Doc 17 & Exp H9):** When pedestrian data mules carry cached `Hop 0` packets across a $200\text{ m}$ dead zone between crowd islands (Main Stage vs Food Trucks), naive store-and-forward bursting creates **$331.7\text{ to } 11,207.5$ false Hop-1 alerts per 5-minute session**, corrupting up to **$61.4\%$ of stationary nodes** ($184.3 / 300$). Searchers are actively misled into chasing moving bystander mules ($46.0\%\text{--}100.0\%$ misled rate) in the opposite direction of the true target.
* **Candidate Critique & Architectural Proofs:**
  * **`PKT_TYPE = CACHED_MULE_BURST` (0x1) Is Cryptographically Impossible:** `PKT_TYPE` is locked inside the 16-bit `ENVELOPE_MAC` (`Origin Invariants = SOS_ID || EPOCH || PKT_TYPE`). Because bystander stranger mules operate under Zero-Decrypt Forwarding (ZDF) without $K_{\text{session}}$, modifying `PKT_TYPE` breaks the MAC and causes immediate rejection as an adversarial forgery.
  * **`BARO_DIFF` Is Orthogonal:** Horizontal 200m transit across a venue floor has $\Delta z = 0$, rendering barometric differentials completely blind to horizontal partition traversal.
  * **`AGE` Bucket (2 bits) & `MULE_STORE_FORWARD` Flag Are ZDF-Mutable:** Honest mules set `AGE = 1, 2, or 3` and clamp `HOP >= 6`. However, under an open crowd with 15% legacy or non-compliant mules, wire-only gating collapses: leaking up to **$1,798.9$ false alerts** and misleading **$98.0\%$ of searchers**.
  * **`EPOCH` Cadence Delta Gating Is Ground Truth:** `EPOCH` is covered by the 16-bit MAC. Walking $200\text{ m}$ at $1.4\text{ m/s}$ takes $142.9\text{ s}$ ($\approx 9.5$ ticks of the $15\text{ s}$ epoch counter). Any packet exhibiting $\Delta \text{Epoch} \ge 2$ ($>30\text{ s}$) is provably a delayed store-and-forward transit echo.
* **Definitive Multi-Layer Decision Rule (`data/ghost_gradient.json`, 1,200 partitioned runs + 500 control runs):**
  * **Total Ghost Alert Eradication:** Slashes false alerts from **$11,207.5 \to \mathbf{0.0}$** and collapses searcher misled rate from **$100.0\% \to \mathbf{0.0\%}$** across all flow densities, even under 15% non-compliant mules.
  * **$100\%$ Partition Healing Delivery:** Corrected rate reaches **$94.0\%$ at $2.0\text{ mules/min}$** and **$100.0\%$ at $\ge 4.0\text{ mules/min}$**.
  * **Accurate ETUI Ingress Arc Synthesis:** Centroid of perimeter receptions yields a navigation corridor bearing toward the origin island with mean angular error of **$10.33^\circ\text{--}23.68^\circ$** (strictly $< 24^\circ$ pointing due West toward Island A).
  * **$0.00\%$ False Negative Rate on Live Targets:** **Co-located Control Benchmark (500 trials at 5.0m):** Measured **$0.00\%$ False Negative Rate** ($100.0\%$ live target detection in $0.01\text{ s}$). Genuine proximate victims are never misclassified. (Doc 27.)

### 15. Multi-Level Barometric Navigation, Stairwell Geometry & Cross-OS Calibration (B-10)
* **The RF Ceiling Shadow Trap:** At 2.4 GHz, reinforced concrete floor slabs (22 dB loss) and elevator shaft waveguides (6 dB loss) do NOT block BLE within a 93 dB link budget (excess link margin +15.8 dB). Under naive 2D hop descent, **100.0% of searchers on lower decks are trapped** under the ceiling projection directly beneath the victim (5.10m mean miss distance), achieving **0.0% arrival success**.
* **Mesh-Level Gating Fallacy:** Dropping cross-floor packets at relays severs the mesh, plunging adjacent decks into a **0.0% alert coverage blackout**. Packets must flood unrestricted venue-wide (100.0% alert coverage).
* **Floor-Aware Receiver Gating & Stairwell Navigation:** Checking `BARO_DIFF` at the receiver eliminates the ceiling trap: detecting $|\Delta P| > 0.35\text{ hPa}$ suppresses in-plane descent and guides searchers to the stairwell portal. Upon reaching the target deck ($|\Delta P| \le 0.25\text{ hPa}$), in-plane descent unlocks, achieving **0.0% entrapment, 100.0% stairwell portal convergence, and 100.0% arrival success (0.00m residual miss)**. (Doc 28.)
* **Cross-OS Calibration:** Uncalibrated cross-OS biases ($\ge 1.0\text{ hPa}$) cause **0.0% exact and within $\pm 1$ floor accuracy** (MAFE 2.4 to 6.0 floors). The Entrance-Gate Baseline Snapshot protocol (1-second turnstile snapshot against reference $P_0$) restores accuracy to **75.6% exact (100.0% at 4.2m concourse tiers), 100.0% within $\pm 1$ floor, and MAFE 0.244 floors**. Peer consensus among $K=8$ co-located peers provides a zero-infrastructure fallback with **60.2% exact and 99.2% within $\pm 1$ floor accuracy**.

### 16. Implementation Blueprint v1 & Codified Reference Specification (B-11)
* **Vol 1: Research Complete:** All findings, verified physics, and simulation models from B-01 through B-10 are formally codified into [[29_IMPLEMENTATION_BLUEPRINT_V1]] and an exportable, concise machine-readable specification `refimpl_spec.md` (113 lines).
* **Consolidated State Machine & Guidance Engine:** Executable pseudocode locked for ZDF relays (ESBW 15s epoch, 10s burst, 211ms adv, $k=3$ suppression), storm-resistant cold-start probing (5s passive listen, $U(0,60\text{s})$ backoff, $k=1$ discovery suppression), and 3-stage responder guidance (macro downhill hop descent + baro floor gating, local torso scan + 3-step walk ambiguity clearance, terminal strobe + localized bystander audio-haptic prompt).
* **Global Failure Mode Resolution:** Consolidated all 18+ documented real-world failure modes across Docs 05, 14, 17, 18 into an exhaustive matrix with concrete fixes and empirical benchmarks.
* **Multi-Year Risk Register:** Established 6 prioritized technology risks (TR-01 through TR-06) with concrete physical hardware prototyping mandates.

---

## Patterns and Insights

1. **Topological Invariance:** Hop counts are immune to rotate-translate-scale ambiguities. Whether a venue is square, circular, or labyrinthine, shortest-path graph distance always decreases toward the source.
2. **Weaponizing Biophysics:** The human body's high permittivity and saline content at $2.4\text{ GHz}$ was historically treated as an RF nuisance. By treating the human body as an engineered cardioid shield, we gain directional antenna capability on completely commodity smartphones.
3. **Bandwidth Economy:** By abandoning vector lists and coordinate frames, the emergency payload drops to **4 bytes (32 bits)**. A 4-byte payload allows extreme forward-error correction and universal BLE Legacy Advertisement encapsulation without pairing or connections.
4. **Dual-Compartment Privacy & Altruistic Relaying (H6):** Partitioning frames into an 8-byte cleartext Public Envelope and a 19-byte ChaCha20-Poly1305 Encrypted Core fits completely within the 31-byte legacy BLE limit. Stranger relays process packets via Zero-Decrypt Forwarding (ZDF) in $0.015\text{ ms}$ ($61.8\times$ faster than decrypt-re-encrypt), drawing $<1.4\text{ mAh/day}$ bystander battery while maintaining 100% group privacy.
5. **Topological Invariance to PDR Chaos (H7):** Pedestrian Dead Reckoning (PDR) completely fails in chaotic "mosh pit" conditions (37% navigation failure due to fake steps from jumping). The Hop-Count gradient field is strictly invariant to physical sensor noise, proving that it must be the sole mechanism for macro navigation, while kinematic vector displacements must be zero-gated by an Activity Recognition (AR) confidence threshold.

---

## Lessons and Constraints

* **Lesson 1 (The Density Contention Trap):** Even with $k=3$ suppression, in crowds $>2,000$ devices, the randomized jitter window must be scaled proportionally to local density ($T_{\text{jitter\_max}} \sim \log N$) to prevent secondary collision spikes.
* **Lesson 2 (The Pocket Veto):** Background apps cannot wake screens or flashlights if the phone is inside a bag or pocket. Ambient Light Sensor (ALS) gating is mandatory.
* **Lesson 3 (Acoustic Range Is Unviable):** Ultrasonic ranging fails in concert environments due to $110\text{ dB}$ SPL crowd noise and mobile OS audio buffer scheduling jitter ($>15\text{ ms} = 5.1\text{ meters}$ ranging error). It should never be used as a core navigation layer.
* **Lesson 4 (Zero-Trust Forwarding):** Relaying nodes must never be asked to decrypt or hold keys for private groups. Decoupling routing state (hop/TTL) from content state (identity/vector) enables strangers to assist without privacy or battery compromises.
* **Lesson 5 (The Drunk Walk Rule):** Never trust raw IMU data from a user in a dense crowd. All vector displacement updates must be bounded by high-confidence AR thresholds, or the map will explode.

---

## Open Questions

1. **Multi-Story Stairwell Geometry:** **[RESOLVED in Doc 28 / Exp B-10]** Concrete floor slabs bleed RF naturally (+15.8 dB margin). Naive 2D hop descent creates a 100% ceiling trap; resolved via Floor-Aware Receiver Gating, which suppresses in-plane descent when $|\text{BARO\_DIFF}| > 0.35\text{ hPa}$ and routes responders to the stairwell portal before unlocking horizontal gradient descent.
2. **Cross-OS Barometric Calibration:** **[RESOLVED in Doc 28 / Exp B-10]** Cross-OS factory bias between Apple (Bosch BMP) and Android (ST LPS / Sensortek) reaches $\pm 2.0\text{ hPa}$ ($\Delta \beta \ge 1.0\text{ hPa}$ collapses uncalibrated floor accuracy to 0.0%). Resolved via Entrance-Gate Baseline Snapshot against turnstile $P_0$, recovering 100.0% within $\pm 1$ floor accuracy and MAFE 0.244 floors (Peer Consensus fallback achieves 99.2% within $\pm 1$ floor).

---

## Optimization Trajectory

```text
Progress Metric: System Feasibility & Emergency Localization Fidelity

1.00 |                                                   [Topological Gradient +
     |                                                    Biological Shadowing]
0.80 |                                                   
     |                                 [Inhibitory
0.60 |                                  Trickle Mesh]
     |
0.40 |
     |  [Legacy Vector Chain:
0.20 |   Compounding Variance &
     |   Spectrum Collapse]
0.00 └─────────────────────────────────────────────────────────────
        Legacy Architecture      Intermediate Mesh     Find Us Architecture
```
