# FIND US — IP / INVENTION CANDIDATE ANALYSIS (STANDALONE)

**Purpose:** This document is intentionally SEPARATE from the research manuscript. It identifies candidate invention areas for further analysis. It does **not** assert patentability of anything. It is an internal research/counsel-prep record.

**Working note (read first):** This is a research document, not legal advice. Any patent strategy must go through a registered patent professional. Nothing here should be treated as a patentability opinion.

---

## 0. Decision frame from the master instruction

- Do **not** claim the whole concept is patentable (BLE, mesh, relative localization, graph localization, SOS messaging, hop routing, smartphone sensing are all established).
- Do **not** publicly disclose detailed mechanisms before filing strategy is discussed with counsel (public disclosure can destroy novelty in many jurisdictions; PCT applications publish ~18 months after priority).
- Sequence: RESEARCH IDEA → PRIOR-ART SEARCH → IDENTIFY POSSIBLE INVENTIVE MECHANISM → DOCUMENT → PATENT PROFESSIONAL → FILE → THEN PUBLICATION.
- AI-assisted inventions are not automatically unpatentable (per current USPTO guidance AI is a tool; inventorship rests with natural persons). Keep an invention log with honest provenance.
- Maintain separation: RESEARCH DISCOVERY vs PATENT CLAIM.

---

## 1. Candidate invention areas (research candidates, NOT claims)

For each: Problem / Existing solutions / Closest prior art (verified §3 of blueprint) / Proposed mechanism / Technical difference / Technical effect to investigate / Alternative implementations / Potential claim elements / Prior-art risks / Experiments required / What would strengthen or weaken.

### C1. Uncertainty-aware dynamic spatial-information relay protocol
- **Problem:** A mesh relays messages; it does not generally relay *measured spatial relationship information* between unknown peers with explicit uncertainty, tier, and expiry.
- **Closest prior art:** DTN routing (RFC 4838/5050; Vahdat & Becker; Spray-and-Wait), goTenna URI/UDP-style mesh, Bridgefy; relationship/vector stores are on-device `core/relationships.py` (internal).
- **Proposed mechanism:** propagate edge payloads `(A→B = vector/bearing/source/uncertainty/tier/timestamp/expiry)` through ZDF relays; receivers merge by source+timestamp, recompute derived uncertainty per hop.
- **Technical difference (candidate):** routing headers carry *measurement provenance + weakest-hop quality tier saturating at a bounded uncertainty*, not just sender/hop/TTL.
- **Technical effect to investigate:** a responder's late-entering node can reconstruct map properties from relayed relationship edges rather than only coordinates/messages.
- **Prior-art risks:** any "distributed coordinates message" prior art; the uncertain-bounded-tier header may be obvious over graph composition. HIGH risk of obviousness → weak standalone.
- **Experiments:** multi-hop relay of relationship edges with ground-truth error vs hop depth vs a no-uncertainty baseline; demonstrate uncertainty stays calibrated or provably bounded.

### C2. Consistency-checked graph merging after crowd partition/reconnection
- **Problem:** two separated components build independent relative frames; upon reconnect, naively merging corrupts the map.
- **Closest prior art (strong):** Mangelson PCM (maximum clique pairwise-consistent loop closures, ICRA 2018); Kimera-Multi (robust distributed PGO, arXiv:2106.14386); loop-odometry consistency (Remote Sensing 2023). These are visual/LiDAR multi-robot SLAM with rich odometry.
- **Proposed mechanism:** apply pairwise-consistency maximization over *sparse, noisy human-RF relationship observations* with drifting PDR between observations, using only phone sensors and legacy-AD BLE.
- **Technical difference (candidate):** consistency checks run on ad-hoc generation human radio measurements (no visual loops, few closure cycles, high noise), where this robotics prior art is untested.
- **Technical effect to investigate:** correct join-merge acceptance/rejection with honest uncertainty on RF-only evidence.
- **Prior-art risks:** medium — direct technique import may be seen as obvious to a person skilled in SLAM merging; the novelty must be in the RF-human domain constraints and the resource budget.
- **Experiments:** two-island merge with planted good/bad loop closures; measure map-corruption rate and consistency-screening accuracy.

