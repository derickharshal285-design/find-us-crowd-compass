
> **RESEARCH-FIRST.** The single detailed paper (research/01_PAPER/01_manuscript.md) is the spine; the native build is its downstream artifact. Read the paper first.

# PROTOCOL

Packet/data model. Source: `docs/MASTER_SPEC.md` §22–24, §53–54, §65. The
packet design must be independent from UI code (§23).

## Design rules

- **Explicit schema versioning.** Binary protocol with version field; unknown
  versions are rejected, not guessed. Round-trip tests `object → bytes →
  object` are mandatory (spec §63 Block 6).
- **No assumed packet size.** The old "~28 useful bits" is not a protocol
  limit (spec §23). Transport has its own overhead; define an explicit
  **transport profile** per link:
  - legacy advertising: 31-byte limit;
  - Bluetooth 5 extended advertising: larger payloads;
  - connected GATT: MTU/attribute semantics.
- **Explicit optional fields (§65).** Unknown distance/direction are `null`
  with an `UNKNOWN` status, never `0`.
- **Every measurement carries timestamp + source.**
- **Transport abstraction (§64).** Core code never calls BLE APIs; it speaks
  `TransportInterface`. The simulator and the real radio both implement it.

## Candidate packet fields (§23)

- protocol version;
- message type;
- SOS/event ID;
- sender ephemeral node ID or relay token;
- origin/event sequence or version;
- hop/TTL;
- timestamp or short lifetime field;
- optional relationship metadata;
- optional local measurement metadata;
- authentication tag/signature (security model pending — spec §45 is RED).

These map to the reference implementation in `core/python/packet_v2.py`
(56-bit payload, FEC, keyed MAC, BLE framing) and the new `core/protocol.py`.

## Message types (initial set)

| Type | Purpose |
| --- | --- |
| HEARTBEAT | Presence / keepalive between peers |
| ADVERTISEMENT | Tiny broadcast of state (spec §24C) |
| SOS | Emergency event creation + periodic refresh |
| SOS_UPDATE | Versioned gradient update (new lower hop) |
| RELAY | Forwarded permitted packet (spec §24E) |
| RELATIONSHIP | Local spatial measurement exchange |
| CAPABILITY | Device capability profile (spec §54) |
| JOIN | Group join / private-group membership |

## SOS gradient rule (§22, §85)

1. Origin creates `SOS_ID`, `hop = 0`.
2. Connected neighbor learns `hop = 1`; nodes forward lower hops only.
3. `nextHops(v, s) = neighbors(v) with hop = hop(v) - 1`.
4. TTL/hop-limit bounds propagation; dedup by (SOS_ID, version) prevents
   repeated copies of the same update.
5. Version/sequence per SOS so old updates never overwrite newer ones.
6. Expiry removes stale SOS; multiple SOS events stay independent (§40).
7. A late responder learns the current gradient from the network (§14, §22.8).

## Benefits

| Problem | Protocol response |
| --- | --- |
| Duplicate flood (§42) | dedup cache keyed on (event ID, version) |
| Stale packets (§22.6) | TTL + expiry window |
| Replay (§45, §72) | version/sequence + auth tag (to design) |
| New node joins (§9) | JOIN/CAPABILITY exchange, edge created |
| Split/reconnect (§11–12) | heartbeat expiry drops edges; bridge edge reconnects components |

## Public vs private information (§53)

- Public beacon: anonymous role, presence, emergency gradient subset.
- Private group data (join code, members, group-only messages): only inside the
  group key. See `core/python/find_group.py` (JoinCode → PBKDF2 key) for the
  current group params.

## Security status (honest)

Security model is **RED / not solved** (spec §60, §45). The current
`relay/relay_node.py` still has a hardcoded SESSION_KEY placeholder. No
production authentication, replay protection, or malicious-relay resistance
is claimed yet. These are research questions D51–D62 in
`docs/RESEARCH_QUESTIONS.md`.