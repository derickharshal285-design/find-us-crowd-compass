# ADR-009 — Versioned binary packet encoding

**Status:** Accepted

**Context (spec §23, §63 Block 6):** Packets cross platforms and devices with
different firmware; the encoding must be compact, deterministic, and forward
compatible enough to reject unknown versions safely.

**Decision:** Field-packed binary encoding with an explicit schema version
byte, transport-profile routing (§23, `docs/PROTOCOL.md`), and mandatory
round-trip tests `object → bytes → object`. Reference implementations:
`core/python/packet_v2.py` (56-bit payload, FEC, keyed MAC, BLE framing).
Unknown versions are rejected, not guessed.

**Consequences:** Human-readable formats (JSON) may be used for tools/logs but
not for the over-the-air packet model. Cross-language fixtures (Swift/Kotlin)
keep expected-hex checks in `tests/cross_language_test.py`.