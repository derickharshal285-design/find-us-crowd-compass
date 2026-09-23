# FIND US — PRIOR-ART / GAP / RQ / EXPERIMENT AUDIT
**Gate for the manuscript. Audit v1.0 — 2026-09-23. Bring back for user cross-check BEFORE structuring the paper.**
Not a finished paper. No invented citations; every entry below is tagged with its verification status.

> Honesty rule (carried from blueprint): nothing is elevated higher than the evidence supports. Every
> claim here about *findings* is what the search actually surfaced this session; every *contribution*
> is a candidate flagged `[AUDIT: NOVELTY UNVERIFIED]` until the audit is re-run adversarially.

---

## 0. Method (PRISMA-lite)

- Sources used this session (live web): IETF datatracker / RFC index, arXiv, US patent literature (patents.google.com), ACM/IEEE abstracts, GitHub project pages, prior-art summaries already in-repo (`research/paper/ip/00_ip_analysis.md`).
- Inclusion: emergency BLE/DTN messaging, disaster mesh / stored & forward relay, cooperative & anchor-free localization, crowd navigation without GPS, dead-reckoning (PDR), barometric floor gating, gradient/Trickle-style routing, TCP/connection-less BLE meshes, iOS/Android background limitations.
- Exclusion: pure Wi-Fi/5G transport, indoor *infrastructure-based* IPS, commercial-license-only products with no readable spec.
- Quality: each entry tagged `[VERIFIED in source]` / `[VERIFIED abstract-level]` / `[VERIFICATION REQUIRED]`.

---

## 1. Prior art identified (with honest closeness ratings)

| Ref | System/Work | Domain | What it does | Closest to our | Closeness |
|---|---|---|---|---|---|
| PA1 | **OEPB — IETF Internet-Draft, Operation of the Emergency Packet Broadcast** (Patel et al., IETF I-D) | Emergency P2P broadcast over BLE/Wi-Fi Direct | Infrastructure-independent emergency message broadcast; Trickle-based suppression; store-and-forward; WFQ priority classes; TTL & dedup. Multi-hop radio mesh (MANET-style). | C1/C4/C9, B-04 anti-spam; whole mesh-epidemic area | **HIGH** — broadcast mesh + trickle suppression + priority + TTL/dedup is directly on our proposed mesh. |
| PA2 | **DisasterMesh / IgniRelay** (IgniDA) | BLE advertising-mesh disaster tool | BLE GATT+advertising mesh, store-and-forward, HPKE+Ed25519 E2EE relay; multi-hop. | Whole mesh-epidemic + relay semantics | HIGH (our IP doc already flags IgniRelay as closest prior art C10-adjacent) |
| PA3 | **CrisisConnect / BlueSOS / Vajra / SOS Mesh** (academic/OSS, various) | BLE mesh SOS | BLE mesh for emergency beaconing with TTL/hop/dedup/relay, E2EE. | SOS propagation gradient + relay E2EE | HIGH |
| PA4 | **CORELS** (et al.) | Cooperative & relative localization | Anchorless/cooperative localization in dynamic wireless networks using inter-node RSS/time measurements. | C1 relationship relay, relative localization, dynamic spatial graph, composition | HIGH — this is the classic cooperative localization line. |
| PA5 | **CLIPS / cross-layer cooperative PF (particle filter)** (Larsson group et al.) | Cooperative RSS+PF | Cooperative localization with particle filters from pairwise RSS and PDR-like motion. | C1, PDR fusion, ghost-gradient uncertainty | HIGH |
| PA6 | **iOS/Android BLE background asymmetry + 23-byte ceiling + scan limits** (Apple CoreBluetooth, Google BLE background scan limits) | Platform constraints | Documented platform ceilings we already rely on (Doc 18). | BLE framing, T_max trade-off | CONTEXT (constraint, not prior art) |
| PA7 | **RFC 6206 Trickle** (Levis et al.) + adaptive jitter variants | Low-power mesh supression | Original Trickle timer; adaptive intervals. | C9 quantized-snapshot congruence | MEDIUM (we *extend* the congruence predicate; already documented in our IP doc C9) |
| PA8 | **Geomagnetic fingerprinting / ppNav / LiMag / EasyFind** + **NIST firefighter & UWB+IMU** | Infrastructure-free indoor navigation | (a) geomagnetic fingerprint + PDR position nav w/o beacons; (b) relative UWB/IMU cooperative tracking for rescue. | Terminal navigation, torso-shadow, spatial graph (navigation layer) | MEDIUM (nav layer; does not carry crowd-gradient SOS with uncertainty) |
| PA9 | **Patent US11627453** (emergency communication over non-persistent P2P BLE network) | Patent (assigned) | Non-persistent P2P BLE emergency comms; relay over BLE mesh. | Our whole system-level claim | HIGH risk — read full claim set before any system-level novelty assertion |
| PA10 | **Flash-mob density / jitter-scaling crowds** (H5 line; simulation-derived, our own) | Crowd simulation | Our own 2,000-node flash-mob density work. | C5, adaptive jitter | Baseline (ours) |
| PA11 | **Data-mule partition healing / ghost-gradient** (our B-09/H9) + DTN custody transfer (RFC 5050) recursion | DTN | DTN custody transfer is generic prior art. Our mule-specific spatial-gradient semantics = candidate. | C3 ghost-gradient, C7 healing | MEDIUM (mule gradient is candidate; custody transfer is old) |
| PA12 | **Endpoint-security / envelope MAC anti-spoofing** (16-bit MAC, Doc 22/B-04) | Packet integrity | Truncated-keyed-MAC anti-forgery: generic principle. Width selection is our contribution candidate, not the MAC itself. | B-04, C4 | MEDIUM-HIGH risk (MAC width selection likely obvious to skilled person) |

