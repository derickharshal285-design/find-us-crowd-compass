# ADR-011 — Privacy / identity model (DECIDED)

**Status:** Decided — implemented in `core/security.py`
(`IncidentSession.pseudonym`, `EphemeralIdentityPool`), mirrored natively in
`android/` (Kotlin) and `ios/` (Swift).

**Context (spec §46, §72):** Graph keys must not be permanent personal
identities (§18). Peers need session linkage without a permanent identity
trail. Public beacon data must be minimized (§53).

**Decision:**
1. **Incident-scoped pseudonyms.** While joined to an incident, a device
   exposes only `pseudonym = base64url(HMAC-SHA256(install_key,
   "incident-pseudonym-v1" || 0x00 || incident_id)[:6])` — an 8-character id
   that is stable within one incident but **different across every incident**.
   All graph nodes, edges, and advertisements are keyed by the pseudonym;
   the install key never appears on the wire.
2. **No GPS/real identity on the wire.** No account, no personal identifier is
   written to the graph edge set. Physical direction is honest-only: a plain
   phone reports UNPROVEN (spec §53), never a fabricated bearing.
3. **Routine (non-incident) operation** uses `EphemeralIdentityPool`: a bounded
   rotating set of slot-derived ids so a reboot resumes the same rotation
   schedule and ids are not reused across rotations in a linkable way.
4. **Shared-link privacy boundary.** Every link holder can read the event id
   and MACs of an incident they are joined to — enforced by the same key that
   provides authentication (ADR-010). Outsiders cannot link a device across
   incidents because pseudonyms differ per incident.

**Implementation notes:** Native parity batteries re-certify pseudonym
stability (same install + same incident ⇒ same id; different incident ⇒
different id) on Android (`EngineSelfTest`) and iOS (`EngineParityTests`).

**Consequences:** Devices are join-able and route-able without tracking.
Remaining field items are UX-level (compass permission optional, manual
azimuth input), not identity design (spec §86).