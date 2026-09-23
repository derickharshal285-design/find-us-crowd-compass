# E10 — Two-Phone Radio Harness

**Purpose.** The single experiment that moves the design from `[EXP:NOT-RUN]` to `[EXP:FIRST-BYTES]`. Two phones trade bytes over the OS Bluetooth stack. Nothing shorter counts.

**Gate (must all pass BEFORE the verdict):**
- [ ] `termux-bluetooth-enable` returns success (radio powered)
- [ ] `termux-bluetooth-scan` returns the OTHER phone's advertisement (≥1 real device, with RSSI + name)
- [ ] Phone A's scanner hears phone B's advert; B's scanner hears A's — both directions
- [ ] ≥ 10 packets exchanged (not one lucky burst)

**Procedure.**
1. `termux-bluetooth-enable` on both phones (root path if the verb is absent from PATH).
2. Phone A: `termux-bluetooth-scan` for 30 s. Phone B: `termux-bluetooth-enable` then advertise.
3. Capture output. Extract the OTHER phone's real name + RSSI.
4. Repeat with roles swapped. Confirm symmetric hearing.
5. Log every byte to `research/08_EXPERIMENTS/E10_output/`.

**Honest verdict rules.**
- Both directions heard ≥ 10 packets → `[EXP:VERIFIED]` mesh = real.
- One direction only → `[EXP:PARTIAL]` — report which side failed, don't call it done.
- Neither → `[EXP:NOT-RUN]` stays. No radio claim.

**Current status: `[EXP:NOT-RUN]` — zero radios have traded bytes. The sim above is `[SIM:MATH]`, deterministic, and does NOT claim to be this.**