**Verification honesty:**
- PA1, PA4, PA5, PA8(b), PA9, PA2, PA3 — `[VERIFIED abstract-level via live search this session]`. Full-text read of OEPB I-D and US11627453 claims `[VERIFICATION REQUIRED — fetch each I-D/patent body]`.
- PA8(a) geomagnetic products — `[VERIFIED publicity-level via search]`; mechanism detail `[VERIFICATION REQUIRED]`.

---

## 2. Findings → gap decomposition (96 target-95 finding overlap note on finding check: re-check gap.)

### The four sub-questions the directive requires the paper to answer, and what prior art answers today:

| Question | Prior-art answer (PA refs) | Find Us position after this audit |
|---|---|---|
| Q1. Can a crowd of ordinary phones do **infrastructure-independent emergency comms**? | Fat YES — PA1, PA2, PA3, PA9 (many systems, several patents). | **NOT our contribution.** We inherit this; must cite & not claim. |
| Q2. Can phones **cooperatively localize / build relative spatial graphs** without anchors? | Fat YES at algorithmic level — PA4 (CORELS), PA5 (CLIPS/coop PF), cooperative SLAM merging (PCM/Mangelson, Kimera-Multi already cited in our IP doc). | **NOT a clean standalone novelty.** Candidate rests on (a) RF-only human-radio sparse observations (vs visual/LiDAR rich loops) and (b) uncertainty-tier bound composition — tagged `[AUDIT: NOVELTY UNVERIFIED]` in C2/C1. |
| Q3. Can a phone navigate **relative / GPS-free indoor**? | Yes — PA8 (geomag/PDR, UWB+IMU NIST); also folio of baro floor gating (Muralidharan line). | **Not a claim alone.** Terminal/torso-shadow + baro-gated gating = candidate C7/C8, tagged unverified. |
| Q4. (the potential intersection) — can the **SOS gradient be spatially-aware and uncertainty-aware across a lossy, partitioned, multi-hop crowd** with **late-responder entry**, such that a responder can both *find the group in physical space* and *detect partition/re-formation*, all while **respecting platform radio ceilings and a bounded energy/UX budget in a dense flash-mob density regime**? | Only **fragments** across PA1–PA9. No single system combines: (mesh + gradient + uncertainty-tier spatial graph + cooperative localize + gradient navigation + late-entry + partition healing + dual-AD byte-ceiling budget + adaptive flash-mob jitter) in one validated design. | **THIS is the only defensible research gap.** It is an *integration/co-design gap*, not a per-mechanism invention. The paper must be framed as: "what integration-level behaviors emerge when you co-design these existing mechanisms under hard radio/energy/platform constraints in a dense crowd," with falsifiable predictions. |

