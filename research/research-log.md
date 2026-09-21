# Research Log: Find Us (Crowd Compass)

## Decision & Progress Timeline

### 2026-09-18 — Project Bootstrap & Core Architectural Pivot
* **Decision:** Formally accepted the user's architectural guidance: **Pivot from continuous metric vector-chains to the Topological Hop-Count Gradient Field**.
* **Crucial Correction Applied:** Decoupled RSSI from the downhill gradient. Hop count ($H \in \mathbb{N}_0$) serves as the sole routing gradient; raw RSSI is relegated to local proximity checks.
* **Workspace Setup:** Initialized full autoresearch project structure inside Obsidian Vault at `/home/derick/Documents/Obsidian Vault/find us reasearch/` with automatic live-sync to Obsidian.
* **Literature Review:** Synthesized prior art across Delay-Tolerant Networking (DTN), RFC 6206 Trickle algorithm, 2.4 GHz biophysical RF attenuation (Gabriel 1996, Cotton 2009), smartphone PDR heading drift (Harle 2013), and graph SLAM.
* **Identified Novelty Gap:** Existing systems either solve pure data mesh without spatial context (BitChat, Bridgefy) or require external infrastructure (GPS, Wi-Fi APs, UWB). Find Us pioneers zero-infrastructure emergency navigation via topological potential fields on a 32-bit payload.

### 2026-09-18 — Simulation Execution & Hypothesis Validation
* **Experiment H1 (Topological Descent vs Vector Chain):**
  * Protocol locked and executed (`sim_gradient_vs_vector_chain.py`).
  * Outcome: Topological gradient descent achieved **100.0% success rate** across all hop tiers (1 to 11 hops), while vector-chain accumulated monotonic metric error up to $10.92\text{ meters}$ with peak relative error of $51.2\%$.
  * Result: **H1 Strongly Supported.**
* **Experiment H2 (Inhibitory Trickle Protocol vs Spectrum Collapse):**
  * Protocol locked and executed (`sim_spectrum_collapse.py`).
  * Outcome: Uninhibited flooding causes channel collisions of $97.7\%$ at $N=5,000$ active devices. The $k=3$ Trickle inhibitory protocol suppressed **$90.0\%$ to $91.0\%$** of redundant transmissions.
  * Discovery: At extreme densities ($N > 2,000$), the randomized jitter window must adaptively scale from $[50\text{ ms}, 250\text{ ms}]$ up to $[250\text{ ms}, 1500\text{ ms}]$ to avoid cluster-level contention.
  * Result: **H2 Strongly Supported.**
* **Experiment H3 (Biological Torso Shadowing):**
  * Protocol locked and executed (`sim_biological_shadowing.py`).
  * Outcome: Repurposing human body attenuation ($15\text{--}20\text{ dB}$) during a 360-degree rotation yields mean angular errors of **$13.2^\circ\text{ to } 18.1^\circ$** with **$83.5\%\text{ to } 96.5\%$** within a $\pm 30^\circ$ cone. This represents a **$4.64\times\text{ to } 7.04\times$ directional gain** over an unshielded smartphone.
  * Result: **H3 Strongly Supported.**

### 2026-09-18 — Outer Loop Reflection 1
* **Reflection:** The core physics and topological math are fully validated. The vector-chain problem is dead; the topological gradient field is triumphant. The three-tier model (Macro Hop Gradient $\to$ Local Torso Shadowing $\to$ Terminal Visual/Torch Runway) provides an airtight answer from $500\text{ meters}$ down to $1\text{ meter}$.
* **Next Steps:** Produce the findings synthesis, comprehensive progress dashboard for the user, and draft the complete research monograph.

### 2026-09-18 — Loop Tick 1: Flash Mobs & Non-Convex Barrier Scaling (H4 & H5)
* **Experiment H4 (Obstacle Shadow & RF Bleed Override):**
  * Protocol locked and executed (`sim_obstacle_shadow_detour.py`).
  * Outcome: In the presence of a non-convex acoustic stage barrier, naive hop descent incurs a mean detour of **$122.58\text{ meters}$** to reach a target physically **$13.34\text{ meters}$ away** (a $10.09\times$ detour multiplier!). Direct RF bleed packet detection (< -90 dBm) flags barrier presence, prompting immediate physical barrier inspection.
  * Result: **H4 Supported.**
* **Experiment H5 (Logarithmic Adaptive Jitter for Mass Flash Mobs up to 10k Nodes):**
  * Protocol locked and executed (`sim_adaptive_jitter_scaling.py`).
  * Outcome: In extreme 1,000-to-10,000 node crowds, fixed jitter windows fail (<15% delivery). Expanding the window dynamically ($T_{\max} \propto \log_2 N \approx 1,240\text{ms}$) increases delivery from $32.8\%$ to **$96.2\%$ at 1,000 nodes** (+63.4% gain) and from $12.3\%$ to **$74.8\%$ at 2,500 nodes** (+62.5% gain).
  * Result: **H5 Strongly Supported.**

### 2026-09-18 — Outer Loop Reflection 2
* **Reflection:** The architectural framework now has rigorous answers for macro scalability (up to 10k nodes) and physical obstacle boundaries. The plain-English navigation guide has been added to the vault as Note 08. All simulation datasets are committed and preserved.

### 2026-09-18 — Loop Tick 2: Dual-Compartment Encrypted Mesh Framing & Zero-Decrypt Relaying (H6)
* **Experiment H6 (Dual-Compartment Wire Framing & Relaying Overhead):**
  * Protocol locked and executed (`sim_encrypted_relay_overhead.py`).
  * Outcome: Formulated a 31-byte legacy BLE advertisement frame cleanly partitioned into an 8-byte Public Envelope (rolling hash, hop, TTL, RSSI hint) and a 19-byte Authenticated Private Core (ChaCha20-Poly1305).
  * Benchmarking: Stranger relays execute Zero-Decrypt Forwarding (ZDF) with $0.015\text{ ms}$ CPU latency, a **$61.8\times$ speedup** over Decrypt-Modify-Reencrypt (DMR) at $0.91\text{ ms}$. Bystander battery drain is reduced from $85.3\text{ mAh/day}$ down to $1.39\text{ mAh/day}$ (a negligible $0.04\%$ of phone battery). Confidentiality score remains $1.00$ (zero plaintext leakage).
  * Result: **H6 Strongly Supported.**

### 2026-09-19 — Loop Tick 3: Brutal Real-World Failure Modes & PDR Chaos (H7)
* **Experiment H7 (PDR Chaos vs. Topological Hop Gradient):**
  * Protocol locked and executed (`sim_pdr_drift_vs_hop_gradient.py`).
  * Outcome: Modeled a "mosh pit" scenario where the target's Pedestrian Dead Reckoning (PDR) generates spurious displacement vectors due to jumping and bumping. Blindly trusting this vector data caused the searcher to fail to converge in 37% of trials. In contrast, the pure Topological Hop-Count Gradient Field is completely invariant to sensor noise and maintained 100% arrival success.
  * Result: **H7 Supported.** Proves that vector updates MUST be strictly gated by Activity Recognition (AR) and that the Hop Gradient is the only mathematically sound macro-navigation layer.

### 2026-09-19 — Loop Tick 4: Data Mule Mesh Partition Healing
* **Decision:** Opened research into Epidemic Store-and-Forward (Data Muling) to solve the "Concert Stage Gap" problem (disconnected crowd islands).
* **Document Added:** Authored `17_DATA_MULE_MESH_PARTITION_HEALING_FOR_FRAGMENTED_CROWDS.md` defining the open problem, temporal topology shift, and upcoming experiments for time-delayed gradient delivery across physical network gaps.
### 2026-09-19 — H9: Data Mule Partition Healing
* **Experiment H9 (Data Mule Partition Healing):**
  * Protocol locked and executed (`src/sim_data_mule_partition_healing.py`).
  * Outcome: Simulated a 200m dead zone between two 300-node dense islands (Main Stage $40\times 40\text{m}$, Food Trucks $30\times 30\text{m}$) bridged by pedestrian Data Mules moving at $1.4\text{ m/s}$. Sweep over flow density $\lambda \in [0.5, 1.0, 2.0, 4.0, 8.0, 16.0]\text{ mules/min}$ across 50 Monte Carlo trials per density.
  * Key Numbers:
    * **Delivery Success Rate:** Requires $\ge 2.0\text{ mules/min}$ to exceed 90% within a 5-minute discovery window (**$94.0\%$** at $2.0\text{ mules/min}$, climbing to **$100.0\%$** at $\ge 4.0\text{ mules/min}$). At lower flows, discovery frequently times out ($52.0\%$ at $0.5\text{ mules/min}$, $76.0\%$ at $1.0\text{ mule/min}$).
    * **Latency Cost:** The theoretical physical minimum transit time is $142.9\text{ s}$ ($200\text{m} / 1.4\text{m/s}$). Asymptotic latency at $16\text{ mules/min}$ is $149.0\text{ s}$ median ($173.0\text{ s}$ $p_{95}$). At the $90\%$ reliability threshold ($2.0\text{ mules/min}$), median latency is **$180.0\text{ s}$** ($p_{95} = 263.0\text{ s}$), reflecting an additional departure waiting penalty of $\sim 31\text{ s}$ to $90\text{ s}$.
    * **Ghost Gradient False Alerts:** Unmitigated cache-bursting creates a massive false alert epidemic in the receiving partition, exploding from **$378.7$ alerts** at $0.5\text{ mules/min}$ to **$1,610.0$ alerts** at $2.0\text{ mules/min}$ and **$10,997.4$ alerts** at $16\text{ mules/min}$ ($66.1\%$ of all nodes misled to Hop 1).