### C3. SOS-gradient + spatial-graph coupled late-responder navigation
- **Problem:** responder enters later; needs both topology (which way is "closer") and physics (which *direction* is the neighbor) without a global frame.
- **Closest prior art:** hop-count gradients (general), anchor-free localization (Čapkun 2001; MDS-MAP), evacuation guidance (Kuo 2022 — infrastructure-dependent), FireChat/Bridgefy (no spatial graph).
- **Proposed mechanism:** hybrid navigation signal = topological hop-gradient for monotonicity PLAIN, plus a spatial-graph bearing estimate (torso-shadowing DirectionSweep + stationarity gating + baro floor gating) for physical direction, fused only within validated uncertainty bounds.
- **Technical difference (candidate):** explicit coupling rule that gates each component on the other's validity (e.g., baro-gated in-plane descent; ghost-gradient-suppressed hop edge), rather than a single fused score.
- **Technical effect to investigate:** late-entering responder reaches target under topology change (movement/partition/rejoin) better than either component alone.
- **Prior-art risks:** medium — routing "quality-of-information" fusion exists broadly; specificity of the gating rule is what could matter.
- **Experiments:** late-join arrival success vs naive topology-only / vector-only baselines, with moving crowds and 15% non-compliant mules.

### C4. Ghost-gradient-safe store-and-forward (mule) partition healing
- **Problem:** data mules carrying cached hop-0 traffic across dead zones create false "closer" gradients (331→11,207 false Hop-1 alerts, 46–100% misled) [Doc 27, simulated].
- **Closest prior art:** DTN custody transfer (RFC 5050), epidemic/spray; no spatial-gradient interpretation of cached burst traffic found.
- **Proposed mechanism:** origin-invariants-bound MAC over `(SOS_ID || EPOCH || PKT_TYPE)` with EPOCH cadence-delta gating (ΔEpoch ≥ 2 = delayed transit echo, demoted from live gradient) + frozen-epoch detector.
- **Technical difference (candidate):** using *time-of-arrival cadence relative to a MAC-bound epoch counter* as a cryptographic freshness discriminator for cached vs live emergency traffic — a hardware-free replay/staleness filter in a broadcast-only channel.
- **Technical effect to investigate:** 0.0 false alerts + 0.00% FNR at ≥4 mules/min while preserving partition delivery (simulated target).
- **Prior-art risks:** medium-high — freshness/anti-replay by counters is an ancient principle; the specific "epoch-cadence-delta bound by MAC and used to *differentiate gradient semantics* under ZDF stranger relaying" is the potentially non-obvious part.
- **Experiments:** adversarial mule injection, non-compliant mule rates, timing jitter; verify zero live-target FNR in hardware.

### C5. Adaptive emergency-aware BLE participation (mode ladder) + dual-role energy budget
- **Problem:** continuous scan+advertise+relay drains phones; emergency utility must be preserved under a measurable energy budget.
- **Closest prior art:** connection-less BLE energy measurements (Siva 2019: scan≫advertise; García-Alonso 2020: ~1.32 µAh/s TX vs ~14.23 µAh/s RX @10 Hz), Trickle density adaptation (RFC 6206).
- **Proposed mechanism:** explicit state ladder NORMAL → RELEVANT → SOS → RETURN-TO-LOW, each with defined radio/sensor duty cycles, with an SOS-mode temporary participation override; energy budget as a first-class constraint in relay selection.
- **Technical difference (candidate):** emergency-specific, role-aware duty-cycle controller with battery-lifetime model, vs generic low-power BLE.
- **Technical effect to investigate:** predict operating lifetime vs mission duration; quantify service degradation in each mode.
- **Prior-art risks:** high — "adaptive duty cycling in BLE" is well-trodden; would need very specific emergency-grade guarantees to form a claim.
- **Experiments:** instrumented phone battery measurement across mode transitions; latency/coverage vs energy Pareto curves.