**Gap verdict:** Find Us is **not** the inventor of BLE mesh, SOS gradient, cooperative localization, gradient routing, or baro/PDR indoor navigation. The *research* gap that survives hostile review is:
> **The system-level question of whether a co-designed, byte-budgeted, energy-budgeted, platform-respectful combination of [Trickle-broadcast mesh + uncertainty-tiered spatial-graph composition + SOS hop-gradient + PDR/baro-gated terminal guidance + late-responder join/partition healing] produces emergent crowd-navigation behaviors that no single subsystem yields, measured against falsifiable density/error/latency/energy bounds.**

Markers for the paper: every subsystem needs a "WHAT ALREADY EXISTS" citation (§ blueprint 7-band). Only the *coupled behaviors + the specific gating rules* are candidate contribution — and even those get `[NOVELTY UNVERIFIED]`.

---

## 3. Rewritten research questions (RQ rewrite — deliverable 3)

Old RQ1 (too broad, claims-compliant only against Q1): "Can phones cooperate to provide emergency communication…?" → **sunk already**, answered YES by PA1/PA2/PA9. Replace:

- **RQ1 (system-level, falsifiable):** Under a hard per-device radio/energy budget (≤23-byte dual-AD payload, ~10 Hz duty, 1–?% battery/hour), what is the **maximum SOS-gradient reach and partition-healing latency** achievable by a Trickle-suppressed, uncertainty-tiered spatial-graph crowd mesh in a dense flash-mob (N∈{50, 500, 2000, 5000}) with 30–70% background-locked devices? (Predictions exist in sim: 96.2% delivery @1000, 74.8% @2500, ESBW restores 99.98%.) **Falsify by** real-device delivery below predicted-with-band at a given density.
- **RQ2 (integration):** Does coupling the **uncertainty-tier spatial graph** (C1/C2 composition, weakest-hop tier) into the **SOS hop-gradient** (C3 gating) improve late-responder arrival vs gradient-only *and* vs graph-only baselines — and under what partition/mule regimes does the coupling *hurt* (falsification boundary)? Sim currently says gradient+graph beats either alone; adversarial cases (mule ghost gradients) must remain at 0-false-alert after C3.
- **RQ3 (energy/UX co-design):** Can the mode ladder (NORMAL→RELEVANT→SOS→RETURN; C5) keep battery drain under a mission budget while preserving discovery/reach — and is the notification-flood (C13) actually bounded when every device renders alerts? **Not yet measured.**
- **RQ4 (platform truth):** Do the iOS 23-byte / background-scan ceilings and Android BLE quirks, *as modelled*, hold on real hardware — i.e., is the whole design realizable or does co-design collapse at the byte/energy wall? **Open `[REAL HARDWARE REQUIRED]`.**

---

## 4. Hostile peer review (deliverable 2 — worst reviewers maximized)

**Reviewer A (mesh expert):** "This is a reimplementation of OEPB (PA1) plus IgniRelay (PA2). Where is the novel mechanism? 'Uncertainty in the header' is obvious over graph SLAM (PCM/Kimera). The 16-bit MAC is a trivial width choice. Reject — incremental."
- Response that survives: we do NOT claim mesh or MAC width. We claim the **specific gating rules at the coupling boundary** (baro-gated floor routing that prevents 100% entrapment; epoch-cadence delta gating that kills mule ghost gradients at 0 false alerts; slope-rule+3-step-walk terminal handoff) and the **emergent system-level falsifiable predictions**. These are the §2.11/C3/C6/C7/C9/C2 items already admitted as "candidate, high prior-art risk" in our IP doc — none is asserted novel; each is presented as "we validate a specific mechanism and report honest bounds." **[VERIFICATION REQUIRED: full OEPB I-D text to confirm we found every overlapping gate.]**