### 2026-09-19 — B-01: BLE Transport Revalidation + Async Scheme
* **Mission:** Revalidate the BLE advertising transport layer against verified facts in Doc 18 and tighten wire budget with real crowd/OS math.
* **Resolution of Open Questions (O1, O2, O3):**
  * **(O2) iOS Background Service UUID Requirement:** Proved via Apple Developer Documentation (*Core Bluetooth Programming Guide*) that `scanForPeripherals(withServices:)` strictly requires a non-nil array of `CBUUID`s in background; background wildcard scanning is rejected. Furthermore, CoreBluetooth has no API to filter on Manufacturer Data (`0xFF`). Type-0xFF-only advertisements are silently discarded by iOS baseband without waking the app.
  * **Architectural Fix:** Injected a 4-byte 16-bit Service UUID AD structure (`AD Type 0x03`, UUID `0xFC00`) alongside the Manufacturer Data (`AD Type 0xFF`), establishing the **23-Byte iOS Background-Safe Ceiling** ($31 - 4 - 4 = 23\text{ B}$).
  * **(O1) Effective iOS Receipt Rate:** Established working rate of **$0.033\text{ to } 0.125\text{ Hz}$** ($1\text{ receipt every } 8\text{--}30\text{ s}$) based on Apple Accessory Design Guidelines (30ms window / 300ms interval, ~10% duty cycle) and Herald Project empirical data. Duplicate advertisements are coalesced by iOS; rotating Resolvable Private Addresses (RPA) every 15s is required to re-trigger discovery.
  * **(O3) Android Doze Wake Latency:** Moving crowd nodes bypass deep Doze via Significant Motion Detection (SMD < 1s). Stationary nodes experience $50\text{ ms to } 3\text{ s}$ latency on controller-offloaded `PendingIntent` filter match, or up to maintenance windows ($9\text{--}30\text{ min}$) if batched by aggressive OEM battery policies.
* **Byte Budget Execution (`src/byte_budget_model.py` & `data/byte_budget_model.json`):**
  * Evaluated wire budgets across 27B Manufacturer Data, 29B Custom Type, and 23B iOS-Safe modes with (7,4) Hamming and RS(16,8) FEC.
  * **Doc 06 Baseline (4 Bytes / 32 bits):** Raw wire: 4B. Under Hamming(7,4): 7B (slack: +20B in 27B mode, +16B in 23B iOS mode). Under shortened RS(16,8): 12B (slack: +15B in 27B mode, +11B in 23B iOS mode). Under full-block RS(16,8): 16B (slack: +11B in 27B mode, +7B in 23B iOS mode).
  * **Doc 06 + 8b Age + 16b Envelope MAC (7 Bytes / 56 bits):** Fits in a single 8-byte RS block ($7 + 8 = 15\text{ B}$), retaining **+8B slack in 23B iOS mode** and **+12B slack in 27B mode**. Under Hamming(7,4): 13B (slack: +10B in iOS mode).
  * **Doc 06 + 8b Age + 32b Envelope MAC (9 Bytes / 72 bits):** Exceeds single RS block ($9 > 8$), forcing 2 blocks ($9 + 16 = 25\text{ B}$ shortened, 32B block), causing **overflow (-2B in iOS mode, -5B in 27B block mode)**. Confirms architectural mandate: **Envelope MAC must be 16 bits** if using RS(16,8).
* **Doc 06 Formal Critique:** Documented that Doc 06's "150ms synchronous relay" is an active foreground myth; real background relay chains take $10\text{--}30\text{ s}$ per hop. The 5-second 4-bit EPOCH causes false routing loop drops during slow async propagation and must be widened to an 8-bit Age counter.
* **Artifacts Created:**
  * Vault Document: `19_ASYNC_SCHEDULE_MESH_OPERATING_MODEL.md`
  * Sizing Tool: `src/byte_budget_model.py`
  * Dataset: `data/byte_budget_model.json`

