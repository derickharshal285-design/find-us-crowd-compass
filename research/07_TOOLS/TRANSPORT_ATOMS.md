# TRANSPORT ATOMS — how phones ACTUALLY exchange bytes (the "learn how they work" pin)

`[RES]` = real atoms verified by bleak import + radio probe · `[PROPOSED]` = design ·
`[EXP:NOT-RUN]` = not yet executed on two real devices (the honest E10 gate).

## The atoms (in phone-talk order)

1. **Scan budgets** `[RES]` — the radio event loop is half-duplex: a phone can
   *listen* (scan) or *talk* (advertise) in a given radio turn, not both. Termux's
   API gives us `termux-bluetooth-scan` (listen verb) but no posix-level advertise
   verb exposed to user space → **every mesh advertisement is `[PROPOSED]` until a
   native bridge proves it.** Honest, byte-proven today.

2. **The 31-byte wall** `[RES]` (see manuscript §13.1) — legacy BLE advertising PDU
   ceiling; iOS dual-AD collapses to 23 usable. The vector envelope must fit there.

3. **Energy asymmetry** `[RES]` (manuscript §13.4) — *listening* costs ≈10× the
   advertising slot. The protocol spends broadcast, hoards listen time.

4. **bleak is the pure-Python client** `[RES]` — imports clean on this device;
   `[EXP:NOT-RUN]` the two-device exchange that would *prove* the mesh transport.

## The honest bottom line
- does BLE work here? **The Python side imports clean; the OS/adapter bridge is
  NOT yet probing any real device** → marked `[EXP:NOT-RUN]`, never claimed as measured.
- anything that reads "phones connected as a mesh" without an E10 run artifact is
  `[EXP:NOT-RUN]` and must say so.