### C6. Terminal handoff protocol: torso-shadow bearing + 3-step verification walk + optical runway
- **Problem:** final 15 m: bodies block, RSSI flips; naive torso scan fails under 1.2 m obstruction (79.9% arrival); pure Hot/Cold walk has no lateral steering (33.8%).
- **Closest prior art:** body-shadow beamforming studies (Cotton 2011 50 dB rotation loss), standard beacon proximity; no anti-flip handoff walk found.
- **Proposed mechanism:** combined torso-scan coarse prior + 2.1 m 3-step walk that (a) clears the near-field obstruction physically, (b) applies slope rule gating (𝔤 < −0.4 dB/m with ΔRSSI < −1.0 dB → flip), then ALS-gated optical strobe + bystander audio-haptic prompts.
- **Technical difference (candidate):** using the walk to *physically escape* the near-field knife-edge shadow while simultaneously disambiguating mirror flips, then a light-blocking-aware terminal cue.
- **Technical effect to investigate:** arrival ≤5 m restored 88.4% (blocked) / 98.3% (simulated); residual bias <30°.
- **Prior-art risks:** medium — combinations of heuristic gating are common; the specific optic/audio+camera ALS interplay may carry weight.
- **Experiments:** real-device reproductions of the 5,000-trial simulation; body-confinement stress tests.

### C7. Floor-aware receiver gating + entrance-gate barometric calibration for multi-deck navigation
- **Problem:** RF bleeds through concrete; naive 2D descent traps 100% under the ceiling projection; uncalibrated cross-OS baro is useless (0.0% ±1 floor).
- **Closest prior art:** barometric floor localization (Muralidharan 2014 "more hype than hope"; pressure-pair floor localization PMC6720727), air-pressure altimetry generally.
- **Proposed mechanism:** unrestricted venue-wide RF flooding + receiver-side `BARO_DIFF` gating (|ΔP|>0.35 hPa suppresses in-plane descent, routes to stairwell portal) + 1 s turnstile snapshot calibration against reference P0 (MAFE 0.244).
- **Technical difference (candidate):** the *receiver-side semantic gating on floor differential as a navigation decision input*, plus venue-entrance zero-infrastructure calibration protocol.
- **Technical effect to investigate:** 0% entrapment, 100% stairwell convergence, 100% arrival (simulated).
- **Prior-art risks:** medium — baro-based floor detection exists; the gating-into-routing use is the potentially non-obvious piece.
- **Experiments:** real stairwell/concourse pressure + navigation trials across device brands.

### C8. AR-gated PDR kinematic-vector clamp
- **Problem:** mosh/bounce/pocket motion floods PDR with false displacement vectors (34% mission failure).
- **Closest prior art:** PDR + gait/step detection surveys (Harle 2013), activity recognition — extensive.
- **Proposed mechanism:** 5-stage 2.0 s @50 Hz deterministic gate (posture band, accel variance band, harmonic cadence 1.1–2.4 Hz + ρxx≥0.42, gyro σω≤0.80, mag σm≤12.5 µT); on any failure, displacement clamped to 0.
- **Technical difference (candidate):** the *specific five-band clamp* replacing probabilistic PDR gating, with drift result 9.86× improvement (simulated).
- **Prior-art risks:** HIGH — activity-gated PDR is crowded prior art; claim would need surprising, precise, and novel threshold logic. Weak standalone.
- **Experiments:** wearable/hands-in-pocket real datasets; mosh-pit field trial.

---

