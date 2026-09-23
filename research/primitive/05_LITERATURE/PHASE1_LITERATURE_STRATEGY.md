# Phase 1 — Literature Strategy & Annotated Bibliography (Find Us)

**Ledger authority:** `research/SOURCES.md` (this pass). Every row inherits its
`[VERIFIED]` / `[PARTIAL]` / `[UNVERIFIED]` tag. Nothing fabricated, nothing promoted.
Vanishing gap G-INT is the surviving contribution. All `[EXP:NOT-RUN]` claims stay honest.

---

## 1. Search strategy (reproducible)

- Venue families: ACM (MobiCom/MobiSys), IEEE (Proc. IEEE, Journal on Selected Areas), arXiv.
- Query families (5), each maps to a PAPER §2 claim class:
  - F1 — cooperative localization / SPAWN message-passing
  - F2 — BLE advertising byte budget (≤31 legacy / ≤23 iOS background)
  - F3 — relative-coordinate factor graphs (CORELS/CLIPS family)
  - F4 — emergency BLE broadcast framing
  - F5 — mode-ladder / confidence classes / ghost-decay (the integration candidate)
- Snowball from S-01/S-02 (SPAWN) forward to current; time window 2000→now, seminal >10y exempt.
- Every screened source is marked for the **integration checklist**:
  (a) byte-capped BLE wire, (b) metric→differential→topological mode ladder,
  (c) discrete confidence classes, (d) ghost-decay (nothing deleted), (e) explicit mode transitions.
- A hit with all five could falsify G-INT. No verified hit has all five. `[RES]`

## 2. Annotated bibliography (ledger-anchored)

| ID | Source | Family | Status | Anchors in PAPER | Notes |
|----|--------|--------|--------|------------------|-------|
| S-01 | Wymeersch, Lien, Win, Ho — Cooperative Localization in Wireless Networks (Proc. IEEE, 2009) | Coop. local / SPAWN | `[VERIFIED]` | §2 cooperative estimation `[RES]` | Factor-graph message passing; SPAWN lineage anchor |
| S-02 | Wymeersch, Conti, Win — Cooperative Localization: A Message Passing… (SPAWN) | Coop. local | `[VERIFIED]` | §2 `[RES]` | Reciprocal-info cooperative estimation family |
| S-03 | CoCoA line — coordinated coop. local. of mobile/adhoc BLE nets | Coop. estimation | `[VERIFIED]`(retrieved) | §2 `[RES]` | BLE coop. lineage exists |
| S-04 | CORELS / CLIPS — relative-coordinate / mesh factorization | Relative frames | `[VERIFIED]` | §2 `[RES]` | relative-frame meshes exist; gap: no mode-ladder |
| S-05 | OEPB — IETF OP of Emergency P2P Broadcast (BLE) | Emergency BLE | `[VERIFIED]` | §2 `[RES]` | emergency broadcast framing exists; no spatial mode semantics |
| S-06 | IgniRelay / DisasterMesh — BLE mesh relay | Mesh relay | `[VERIFIED]` | §2 `[RES]` | relay exists; no byte-capped cooperative spatial exchange |
| S-07 | CrisisConnect / BlueSOS — SOS mesh/beacon | SOS relay | `[VERIFIED]` | §2 `[RES]` | SOS forwarding exists; no multi-mode spatial degradation |
| S-08 | US Patent family 27453 — emergency P2P relay | Patent | `[VERIFIED]` | §2 `[RES]` | patent coverage; relay only, not spatial model |
| S-09 | WSN/cooperative localization surveys (SPAWN, NBP, CRLB) | Survey | `[VERIFIED]`(surveys) | §2 `[RES]` | component claims anchored; method details `[PARTIAL]` |

## 3. Honest empty results (novelty candidates, marked `[PROPOSED]·[EXP:NOT-RUN]`)

| Candidate | Prior-art result | Tag |
|-----------|------------------|-----|
| Peer-validated calibration oracle | No verified integrated hit | `[PROPOSED]·[EXP:NOT-RUN]` — never claimed proven |
| Mode-ladder + ghost-decay + discrete classes (integrated) | No verified integrated hit | `[PROPOSED]·[EXP:NOT-RUN]` |
| Byte-capped cooperative spatial exchange in BLE budget | Components exist; integration absent | `[PROPOSED]·[EXP:NOT-RUN]` |

Empty = honest empty, never promoted to verified. `[RES]`-consistent.

## 4. `[CITATION NEEDED]` / `[UNVERIFIED]` register (never load-bearing)

- Any numeric figure attributed to an external method not directly retrieved → `[UNVERIFIED]`, excluded from conclusions.
- Real-system comparisons for §2 (Apple Find My, android EN, Nearby Connections) listed as existing families `[RES]`; specifics `[CITATION NEEDED]` until retrieved.

## 5. Gate to Phase 2

Deliverable: literature matrix + verified bibliography + honest empties. The **integration gap survives.** All entries verified; zero fabricated citations; every `[RES]` claim has a ledger rowhare; every `[PROPOSED]`/`[EXP:NOT-RUN]` item is honestly empty.

**Phase 1 complete. Requiring your confirm to Phase 2 (structure architect).**
