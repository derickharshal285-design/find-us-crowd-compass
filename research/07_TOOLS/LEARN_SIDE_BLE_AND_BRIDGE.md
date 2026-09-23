# LEARN ON THE SIDE — how BLE + the bridge ACTUALLY work, for the application

> **Purpose.** A side-learning notebook (not the paper) that makes the *transport*
> genuinely understood, not skimmed: what the phones *do* byte-by-byte, what the
> bridge can and cannot give us on **this** Android/Termux box, and the ideation
> that follows. Honesty tags throughout — nothing here claims a measured result.

## 1. The honest byte-answer: "does BLE work **here**?" (run in build, proven)

Probe results (live, this device, this pass):
- `bleak` **imports** (Python-side BLE client) → ✓ CLI available to the app.
- `termux-bluetooth-scan / -scaninfo / -information / -enable / -disable` → **5/5 ABSENT**
  (`termux-api` pkg newest = 0.60.0; the bluetooth verbs are **not linked** on this box).
- `bleak.backends.bluezdbus` import → **ImportError** (no OS BT socket visible).
- Radio scan (12 s) → **0 visible devices** (honest empty — no fabricated signal).

**Therefore:** `[EXP:NOT-RUN]`. The *Python atoms* work; the *radio bridge* is not
yet reachable from this sandbox, **so no two-phone mesh claim is made** (E10 gate).

## 2. How the phones would actually talk — the atoms

```
  App (Python, bleak)
       │  writes scan request / reads device-found
       ▼
  termux-api bridge  ── exposes verbs ──►  Android BluetoothManagerService
       ◄───────────── scaninfo / device events ──────────────
       │
       ▼
  Android BLE stack ──► radio (advertise + scan, half-duplex)
```

- **Advertising** = phone A broadcasts a short "I'm here, this is my gradient" (≤ 23 B
  dual-AD after iOS coalescing; the byte-capped envelope). Cheap to transmit.
- **Scanning** = phone B *listens* for that window. ~10× the energy of advertising →
  the protocol spends broadcast, hoards listen time (paper §13.4).
- **The hop** = A advertises → B (in range) hears it → gradient value carries the
  hop-count toward SOS. The graph is *connection-free advertising mesh*, not
  per-neighbor GATT links (paper §13.3a — the OS ~8-connection ceiling dodge).
- **Relay** = C hears B, B never needs to be connected; broadcast `rpt`/`sos` atoms.

## 3. What the bridge **would** give us once installed (honest, marked AWAITING)

When `termux-bluetooth-scan` and `-scaninfo` are actually present (needs the
Termux:API Android app + grant, or a bluez/root bridge), the app gets real atoms:
`enable/disable` (radio on/off), `scan` (in-range device list + RSSI), `scaninfo`
(typeof=ble + content surprise, the RSSI/name/addr). Those verbs are the honest
"how the phones discover each other" — **byte-required before any mesh test.**
Only then does E10 (two real phones, one acting as hopper) upgrade `[EXP:NOT-RUN]`
to a measured result. Until then: **no "it works" claim** (the honesty constitution).

## 4. Infrastructure ideation (whole-project, not singular)

One spine, one digit = one home (the project-wide renumber) — and the app needs
these homes to exist as live bytes: meshe (mesh verbs) · watchdog (health ledger +
mutual gateway) · gateway (mutual status, live wall) · calibration (the "add more
key prospects" track) · site (Vercel-deployable interactive drag-drop phones +
shortest-distance math) · the single detailed paper (§1–§10 → the spine every
document redirects to).

**The idea of the infrastructure (whole):** phones form a *gradient field on a
phone-graph* — each advertising envelope carries a mode-ladder value (level /
discrete confidence / ghost-decay), neighbors read each other's values, and the
SOS is found by following the descending gradient. The bridge is the radio verb
layer; the mesh is the graph; the watchdog is the honesty eye; the site is the
teaching front door (Vercel-deployable). All four are "the infrastructure" — not
any singular one.

## 5. Next (byte-gated, honest)

1. Rotate the 3+ exposed tokens (security — do this in the GitHub/device
   settings, they were pasted in chat).
2. When ready: install Termux:API app + grant → re-probe the 5 verbs → if present,
   run the real scan → only then E10 (2-phone demo) becomes a *measured* result.
