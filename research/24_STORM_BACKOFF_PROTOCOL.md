# 24. End-of-Event Discovery-Probe Storm: Backoff & Suppression Protocol

> **Status:** VERIFIED (sim re-runs, reproduces all headline numbers). Completed by opencode brain after agy sim completed but exited before doc delivery.
> **Headline:** When an event ends and ~1,250 rescue groups leap into discover-probe mode simultaneously, **naive flooding collapses to 77.8% discovery success**. The winning protocol is **passive listen + CSMA/CA urgency backoff + passive discovery suppression**: **100% discovery in 60 s, 90.9% in 30 s, overall collision 12.4%, 87.3% fewer collisions than the H2 baseline**.

---

## 1. The Storm Scenario

At 5,000-node end-of-event **mass rescue** (stadium / arena clearance), every bystander with a phone becomes a rescuer. Each of ~1,250 rescue groups (avg 4 people each) simultaneously:
1. Switches from passive gradient relay to **active discovery probe** mode (seeking the gradient with `PKT_TYPE = DISCOVERY_PROBE`).
2. Issues a **probe burst** — a near-simultaneous wall of identical discovery packets.
3. Holds in probe and waits for any Hop-0 gradient anouncement.

Doc 21's ESBW epoch (~47 packets/window at ~211 ms cadence) was designed for *steady-state* gradient relay. This is the **cold-start pathological case**: everyone talks at once, no gradient exists yet to gate on. It is the same "flash mob" regime H2 warned about — but here 100% of nodes are **active transmitters**, not a mix.

---

## 2. Simulated Strategies & Headline Results (`src/sim_storm_avoidance.py` → `data/storm_avoidance.json`)

Parameters: N=5,000 nodes, 1,250 groups of 4, 300 s observation window, 3 channels (37/38/39), `t_packet = 0.376 ms`, H2 collision baseline = 97.7%.

| Strategy | Burst Col % | Overall Col % | 5-min Disc % | 60-s Disc % | 30-s Disc % | Probes Tx | vs H2 reduction |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **naive** (flood at t=0) | 98.6 ±0.1 | 86.7 ±0.5 | 77.8 ±1.0 | 77.8 | 77.8 | 12,550 | 11.3% |
| **passive_first_only** (+5 s listen, no backoff) | 98.4 ±0.1 | 86.3 ±0.4 | 79.3 ±0.3 | 79.3 | 79.3 | 12,070 | 11.7% |
| **plus_backoff** (+CSMA/CA random 0–60 s urgency backoff) | 10.4 ±5.5 | 22.8 ±0.2 | **100.0** | 94.5 | 44.7 | 5,665 | 76.7% |
| **plus_suppression** (backoff + passive-discovery suppression) | 14.5 ±4.2 | **12.4 ±0.5** | **100.0** | **100.0** | **90.9** | 1,409 (est) | **87.3%** |

### Reading the table
- **`naive` is a partial blackout: 22% of groups never discover in 5 minutes.** Channel saturation at 98.6% burst collision rate strangles the probe window. Passive listen alone (no backoff) barely helps (79.3%).
- **The 5-second passive-listen lockstep is the real culprit**: it removes the sync cause but leaves the *lockstep* — all 1,250 groups then transmit in the same 6th-second. That's why `passive_first_only` still collides ~98%.
- **Adding CSMA/CA urgency backoff breaks the lockstep** (transmit at random 0–60 s offsets weighted by urgency). Collision collapses >9×; discovery reaches 100% by 5 min, 94.5% by 60 s.
- **Passive-discovery suppression** is the cherry on top: nodes that have already *heard* an on-tap discovery response or gradient packet suppress their own redundant probe. Overall collision drops to **12.4%**, 60-s discovery reaches **100%**, 30-s discovery climbs to **90.9%**, and probe count falls by ~5×, freeing the spectrum for urgency and confirm packets. Collision reduction vs H2 baseline: **87.3%** — the best of all four.

---

## 3. Derived Protocol Rules for the Implementable Spec

1. **Cold-start probe (Rescue / End-of-Event mode):** every probe group MUST wait a mandatory **`T_listen = 5 s`** passive interval, then transmit at a **CSMA/CA random offset `U(0, 60 s)` re-weighted toward urgency** (`SEVERE_URGENCY` flag → earlier window, e.g. `U(0, 10 s)`).
2. **Discovery suppression (k=1 passive variant):** upon *hearing* an on-air discovery response or a fresher hop-0/`ACK` announcement, drop out of the probe burst and switch to gradient relay. This is `k=1` passive suppression (not `k=3` of ESBW — cold start has no shared burst cadence to compare against).
3. **Probe packet reuse:** a DISCOVERY_PROBE carries `PKT_TYPE=2`; under the 56-bit packet it is itself MAC-protected (`ENVELOPE_MAC`, doc 22) so early responders cannot forge a "discovered" announcement to suppress probes they don't like.
4. **Latency trade captured:** discovery latency increases vs naive (p50 11.5 s → ~15–33 s) but *guaranteed* discovery (100% vs 77.8%) dwarfs the speed penalty in a mass-rescue setting. Combined with ESBW (doc 21) the mesh converges in ~4.8–7.4 min to full gradient.

---

## 4. Open Item (flagged to Implementation Blueprint, doc 29)

Urgency-weighted backoff distribution (exponential vs uniform, hot gradients) was not swept here — only headroom exists. Recommend an implementation-phase micro-sweep to tune the urgency curve, or keep uniform `U(0,60)`/`U(0,10)` as spec default.

---

## 5. Artifacts
- `src/sim_storm_avoidance.py` (20,317 B)
- `data/storm_avoidance.json` (13,437 B)
- Command: `python3 src/sim_storm_avoidance.py` (saved both vault + mirror).