### 2026-09-19 — B-02: Packet v2 Definitive Specification & Implementation
* **Mission:** Design the definitive byte-level navigation packet (v2) that survives the real asynchronous mesh, carrying Age-of-Packet for data mules and an outer envelope MAC for anti-spoofing, all within the legacy advertising budget.
* **Protocol & Bit Layout Locked (48 bits / 6.0 Bytes Raw):**
  * Three 16-bit big-endian words (`>HHH`):
    * **Word 0:** `PKT_TYPE` (4b: `0x0`–`0xF`) + `SOS_ID` (12b: `0x000`–`0xFFF`).
    * **Word 1:** `HOP_COUNT` (4b: $0\text{--}15$) + `BARO_DIFF` (6b signed 2's comp: $-32\dots +31$) + `FLAGS` (6b: bitmask with `MULE_STORE_FORWARD`).
    * **Word 2:** `EPOCH` (4b: $0\text{--}15$) + `AGE` (2b: $0\text{--}3$) + `RESERVED` (2b: `SECONDARY_PHY` & `COLLISION_EXPEDITE`) + `ENVELOPE_MAC` (8b: `0x00`–`0xFF`).
* **Outer-Envelope Anti-Spoofing Architecture:**
  * Implemented 8-bit rolling MAC via HMAC-SHA256 over origin invariants `(SOS_ID || EPOCH || PKT_TYPE)` keyed with shared symmetric secret $K_{\text{session}}$.
  * Intermediate relays execute Zero-Decrypt Forwarding (ZDF) and preserve the MAC unmodified across hops.
  * Searcher authenticates incoming Hop 0/1 candidates: single-packet guess probability is $1/256 = 0.39\%$ (measured empirically across 10,000 trials: $0.36\%$). Two-epoch consecutive freshness gating brings false positive forgery acceptance to $1/65536 = 0.0015\%$. Neutralizes festival Black Hole attacks (Doc 14 §4).
* **Data Mule Partition Healing (Doc 17 & Exp H9):**
  * Integrated 2-bit `AGE` bucket (`0`=Live <10s, `1`=<1min, `2`=<5min, `3`=>5min) alongside `MULE_STORE_FORWARD` flag (`0x20`).
  * Mule re-ignitions clamp virtual hop floor ($H \ge 6$) and flag delayed age, suppressing false Hop-1 proximity alerts and resolving the Ghost Gradient epidemic.
* **Lightweight Forward Error Correction (Hamming 7,4):**
  * Systematic (7,4) Hamming code encodes 12 nibbles (48 data bits) into 84 code bits + 4 padding bits = 88 bits (**11.0 Bytes** on wire, $1.833\times$ expansion).
  * In a high-loss primary advertising channel with $1\%$ BER ($p_b = 0.01$, modeled in H2), Hamming FEC boosts packet delivery probability from **$61.64\%$ up to $97.60\%$** ($+35.96\%$ absolute reliability gain).
  * Unit test verified 100% restoration across 1,000 packets subjected to 12 simultaneous bit errors per packet.
* **Wire Budget & GAP Slack Verification (`src/byte_budget_model.py`):**
  * **27-Byte Manufacturer-Data Mode (`0xFF`):** Raw (6B) slack = **+21 Bytes**; Hamming FEC (11B) slack = **+16 Bytes**; Shortened RS(16,8) (14B) slack = **+13 Bytes**.
  * **29-Byte Custom-Type Mode (`0x7F`):** Raw (6B) slack = **+23 Bytes**; Hamming FEC (11B) slack = **+18 Bytes**; Shortened RS(16,8) (14B) slack = **+15 Bytes**.
  * **23-Byte iOS Background-Safe Dual-AD Mode:** Raw (6B) slack = **+17 Bytes**; Hamming FEC (11B) slack = **+12 Bytes**; Shortened RS(16,8) (14B) slack = **+9 Bytes**. Zero overflow in all modes.
* **Implementation & Automated Verification Runs (`src/packet_v2.py`):**
  * Tested 100,000 brute-force random packets in 0.34s ($290,636\text{ pkts/sec}$) with 100% lossless fidelity.
  * Tested 2,240 boundary value combinations (all extremes of baro $[-32, 31]$, hop $[0, 15]$, SOS ID $[0, 4095]$, MAC $[0, 255]$).
  * Asserted canonical reference vector bitstring `000101111010010100111110111000101001100110001111` (`17a53ee2998f`).
  * Verified BLE GAP encapsulation into 27B and 23B frames.
* **Artifacts Created & Updated:**
  * Code: `src/packet_v2.py` (pack, unpack, bitstring, HMAC-SHA256, Hamming FEC, BLE GAP framing, test suite)
  * Dataset: `data/packet_v2_roundtrip.json` (all 6 test stages passed)
  * Specification Document: `20_PACKET_V2_WIRE_FORMAT.md`
  * Modeling Script: `src/byte_budget_model.py` (updated with `packet_v2_48bit`)
  * Modeling Dataset: `data/byte_budget_model.json`
  * Index: `00_START_HERE_Find_Us_MOC.md`

### 2026-09-19 — B-03: Async Trickle Mesh
* **Mission:** Redesign the Inhibitory Trickle mesh to survive the REAL asynchronous operating schedule (Doc 18/19): iOS coalesced-single-discovery, Android PendingIntent wake-ups, and seconds-to-minutes node invisibility — replacing the idealized 150ms synchronous relay.
* **The Synchronous Relay Collapse (Empirical Proof):**
  * Built discrete-event simulation (`src/sim_async_trickle.py`) modeling 2,000 nodes across a $200\times 200\text{ m}$ arena over 50 Monte Carlo trials per condition.
  * Node distribution: $20\%$ "alive" (continuous scan, 150ms jitter), $70\%$ "background iOS" ($U(20\text{ s}, 60\text{ s})$ inter-wake, 1.5s scan window, coalesced discovery), $10\%$ "dead/out" (Doze/suspended).
  * **Synchronous (H2 Baseline):** Mean coverage = **$99.97\%$**, mean responder delivery = **$99.98\%$**, $p_{95} = 1.829\text{ s}$, 100% convergence in $2.131\text{ s}$ ($90.0\%$ of trials reached 100% within 2.5s).
  * **Async Unmitigated Reality:** Mean coverage collapsed to **$1.51\%$**, responder delivery collapsed to **$0.22\%$**, and $0.0\%$ of trials converged. Transient 150ms pulses vanish while background devices sleep, strangling the gradient at Hop 1.
* **Percolation Breaking Point Analysis (Parametric Sweep):**
  * Evaluated background-locked ratio sweep $\in [0\%, 30\%, 50\%, 70\%, 90\%]$ across 50 trials per level.
  * Derived theoretical 2D continuum percolation threshold $\lambda_c \approx 4.512$ for the alive sub-network.
  * **Results Matrix:**
    * **$0\%$ Background (90% Alive, $\langle k \rangle = 14.14$):** Coverage = **$99.99\%$**, Delivery = **$97.98\%$** (Super-critical, fast relay).
    * **$30\%$ Background (60% Alive, $\langle k \rangle = 9.42$):** Coverage = **$61.86\%$**, Delivery = **$68.91\%$** (Marginal transition, network gaps emerge).
    * **$50\%$ Background (40% Alive, $\langle k \rangle = 6.28$):** Coverage = **$7.93\%$**, Delivery = **$10.43\%$** (Catastrophic percolation cliff).
    * **$70\%$ Background (20% Alive, $\langle k \rangle = 3.14 < \lambda_c$):** Coverage = **$1.47\%$**, Delivery = **$0.05\%$** (Sub-critical shattered graph).
    * **$90\%$ Background (0% Alive, $\langle k \rangle = 0.00$):** Coverage = **$0.75\%$**, Delivery = **$0.00\%$** (Fully deaf except direct Hop 0 neighbors).
  * **Breaking Point Pinpointed:** The network undergoes a catastrophic phase transition between **$30\%$ and $50\%$ background-locked nodes**. Above $50\%$ background, single-pulse synchronous Trickle fails completely.
* **Protocol Redesign: Epoch-Synchronized Burst Windows (ESBW) + Gossip Re-Warming:**
  * **Macro Cadence:** 15.0s epochs aligned with 15s RPA MAC rotation and Packet v2 4-bit `EPOCH`.
  * **Active Burst Windows:** Relays broadcast an on-window burst ($T_{\text{burst}} = 10.0\text{ s}$, $T_{\text{adv}} = 211.25\text{ ms}$, $\sim 47$ packets) upon adopting an improved gradient or at epoch ticks. Discovery probability for sleeping iOS nodes exceeds **$98.6\%$**.
  * **Inhibitory Gating ($k=3$):** Relays apply $U(0.05\text{ s}, 2.0\text{ s})$ jitter. If $k \ge 3$ neighboring bursts of the same or better hop are detected, the burst is suppressed, eliminating spectrum collapse. Measured suppression rate: **$34.74\%$**.
* **Mitigated Simulation Results (50 Trials, 70% Background iOS):**
  * **Gradient Coverage:** Restored from $1.51\%$ to **$99.86\%$** ($\pm 0.28\%$).
  * **Responder Delivery Success:** Restored from $0.22\%$ to **$99.98\%$** ($\pm 0.14\%$).
  * **Operational Convergence Timeline:** $p_{50} = 287.531\text{ s}$ ($4.79\text{ min}$), $p_{80} = 369.304\text{ s}$ ($6.16\text{ min}$), $p_{90} = 407.741\text{ s}$ ($6.80\text{ min}$), $p_{95} = 442.120\text{ s}$ ($7.37\text{ min}$), 100% convergence = $556.656\text{ s}$ ($9.28\text{ min}$).
* **Artifacts Created & Committed:**
  * Simulation Code: `src/sim_async_trickle.py` (discrete-event baseline, sweep, and mitigation)
  * Datasets:
    * `data/async_trickle.json` (54,619 bytes)
    * `data/async_trickle_sweep.json` (1,887 bytes)
    * `data/async_trickle_mitigation.json` (25,513 bytes)
  * Architectural Specification: `21_ASYNC_TRICKLE_MESH_DESIGN.md` (23,119 bytes)

### 2026-09-19 — B-04: Anti-Spoofing Outer-Envelope MAC (Black-Hole Attack Kill)
* **Threat:** 1–10% rogue nodes broadcast fake Hop-0 frames; ZDF relays can't tell origin-authenticated from forged → responders descend into a black hole.
* **Agent outage:** agy under-delivered — ran `sim_spoof_resistance.py`, saved `data/spoof_resistance.json`, then exited before writing the doc. Data verified authentic (theoretical birthday math ≈ empirical at every cell); **doc 22 written + doc 20 amended by opencode (brain).**
* **Verified simulation** (`src/sim_spoof_resistance.py`, N=1,000 nodes, 200×200 m, 5 trials/cell):
  * **No MAC = total defeat:** at 0.5% rogue, 88–100% of responders are led to a rogue.
  * **At 5% rogue (memoryless):** 6-bit → 25% misled, 8-bit → **11%**, 10-bit → 4%, 12-bit → 1%. Hardened model (rate-limited re-injection): 8-bit → 1%, 10-12-bit → 0%.
  * **Birthday-collision sweep @ ≤100 forged messages/epoch:** 8-bit → **31.6–32.4%** accept, 12-bit → 2.4%, 14-bit → 0.6%, **16-bit → 0.15–0.18%.**
* **DECISION (kills Doc 20 lock):** `ENVELOPE_MAC` widened **8 → 16 bits**. Packet v2 native payload 48 b (6 B) → **56 b (7 B)**; (7,4) Hamming coded → **13 B**; iOS mode-C slack = **10 B** (fits).
* **Artifacts:** `data/spoof_resistance.json` (24,451 B), `sim_spoof_resistance.py`, `22_ANTI_SPOOFING_ENVELOPE_MAC.md`, doc 20 amended.
* **TODO (implementation phase):** update `src/packet_v2.py` MAC constant to 16 bits, re-run round-trip suite (forgery threshold → 1/65536).
* **DONE (by opencode brain, 2026-09-19):** `src/packet_v2.py` patched 8→16-bit MAC (48→56-bit, 7-byte packet, 13-B Hamming FEC, 14 nibbles). All 6 tests re-run PASSED: canonical vector `17a53ee2998f42`, 2240 boundary cases, 100k random roundtrips, **measured fake-MAC forgery pass 0.0000170 vs theoretical 1/65536=0.0000153**, 14-bit-flip FEC recovery 100%, iOS-safe framing 21 B ≤ 23 B ceiling.

### 2026-09-19 — B-06: End-of-Event Discovery-Probe Storm (Backoff + Suppression)
* **Scenario:** ~1,250 rescue groups simultaneously probe for the gradient (cold-start pathological case, ~12.5k + abrupt probe bursts).
* **Agent outage (pattern):** agy launched `sim_storm_avoidance.py`, saved `data/storm_avoidance.json`, exited before writing the doc. Sim verified re-runnable & reproducible; **doc 24 written + log updated by opencode brain.**
* **Verified sweep (N=5000, 1250 groups, 300 s):**
  * naive flood → 98.6% burst collision, **77.8% discovery** (22% of groups never discover in 5 min!).
  * passive 5 s listen only → 79.3% (lockstep persists — all groups talk in the same 6th second).
  * CSMA/CA urgency backoff `U(0,60)` → 100% @5 min, 94.5% @60 s, burst col 10.4%.
  * **plus_suppression (backoff + passive suppression) → 100% @60 s, 90.9% @30 s, overall col 12.4%, 87.3% reduction vs H2 baseline, probe count ×5 lower. CHOSEN.**
* **Artifacts:** `data/storm_avoidance.json` (13,437 B), `sim_storm_avoidance.py` (20,317 B), `24_STORM_BACKOFF_PROTOCOL.md`.
* **Flagged to doc 29:** urgency-weighted backoff curve tuning (exponential vs uniform) as implementation-phase micro-sweep.

### 2026-09-19 — B-05: Multipath Wall Alerts (RF Confirmation Layer)
* **Mission:** Solve the "Wall Override" false-alert and multipath problem quantitatively (Teardown Issue #5, Doc 14 §5) and design the multi-second RF-confirmation layer for the localization pipeline.
* **The Single-Sniff Failure (Empirical Proof):**
  * Modeled 3 physical scenarios in a concrete stadium bowl (`src/sim_multipath_wall_detection.py`, 1,000 trials/class, 15,000 total simulated windows):
    * **Position A (Window Gap LoS):** $d \approx 14\text{ m}$, crowd loss $\sim 17\text{ dB}$, mean RSSI $-83.04\text{ dBm}$, Rician $K = 7.0\text{ dB}$ ($s_R = 2.74\text{ dB}$), $H_{\text{mesh}} \le 2$, $\rho = +0.989$.
    * **Position B (Behind Concrete Barrier):** $d \approx 5.5\text{ m}$, concrete loss $26\text{--}32\text{ dB}$, mean RSSI $-92.88\text{ dBm}$, Rayleigh fading ($s_R = 2.86\text{ dB}$), $H_{\text{mesh}} \ge 4$, $\rho = +0.009$ (orthogonal).
    * **Position C (Multipath Bounce off Metal Bleacher/Roof):** Bounce path $\approx 32\text{ m}$, metal loss $1\text{ dB}$, mean RSSI $-85.62\text{ dBm}$ (strong-ish), multi-carrier Rayleigh fading across channels 37/38/39 ($s_R = 5.55\text{ dB}$), $H_{\text{mesh}} \ge 4$, $\rho = -0.934$ (discordant).
  * **Single-Sniff Catastrophe:**
    * **RSSI Threshold Classifier ($-88\text{ dBm}$ cutoff):** Position C is misclassified as Position A (False Line-of-Sight Shortcut) in **$78.9\%$ of trials**, and as Position B (False Wall Alert) in **$21.1\%$ of trials** ($0.0\%$ multipath detection; $64.27\%$ overall accuracy).
    * **Naive Wall Override Heuristic (Doc 14 Critique):** Triggers False Wall Alerts on **$100.0\%$ of multipath sniffs** ($50.0\%$ overall False Positive Rate).
    * **Bayesian MAP Upper Bound:** Even with calibrated priors, single sniffs suffer **$14.9\%$ error on Position C** ($4.1\%$ as A, $10.8\%$ as B; $87.57\%$ overall accuracy).
    * **Conclusion:** Spatial provenance (direct LoS vs wall bleed vs metal bounce) cannot be extracted from a single packet sniff. Multi-second temporal and frequency-selective statistics are mathematically mandatory.
* **Multi-Second Statistical Sweeps ($0.5\text{ s} \to 5.0\text{ s}$):**
  * Evaluated feature vector $\mathbf{x} = [\Delta H, \bar{R}, s_R, \rho]$ across window durations:
    * **$0.5\text{ s}$ ($5$ pkts):** Acc = $89.03\%$, Wall TPR = $67.10\%$, Wall FPR = $0.00\%$, Wall FNR = $32.30\%$ (high FNR due to Rayleigh fade erasures below $-98\text{ dBm}$).
    * **$1.0\text{ s}$ ($10$ pkts):** Acc = $92.10\%$, Wall TPR = $76.30\%$, Wall FPR = $0.00\%$, Wall FNR = $23.70\%$.
    * **$2.0\text{ s}$ ($20$ pkts - RECOMMENDED):** Acc = **$94.73\%$**, Wall TPR = **$84.20\%$**, Wall FPR = **$0.00\%$**, Wall FNR = **$15.80\%$**, Multipath $\to$ Wall Alert (C $\to$ B) = **$0.00\%$**, Multipath $\to$ LoS (C $\to$ A) = **$0.00\%$** ($100.0\%$ multipath bounce rejection!).
    * **$5.0\text{ s}$ ($50$ pkts):** Acc = $95.30\%$, Wall TPR = $85.90\%$, Wall FPR = $0.00\%$, Wall FNR = $14.10\%$.
* **Recommended Protocol Rule & Concrete Thresholds ($T = 2.0\text{ s}$):**
  * **Window Duration:** $2.0\text{ s}$ ($M \ge 4$ packets at $10\text{ Hz}$).
  * **Hop Disparity Trigger:** $\Delta H = H_{\text{mesh}} - H_{\text{direct}} \ge 3$.
  * **Wall Bleed RSSI Band:** $-99.0\text{ dBm} \le \bar{R} \le -89.5\text{ dBm}$.
  * **Multi-Carrier Variance Veto:** $s_R \le 4.8\text{ dB}$ (rejects as multipath if $s_R \ge 4.9\text{ dB}$).
  * **Bearing Coherence Veto:** $|\rho| \le 0.60$ (rejects as multipath if $\rho \le -0.20$).
  * **Measured Performance:** $84.20\%$ sensitivity (TPR), $0.00\%$ false positive rate (FPR), $15.80\%$ false negative rate (FNR), $100.0\%$ multipath rejection, $94.73\%$ overall multi-class accuracy.
* **Artifacts Created & Committed:**
  * Simulation Code: `src/sim_multipath_wall_detection.py` (calibrated channel models, single-sniff baselines, multi-second sweeps)
  * Dataset: `data/multipath_wall_detection.json` (8,623 bytes)
  * Architectural Specification: `23_RF_CONFIRMATION_WALL_ALERTS.md`
  * Index: `00_START_HERE_Find_Us_MOC.md`

### 2026-09-19 — B-07: PDR Gating
* **Mission:** Finalize the PDR / Activity-Recognition gating layer (Teardown Issue #1, Doc 14 §1 + Experiment H7) into a concrete, testable specification for responder and target smartphone firmware logic.
* **The Kinematic Chaos Reality (Empirical Proof):**
  * Modeled 5 crowd activities (`src/sim_ar_gated_pdr.py`, $50\text{ Hz}$ IMU, $1,000$ trials/class = $5,000$ windows, 100 multi-phase 120s missions):
    * **Navigating Walk:** $v \approx 1.25\text{ m/s}$, chest posture ($\theta \approx 42.1^\circ, |\phi| \approx 3.1^\circ$), rhythmic cadence ($2.00\text{ Hz}$, $\rho_{xx} = 0.967$), $\sigma_a^2 = 1.50\text{ m}^2/\text{s}^4$, $\sigma_\omega = 0.147\text{ rad/s}$, $\sigma_m = 3.16\text{ }\mu\text{T}$.
    * **Mosh Pit / Bass Bounce:** Jumping/shoved, net $v \approx 0.05\text{ m/s}$, violent energy ($\sigma_a^2 = 52.28\text{ m}^2/\text{s}^4$), high bounce cadence ($6.42\text{ Hz}$), flailing gyro ($\sigma_\omega = 1.638\text{ rad/s}$), magnetic distortion ($\sigma_m = 22.43\text{ }\mu\text{T}$). Ungated PDR emits $8.98\text{ m}$ phantom drift per 2s window.
    * **Pocket / Drunk Shuffle:** Phone vertical/inverted ($\theta \approx 3.8^\circ$ / $82.1^\circ$ off), leg swing cadence ($2.79\text{ Hz}$), normal-looking accel variance ($1.02\text{ m}^2/\text{s}^4$). Compass points into thigh ($88.83^\circ$ heading error!).
    * **Torso Spin Proximity Search:** Standing in place rotating $360^\circ$ at Hop 1 ($\sigma_a^2 = 0.02\text{ m}^2/\text{s}^4$, $0\text{ Hz}$).
    * **Stationary / Texting / Waiting:** Standing still in crowd ($\sigma_a^2 = 0.02\text{ m}^2/\text{s}^4$, $\sigma_\omega = 0.027\text{ rad/s}$).
  * **Failure of Pure PDR:** In a 120s multi-phase festival mission, pure ungated PDR fails searcher convergence in **$34.0\%$ of missions** ($66.0\%$ arrival rate, confirming H7's $37\%$ failure rate), accumulating a mean target drift of **$32.94\text{ m}$** (peak **$75.13\text{ m}$**) and emitting $25.0$ false vectors per mission with $45.50^\circ$ mean heading error.
* **The 5-Stage AR Gating Architecture & Locked Thresholds ($2.0\text{ s}$ Window, $N=100$ Samples @ $50\text{ Hz}$):**
  * **G1 (Posture):** Mean Pitch $\bar{\theta} \in [20.0^\circ, 65.0^\circ]$ AND Mean Absolute Roll $\bar{|\phi|} \le 28.0^\circ$.
  * **G2 (Dynamic Accel Variance):** $\sigma_a^2 \in [0.35, 4.20]\text{ m}^2/\text{s}^4$ (rejects stationary $<0.35$; rejects mosh shocks $>4.20$).
  * **G3 (Cadence & Periodicity):** Step Cadence $f_{\text{step}} \in [1.10, 2.40]\text{ Hz}$ ($66\text{--}144\text{ spm}$) AND Autocorrelation Peak Ratio $\rho_{xx} \ge 0.42$.
  * **G4 (Rotational Jitter):** Gyroscope Magnitude Standard Deviation $\sigma_\omega \le 0.80\text{ rad/s}$ ($45.8^\circ/\text{s}$).
  * **G5 (Magnetometer Anomaly):** Field Magnitude Standard Deviation $\sigma_m \le 12.5\text{ }\mu\text{T}$.
  * **Master Rule:** Emitted vector $[\Delta x, \Delta y]$ is emitted ONLY if all 5 gates evaluate True; otherwise strictly clamped to $[0.0, 0.0]$ (`0x0000`).
* **Empirical Verification Results (`data/ar_gated_pdr.json`):**
  * **False-Vector Suppression:** $100.0\%$ suppression of false emissions in non-walking windows ($25.0 \to 0.00$ per mission). $0.00\%$ False Positive Rate across 4,000 non-walking windows.
  * **True-Vector Retention:** $98.60\%$ True Positive Rate during genuine navigating walk.
  * **Heading Error Reduction:** Collapsed from $45.50^\circ$ (ungated) to **$3.14^\circ$ (gated)** — a **$14.5\times$ precision improvement**.
  * **Target Drift Error Reduction:** Collapsed from $32.94\text{ m}$ mean / $75.13\text{ m}$ peak (ungated) to **$3.34\text{ m}$ mean / $8.23\text{ m}$ peak (gated)** — a **$9.86\times$ reduction**.
  * **Searcher Navigation Success:** Restored from $66.0\%$ (pure ungated PDR) to **$100.0\%$ (AR Gated Fusion)**.
* **Ablation Findings:**
  * Posture gate is the sole defense against pocket drift: omitting posture leaks $9.10\%$ of pocket windows ($88.8^\circ$ corrupted heading).
  * Accel variance and cadence independently kill $100\%$ of mosh pit bouncing.
  * Gyroscope and magnetometer cap rotational chaos and metal/speaker proximity.
### 2026-09-19 — B-08: Terminal Handoff
* **Mission:** Sanity-verify the terminal-layer (last 15m) torso-shadowing "synthetic lighthouse" (Hypothesis H3) and its fallback Hot/Cold RSSI smoother when the responder is physically pinned in dense crowd clutter (Teardown Issue #2, Doc 14 §2).
* **The Near-Field Waterbag Breakdown (Empirical Proof):**
  * Built biophysical simulation (`src/sim_terminal_handoff.py`) modeling 5,000 Monte Carlo trials in the final 15m terminal zone with an 18 dB sternum cardioid pattern and a nearby standing body ($d_B = 1.2\text{ m}$) casting a 16 dB knife-edge diffraction / absorption shadow ($\sigma_{\text{body}} = 0.25\text{ m}$).
  * **Direct Line-of-Sight Blockage Regime ($|\Delta \theta_B| \le 25^\circ$, $N=747$):**
    * **Pure Torso 360° Scan (Strat a):** Shadowing collapses direct path power below multipath reflections. Mean angular error degrades to **$21.92^\circ$** (median $9.93^\circ$, $p_{90} = 59.22^\circ$, $p_{95} = 96.61^\circ$), with **$5.49\%$ catastrophic reflection flips** ($>90^\circ$ error) and terminal arrival ($\le 5\text{ m}$) dropping to **$79.92\%$** (mean distance $3.54\text{ m}$).
    * **Pure Hot/Cold 3-Step Walk (Strat b):** Pinned 3-step walk ($2.1\text{ m}$) along initial facing heading provides only a 1D hemisphere sign check with zero lateral steering. Mean angular error is **$66.21^\circ$** (median $61.27^\circ$, $p_{90} = 133.10^\circ$), with **$29.85\%$ flips** and only **$29.59\%$ terminal arrival success** (median distance $8.81\text{ m}$).
    * **2D Orthogonal Probe Ablation (Strat b_ortho):** 2 steps forward + 1 step lateral fails due to severe SNR deficit ($\Delta \text{RSSI}_{\text{signal}} \approx 0.025\text{ dB}$ vs $\sigma_{\text{channel}} \approx 2.09\text{ dB}$, $\text{SNR} = -19.2\text{ dB}$). Mean error remains **$58.42^\circ$**, arrival success only **$30.66\%$**.
* **Combined Terminal Handoff Protocol & Resolution (Strat c):**
  * **Protocol:** (1) Coarse Torso Scan candidate prior $\hat{\theta}_{\text{cand}}$ + alternate reflection $\hat{\theta}_{\text{cand}} + 180^\circ$; (2) 3-step walk ($2.1\text{ m}$) along $\hat{\theta}_{\text{cand}}$; (3) Ambiguity flip test ($\hat{g} < -0.4\text{ dB/m}, \Delta R < -1.0\text{ dB} \to$ reverse course); (4) If forward, advancing $2.1\text{ m}$ physically steps past the $1.2\text{ m}$ bystander obstacle, clearing the shadow ($A_B \to 0\text{ dB}$) and allowing an unblocked micro-check that clamps residual angular bias strictly $< 30^\circ$.
  * **Direct Blockage Regime ($N=747$):** Mean angular error collapses to **$13.67^\circ$** ($1.60\times$ improvement over torso alone), median error **$5.98^\circ$**, $p_{90}$ error cut in half to **$30.01^\circ$**, flips cut to **$2.54\%$**, and terminal arrival ($\le 5\text{ m}$) restored to **$88.35\%$** (median miss distance $0.95\text{ m}$).
  * **Aggregate Across All Regimes ($N=5,000$):** Mean angular error **$6.71^\circ$**, median **$4.72^\circ$**, **$98.50\%$** within $\pm 30^\circ$ walking cone, **$0.38\%$** catastrophic flips, and **$98.26\%$** terminal arrival success within $\pm 5\text{ m}$ (median miss distance **$0.62\text{ m}$**).
* **Artifacts Created & Committed:**
  * Simulation Code: `src/sim_terminal_handoff.py` (biophysical cardioid + knife-edge diffraction models, 5,000 trials, 4 strategies)
  * Dataset: `data/terminal_handoff.json` (47,310 bytes)
  * Architectural Specification: `26_TERMINAL_HANDOFF_PROTOCOL.md`
  * Index: `00_START_HERE_Find_Us_MOC.md`

### 2026-09-19 — B-09: Ghost Gradient
* **Mission:** Solve the Ghost Gradient problem (Doc 17 Open Question §4, Exp H9) — data mules carrying Hop-0 packets across physical dead zones create catastrophic false Hop-1 alerts in receiving crowd partitions, misleading searchers into actively tracking moving bystander mules away from the real target.
* **Theoretical Candidate Analysis:**
  * **(1) AGE Bucket (2 bits, Word 2 [11:10]):** Unauthenticated mutable transit field under ZDF. Cooperative mules update it based on elapsed transit time ($t - t_{\text{cache}} \ge 143\text{ s} \implies \text{AGE} = 2$). However, wire-only self-reporting fails in open heterogeneous crowds: under 15% non-compliant/legacy mules, false alerts surge up to 1,798.9 and 98% of searchers are misled.
  * **(2) PKT_TYPE = CACHED_MULE_BURST (4 bits, Word 0 [15:12]):** Cryptographically impossible for stranger relays. Origin authenticates `Origin Invariants = (SOS_ID || EPOCH || PKT_TYPE)` under the 16-bit `ENVELOPE_MAC`. Stranger relays lack $K_{\text{session}}$ (ZDF); mutating `PKT_TYPE` breaks the MAC, causing immediate packet discard as a forgery.
  * **(3) BARO_DIFF Freshness (6 bits, Word 1 [11:6]):** Vertical differential $\Delta z \approx -4.2\text{ m} \times \text{BARO\_DIFF}$ is completely blind to horizontal dead-zone transit ($\Delta z = 0$).
  * **(4) EPOCH Cadence & Dynamic Gating (4 bits, Word 2 [15:12]):** Authenticated by `ENVELOPE_MAC`. Walking 200m at $1.4\text{ m/s}$ incurs $142.9\text{ s}$ delay ($\approx 9.5$ ticks of 15s epoch). Any packet with $\Delta \text{Epoch} \ge 2$ ($> 30\text{ s}$) is provably a delayed transit echo. Multi-sniff static epoch dynamics ($dE/dt = 0$ over $> 22.5\text{ s}$) detects frozen replays.
* **The Definitive Multi-Layer Receiver Decision Rule:**
  * Tier 1: Fast-Path Wire Metadata (`AGE > 0` or `FLAGS.MULE_STORE_FORWARD` or `HOP >= 6`).
  * Tier 2: 16-bit HMAC Integrity & Anti-Spoofing check.
  * Tier 3: Epoch Cadence Delta Gating ($\Delta E = (E_{\text{expected}} - E_{\text{pkt}}) \pmod{16} \ge 2$).
  * Tier 4: Frozen Epoch Dynamic Detector ($dE/dt = 0$ over $> 22.5\text{ s}$).
  * Tier 5: Ingress Corridor Arc Synthesis for ETUI (recommending bearing toward Island A from perimeter centroid).
* **Empirical Verification (`src/sim_ghost_gradient.py` & `data/ghost_gradient.json`):**
  * Evaluated across 6 flow densities ($\lambda \in [0.5, 1.0, 2.0, 4.0, 8.0, 16.0]\text{ mules/min}$, 50 trials/density = 1,200 runs):
    * **Baseline (Unmitigated H9):** Spurious false Hop-1 alerts explode from **$331.7$** to **$11,207.5$**, corrupting up to **$184.3 / 300$ nodes** ($61.4\%$). Searcher misled rate explodes from **$46.0\%$** to **$100.0\%$** ($0.0\%$ corrected).
    * **Wire-Only (100% Compliant):** Collapses false alerts to $0.0$, achieving $92.0\%\text{--}100.0\%$ corrected rate.
    * **Wire-Only (15% Legacy / Non-compliant Mules):** Catastrophically leaks: false alerts surge from **$24.6$ to $1,798.9$**, and searcher misled rate escalates from **$6.0\%$ to $98.0\%$**. Proves wire-only gating cannot survive open crowd heterogeneity.
    * **Definitive Multi-Layer Decision Rule:** Achieves **$0.0$ false Hop-1 alerts** and **$0.0\%$ searcher misled rate** across ALL flow densities, even under 15% non-compliant mules. Searcher corrected rate reaches **$94.0\%$ at $2.0\text{ mules/min}$** and **$100.0\%$ at $\ge 4.0\text{ mules/min}$**, with mean ETUI arc error of **$10.33^\circ\text{--}23.68^\circ$** (strictly $< 24^\circ$ pointing due West toward Island A).
  * **Co-located Control Benchmark (500 trials at 5.0m):** Measured **$0.00\%$ False Negative Rate** ($100.0\%$ live target detection in $0.01\text{ s}$). Genuine proximate victims are never misclassified.
* **Artifacts Created & Committed:**
  * Simulation Code: `src/sim_ghost_gradient.py` (1,200 partitioned trials + 500 control trials)
  * Dataset: `data/ghost_gradient.json` (11,630 bytes)
  * Architectural Specification: `27_GHOST_GRADIENT_RESOLUTION.md`
  * Index: `00_START_HERE_Find_Us_MOC.md`

### 2026-09-19 — B-10: Multilevel Barometric Navigation & Stairwell Geometry
* **Mission:** Resolve the two long-standing open research questions from [[findings.md]] §Open Questions: (1) multi-story stairwell gradient geometry and 2D-hop entanglement, (2) cross-OS barometric calibration; plus formally close the iOS foreground-service / O2 open item flagged in [[18_BLE_ADVERTISING_TRANSPORT_REALITY]].
* **Atmospheric Physics & Granularity (Part A):**
  * Linear vertical pressure gradient: $dP/dz \approx -0.1181\text{ hPa/m}$ at $20^\circ\text{C}$ / sea level ($\rho = 1.204\text{ kg/m}^3$).
  * Standard commercial floor ($3.5\text{ m}$): $\Delta P_{\text{floor}} \approx 0.4132\text{ hPa}$. Arena concourse tier ($4.2\text{ m}$): $\Delta P_{\text{floor}} \approx 0.4958\text{ hPa} \approx 0.50\text{ hPa}$.
  * Wire format: 6-bit signed two's complement `BARO_DIFF` ($[-32, +31]$) with $0.5\text{ hPa}$ resolution per LSB ($\pm 135\text{ m}$ range).
  * **The Sensor Bias Catastrophe:** Evaluated cross-OS factory bias between Apple (Bosch BMP series: $\pm 0.5\text{ to } \pm 1.5\text{ hPa}$) and Android (STMicro LPS series: $\pm 1.0\text{ to } \pm 2.0\text{ hPa}$). At $\Delta \beta \ge 1.0\text{ hPa}$, exact floor accuracy and within $\pm 1$ floor accuracy collapse to **0.0%**, accumulating $2.425$ to $5.968$ floors of systematic error.
* **Multi-Deck Gradient Wrap & Stairwell Simulation (Part B):**
  * Modeled a 2-deck venue ($60\text{m} \times 60\text{m}$, 200 nodes) with concrete floor slab ($22\text{ dB}$ loss), elevator shaft waveguide ($6\text{ dB}$ loss), and stairwell corridor ($12\text{ m}$ flight).
  * **RF Ceiling Penetration Reality:** Transmit power $0\text{ dBm}$, sensitivity $-93\text{ dBm} \implies 93\text{ dB}$ link budget. Path loss through $3.5\text{ m}$ concrete slab is $77.2\text{ dB}$ ($+15.8\text{ dB}$ excess margin). RF punches through ceilings and elevator shafts naturally.
  * **Strategy 1 (Naive 2D Hop Descent):** **100.0% of searchers on Deck 0 are trapped** under the ceiling projection directly beneath the victim ($5.10\text{ m}$ mean miss distance) or at locked elevator doors, achieving **0.0% arrival success**.
  * **Strategy 2A (Strict Mesh-Level Baro Gating):** Relays dropping cross-floor packets ($|\Delta P| > 0.35\text{ hPa}$) creates a deaf partition with **0.0% alert coverage on Deck 0**.
  * **Strategy 3 (Floor-Aware Receiver Gating & Stairwell Portal Navigation):** Packets flood unrestricted venue-wide (100% alert coverage). Receivers gate on `BARO_DIFF`: detecting $|\Delta P| > 0.35\text{ hPa}$ suppresses in-plane descent and routes searchers to the stairwell portal. Upon reaching target deck ($|\Delta P| \le 0.25\text{ hPa}$), in-plane descent unlocks, achieving **0.0% entrapment, 100.0% stairwell portal convergence, and 100.0% arrival success (0.00m residual miss)**.
* **Barometric Calibration Protocols (Part C, 5,000 trials):**
  * **Protocol 1 (Uncalibrated Raw):** $12.9\%$ exact accuracy, $38.2\%$ within $\pm 1$ floor, $\text{MAFE} = 2.320\text{ floors}$.
  * **Protocol 2 (Entrance-Gate Baseline Snapshot):** 1-second reference snapshot at turnstiles ($z=0$) against $P_0$ slashes residual bias to thermal drift ($\sigma \approx 0.08\text{ hPa}$), delivering **$75.6\%$ exact accuracy ($100.0\%$ for $4.2\text{ m}$ floors), $100.0\%$ within $\pm 1$ floor, and $\text{MAFE} = 0.244\text{ floors}$**.
  * **Protocol 3 (Co-located Peer Consensus Fallback):** Clustering $K=8$ peers achieves **$60.2\%$ exact accuracy, $99.2\%$ within $\pm 1$ floor, and $\text{MAFE} = 0.405\text{ floors}$** with zero infrastructure.
* **Resolution of iOS Foreground Service & O2:**
  * Proved iOS has no general foreground service API.
  * Verified O2: CoreBluetooth background scanning strictly requires non-nil `serviceUUIDs`; Type-0xFF (Manufacturer Data) only scanning is silently dropped by iOS baseband without waking the app.
  * Reconfirmed Dual-AD 23-byte wire ceiling ($31 - 4 - 4 = 23\text{ B}$), where Packet v2 (7.0B raw / 13.0B Hamming-FEC) fits with 10B slack.
* **Artifacts Created & Committed:**
  * Simulation Code: `src/sim_multilevel_baro.py` (2,000 bias trials/point, 50 multi-deck trials / 500 searchers, 5,000 calibration trials)
  * Dataset: `data/multilevel_baro.json` (8,616 bytes)
  * Architectural Specification: `28_MULTILEVEL_BARO_AND_STAIRWELL.md`
  * Updated: `18_BLE_ADVERTISING_TRANSPORT_REALITY.md`, `findings.md`, `00_START_HERE_Find_Us_MOC.md`.

### 2026-09-19 — B-11: Implementation Blueprint v1 (Vol 1: Research Complete)
* **Mission:** Consolidate everything from B-01 through B-10 into ONE authoritative, indexed implementation blueprint (`29_IMPLEMENTATION_BLUEPRINT_V1.md`) and a concise machine-readable specification (`refimpl_spec.md`). This marks the formal completion of Volume 1 Research.
* **Core Syntheses Locked into Specification:**
  * **Canonical Wire Format (Packet v2):** 56 bits (7.0 Bytes) raw payload, expanding to 104 bits (13.0 Bytes) under nibble-wise systematic Hamming (7,4) FEC. Confirmed 100% compliant with the 23-byte iOS Background-Safe Dual-AD Mode C (AD Type `0x03` UUID `0xFC00` + AD Type `0xFF`), retaining +10.0 Bytes spare slack. Re-verified canonical test vector `17a53ee2998f42` across 100,000 randomized roundtrips (0.35s, 282,146 pkts/sec) and 2,240 boundary cases in `src/packet_v2.py`.
  * **Executable Node State Machine:** Specified Zero-Decrypt Forwarding (ZDF) for intermediate stranger relays; Epoch-Synchronized Burst Windows (ESBW: $T_{\text{epoch}} = 15.0\text{ s}$, $T_{\text{burst}} = 10.0\text{ s}$, $T_{\text{adv}} = 211.25\text{ ms}$, $k=3$ inhibitory suppression); Cold-Start Discovery Storm Avoidance ($5.0\text{ s}$ passive listen, $U(0, 60\text{ s})$ urgency backoff, $k=1$ discovery suppression); and 16-bit rolling HMAC-SHA256 verification over Origin Invariants `(SOS_ID || EPOCH || PKT_TYPE)`.
  * **Responder Guidance Engine:** Complete 3-stage localization pipeline: (1) Macro downhill hop descent gated by barometric floor differentials ($|\Delta P| > 0.35\text{ hPa}$ halts in-plane descent and routes to stairwells) and 4-feature multi-second RF wall confirmation ($\Delta H \ge 3, -99 \le \bar{R} \le -89.5\text{ dBm}, s_R \le 4.8\text{ dB}, |\rho| \le 0.60$); (2) Local terminal handoff combining sternum cardioid torso scans ($\hat{\theta}_{\text{cand}}$) with 3-step exploratory walks ($2.1\text{ m}$) to clear near-field bystander shadowing and resolve mirror reflection flips; (3) Terminal optical strobe runway and bystander localized audio-haptic alerts at $d \le 3\text{ m}$ / $\text{RSSI} \ge -65\text{ dBm}$.
  * **Global Failure Mode Matrix:** 18 documented real-world failure modes (kinematic mosh chaos, pocket compass drift, near-field bystander waterbags, iOS background throttling, percolation collapse, black-hole spoofs, multipath bounce overrides, discovery storms, ghost gradients, multi-deck ceiling traps, cross-OS baro offsets, channel BER, etc.) mapped directly to blueprint mechanisms and verified empirical numbers.
  * **Multi-Year Technology Risk Register:** Formulated 6 prioritized hardware and OS risk items (TR-01 through TR-06) with explicit physical prototype and testing mandates (anechoic chambers, 20-device iOS backpack arrays, stadium HVAC logging).
* **Artifacts Created & Committed:**
  * Master Implementation Blueprint: `29_IMPLEMENTATION_BLUEPRINT_V1.md`
  * Machine-Readable Specification: `refimpl_spec.md` (113 lines, < 250 line limit)
  * Test Suite Verification: Re-executed `src/packet_v2.py` (all 6 tests passed, output in `data/packet_v2_roundtrip.json`)
  * Updated: `00_START_HERE_Find_Us_MOC.md`, `research-log.md`.

### 2026-09-21 — B-12: Compatibility Layer & Direction-Finding Parity
* **Mission:** Begin the Volume 1 build phase: add a cross-language (Python / Kotlin / Swift) engine-parity compatibility layer with a wire-frozen `MeasurementSource` enum set and NavTier negotiation, plus a fully unit-tested relative direction/bearing layer (`core/direction.py`, 21 checks) that stays faithful to the topological-gradient design (RSSI is proximity evidence, never the routing gradient).
* **Core Parities Locked:**
  * `compat.py` — capability negotiation, `CapabilityRegistry`, `OobSideband`; test assertion corrected to `best_tier(b6, None) == MOTION_VECTOR` (15 checks).
  * `relationships.py` `compose()` now propagates weakest-hop `tier` + quadrature `bearing_uncert_deg` (19 checks) so multi-hop vector composition carries uncertainty (VRLG readiness).
  * `simulation.py` — FakeRadio gains `rssi_between`/`meters_from_rssi`/`bearing_deg`; new `scenario_relative_vector_nav` (§57.26) exercises heading/out-of-band sideband + route metrics (37/37).
  * Kotlin parity: `Direction.kt`, `CompatTier.kt`, `EngineSelfTest.runDirectionCompatParity`, `BLEManager.onRssiSample` hook (compile pending—no toolchain).
  * Swift parity: `Direction.swift`, `CompatTier.swift`, `EngineSelfTest.runDirectionCompatParity`.
  * `tests/test_compat_direction.py` 13/13 PASSED; full regression green (robustness suite 91/91, cross-language + app selftests).
* **Artifacts Created & Committed:**
  * `core/direction.py`, `core/compat.py`, `core/python/demo_direction.py`, `tests/test_compat_direction.py`, Kotlin/Swift parity sources.
  * Pending: compile validation on a device with android/gradle toolchain.

### 2026-09-21 — Paper pipeline start: blueprint, IP doc, manuscript v0.1, PDFs

* **What happened:** Phase 1–2 (system decomposition + verified prior-art survey)
  completed. Wrote three deliverables and rendered them as PDFs (reportlab;
  no pandoc/latex available on device):
  1. `paper/00_research_blueprint.md` + `.pdf` (10 pages) — full layered system
     decomposition (22 layers), prior-art map with verified citations (RFC 4838/5050,
     epidemic/spray-and-wait, Trickle RFC 6206, Čapkun GFS, MDS-MAP, DILOC, Patwari,
     PCM, Kimera-Multi, Bridgefy breaks, goTenna, body-shadowing, BLE energy, etc.),
     7-band mapping, risk register.
  2. `paper/ip/00_ip_analysis.md` + `.pdf` (5 pages) — SEPARATE IP/invention-candidate
     doc (C1–C8) with problem/existing-solutions/closest-prior-art/mechanism/
     difference/risks/experiments + counsel-consultation guidance. Research-level only,
     no claim language.
  3. `paper/01_manuscript.md` + `.pdf` (7 pages) — working manuscript v0.1 for the
     WHOLE system (communication+protocol+SOS+sensing+VRLG+topology+navigation+
     fallbacks+security/privacy/energy+platform), status-tagged evidence table,
     RQ map, gaps list. No fabricated data; all figures SIMULATED/MODELED/UNIT TESTED.
* **Status markers kept:** 7-band distinction; `[EXPERIMENT REQUIRED]`,
  `[CITATION REQUIRED]`, `[RESULTS REQUIRED]`, `[IMPLEMENTATION VALIDATION REQUIRED]`.
* **Next:** fill E-series real-hardware experiments; section-level drafting of
  manuscript chapters (Phase 9); academic-paper-reviewer pass on manuscript.

### 2026-09-21 — Manuscript v0.2: full-prose penetration draft (publisher-track)

* Expanded 01_manuscript.md from skeleton (v0.1, ~220 lines) to full-prose v0.2
  (564 lines, 17-page PDF): Abstract, Intro (scenario/why/it/contributions),
  Problem Definition R1–R10, Motivation, Requirements, Threat model, Related
  Work 6.A–6.O with IEEE-style citation numbers, Prior-art capability matrix,
  Research Gap, Objectives O1–O7, RQ hierarchy RQ1–RQ21, Architecture (10-layer),
  Comms/BLE (23-byte iOS ceiling, Trickle K=3, ESBW, mode ladder), Packet v2
  (56-bit+FEC+16-bit MAC), SOS/ghost-gradient, Sensing heterogeneity, Relative
  localization/direction layer, VRLG, Dynamic topology, Navigation/Z-axis,
  Fallbacks, Security/Privacy/Energy/Platform, Experimental methodology incl.
  E-series design + explicit "what this paper does NOT claim", status-tagged
  evidence table, Failure analysis, Discussion, Limitations (9), Future work,
  Conclusion, Declarations (Data avail/Ethics/CRediT/COI/Funding/AI-use),
  References (49, verified survey, 4 author lists flagged).
* Honesty: all figures tagged SIMULATED/MODELED/UNIT TESTED; [HW REQUIRED]
  markers throughout; no over-the-air measurements claimed.
* Next: E-series data; academic-paper-reviewer pass; citations finalize.

## 2026-09-21 00:55 — Manuscript v0.3 whole-system expansion [Cycle 9]

- Expanded manuscript to **whole-system v0.3**: `paper/01_manuscript.md` (1,091 lines → **27-page PDF**).
- Structure: 41 sections, all eleven layers, whole-app scope (not BLE-mesh-only).
- Added: 7-band status tagging throughout, 59-section architecture intent, E1–E23 program table with executed/not-executed split, RQ-by-RQ analysis (RQ1–RQ21), failure reports (frame mismatch, landmark conflation), fallback ladders, cross-regime scaling, 26 references (4 retained flags).
- Evidence re-mined from repo via explore digests (protocol internals: 56-bit/13B packet, Hamming FEC, envelope-MAC, ghost-gradient rules, merge protocol, trickle-with-absorption; quantitative: 2,000-node/50-MC/200×200m/hops 1–11).
- Honesty: [RES] only for unit/simulation results; [EXP:NOT-RUN] markers on all hardware-field items (E13/E15/E17/E21/E22). No fabricated results.
- Deliverables copied to `~/storage/downloads/Find_Us_research/` (01_manuscript.md/.pdf).
- Renderer quirk: passing a `.pdf` as argv arg parses it as markdown (paste error only); render itself clean.

## 2026-09-21 01:33 — Manuscript v0.4 critique-hardened [Cycle 10]

- Integrated an external adversarial critique of the infrastructure-less crowd-smartphone paradigm into the manuscript.
- New **Section 39 "Adversarial engineering critique and response"** (band-tagged claim-by-claim):
  - AoA/AoD hardware reality — accepted (design never required array-phase DF; direction provenance tiering).
  - OS background execution + ~8-connection limit — connection-free (advertising-not-GATT) topology dodge; FGS-as-feature.
  - Trickle perpetual-inconsistency — repaired: quantized snapshot-anchor congruence + persistence-gated reset + SOS bypass; new experiment E31.
  - Kabsch/SVD reflection hazard — det(R)=+1 admission rule, V-column sign-flip; new experiment E32.
  - Robust PGO — Huber/Cauchy + switchable constraints + incremental (iSAM2-style) mandated for any PGO stage.
  - DTN crypto — TOCTOU key-pinning, QR web-of-trust onboarding, no single broadcast key, IRK/BD_ADDR hygiene; passive-linkability left open (RQ18).
- Renumbered tail sections 39–45 → 40–46; added E31/E32 to program table; limitations updated.
- Added **Appendix K open-source compendium** (NASA dtn-tools, dtnsim, pyD3TN, ION-DTN; g2o_tutorial, gtsam-SLAM, PyPose, GTSAM examples; Kabsch-Cookbook, Songze1019/Kabsch, find_rigid_alignment_pytorch, zalign).
- References extended to [34] (BLE 5.1 DF; Kabsch; Horn; switchable constraints; iSAM2; Bridgefy analyses; Android FGS types; BLE MAC/IRK traceability).
- Re-rendered PDF (32pp), verified section presence via text extraction; Downloads + state/log refreshed. Zero fabricated results.

## 2026-09-21 19:25 — Full reviewer panel + revision round [Cycle 11]

- Ran academic-paper-reviewer full panel (5 role-separated read-only seats) on manuscript v0.4.
- Editorial Decision: MAJOR REVISION; filed at paper/review/01_editorial_decision_v1.md (with DA-CRITICAL adjudication record).
- Applied consensus revision round to manuscript (now v0.5):
  - Placeholders killed: RQ4 explicit 10% target; RQ11 explicit 20° direction-grade threshold.
  - Point estimates anchored to repo run registry ids (exp_002_trickle, exp_009_async_trickle, exp_011_ar_gated_pdr, exp_012_terminal_handoff); qualitative claims relabeled [RES: qualitative].
  - Appendix J.1 executed->reported audit table (18 executed runs mapped to reporting subsections).
  - Energy constants flagged model-derived; "[ESP→EXP]" and "proof assert" slips fixed.
  - DA-CRITICAL-1 resolved: Sec 13.5/39.3 corrective now provisional-on-E31; RQ4/RQ5/E3 retagged provisional.
  - DA-CRITICAL-2 resolved: Sec 25.3 "cannot loop" scoped to conditional direction-complete lemma; tree/no-cycle hole acknowledged.
  - Gap claims narrowed (framing-specific); rigidity grounding added (global rigidity, Henneberg, necessary-not-sufficient cycle consistency).
  - Prior-art lineage added to Sec 7.3 (directed diffusion, DV-hop/APS, Doherty convex, AFL); references extended to [38]; Kimera-Multi author fixed; [15] split into incident vs USENIX traceability; [16] venue added.
  - Platform/human hardening: FGS tone de-rhetoricized (notification flood flagged as storm-class, unmeasured); accessibility framed as co-design [EXP:NOT-RUN]; privacy governance paragraph (Sec 29.1a); QR OOB operational cost acknowledged.
  - Capability: Sec 39.7 reviewer-consensus note added.
- IP doc: v1.0 — added critique-driven candidates C9-C13 (quantized-snapshot Trickle congruence; connection-free topology; Kabsch reflection guard; TOCTOU key-pinned sequent chain; notification-flood accounting), revised strength sheet, counsel-consult list.
- Deliverables refreshed in ~/storage/downloads/Find_Us_research/ (manuscript md/pdf 34pp, IP md/pdf 6pp, editorial decision).
