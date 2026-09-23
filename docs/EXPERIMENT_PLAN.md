
> **RESEARCH-FIRST.** The single detailed paper (research/01_PAPER/01_manuscript.md) is the spine; the native build is its downstream artifact. Read the paper first.

# EXPERIMENT PLAN

Source: `docs/MASTER_SPEC.md` §56–59, §74, §77, §79. Two tracks: simulation
first (no hardware), then staged real devices. Never present simulator accuracy
as real-world accuracy (§77).

## 2026-09 — TTL & signal-expiry parameter plan (required before Block 10/11)

Spec §37 says hop limits and expiry "must be experimentally determined." Our
placeholders (TTL=8, node/edge 30s/120s, SOS lifespan 900s) are NOT facts.
This plan fixes the numbers with simulation evidence first, then real devices.

### How to re-run the sweep

```bash
PYTHONPATH=core python3 -m core.simulation --sweep
```

### Rule set (the invariants the parameters must respect)

1. Wireless topology = what is actually heard now + relationship memory
   (§23): keep recent relationships briefly, expire if truly absent.
2. Topology truth beats grace: when absence is *confirmed* (user left range,
   relay gone), the route dies immediately — grace never covers a confirmed
   disconnect.
3. Device liveness ≠ edge liveness: an in-range silent device can stay
   ACTIVE while its stale edges (only touched on real signal) age out.
4. Devices that keep signaling must never age out (liveness guard).
5. TTL bounds hop depth, so a crowd of diameter D hops needs TTL ≥ D for
   full coverage (§22.6). TTL is carried on the wire from the event (§23).

### Evidence (simulation, `core/simulation.py --sweep`, deterministic)

**A. Hop budget (TTL) — 14-node chain, SOS at n0 (worst-case depth = 13):**

| TTL | coverage | max hop |
|-----|----------|---------|
| 3   | 0.286    | 3       |
| 5   | 0.429    | 5       |
| 6   | 0.500    | 6       |
| 7   | 0.571    | 7       |
| 8   | 0.643    | 8       |
| 10  | 0.786    | 10      |
| 12  | 0.929    | 12      |
| 13  | 1.000    | 13      |

Coverage = (TTL+1)/N exactly; full coverage needs TTL ≥ crowd diameter in
hops. **Plan:** default TTL=8 covers ≤8-hop crowds (typical dense venue);
configure TTL per-event for deeper crowds. Choose TTL ≥ expected crowd
diameter; there is no benefit above diameter.

**B. Signal expiry — route vs device, seconds after B goes silent:**

| stale | hard | route gone | STALE@ | EXPIRED@ | grace reconnect |
|-------|------|-----------|--------|----------|-----------------|
| 15    | 30   | 1.0 (immediate) | 16 | 31 | True |
| 30    | 60   | 1.0 (immediate) | 31 | 61 | True |
| 30    | 120  | 1.0 (immediate) | 31 | 121| True |
| 60    | 180  | 1.0 (immediate) | 61 | 181| True |
| 120   | 300  | 1.0 (immediate) | 121| 301| True |

Topology dies the moment absence is confirmed; the device lingers until hard
expiry = relationship memory (§23) without ghost routes. A peer returning
inside the stale window reconnects instantly. STALE/EXPIRED track the
configured windows ±1s (1s sim tick).

**C. Liveness guard:** 6 nodes signaling continuously still ACTIVE after 140s
(> node_expire_after=120). Fix: radio contact now refreshes node/edge
lifecycles (`core/simulation.py`: `_sync_links` touch + delivery touch).
Previously every node aged out in >120s meshes even while relaying — lifecycle
did not follow real signal.

### Working defaults to validate on real devices (Block 11, §58 step 1–2)

- TTL = 8 default (raise per-event); *field:* measure real multi-hop depth.
- edge stale 30s / edge hard 60s; node stale 30s / node hard 120s.
- SOS lifespan 900s (15 min), renew by origin §34; *field:* responder
  mission timing + rescue-state renewal policy.

### Open items (stay OPEN, do not fake)