### C9. Quantized-snapshot Trickle congruence for spatial reports (perpetual-inconsistency fix)
- **Problem:** a naive Trickle (RFC 6206) application to spatial state is in perpetual "inconsistency": coordinates move constantly, so I resets to I_min and suppression collapses (documented external critique, manuscript Sec 39.3).
- **Closest prior art:** RFC 6206 Trickle; adaptive interval/jitter extensions (Flash-Mob scaling H5 lineage). The congruence predicate is normally "same content."
- **Proposed mechanism:** redefine the spatial-report congruence predicate to a **quantized snapshot anchor** (hash over tier + quantized delta bucket of an edge-cluster, e.g., >1.0 m composition drift), plus **persistence-gated inconsistency reset** (reset only on two consecutive disagreeing anchors or SOS urgency).
- **Technical difference (candidate):** driving the *dedup/consistency predicate* off a quantized state fingerprint rather than the raw measured value — Trickle suppresses exactly where raw application of the RFC would un-suppress.
- **Prior-art risks:** medium — "quantize to dedup" is a general trick; novelty must be in the *spatial-gradient semantics* of the anchor and the persistence gate (which reports are congruence-compared and how disagreement is gated).
- **Experiments:** E31 density/energy sweep (thresholds 0.5–5.0 m) vs naive RFC 6206 at 2,000 nodes; show suppression near no-quantization baseline with bounded spatial error. [EXP:NOT-RUN]

### C10. Connection-free (advertising-not-GATT) crowd topology with OS degree-limit invariance
- **Problem:** Android/iOS cap concurrent BLE connections (~8 system-wide), which would bottleneck node degree in connected mesh topologies.
- **Closest prior art:** mesh-over-connections (many BLE meshes open GATT links); broadcast/discovery meshes exist but not with byte-ceiling-optimized spatial-gradient payloads.
- **Proposed mechanism:** pure advertising/scanning (half-duplex trades) for all spatial-gradient traffic; connections reserved for low-density chunk/mule paths only (WiFi-direct, USB/Ethernet chain).
- **Technical difference (candidate):** the claim that effective node degree is bounded by radio duty/energy, not the OS connection cache — an architectural constraint elimination rather than a parameter tweak.
- **Prior-art risks:** high-medium — the *consequence* (degree invariance, energy/listen limit) is derivable; candidate value is in co-designing the byte/trickle/energy budget to that consequence (ties to C1/C5/C9).
- **Experiments:** E16/E17/E21/E22 device-measured duty/connection audit across the ~10-Hz listen regime. [EXP:NOT-RUN]

### C11. Frame-registration reflection guard (Kabsch det(R)=+1) with cycle-consistent rejection
- **Problem:** naive SVD Kabsch registration can return an improper rotation (det R = −1) under coplanar/noisy RF point sets, injecting a mirror frame into the mesh.
- **Closest prior art:** Kabsch correction (sign-flip of final V column) is textbook; robotics PGO robust losses.
- **Proposed mechanism:** mandatory det(R)≈+1 admission test on every frame registration in the graph-consistency engine; reflected frames rejected at VRLG admission and re-negotiated; gradient-safe SVD specified for any ML path.
- **Technical difference (candidate):** the *enforcement at graph admission* (rejection + re-negotiation semantics) vs per-algorithm correction — the control-plane placement of an existing math fix.
- **Prior-art risks:** high for the math itself; the candidate is the *admission-control semantics* in a distributed crowd graph (ties to C2).
- **Experiments:** E32 mirror-inverted point-pair unit test verifying no reflected frame enters the store. [EXP:NOT-RUN]

### C12. Key-pinned sequent chain for DTN TOCTOU mitigation (mesh E2E)
- **Problem:** in delay-tolerant multi-hop delivery, a large gap between message queue and key fetch lets an adversary bind their own key to a target session (TOCTOU; documented Bridgefy-class finding).
- **Closest prior art:** TOCTOU mitigations in secure protocol design; QR OOB fingerprint verification (web-of-trust) — standard.
- **Proposed mechanism:** pin the key at message-signing time and re-verify at every handoff against a lock-step sequent chain; in-crisis first contacts fall back to envelope-MAC-guarded TOFU (honest residual).
- **Technical difference (candidate):** binding the *sequenced payload* (sequent chain), not merely identities, to a pinned key so a key-swap in a routing queue is detectable at the next hop.
- **Prior-art risks:** high — "pin keys, sequence messages" is old crypto; candidate strength depends on the DTN-queue specifics (untrusted carrier hops, half-duplex). [EXP:NOT-RUN]
- **Experiments:** adversarial hop simulation; verify key-swap detection rate and no false negatives on honest delay.