**Reviewer B (localization):** "CORELS/CLIPS already do cooperative localization; your inverse-uncertainty composition is textbook. Reject."
- Response: agree; C1/C2 mechanism alone is not original. What we add is the *integration with SOS gradient + platform byte budget + real crowd density regime*, and we mark the relative-localization purely as enabling, not claimed-usage. **Our honest defensive line is the co-design, not the algebra.**

**Reviewer C (HCI/platform):** "You simulate everything; no real phones; iOS background is impossible as you describe."
- Response: TRUE. We will not claim real-world validation. Every claim carries its evidence tier (simulated ↔ real). The paper either (a) stays a "design + simulation + honest bounds" systems paper — which is publishable as a systems/challenge paper if RQ1–RQ3 are cleanly falsified in sim and the real-hardware gap is stated, OR (b) we run the real device battery (blocked locally: no JVM/gradle/swiftc in termux; CI is the only runner). **[DECISION REQUIRED from user: publish as simulation+design with explicit hardware caveat, or gate paper on CI-green real builds only.]**

**Reviewer D (intellectual-honesty / prior-art cop):** "Every 'novel candidate' in your IP doc has medium-high obviousness risk. Why should anyone believe this is research and not reinvention?"
- Response: the correct posture (already adopted in the repo's master instruction) is to *pre-emptively publish the hostile table*: for each candidate, list closest art, the technical difference (candidate), and the falsifying experiment. That is what a rigorous systems paper does. We keep research-discovery vs patent-claim separation (`research/paper/ip/00_ip_analysis.md` §4).

---

## 5. Research gap statement (deliverable 3, consolidated — this is the paper's hinge)

> Most emergency-mesh systems (PA1/PA2/PA3/PA9) transport *messages*; most cooperative-localization systems (PA4/PA5) build *geometry*; most indoor-nav systems (PA8) navigate *one device*. Find Us asks what happens when you push **uncertainty-annotated spatial-gradient information** (not free text) through a **connection-less, byte-capped, platform-limited, energy-budgeted** crowd mesh where devices **join late, partition, and rejoin** — and whether the *coupled* gradient+graph+gate design yields useful, *falsifiable* emergency-navigation behavior in the dense-crowd regime that prior art reports only piecewise. The contribution is the **co-design + honest measurement**, not a new physics or a new routing protocol.

---

## 6. Experiment matrix with falsification conditions (deliverable 4)

Each row: Experiment | Primary prediction | Falsification condition (what would sink it) | Status | Hardware note

| ID | Prediction | Falsified if… | Status |
|---|---|---|---|
| E-dense | Trickle+jitter keeps ≤?% collision, ≥96.2% delivery @1k, 74.8% @2.5k nodes | real-phone delivery falls outside predicted-band at density | SIM (exists) — real `[REQUIRED]` |
| E-esbw | ESBW restores 99.98% delivery @70% iOS-locked | real-device < sim by >X% | SIM — real `[REQUIRED]` |
| E-grad | Gradient-only late-responder nav < gradient+graph-coupled (RQ2) | coupled performs no better OR worse in a named mule/partition regime (ghost-gradient returns) | SIM — real `[REQUIRED]` |
| E-mule | Epoch-cadence delta gating holds 0-false-alert + 0%FNR @≥4 mules/min | any false alert or co-located-live FNR>0 in adversarial injection (exp already 0.0@331–11k false) | SIM (B-09/C3) — real `[REQUIRED]` |
| E-baro | Baro-diff floor gating ⇒ 0% entrapment; cross-OS ±1 floor via entrance calibration (MAFE 0.244) | any 2D-in-plane-descent trap survives on real stairwell/concourse | SIM — real stairwell `[REQUIRED]` |
| E-terminal | Torso-shadow+slope-rule+3-step walk ⇒ arrival ≤5 m ≥88.4% (blocked)/98.3% (clean) | real-body terminal handoff < band | SIM — real `[REQUIRED]` |
| E-energy | Mode-ladder keeps drain ≤ mission budget; C13 notif-flood bounded | drain exceeds budget OR notification flood unbounded at density | **NOT-RUN** `[REQUIRED]` |
| E-byte | 56-bit→23-byte dual-AD + 16-bit MAC round-trips on real BLE | real radiated bytes ≠ packed spec OR MAC width > acceptable forgery rate | SIM/PY green; real `[REQUIRED]` |
| E-plat | iOS 23-byte ceiling / background scan holds hardware-side | walls differ from modelled → any subsystem collapses | **blocked locally** (no swiftc/kotlinc); CI-only |

Every row has an explicit "what would kill this claim" — no row is asserted as real-world-true until hardware measurement.

---

## 7. Corrected architecture (deliverable 5) — changes forced by this audit

1. **Drop standalone novelty for subsystems.** The manuscript must *frame* mesh/coop-loc/gradient as inherited (cite PA1/PA2/PA4/PA5/PA9), so no reviewer can kill the paper for "reinventing BLE mesh."
2. **Own only the coupling + the specific gates**, and label each `[CANDIDATE, FALSIFIABLE]`: baro-gated floor routing; epoch-cadence-delta ghost-gradient kill; slope-rule+walk terminal handoff; quantized-snapshot Trickle congruence; uncertainty-tier weakest-hop composition under platform byte budget; flash-mob adaptive jitter (our own simulation-backed H5/B-11).
3. **Make the energy/UX budget a first-class axis** (C5/C13), currently only designed not measured — add as explicit RQ3.
4. **Add the platform-truth axis as RQ4** and mark the entire paper as simulation-validated + real-hardware-pending (unless user directs otherwise, §4 Reviewer C).
5. **Consistency pass:** manuscript's "novel" framing (Sec 39.3 critique round) must be trimmed to match this audit's honesty; the two separate packet codecs (protocol.py vs Packet v2 wire) must be consolidated before submission (already flagged in blueprint §2.3).

---

## 8. Concrete next actions (what I need from you before structuring the paper)

1. **Decision A (framing):** Publish as **"design + simulation + honest bounds"** (publishable now if CI builds green) vs **"gate on real-hardware validation"** (needs the device battery which I cannot run locally — CI only). [Recommended: A-option, with a prominent Hardware-Validation-Pending section.]
2. **Decision B (audit depth):** I recommend one deepening pass: fetch and read **full text** of OEPB I-D (PA1) and **claim set** of US11627453 (PA9) to close the two HIGH-closeness gaps before we commit the paper's "closest prior art" table. [Recommended: yes.]
3. **Decision C (CI gate):** ship the repo-red fix (empty-message check hunt + 5 iOS compile errors) to green CI *first*, as the audit-gated next step, so the paper reflects a build that actually compiles.
4. **Cross-check:** Confirm the gap/RQ/experiment framing above is what you want to defend. I will restructure the manuscript only after you approve this audit.

---

## 9. Status ladder of every claim I'm carrying forward

All entries carry their evidence tier explicitly; nothing is elevated one rung above evidence:
- **Established prior art (cite, don't claim):** OEPB, IgniRelay, CrisisConnect, CORELS/CLIPS coop-PF, geomag-PDR nav, US11627453, RFC6206/5050, platform ceilings.
- **Our simulation-backed behavior (report with bounds):** flash-mob jitter, ESBW, ghost-gradient kill @0 false, baro-gated floor, terminal handoff, 16-bit MAC forgery rate, uncertainty-tier composition — ALL in sim/tests only, REAL REQUIRED.
- **Candidate contribution (unverified, falsifiable):** the coupling gates listed in §7.2.
- **NOT claimed:** mesh itself, MAC-width choice, cooperative-localization algebra, gradient routing, SOS gradient as a concept.

*Audit v1.0 — end. Next: get CI green, optionally deepen PA1/PA9 full-text, then restructure manuscript only after user approves this audit.*
