# 22. Anti-Spoofing Outer-Envelope MAC: Decision Matrix & Measured Forgery Resistance

> **Status:** VERIFIED (empirical sim + birthday math match). **REVISES Doc 20 §2.9.**
> **Headline:** The Doc 20 lock of an **8-bit** `ENVELOPE_MAC` is **defeated** by the black-hole attack model. The only truncation width meeting the hard requirement (<1% spoof success at ≤100 live messages) is **16 bits**. 12-bit fails at 2.4%; 14-bit squeezes under at 0.6% but leaves zero margin.
>
> **Fallout for Packet v2:** MAC width 8 → 16 bits. Raw payload 48 bits (6 B) → **56 bits (7 B)**; under (7,4) Hamming FEC → 13 B coded; slack in iOS Background-Safe mode C (23 B ceiling) = **10 B**. Still fits; no architectural breakage.
>
> **Verdict: KEEP packet v2 architecture; WIDEN `ENVELOPE_MAC` to `[55:40]` (16 bits). HMAC-SHA256 over `(SOS_ID || EPOCH || PKT_TYPE)`, truncated to 16 bits, keyed with shared searcher secret `K_session`.

---

## 1. Threat Model Recapitulation (from Doc 14 Issue #4 & Doc 20 §3)

The **Festival Black-Hole Attack**: 1–10% of nodes are adversarial rogues that broadcast fake Hop-0 packets ("I am the searcher") with forged/absent MACs. Because relays perform **Zero-Decrypt Forwarding (ZDF)** — packets are hopped without decryption — a bogus Hop-0 frame propagates identically to a genuine one anywhere in the mesh. A responder descending the gradient converges on the rogue instead of the actual emergency target. The only layer that can stop this is the origin-authenticated envelope MAC: a relay accepts a *lower*-hop packet only if its MAC validates.

The MAC must be validated at a far relay with **no knowledge of the origin's per-packet secret**. Hence: keyed HMAC-SHA256 over origin invariants `(SOS_ID || EPOCH || PKT_TYPE)` keyed with the shared session secret. Because the key is shared mesh-wide, the MAC is not a confidentiality mechanism — it is an **authentication tag** that a rogue (who knows the key but must inject packets *without* prior interception to learn valid tags) cannot forge in real time, and that the network as a whole refuses to relay if it does not validate. Truncation narrows the tag cheaply; the question answered here is *how narrow while still killing the attack*.

**Message budget of the attacker:** the adversary injects hop-0 forgeries continuously during an epoch window. Over an ESBW epoch (15 s), at ~47 packets/window and re-injection across the far ring, ≤100 forged candidates per epoch is a realistic upper bound. The hard target is <1% that any one of these is accepted as a valid origin MAC.

---

## 2. Verified Simulation (`src/sim_spoof_resistance.py` → `data/spoof_resistance.json`)

Monte-Carlo, N=1,000 nodes in 200×200 m, tx range 20 m, 5 trials per parameter cell. Metric = **P(responder is led to a rogue instead of the real target).**

### 2.1 Grid: Rogue Fraction × MAC Width

| Attacker model | Rogue | 0-bit | 6-bit | 8-bit | 10-bit | 12-bit |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Memoryless | 0.5% | 88.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Memoryless | 1.0% | 97.0% | 1.0% | 1.0% | 1.0% | 0.0% |
| Memoryless | 5.0% | 100.0% | 25.0% | **11.0%** | 4.0% | 1.0% |
| Memoryless | 10.0% | 100.0% | 54.0% | **16.0%** | 2.0% | 0.0% |
| Hardened* | 0.5% | 88.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Hardened* | 1.0% | 97.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Hardened* | 5.0% | 100.0% | 1.0% | 1.0% | 0.0% | 0.0% |
| Hardened* | 10.0% | 100.0% | 4.0% | 0.0% | 0.0% | 0.0% |

\* *Hardened*: relays additionally require a minimum observed interval between distinct valid-MAC senders (throws away mass re-injection), approximating per-epoch rate limiting.

**Reads:**
- **No MAC (0-bit) = total defeat.** Even at 0.5% rogue, 88–100% of responders are led to a rogue. The black-hole attack is fully effective without authentication.
- **8-bit at realistic 5% rogue rates the responder is led to a rogue 11% (memoryless) / 1% (hardened)** — better than nothing, but 1-in-9 responders misled in the un-hardened regime is catastrophic for an emergency-escape protocol.
- **12-bit drives memoryless 10%-rogue down to 0%, hardened everything to 0%.**

### 2.2 Birthday-Collision Sweep: Forgery Acceptance vs Live-Message Budget

Theoretical `1 − (1 − 2^(−w))^n` (n = injected forgeries) versus empirical 10,000-trial Monte-Carlo:

| Width | @1 msg | @10 | @25 | @50 | @100 | @100 empirical |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 6-bit | 0.0156 | 0.1457 | 0.3254 | 0.5450 | 0.7930 | 0.7881 |
| 8-bit | 0.0039 | 0.0384 | 0.0932 | 0.1777 | 0.3239 | **0.3156** |
| 10-bit | 0.0010 | 0.0097 | 0.0241 | 0.0477 | 0.0931 | 0.0894 |
| 12-bit | 0.0002 | 0.0024 | 0.0061 | 0.0121 | 0.0241 | 0.0240 |
| 14-bit | 0.0001 | 0.0006 | 0.0015 | 0.0030 | 0.0061 | 0.0054 |
| **16-bit** | 0.0000 | 0.0002 | 0.0004 | 0.0008 | **0.0015** | **0.0018** |

Theoretical ≈ empirical to within sampling noise at every cell → **the data is statistically sound.**

**Decision pivot, explicitly.** At the attacker's realistic ≤100-msg budget:
- 8-bit → **31.6–32.4%** forgery acceptance. Unacceptable.
- 12-bit → **2.4%**. Still above the 1% hard line.
- 14-bit → **0.6%**. Under the line, but with only 4× margin; any higher replay rate or a second epoch of accumulation crosses it.
- **16-bit → 0.15–0.18%. Nearly 6× margin below the 1% line, and robust to multi-epoch replay accumulation.** → **CHOSEN.**

---

## 3. Security Footprint Table (packet-level cost of each width)

| MAC width | Raw payload | (7,4) Hamming coded | Slack (iOS safe 23 B ceiling) | P(forge @1 pkt) | P(forge @100 pkts) | Meets <1% @100? |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0-bit | 40 b (5 B) | 9 B | 14 B | 1.00000 | 1.0000 | ❌ |
| 6-bit | 46 b (6 B) | 11 B | 12 B | 0.01562 | 0.7930 | ❌ |
| 8-bit | 48 b (6 B) | 11 B | 12 B | 0.00391 | 0.3239 | ❌ |
| 10-bit | 50 b (7 B) | 12 B | 11 B | 0.00098 | 0.0931 | ❌ |
| 12-bit | 52 b (7 B) | 12 B | 11 B | 0.00024 | 0.0241 | ❌ |
| 16-bit | 56 b (**7 B**) | **13 B** | **10 B** | 0.00002 | **0.0015** | ✅ ✅ |

**16-bit fits the iOS mode-C budget with 10 B of headroom** — 13 B coded < 23 B ceiling. No change to the Dual-AD structure (Doc 19) or ESBW epoch (Doc 21) is required.

---

## 4. Explicit Amendment to Doc 20

1. `ENVELOPE_MAC`: width **8 → 16 bits**; bit range `[47:40]` → **`[55:40]`**; range 0–255 → **0–65535**; HMAC-SHA256 truncation target **16 bits**.
2. Packet v2 raw payload: 48 bits (6 B) → **56 bits (7 B)**.
3. Coded payload under (7,4) Hamming FEC: 11 B → **13 B**.
4. Invariants block re-worded: "8-bit rolling HMAC" → **"16-bit rolling HMAC, P(forge @ ≤100 live msgs) ≤ 0.2%"**.
5. `src/packet_v2.py` MAC width constant must be updated to 16 bits and the round-trip suite re-run (forgery threshold becomes 1/65536 ≈ 0.0015%). **TODO item for the implementation phase / a re-validation patch.**

---

## 5. Operational Micro-Decisions

- **Key rotation:** `K_session` rotates per incident (`SOS_ID`). No cross-incident key reuse → a tag harvested at incident A is useless at incident B.
- **Replay window:** `EPOCH` (4-bit, salt) + 16-bit MAC bound the replay lifetime to one epoch-ish window; relays drop valid-tag frames older than `AGE`.
- **Forgery accounting:** attacks manifest as a burst of distinct-but-invalid MACs on the far ring; relays SHOULD report anomalous invalid-MAC counts upward (flag for responder-side anti-spoof hardening — see Doc 23 multipath alerting).
- **ZDF preserved:** relays still forward without decryption; only the 16-bit tag is checked at accept-time (cheap, 1 HMAC-SHA256 truncated → ~µs/µP).

---

## 6. Artifacts

- `src/sim_spoof_resistance.py` — Monte-Carlo attack simulation (grid + birthday sweep).
- `data/spoof_resistance.json` (24,451 B) — all tables above, incl. per-cell raw trial data.
- Command used: `python3 src/sim_spoof_resistance.py` (6.01 s runtime, 24,451 B out).