### C13. Notification-flood-aware storm accounting for foreground-service crowd UX (regulatory/UX co-design)
- **Problem:** OS-mandated persistent notifications in a dense crowd are themselves a storm class (audible/visual flood) and an unmeasured usability risk (Section 39.2/31.1).
- **Closest prior art:** notification-dos studies; crowdsourcing attention literature.
- **Proposed mechanism:** treat notification flood as a first-class storm class with rate/semantic budget across participating devices (who renders which alert at what rate), co-designed with FGS mandates.
- **Prior-art risks:** high — likely UX/policy, lower patentability surface; kept as a defensive design note, not a claim candidate.

## 2. Comparative strength assessment (working sheet)

| # | Candidate | Prior-art risk | Experimental depth needed | Perceived strength |
|---|---|---|---|---|
| C2 | Consistency-checked RF crowd-graph merging | medium | high | strongest-structured |
| C4 | MAC-bound epoch-cadence staleness gating | med-high | medium | distinctive mechanism |
| C3 | SOS-gradient + spatial-graph coupled gating | medium | high | strong system-level |
| C7 | Receiver-side baro floor gating + entrance calib | medium | medium | distinctive |
| C9 | Quantized-snapshot Trickle congruence | medium | medium (E31) | distinctive, critique-driven |
| C10 | Connection-free topology dodge | high-med | high (E16/E17/E21/E22) | architectural (derivable) |
| C6 | Terminal handoff walk + flip disambiguation | medium | high | workable |
| C1 | Uncertainty-tier relationship relay | high | medium | needs sharpening |
| C11 | Frame-registration reflection guard | high(math)/med(admission) | low (E32) | control-plane placement |
| C5 | Emergency adaptive BLE mode ladder | high | medium | weak standalone |
| C8 | AR-gated PDR clamp | high | medium | weak standalone |
| C12 | Key-pinned sequent chain (TOCTOU) | high | medium | weak-med standalone |

**Honest verdict:** no candidate is asserted patentable. Counsel-consult after deepened patent search on: C2, C4, C3, C7, **C9** (best critique-derived prospect), and the C11 admission-control placement. C10/C12/C13 remain open discussion items with high obviousness exposure.

---

## 3. Publication-vs-patent sequencing (for the project owner)

Current recommended order:
1. Keep this doc and any invention-log entries private.
2. Deepen patent search (counsel or full-text USPTO/EPO/Google Patents) on C2, C4, C3, C7.
3. If filing is desired, file before any public disclosure (repository, arXiv, conferences, this document itself).
4. Only then run the publication pipeline.
- Note: some jurisdictions have limited grace periods (e.g., India §31 exhibition/disclosure exception with strict conditions) — must not be relied upon as general strategy.

---

## 4. Research discovery vs patent claim separation (explicit)

- **Research discovery** = "we observed in simulation that X happens / a mechanism Y exists." May be published.
- **Patent claim** = "a specific technical method comprising [steps] that solves [problem] with [technical effect], not obvious vs [prior art]." Needs counsel.
- This document records RESEARCH-level candidate mechanisms only. No claim language has been drafted. `[LEGAL REVIEW REQUIRED]`.

---

*End of IP analysis v1.0 — separate from the research manuscript by design. v1.0 adds critique-driven candidates C9–C13 (quantized-snapshot Trickle congruence; connection-free topology; reflection guard; TOCTOU sequent chain; notification-flood accounting) per the adversarial-critique hardening round (manuscript Sec 39).*