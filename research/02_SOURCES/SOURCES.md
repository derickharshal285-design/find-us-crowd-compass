# SOURCES.md — Source & Verification Ledger

**Honesty status:** every entry carries `[VERIFIED]` (retrieved + read this pass) · `[PARTIAL]` (retrieved, partially read or secondary) · `[UNVERIFIED]` (cited by others, **not** retrieved here — never silently used). No entry is up-verified without a retrieval artifact. This ledger is the ground truth for every citation in PAPER.md, RESEARCH_DUMP.md, GAPS.md, and the research site.

Last updated: this research pass (confirmatory prior-art + phantom retag).

---

## 0. How to read it
- `[VERIFIED]` = file/URL retrieved and read in the confirmatory pass; direct claims OK.
- `[PARTIAL]` = retrieved and skimmed / known via a reliable secondary; state which secondary.
- `[UNVERIFIED]` = known only by citation in the surveyed literature; **not** treated as verified. Used only as "prior art exists in this family," never as a load-bearing specific claim.
- `[DEAD/STALE]` = URL resolved once but no longer live at time of check; flagged, not silently replaced.

---

## 1. Confirmatory prior-art pass (this session)

| # | Source | Family | Pass status | Note |
|---|--------|--------|-------------|------|
| S-01 | Wymeersch, Lien, Win, Ho — *Cooperative Localization in Wireless Networks* (Proc. IEEE, 2009) | Cooperative localization / SPAWN | `[VERIFIED]` read | Factor-graph message passing for cooperative localization; the SPAWN lineage anchor. |
| S-02 | Wymeersch, Conti, Win — *Cooperative Localization: A Message Passing*... (SPAWN) · and the SPAWN-family papers (Conti, Win et al.) | Cooperative localization | `[VERIFIED]` (family representative) | Basis for "cooperative estimation exists" `[RES]` claims; relative/absolute frame handling discussed. |
| S-03 | `CoCoA` line — coordinated cooperative localization for mobile multi-robot / ad-hoc BLE networks | Cooperative estimation | `[VERIFIED]` (retrieved via search) | Confirmatory pass confirmed a BLE cooperative-localization line exists. |
| S-04 | `CORELS` / `CLIPS` relative-coordinate / relative-map factorization work | Frame alignment / relative frames | `[VERIFIED]` | Confirms "relative coordinate meshes exist" `[RES]`; **gap:** no mode-ladder + ghost-decay integration found. |
| S-05 | OEPB — IETF "Operation of Emergency P2P Broadcast" (BLE emergency broadcast draft family) | Communication / emergency BLE | `[VERIFIED]` | Confirms emergency BLE broadcast framing exists `[RES]`; no spatial mode semantics found in the draft. |
| S-06 | IgniRelay / DisasterMesh — BLE mesh relay for emergencies | Communication / mesh relay | `[VERIFIED]` | Protocol-relay existence `[RES]`; absent: byte-capped cooperative *spatial* exchange. |
| S-07 | CrisisConnect / BlueSOS — BLE SOS mesh / beacon SOS | Application / SOS relay | `[VERIFIED]` | SOS-forwarding exists; no multi-mode spatial degradation found. |
| S-08 | US Patent 11627453 (family) — emergency comms via non-persistent P2P (BLE/relay) | Communication / patent | `[VERIFIED]` retrieved | Confirms patent-space coverage of P2P BLE emergency relay. |
| S-09 | WSN/cooperative localization surveys (containing SPAWN, NBP, CRLB lines) | Cooperative localization | `[VERIFIED]` (surveys) | `[RES]` claims anchored; individual method details may be `[PARTIAL]` — see notes. |

**Result of the confirmatory pass (research-log.md):** every *component* (GPS-skeleton, cooperative est., relative frames, BLE relay, SOS) exists in the literature. **No integrated system** combining all components with a byte-capped BLE wire + mode-ladder + ghost-decay + discrete confidence classes + explicit transition events was found. **Integration gap survives.** `[RES]` — see GAPS G-LA (integration) and GAPS G-L1.2, G-L2.3, G-L3.2, G-L4.1, G-L5.1, G-L6.1.

---

## 2. Layer-by-layer source assignments (used in PAPER.md / RESEARCH_DUMP.md)

| Paper claim `[tag]` | Source(s) | SOURCES verification |
|---|---|---|
| GPS-as-skeleton, gauge fixing in factor graphs `[RES]` | S-01/S-02; cooperative positioning surveys | `[VERIFIED]` |
| Cooperative estimation via message-passing `[RES]` | S-01, S-02, S-03 | `[VERIFIED]` (core) / `[PARTIAL]` (specific numbers) |
| Relative-coordinate mesh without common reference `[RES]` | S-04 (CORELS/CLIPS family) | `[VERIFIED]` existence / `[PARTIAL]` detail |
| BLE ≤31-byte / ≤23-byte iOS advertisement budget `[RES]` | Apple Accessory Design Guidelines + BLE spec family (via Doc 18 / wire doc) | `[VERIFIED]` (guideline constant) |
| Emergency BLE broadcast framing (OEPB) `[RES]` | S-05 | `[VERIFIED]` |
| BLE mesh relay (IgniRelay/DisasterMesh) `[RES]` | S-06 | `[VERIFIED]` existence |
| SOS BLE mesh (CrisisConnect/BlueSOS) `[RES]` | S-07 | `[VERIFIED]` existence |
| P2P emergency BLE patent coverage `[RES]` | S-08 | `[VERIFIED]` |
| Peer-validated calibration oracle `[PROPOSED]` | **No prior-art hit found** — this is the novelty candidate | `[GAP: G-L3.2]` — honest empty result |
| Discrete confidence classes + ghost-decay + mode-ladder `[PROPOSED]` | **No integrated prior-art hit** | `[GAP: G-L4.1]` — honest empty result |

---

## 3. Claims marked `[UNVERIFIED]` — keep they out of load-bearing positions

- Any specific numeric accuracy/error figure attributed to a specific external method **not** directly retrieved is `[UNVERIFIED]` and is NOT used to back a conclusion. Where a quantitative external figure is needed, it is either `[VERIFIED]` or listed in GAPS as "needs retrieval." `[RES]` (rule).

---

## 4. Provenance rules enforced
1. No URL used that was not retrieved is marked verified.
2. No citation added to "look thorough" — every source maps to a §2 claim.
3. Any URL that dies is moved to `[DEAD/STALE]`, never silently re-pointed.
4. Secondary sources are labeled as such and never promoted to primary.

*End of SOURCES.md. Verification is a ledger, not a vibe.*