- Real BLE discovery latency vs these aging windows (12–30s background load).
- Whether confirmed-absence is reliably detectable on iOS/Android or only
  inferred (affects rule 2 implementability).
- Authenticated TTL/expiry (ADR-010) — a malicious relay can lie about TTL.

## Track 1 — Simulation (authored in `core/simulation.py`)

The simulator represents nodes, 2D positions (optional 3D/floor), range,
packet loss, mobility, discovery latency, RSSI noise, directional measurement
error, join/leave, split/merge, SOS creation, hop propagation, relay policies,
battery cost, attacker behavior (§56).

### Mandatory scenarios (§57)

1. Two nodes close together.
2. Nodes move apart.
3. One relay.
4. Multiple relays.
5. A relay disappears.
6. A new node joins.
7. A group splits.
8. Two groups reconnect.
9. Anchor disappears.
10. SOS from a node deep inside the network.
11. Responder joins later.
12. Multiple possible paths to SOS.
13. Relay storm.
14. Packet loss.
15. Very dense crowd.
16. Sparse crowd.
17. Moving crowd.
18. Multiple SOS events.
19. Multi-floor environment.
20. Malicious relay.
21. False SOS.
22. Replay attack.
23. High RSSI noise.
24. Dead-reckoning drift.
25. No directional sensor available.

### First graph tests (§84) — must run with no radio hardware

- **A** Add nodes and edges.
- **B** Remove a node and ensure unrelated edges survive.
- **C** Split one graph into two components.
- **D** Reconnect two components.
- **E** Create an SOS at a node.
- **F** Compute hop 0/1/2/3/….
- **G** Remove the shortest-path relay and ensure the route changes.
- **H** Add a new node after the SOS exists; confirm it learns the current
  gradient.
- **I** Run two SOS events simultaneously.
- **J** Expire an old SOS.
- **K** Flood a dense graph and measure duplicate suppression.
- **L** Simulate packet loss.

### Metrics to record (§59)

- Communication: peer discovery time, delivery rate, relay latency, end-to-end
  delivery probability, duplicate ratio, packet loss, storm rate.
- Network: component size, path availability, reconnection time, graph
  stability.
- Emergency: SOS propagation time, % reachable recipients, responder discovery
  time, time-to-lower-hop route, false route rate.
- Spatial: distance error, angular error, graph position error, drift, floor
  error.
- Energy: battery/min, duty cycle, relay cost, emergency-mode cost.
- UX: time to understand instruction, time to find target, wrong-direction
  events, confusion rate.

### Baseline success criteria (§79)

Early milestone — a small group of real phones can discover one another,
exchange small messages, relay SOS across multiple hops, recover from at least
one relay disappearing, let a late responder join, and compute correct logical
hop relationships to the SOS.

## Track 2 — Real devices (§58)

Scaling rule, start small; never jump from a five-phone demo to stadium claims:

1. **Two phones** — discovery latency, BLE range, packet delivery, battery.
2. **Three phones** — `A → B → C`: does app-level relay work?
3. **Five phones** — dynamic topology.
4. **Ten phones** — collision/relay behavior.
5. **20+ phones** — density and battery.
6. **Moving participants** — walk while relaying.
7. **Dense human obstruction** — bodies between devices.
8. **Indoor multi-room** — walls/partitions.
9. **Multi-floor** — stairs/floors.
10. **Controlled crowded event** — closest real approximation of the target.

## Track 3 — Navigation/spatial experiments (later phases, §78)

- Spatial experiments: local measurements + IMU.
- Direction research on supported technologies.
- Terminal guidance experiments: UWB / BLE direction / acoustic / optical.

## Failure modes to inject during both tracks (§74)

Bluetooth disabled; permissions denied; background process killed; low battery;
phone reboot; random identifier changes; device/relay leaves; network
partitions; packet corruption/duplication/replay; fake SOS; malicious relay;
crowded RF; body blocking; multi-floor; poor compass calibration; IMU drift;
UWB/terminal sensor unavailable; target screen off / backgrounded /
mic+speaker blocked; late responder.