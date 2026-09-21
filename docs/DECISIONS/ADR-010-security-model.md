# ADR-010 — Security model (DECIDED)

**Status:** Decided — implemented in `core/security.py`, `core/protocol.py`
(Protocol v3), mirrored natively in `android/` (Kotlin) and `ios/` (Swift).

**Context (spec §45, §74):** Emergency traffic is sensitive. Threat list:
replay, fake hop updates, malicious routing, malicious broadcast, fake SOS,
unauthorized responders, replay of old SOS. The hardcoded `SESSION_KEY`
placeholder in `relay/relay_node.py` is legacy-only and is banned from the new
device code paths.

**Decision — incident-scoped authenticated packets (the distributed backend):**
- Every device that joins an incident holds the **same incident link**
  (`incident://<b64(incident_id||0x00||salt)>?salt=..&ttl=..&life=..`), from
  which the session derives `key` and `auth_key` via double-HMAC-SHA256 —
  byte-for-byte identical across Python, Kotlin and Swift.
- Every packet carries an **8-byte HMAC-SHA256 tag** (Protocol v3). The MAC is
  computed over the canonical on-wire fields — U8 type | 16B event | 8B sender
  | U16 version | U8 hop | U8 ttl | **U32 timestamp**. Timestamp is uint32, so
  real-world (post-2000, 2026+) timestamps never wrap (uint16 regression was
  caught and armored during this build).
- Receivers verify the MAC **before any graph write**; failures increment
  `rejected_macs` and are dropped. Tampering any covered field fails the MAC.
- Attacker model is explicitly scoped: the session key is shared by every link
  holder, so an insider can forge another insider's gradient. That is the
  documented emergency tradeoff (light model); per-device PKI is deferred
  (`docs/PLAN_NATIVE_BACKEND.md` non-goals). Replay/aging is bounded by the
  timestamp field + dedup window; TTL/lifespan windows cap event lifetime.

**Implementation notes:**
- O(1) per-packet cost; per-device key state is just the session (bounded by
  neighborhood, never by N).
- 50k device envelope (measured at `core/crowd.py`): MAC attach ~19 µs, frame
  ~42 µs, steady-state ~1 ms/s of CPU per device.
- Native parity batteries: `android/` EngineSelfTest (kotlinc-verified, 22
  checks PASSED) and `ios/` EngineParityTests mirror the Python reference.

**Consequences:** Production claims now hold for incident-authenticated
packets on-device, no cloud. Remaining open items are field validation
(spec §86), NOT security design: real-world BLE rate/latency tuning under
triggered crowds, and optional responder-grade authorization (D57).