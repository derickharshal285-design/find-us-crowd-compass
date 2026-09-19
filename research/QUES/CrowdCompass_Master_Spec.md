# CROWD COMPASS — MASTER PROJECT SPECIFICATION & RESEARCH/BLOCK PLAN

## 0. Purpose of this document

This document is the current master handoff for the Crowd Compass project.

It is written so an AI coding agent (such as OpenCode) can understand:

- what the project is trying to solve;
- what has already been conceptually figured out;
- what has NOT been proven;
- the core mathematical model we are currently considering;
- the problems that caused the original design to become complicated;
- the proposed fixes for those problems;
- the feature/system layers we intend to build;
- the research questions that must be answered before claiming feasibility;
- the base software blocks that can be built now without pretending the unresolved algorithms are solved;
- the experiments and simulations required to validate the system.

IMPORTANT: This is a research-and-build specification, not a claim that all of these mechanisms work in real crowds yet. Any item marked CONCEPTUAL, RESEARCH, or UNVERIFIED must not be represented in the UI or documentation as scientifically proven.

---

# 1. PROJECT IN ONE SENTENCE

Crowd Compass is a phone-first offline emergency discovery and navigation system for dense crowds that uses phones already present in the crowd to create a dynamic peer-to-peer communication/network graph, propagate emergency information without depending on the internet, and eventually guide a responder toward an emergency target without requiring a permanent global GPS-style coordinate anchor.

The project should use existing phone infrastructure first and allow dedicated infrastructure or stronger sensing to be added later as optional augmentation.

---

# 2. THE CENTRAL DESIGN PHILOSOPHY

The project should be built around these principles:

1. Phone-first.
   Use the hardware people already carry before requiring dedicated infrastructure.

2. No mandatory permanent anchor phone.
   The system should not collapse if one device moves, disconnects, dies, or leaves.

3. Local information first.
   A phone only needs to know what it can actually measure about nearby phones; larger relationships are derived from the graph.

4. Dynamic graph, not a static map.
   Phones may appear, move, disappear, split the network, reconnect, and change relationships.

5. Communication and spatial reasoning are separate layers.
   A communication path does not automatically equal a physical distance map.

6. Emergency navigation should not require a perfect global coordinate map.
   A temporary SOS-centered network gradient may be sufficient for some navigation stages.

7. Graceful degradation.
   Losing a sensor, relay, or some nodes should reduce precision rather than instantly destroy the system.

8. Research before overengineering.
   Do not build elaborate sensor fusion or AI before proving the basic graph, relay, and emergency logic.

9. No fake claims.
   Do not claim “accurate indoor positioning”, “safe navigation”, “works in any crowd”, “exact location”, “GPS replacement”, or any similar claim unless experiments actually establish the relevant metric.

---

# 3. WHAT CROWD COMPASS IS NOT

The current architecture is not supposed to be:

- a normal internet-based location sharing app;
- a permanent GPS replacement;
- a simple chat application;
- a system where one phone is always the global master anchor;
- a system that assumes RSSI is an accurate distance meter;
- a system that assumes Bluetooth hop count equals physical distance;
- a system that assumes every smartphone exposes Bluetooth direction finding;
- a system that assumes Android and iOS provide identical background BLE behavior;
- a system that requires all users to be in the same friend group.

---

# 4. ORIGINAL CORE PROBLEM

The original problem was not really “how do phones communicate?”.

Bluetooth/BLE can provide nearby-device communication and discovery mechanisms. The difficult problem was spatial meaning.

The basic problem statement is:

> Multiple phones can communicate locally, but there is no automatic common spatial coordinate system shared by every phone in a dynamic crowd. A system must determine how local relationships between phones can be represented, propagated, updated, joined, removed, and used to locate or navigate toward an emergency target.

This led to several specific core problems.

---

# 5. CORE PROBLEM 1 — INDEPENDENT COORDINATE SYSTEMS

## Problem

Each phone can theoretically maintain a local coordinate system. A phone could choose itself as `(0,0)`, but another phone can also choose itself as `(0,0)`.

Therefore, two independent coordinate frames do not automatically refer to the same physical space.

Questions:

- How does a new device discover the coordinate frame of an existing graph?
- Can two independent local coordinate systems be related using a small number of local measurements?
- What minimum information is required to translate one local frame into another?
- Do we actually need to merge coordinate frames at all for emergency navigation?

## Basic conceptual fix

Represent the system primarily as a graph of relative relationships rather than forcing every phone to share one permanent origin.

A relationship can be expressed as local spatial information between two nodes.

Conceptually:

`A -> B = relative relationship`

Multiple relationships can be composed:

`A -> B + B -> C = A -> C`

For vector relationships in a shared frame, vector addition is the basic operation. However, the implementation must explicitly handle the fact that local phone orientation/frames may differ. Do not simply add raw phone-local vectors until the frame transformation problem is solved.

STATUS: CONCEPTUAL FOUNDATION — NOT YET VALIDATED.

---

# 6. CORE PROBLEM 2 — DISTANCE/SPATIAL INFORMATION DOES NOT AUTOMATICALLY TRAVEL THROUGH THE MESH

## Problem

A message can travel across multiple relays:

`A -> B -> C -> D -> E`

but E does not automatically know the physical relationship between E and A merely because the packet arrived through those relays.

Communication path length and physical distance are different quantities.

## Basic conceptual fix

Every local relationship can be considered graph information.

If the relevant spatial relationships can be represented in a compatible mathematical form, the system can compose them:

`A -> C = (A -> B) + (B -> C)`

and so on through longer paths.

This led to the concept of a **relationship graph**.

A relationship edge may eventually contain:

- distance estimate or distance class;
- bearing/direction estimate if available;
- measurement timestamp;
- age/expiry;
- movement/change information;
- source/measurement method;
- optional quality metadata.

STATUS: CONCEPTUAL — THE COMPOSITION MATH IS SIMPLE; THE REAL-WORLD MEASUREMENT QUALITY AND FRAME ALIGNMENT ARE NOT SOLVED.

---

# 7. CORE PROBLEM 3 — THE ANCHOR PHONE CAN MOVE

## Problem

A single anchor-based model creates a moving-reference problem.

If one phone is `(0,0)` and all other positions are interpreted relative to it, then movement of that anchor changes the reference for everything else.

## Basic conceptual fix

Do not make one device the permanent source of truth.

Use relationships between nodes as the primary structural information.

An anchor can still be used as a temporary local reference when helpful, but the architecture should not depend on one permanent anchor.

STATUS: CONCEPTUALLY ADDRESSED, NOT FULLY VALIDATED.

---

# 8. CORE PROBLEM 4 — THE ANCHOR PHONE CAN DISAPPEAR

## Problem

If all coordinates depend on one anchor and the anchor disappears, the graph may lose its reference.

## Basic conceptual fix

Use distributed relationships rather than one mandatory anchor.

If an anchor disappears, its node and incident edges may disappear, while relationships among remaining nodes can continue to exist.

The system should be able to recompute or continue from the connected graph that remains.

STATUS: CONCEPTUAL.

---

# 9. CORE PROBLEM 5 — A NEW PERSON JOINS

## Problem

A phone entering the network later has no knowledge of the coordinate frame or relationship graph that existed before it arrived.

The new phone cannot assume that its local `(0,0)` has the same meaning as the existing group's `(0,0)`.

## Basic conceptual fix

Establish at least one known relationship between the new phone and the existing graph.

Conceptually:

`New phone -> known node`

Once that edge is established, the new phone becomes a node in the same graph.

The deeper research question is how much information must be exchanged before the new node can understand enough of the existing graph to participate in navigation.

STATUS: BASIC LOGIC CLEAR; COMPLETE MATHEMATICAL FRAME-MERGING PROCESS UNRESOLVED.

---

# 10. CORE PROBLEM 6 — PEOPLE LEAVE

## Problem

People move away, turn devices off, lose radio visibility, or leave the venue. Therefore graph edges and nodes are not permanent.

## Basic conceptual fix

Treat the topology as dynamic.

A relationship has a lifetime:

`created -> updated -> becomes stale -> expires`

Do not instantly erase information when one advertisement is missed.

Use timestamps and expiry/aging to prevent the graph from becoming unstable while still removing obsolete relationships.

STATUS: GOOD SOFTWARE MODEL; PHYSICAL BEHAVIOR NEEDS TESTING.

---

# 11. CORE PROBLEM 7 — THE NETWORK SPLITS

## Problem

The crowd may separate into disconnected groups.

There may temporarily be no communication path between the groups.

## Basic conceptual fix

Represent each connected component independently.

When disconnected:

- each component maintains its own current graph;
- information cannot magically cross the gap;
- the system records that the components are disconnected.

When a new connection appears:

- that edge becomes a bridge;
- information can propagate again;
- graph information can be reconciled.

STATUS: CONCEPTUAL.

---

# 12. CORE PROBLEM 8 — TWO PREVIOUSLY SEPARATE GROUPS MEET

## Problem

Two groups may have unrelated coordinate origins and unrelated graph histories.

## Basic conceptual fix

Create a new measured relationship between a node in one group and a node in the other.

That edge becomes a bridge between the graphs.

The major research question is how to merge or translate the two spatial frames without introducing an incorrect global map.

STATUS: BASIC GRAPH BRIDGING IS CLEAR; ROBUST SPATIAL FRAME MERGING IS UNRESOLVED.

---

# 13. CORE PROBLEM 9 — SOS EXISTS BUT RESPONDER IS OUTSIDE THE PRIVATE GROUP

## Problem

A group can understand its own local relationships, but an emergency responder may enter later and not know:

- the original anchor;
- the group's coordinate origin;
- the original group members;
- the group's entire spatial map.

Therefore the SOS cannot depend entirely on private group state.

## Basic conceptual fix

Make the emergency event itself a temporary logical reference.

Each SOS has a unique identifier.

The SOS target is assigned:

`Hop = 0`

Devices that can directly participate in the emergency propagation become progressively higher-hop nodes.

Conceptually:

`SOS = 0`

`near emergency network = 1`

`next network layer = 2`

`next layer = 3`

and so on.

STATUS: CONCEPTUALLY STRONG; NETWORK AND PHYSICAL NAVIGATION MUST STILL BE CONNECTED.

---

# 14. CORE PROBLEM 10 — RESPONDER ENTERS LATE

## Problem

The responder was not present when the emergency graph formed.

## Basic conceptual fix

The responder should not need the original global anchor.

The responder joins the currently visible network, learns the SOS gradient, and determines how it relates to the SOS from the nodes it can currently observe/reach.

The basic logical navigation target is:

`higher hop -> lower hop -> ... -> Hop 0`

STATUS: CONCEPTUAL. PHYSICAL DIRECTION TO A LOWER-HOP NODE IS NOT YET SOLVED.

---

# 15. CORE PROBLEM 11 — HOP COUNT IS NOT PHYSICAL DISTANCE

This must be permanently documented because it is easy to misunderstand.

A hop count means:

> how many network relationships away from the SOS.

It does NOT automatically mean:

> how many metres away from the SOS.

Therefore:

`Hop = topology`

`Distance = physical measurement`

These must remain separate concepts.

STATUS: RESOLVED AS A CONCEPTUAL DISTINCTION.

---

# 16. CORE PROBLEM 12 — HOP COUNT DOES NOT AUTOMATICALLY GIVE WALKING DIRECTION

## Problem

Knowing that another node is one hop closer to the SOS does not tell a human responder whether to walk north, south, left, right, upstairs, etc.

## Current direction of research

The system should eventually combine:

- emergency topology (which node/relationship is closer to SOS);
- local physical direction information (where that neighbor physically is);
- local movement/orientation sensing;
- optional stronger ranging/direction technologies on compatible devices.

This is now the most important unresolved bridge between network navigation and physical navigation.

STATUS: NOT SOLVED.

---

# 17. CURRENT ARCHITECTURAL PIVOT: RELATIONSHIP GRAPH + SOS GRADIENT

The current preferred conceptual architecture is hybrid rather than purely coordinate-based or purely hop-based.

### Layer 1 — Dynamic communication graph
Who can currently communicate with whom?

### Layer 2 — Local spatial relationships
What is the local spatial relationship between nearby nodes, if it can be measured?

### Layer 3 — Emergency gradient
How many network steps separate a node from a specific SOS?

### Layer 4 — Local physical guidance
Which physical direction should the responder move to reach a lower-hop route?

### Layer 5 — Terminal target finding
Once near the target, how do we identify the actual person/device?

This layered design keeps one system from having to solve every problem simultaneously.

---

# 18. THE DYNAMIC GRAPH MODEL

Represent the network as:

`G = (V, E)`

where:

- `V` = phones/nodes;
- `E` = current relationships/communication links.

Each edge may later contain:

`E(u,v) = {communication, spatial_measurement, direction, timestamp, expiry, source}`

The exact data structure should remain modular so that a missing measurement does not prevent the communication graph from functioning.

Nodes should use privacy-preserving ephemeral identifiers rather than exposing permanent personal identity as the graph key.

---

# 19. GRAPH LIFECYCLE

Every node/edge should have a lifecycle.

### Node

`DISCOVERED -> ACTIVE -> STALE -> EXPIRED`

### Edge

`SEEN -> ACTIVE -> AGING -> EXPIRED`

A missed scan result should not automatically mean “person gone”.

Use configurable timeouts.

The simulation must allow these parameters to vary.

---

# 20. RELATIONSHIP AGING

Every relationship should have a timestamp.

Conceptually:

`relationship_value + time_of_measurement`

An old relationship should carry less operational relevance than a recent one.

Possible future implementation:

- age in milliseconds/seconds;
- soft expiry;
- hard expiry;
- refresh interval;
- last successful bidirectional exchange.

Do not use arbitrary values without experiments.

---

# 21. MULTI-PATH GRAPH

Do not build the emergency system around a single route.

If multiple paths exist, the graph should be able to represent them.

This helps when one relay disappears.

Research question:

- How many alternate paths should be maintained?
- Is a full routing tree needed, or is a parent/next-hop set enough?
- How do we avoid keeping too much state?

---

# 22. BASIC SOS GRADIENT LOGIC

For each SOS, the conceptual algorithm is:

1. SOS origin creates `SOS_ID`.
2. Origin has `hop = 0`.
3. A newly connected neighbor learns `hop = 1`.
4. A node that receives a better hop value may update its current route.
5. A node may propagate a new lower hop to neighbors.
6. TTL and expiry prevent infinite propagation.
7. Duplicate suppression prevents repeated copies of the same emergency update.
8. Responder joining later can learn the current gradient from the network.

Possible algorithmic base:

- BFS-style hop propagation over the app-level communication graph.
- Sequence number/version per SOS so older updates do not overwrite newer ones.
- TTL/hop limit for bounded propagation.
- Multiple equal-cost next hops can optionally be retained.

STATUS: EASY TO SIMULATE. REAL RADIO IMPLEMENTATION UNPROVEN.

---

# 23. RELAY PACKET MODEL

A packet must be designed independently from UI code.

Candidate fields:

- protocol version;
- message type;
- SOS/event ID;
- sender ephemeral node ID or relay token;
- origin/event sequence or version;
- hop/TTL;
- timestamp or short lifetime field;
- optional relationship metadata;
- optional local measurement metadata;
- authentication tag/signature depending on security design.

The old idea of approximately “28 useful bits” is NOT an established protocol limit.

Do not hardcode 28 bits as a Bluetooth maximum.

Bluetooth LE advertising and connected transports have their own protocol overhead and different capacity characteristics. Legacy advertising data is limited to 31 bytes; Bluetooth 5 extended advertising can carry larger advertising payloads, while connected transports have different MTU/attribute constraints. Therefore, the protocol needs an explicit transport profile rather than one assumed packet size.

Bluetooth SIG documentation confirms legacy advertising at 31 octets and extended advertising support for larger host data, while Android GATT behavior has its own MTU semantics. These details must be treated as transport-level constraints, not application payload assumptions.

---

# 24. BLUETOOTH SYSTEM — WHAT WE ACTUALLY NEED

The Bluetooth subsystem should be split into:

### A. Discovery
Find nearby Crowd Compass devices.

### B. Identity
Map a discovered radio interaction to an application-level ephemeral peer ID.

### C. Advertisement
Broadcast tiny state/heartbeat/emergency information.

### D. Connection
Establish an optional GATT connection when larger or more reliable data exchange is required.

### E. Relay
Forward permitted packets.

### F. Deduplication
Reject repeated message IDs/versions.

### G. Time-to-live
Stop stale packets from propagating forever.

### H. Peer state
Track last seen, link status, capabilities, and expiry.

### I. Transport abstraction
Keep BLE-specific code separate from graph/navigation code.

---

# 25. BLUETOOTH RESEARCH QUESTIONS

These are mandatory research questions, not assumed answers.

## Discovery

- Can Android reliably advertise and scan simultaneously for the required pattern?
- What happens under high device density?
- How many unique peers can realistically be tracked?
- How fast can a peer be discovered?
- What is the discovery latency in foreground and background?
- Can iOS participate in the same low-level application protocol with equivalent behavior?
- How are device IDs represented without relying on stable MAC addresses?
- What happens when MAC/randomized addresses rotate?

## Background operation

- What Android service model is required for continuous operation?
- What permissions are required on current Android versions?
- What foreground-service restrictions apply?
- How much background throttling occurs?
- What happens when the screen is off?
- What happens when the app is backgrounded for long periods?
- How do OEM battery optimizers affect scanning/advertising?
- What does iOS allow for background central/peripheral behavior?
- How does iOS background coalescing affect discovery latency?
- Can an SOS emergency mode justify/trigger the required background behavior under platform rules?

Current official platform documentation confirms that modern Android versions require specific Bluetooth permissions for scanning, advertising, and connecting, and that Android background behavior has additional restrictions. Apple Core Bluetooth provides background modes but changes behavior in the background, so the iOS design must be tested rather than assumed to be equivalent to Android. 

## Packet transport

- Which information belongs in advertising?
- Which information requires a connected channel?
- What is the smallest practical SOS packet?
- How much overhead exists after encoding?
- Should data use bit fields, CBOR, protobuf, custom binary, or another format?
- Can the same binary protocol be carried over both advertising and GATT?
- How does fragmentation affect reliability?
- What is the retransmission behavior?

## Range

- What is realistic phone-to-phone BLE range in an empty room?
- What is realistic range indoors?
- What happens in a dense crowd?
- How much attenuation is caused by bodies between phones?
- How does phone orientation affect range?
- What does 1M vs coded PHY change on real devices?
- Which phones support which PHYs?
- Does longer range actually help relay density or make collisions worse?

## Relay behavior

- Should every phone relay?
- How do we select relay candidates?
- What is the best forwarding delay?
- How do we detect duplicates?
- How large should the recent-message cache be?
- How long should cached messages live?
- How should nodes behave when many peers are nearby?
- How do we prevent relay storms?
- How do we prevent one malicious device from exhausting relay capacity?

---

# 26. BLUETOOTH DIRECTION FINDING RESEARCH

Bluetooth Direction Finding defines AoA and AoD methods for determining signal direction. It depends on antenna arrangements and device capabilities; it must not be assumed that a normal smartphone exposes usable AoA/AoD measurements to a third-party app.

Research every target phone model.

Questions:

- Which smartphones in our target deployment expose Bluetooth direction-finding hardware?
- Does the OS expose the relevant measurements to third-party apps?
- Is raw CTE/IQ data available?
- Can a phone act as the required receiving antenna array?
- Can a normal phone act as an AoD transmitter?
- Does a commercial smartphone with multiple antennas actually expose enough information?
- What is the angular accuracy in a crowd?
- How does body blocking affect it?
- How does phone orientation affect it?
- Does the camera/phone orientation need to be constrained?
- Could direction finding be an optional premium capability rather than a core requirement?

Bluetooth SIG documentation describes AoA as using a multi-antenna receiving array and AoD as using a multi-antenna transmitting array, making smartphone hardware/API availability a major feasibility question rather than a guaranteed capability.

---

# 27. UWB RESEARCH OPTION

UWB should be investigated as an optional high-precision local layer, not assumed as a universal requirement.

Apple's current Nearby Interaction documentation supports peer distance and direction on supported UWB devices, with device capability checks and environmental/line-of-sight limitations. This makes UWB potentially valuable for supported devices, but it is not a substitute for a universal phone-first BLE layer.

Research questions:

- Which Android phones support usable UWB APIs?
- Which iPhones support UWB and direction measurement?
- Can Android and iOS devices share a common application-level session identifier?
- Can UWB be used only near the responder/target?
- What happens when one or both devices lack UWB?
- What is the real indoor/crowd range?
- Is the power cost acceptable?
- Can UWB become the optional high-precision terminal layer?

---

# 28. WIFI-BASED AUGMENTATION

Investigate Wi-Fi Aware/Wi-Fi Direct/local networking as an optional higher-throughput layer.

Android documentation describes Wi-Fi Aware as allowing nearby Android devices to discover and connect directly without an access point, with device/system capabilities determining behavior.

Research questions:

- Which target Android phones support Wi-Fi Aware?
- Can it coexist with BLE scanning/advertising?
- Is it power-efficient enough for emergencies?
- Can it be used after BLE discovery for richer data transfer?
- Can it work when normal Wi-Fi internet is unavailable?
- What is the iOS interoperability story?
- Is Wi-Fi Direct useful for Android-only high-bandwidth links?
- Could it carry graph snapshots while BLE carries tiny beacons?

This should remain optional.

---

# 29. COMMUNICATION MODES TO INVESTIGATE

The protocol should support a hierarchy rather than one transport.

### Mode 1 — BLE tiny broadcast
For:

- discovery;
- heartbeat;
- emergency beacon;
- tiny graph updates;
- hop gradient.

### Mode 2 — BLE connected exchange
For:

- larger graph chunks;
- synchronization;
- acknowledgements;
- capability exchange.

### Mode 3 — Wi-Fi local peer link
For:

- higher-volume synchronization;
- optional map snapshots;
- data exchange when supported.

### Mode 4 — Internet/backend
Optional when the internet exists.

### Mode 5 — SMS fallback
Research whether a compact emergency message can be handed to normal cellular SMS when available.

The architecture should not make the internet mandatory.

---

# 30. SPATIAL RELATIONSHIP ENGINE

Create a pure domain module independent of Bluetooth.

Responsibilities:

- store local relationships;
- update measurements;
- timestamp them;
- age them;
- expire them;
- compose compatible relationships;
- detect inconsistent relationships;
- generate local graph snapshots;
- expose data to simulation and UI.

Potential data model:

`Node`
- ephemeralId
- capabilities
- firstSeen
- lastSeen
- state

`Edge`
- nodeA
- nodeB
- communicationState
- distanceEstimate? 
- distanceClass?
- bearing?
- verticalEstimate?
- timestamp
- expiry
- source

Do not force all fields to exist. Missing physical information should be represented explicitly.

---

# 31. VECTOR/RELATIVE MAP RESEARCH QUESTIONS

The old vector idea remains useful as a research layer.

Questions:

- What exactly is the vector frame for each measurement?
- How are phone-local orientation frames transformed into a graph frame?
- Can orientation be aligned with magnetometer + gyroscope?
- Can relative bearing be expressed without a global compass?
- How is the 180°/yaw ambiguity handled?
- How are noisy distance estimates accumulated?
- How does error grow along a long chain?
- What happens when there are multiple paths that imply different positions?
- Can the graph solve a least-squares relative localization problem?
- Can anchor-free graph optimization recover a stable local map?
- Can the map be continuously updated without massive recomputation?
- What is the minimum graph size required for useful geometry?
- How do we detect when the geometry is underconstrained?

The vector map is a research capability, not the current mandatory emergency navigation method.

---

# 32. RSSI / “WATERBAG” PROBLEM

The project identified a major real-world issue:

Human bodies and the crowd can strongly alter 2.4 GHz signal propagation.

Therefore raw RSSI should not be treated as exact distance.

Research questions:

- How much RSSI changes when one body blocks the line of sight?
- How much does device orientation matter?
- Can RSSI at least classify near/mid/far?
- Can temporal smoothing help?
- Can repeated observations improve a relative distance estimate?
- Can multiple phones reduce ambiguity?
- Is RSSI useful only for local ranking rather than metric distance?
- Can calibration be event-specific?

Potential design rule:

`RSSI = supporting signal, not unquestioned ground truth.`

---

# 33. DEAD RECKONING / PHONE IMU

Investigate use of:

- accelerometer;
- gyroscope;
- magnetometer/compass;
- rotation vector;
- step detection;
- device orientation;
- optional barometer for vertical information where available.

Basic idea:

Start from a known local state, detect movement, estimate displacement/orientation, and update a local position estimate.

Research questions:

- What is the drift over 5 seconds, 10 seconds, 30 seconds, 1 minute?
- Is the user walking, standing, running, or holding the phone differently?
- Can step-based PDR work better than double-integrating raw acceleration?
- Can direction be estimated reliably while the phone is in a pocket?
- What happens when the user rotates their body but not the phone?
- Can external graph relationships reset inertial drift?
- Can graph constraints correct local drift?

Dead reckoning should be an auxiliary signal, not an unquestioned absolute position.

---

# 34. INERTIAL TRUST / STATIC NODES IDEA

A proposed idea was to identify relatively stationary phones as useful temporary structural references.

Concept:

- Phones with low measured movement can become temporary stable reference nodes.
- Highly moving phones are treated as more dynamic.
- The graph may use stationary nodes to reduce drift in local relative calculations.

Research questions:

- How accurately can the system classify stationary vs moving?
- What is the best time window?
- Does using static phones actually stabilize a graph?
- Does this merely reintroduce an anchor problem under another name?
- Can several static nodes be used together instead of one elected anchor?
- Is the computational complexity worth the improvement?

STATUS: RESEARCH IDEA ONLY.

---

# 35. MAGNETIC FINGERPRINTING IDEA

Concept:

Phones sample local magnetic-field signatures caused by structural steel, speakers, electrical infrastructure, and other local features.

Phones could potentially compare these signatures to infer whether they are in the same spatial region.

Research questions:

- Are signatures stable long enough to be useful?
- How unique are nearby locations?
- How much does phone model/calibration alter measurements?
- Can two different devices compare magnetometer readings meaningfully?
- How much does the human body affect the reading?
- How much do loudspeakers and electrical loads change the field?
- Can signatures be normalized across devices?
- Does a venue produce a useful fingerprint map?

STATUS: RESEARCH ONLY.

---

# 36. VERTICAL / Z-AXIS PROBLEM

A 2D map can fail in multi-level venues.

Potential cases:

- one floor above another;
- stadium tiers;
- underground/subway areas;
- multilevel clubs;
- staircases and ramps;
- balconies.

A device may be physically close in 3D but separated by a floor or wall.

Research questions:

- Can phone barometers detect relative floor changes?
- Can elevation change be inferred from pressure differences?
- Can topology distinguish “above/below” from “nearby”? 
- Can venue floor plans be optionally incorporated?
- Can a responder be told that the correct route is a staircase rather than a straight line?
- How do we prevent the system from directing someone through a wall/floor?
- Should the graph have a discrete `level/floor` concept instead of purely continuous Z?

Potential model:

`position = (x, y, z)`

or, for indoor venues,

`position = (local_region, floor_level, local_relationship)`

The second model may be easier for emergency navigation.

STATUS: NOT SOLVED.

---

# 37. GRAPH CONSISTENCY PROBLEM

Measurements may disagree.

The system should be able to detect inconsistent local geometry rather than silently building impossible maps.

Research questions:

- What simple mathematical checks can reject impossible measurements?
- Can triangle inequality provide a basic sanity check for distance-only measurements?
- Can multiple paths be compared for consistency?
- How much disagreement is normal in a crowd?
- How should stale measurements be weighted?
- How should conflicting direction readings be handled?

Possible future scoring model:

`consistency_error = difference between independently inferred relationships`

Do not create a complicated confidence engine until basic tests show the need.

---

# 38. TWO TYPES OF INFORMATION: TOPOLOGY VS GEOMETRY

This distinction must remain explicit everywhere in the codebase.

## Topology

Answers:

> Which nodes can reach which nodes?

Examples:

- neighbor set;
- hop count;
- connected component;
- route;
- relay path.

## Geometry

Answers:

> Where are things relative to each other physically?

Examples:

- distance;
- bearing;
- vector;
- elevation;
- orientation.

A correct implementation must never treat a topology value as geometry just because both use a number.

---

# 39. EMERGENCY NAVIGATION MODEL

The current conceptual model is:

`SOS target -> Hop 0`

The emergency graph propagates outward.

A responder sees a local part of the network.

The responder's logical objective is:

`current hop -> smaller hop -> ... -> 0`

Then a local direction layer determines where the relevant lower-hop relationship is physically located.

The terminal layer identifies the actual target phone/person.

This is the current preferred emergency model because it avoids making a perfect global coordinate map a hard dependency.

---

# 40. MULTIPLE SOS EVENTS

The system must support multiple simultaneous emergencies.

Each emergency gets:

- unique SOS/event ID;
- event version/sequence;
- origin/target token;
- lifecycle/expiry;
- optional priority class;
- optional authenticated emergency state.

A node can participate in gradients for multiple active events.

Research questions:

- How many simultaneous SOS events should a phone track?
- How much memory is required?
- How do multiple gradients interact?
- How does the UI avoid confusing the responder?
- Can event IDs be kept private?

---

# 41. SOS LIFETIME

An SOS should not flood forever.

Possible lifecycle:

`CREATED -> ACTIVE -> ACKNOWLEDGED -> RESOLVED -> EXPIRED`

Research questions:

- Should only the origin cancel an SOS?
- Can responders mark it acknowledged?
- How is false cancellation prevented?
- What timeout is appropriate if the user cannot interact?
- How are stale emergency packets removed from the mesh?

---

# 42. PACKET STORM / SPECTRUM COLLAPSE PROBLEM

If thousands of phones relay every emergency update at the same time, the system can overload itself.

Possible problems:

- collisions;
- duplicate relays;
- channel occupancy;
- battery drain;
- scan congestion;
- delayed emergency messages.

Potential mechanisms to research:

- deduplication;
- TTL;
- randomized relay delay;
- probabilistic forwarding;
- density-aware forwarding;
- coverage-aware forwarding;
- relay quotas;
- priority queues;
- emergency vs ordinary traffic separation.

The first implementation should start with:

`message_id + version + TTL + seen-cache + randomized relay delay`

Then measure before adding more complexity.

---

# 43. STORE-AND-FORWARD

A node may encounter a packet when the final path is temporarily unavailable.

Research whether the relay should:

- hold the packet briefly;
- retry later;
- forward on a new connection;
- discard it after TTL.

For emergency traffic, bounded store-and-forward may increase resilience but can also create stale information.

Questions:

- What is the maximum useful packet lifetime?
- How much storage should a phone reserve?
- Does store-and-forward help in real crowd partitions?

---

# 44. ROUTING / RELAY SELECTION

Basic initial protocol:

- relay only packets not previously seen;
- decrement TTL at every logical forward;
- do not relay after TTL reaches zero;
- use randomized transmission delay;
- optionally suppress transmission when a packet has already been overheard from multiple peers.

Future research:

- probabilistic forwarding;
- density-aware forwarding;
- expected coverage;
- mobility-aware forwarding;
- energy-aware forwarding;
- relay reputation/trust.

Do not start with a complex reinforcement-learning router.

---

# 45. SECURITY PROBLEMS

This system is vulnerable to network-level abuse if security is ignored.

Required research questions:

- Who is allowed to generate an SOS?
- Can any device generate unlimited fake emergencies?
- How do we authenticate an SOS without needing the internet?
- How do we prevent replaying an old SOS?
- Can a malicious phone impersonate another phone?
- Can an attacker inject false hop information?
- Can a malicious node attract responders into a wrong direction?
- Can a malicious node suppress relays?
- How do we revoke or expire credentials?
- Can cryptographic signatures fit within our packet budget?
- Should users have pre-established event credentials?
- Can emergency networks use short-lived keys?

Security must not become an excuse for permanent identity tracking.

---

# 46. PRIVACY PROBLEMS

Questions:

- Can the network locate individuals permanently?
- Can an observer build a history of where a phone travels?
- How often should node identifiers rotate?
- Can rotating IDs break routing?
- Can SOS IDs reveal the user's identity?
- How long does emergency information remain stored?
- Should local graph data be deleted after an event?
- What information can a normal participant see?
- What information is restricted to responders?

Default philosophy:

`minimum information + temporary identifiers + short lifetimes + emergency-specific visibility`

---

# 47. TERMINAL NAVIGATION — ULTRASONIC IDEA

Proposed concept:

When the responder is already near the target network, the target phone could emit a high-frequency signal and the responder could use its microphone(s) to infer direction.

This should be treated as a **terminal guidance research option**, not the entire architecture.

Research questions:

- Can smartphone speakers reproduce a useful ultrasonic or near-ultrasonic signal?
- What frequencies are reliably emitted?
- Can the microphone capture them?
- What is the sample rate?
- What is the useful range?
- How much does music overwhelm the signal?
- How much do reflections/echoes distort direction?
- What happens with many phones emitting simultaneously?
- Is a coded chirp better than a continuous tone?
- Can cross-correlation identify the target signal?
- Can stereo microphone phase/delay estimate bearing?
- Do phone microphone placements differ too much between models?
- Can this work with a phone in a pocket?

STATUS: UNVERIFIED.

---

# 48. TERMINAL NAVIGATION — OPTICAL/STROBE IDEA

Proposed concept:

The target phone emits a fast visible or infrared optical pattern, and the responder's camera detects/highlights that source.

Research questions:

- Can the phone LED/flash emit a sufficiently distinctive pattern?
- Can the camera capture it reliably in a moving crowd?
- Can infrared be accessed reliably across phone models?
- Is visible flashing safer/more usable than IR?
- How does lighting affect detection?
- What is the maximum useful range?
- Can computer vision isolate the signal from other lights?
- Can an AR overlay point to the target?
- What happens if the target phone is behind people?

STATUS: UNVERIFIED.

---

# 49. TERMINAL NAVIGATION — BLE/UWB LOCALIZATION

Investigate whether the final stage can use stronger local positioning where available.

Candidates:

- BLE direction finding on capable hardware;
- UWB distance/direction on compatible devices;
- repeated local measurements;
- acoustic/optical assist;
- camera-based recognition only as an optional final identification step.

The terminal layer should be pluggable.

---

# 50. RESPONDER UI CONCEPT

The responder UI should not pretend to show an exact GPS marker when it does not have one.

The UI can have stages:

### Stage 1 — Emergency found
Show:

- SOS ID;
- estimated network relationship/hop status;
- emergency age;
- signal/network quality indicators.

### Stage 2 — Move through network gradient
Show:

- current hop;
- next lower-hop route/neighbor information;
- local directional guidance when available.

### Stage 3 — Local/terminal mode
Show:

- “near target” state;
- optional direction arrow;
- target detection signal;
- target confirmation.

The app must not call this “exact location” unless supported by measured evidence.

---

# 51. NORMAL USER FEATURES

Base features to plan:

## Identity/session

- temporary local node identity;
- event/session identity;
- privacy controls;
- capability display.

## Mesh status

- nearby peers count;
- connected components/mesh state;
- active relays;
- transport state;
- last-seen information for diagnostics.

## Emergency

- create SOS;
- cancel/resolve SOS;
- acknowledge SOS;
- show emergency propagation status;
- optionally select event type.

## Groups

Private group features may exist as a separate layer from emergency broadcast.

Research whether friend/private relationships should be represented as a permission layer rather than a separate physical graph.

---

# 52. PRIVATE GROUP SPATIAL MAP

The project originally considered a private group where known members share their relative relationships.

Possible use cases:

- friends at a concert;
- group members trying to reunite;
- group members sharing relative positions;
- emergency awareness inside a private group.

This private group system should NOT become a prerequisite for SOS response.

A responder must be able to use the emergency layer without being a member of the private group.

---

# 53. PUBLIC VS PRIVATE INFORMATION

Separate these concepts:

### Public mesh data
Minimal information needed for relaying/network navigation.

### Private group data
More detailed relative positions among explicitly consenting group members.

### Emergency response data
Information that must be shared to support locating an SOS.

This prevents the system from turning ordinary users into permanent crowd-tracking sensors.

---

# 54. CAPABILITY NEGOTIATION

Every device may have different hardware and OS capabilities.

A node capability profile should eventually include:

- BLE scan support;
- BLE advertise support;
- GATT support;
- extended advertising support if available;
- direction-finding support if exposed;
- UWB support;
- Wi-Fi Aware/Direct support;
- barometer;
- magnetometer;
- gyroscope;
- accelerometer;
- camera/flash capabilities;
- microphone capability;
- platform/background mode support.

This allows the network to adapt instead of assuming all phones are identical.

---

# 55. THE “BEST AVAILABLE SENSOR” PRINCIPLE

A device should contribute whatever it can.

For example:

Phone A:

- BLE only.

Phone B:

- BLE + IMU.

Phone C:

- BLE + UWB.

The graph should still function at the communication level.

Higher-capability devices can provide richer local information without becoming mandatory infrastructure.

---

# 56. EXPERIMENTAL SIMULATION SYSTEM

A simulator should be built before attempting thousands of physical devices.

The simulator should represent:

- nodes;
- 2D positions;
- optional 3D/floor levels;
- communication range;
- packet loss;
- mobility;
- discovery latency;
- RSSI noise;
- directional measurement error;
- node joining;
- node leaving;
- group split;
- group merge;
- SOS creation;
- hop propagation;
- relay policies;
- battery cost models;
- attacker behavior.

---

# 57. SIMULATION SCENARIOS

Mandatory simulations:

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

---

# 58. REAL-WORLD EXPERIMENT PLAN

Start small.

### Test 1 — Two phones

Measure:

- discovery latency;
- BLE range;
- packet delivery;
- battery impact.

### Test 2 — Three phones

Test:

`A -> B -> C`

Measure whether app-level relaying works.

### Test 3 — Five phones

Test dynamic topology.

### Test 4 — Ten phones

Measure collision/relay behavior.

### Test 5 — Twenty or more

Study density and battery.

### Test 6 — Moving participants

Walk around while relaying.

### Test 7 — Dense human obstruction

Put people between devices.

### Test 8 — Indoor multi-room

Walls and partitions.

### Test 9 — Multi-floor

Staircases/floors.

### Test 10 — Controlled crowded event

Closest real approximation to target use case.

Never jump from a five-phone demo to claims about a stadium.

---

# 59. METRICS

The system needs measurable goals.

## Communication

- peer discovery time;
- message delivery rate;
- relay latency;
- end-to-end delivery probability;
- duplicate ratio;
- packet loss;
- packet storm rate.

## Network

- connected component size;
- path availability;
- reconnection time;
- graph stability.

## Emergency

- SOS propagation time;
- percentage of reachable nodes receiving SOS;
- time to responder discovery;
- time-to-lower-hop route;
- false route rate.

## Spatial

- relative distance error;
- angular error;
- graph position error;
- drift over time;
- floor/level classification error.

## Energy

- battery drain per minute;
- scan/advertise duty cycle;
- relay energy cost;
- emergency-mode energy cost.

## User experience

- time to understand instruction;
- time to find target;
- wrong-direction events;
- user confusion rate.

---

# 60. CURRENT STATUS — WHAT HAS BEEN FIGURED OUT

## GREEN / BASIC CONCEPTUAL FOUNDATIONS

- Phone-first architecture.
- Offline peer communication as a core requirement.
- BLE as a primary candidate transport.
- Multi-hop relay concept.
- Small emergency packet concept.
- Dynamic graph concept.
- Relationship-based spatial model.
- No mandatory permanent anchor.
- New-node joining through graph relationships.
- Node/edge aging and expiry concept.
- Split/reconnect graph concept.
- SOS as a temporary logical reference.
- Hop gradient concept.
- Topology vs physical distance distinction.
- Need for terminal guidance as a separate stage.

## YELLOW / CONCEPTUALLY PROMISING BUT UNPROVEN

- relative vector chaining;
- graph-based relative localization;
- dead reckoning integration;
- static/stationary node assistance;
- RSSI-based near/far classification;
- multiple-path spatial reconstruction;
- local direction from phone sensors;
- UWB optional layer;
- Wi-Fi augmentation;
- terminal acoustic guidance;
- optical target handoff;
- sophisticated relay optimization;
- multi-floor graph model.

## RED / NOT YET SOLVED

- reliable physical direction to lower-hop neighbor on ordinary phones;
- universal Android/iOS background equivalence;
- large-scale crowd performance;
- robust indoor 3D navigation;
- security model;
- privacy-preserving persistent graph semantics;
- real-world dense-crowd radio performance;
- verified packet-size architecture;
- guaranteed emergency delivery;
- proven terminal locator;
- production-level responder UX.

---

# 61. NEW IDEAS TO KEEP AVAILABLE

These are optional research paths, not current mandatory architecture.

1. Temporary local anchors.
2. Multiple overlapping local references instead of one global anchor.
3. Stationary-node structural references.
4. Magnetic fingerprints.
5. Ultrasonic terminal guidance.
6. Optical/strobe terminal guidance.
7. UWB terminal ranging.
8. BLE direction finding where hardware supports it.
9. Wi-Fi Aware/Direct as a richer local transport.
10. Local graph regions/clusters.
11. Topological emergency gradients.
12. Movement-derived graph updates.
13. Local consistency checks.
14. Multi-path emergency routing.
15. Store-and-forward.
16. Density-aware relay selection.
17. Adaptive relay sleeping.
18. Venue-floor topology.

Do not choose these simply because they sound advanced. Each must earn its place through testing.

---

# 62. BASE SOFTWARE ARCHITECTURE TO BUILD NOW

The coding agent should NOT begin by hardcoding the final navigation algorithm.

Build modular blocks.

Recommended high-level modules:

```text
crowd-compass/
│
├── apps/
│   ├── android/
│   └── ios/                  # future / capability probe first
│
├── core/
│   ├── protocol/
│   ├── graph/
│   ├── topology/
│   ├── spatial/
│   ├── emergency/
│   ├── identity/
│   ├── security/
│   └── simulation/
│
├── platform/
│   ├── android-ble/
│   ├── ios-bluetooth/
│   ├── sensors/
│   ├── uwb/
│   └── wifi/
│
├── tools/
│   ├── packet-inspector/
│   ├── graph-visualizer/
│   └── simulation-runner/
│
├── docs/
│   ├── architecture/
│   ├── research/
│   ├── protocol/
│   ├── experiments/
│   ├── decisions/
│   └── unanswered-questions/
│
└── tests/
    ├── unit/
    ├── integration/
    ├── simulation/
    └── device-matrix/
```

Adapt this to the existing repository after inspection. Do not overwrite or reorganize an existing project blindly.

---

# 63. BASE BLOCKS OPENCODE SHOULD BUILD FIRST

### Block 1 — Domain types

Create clean types/interfaces for:

- NodeId
- EdgeId
- PeerState
- EdgeState
- RelationshipMeasurement
- GraphSnapshot
- SOS
- SOSUpdate
- RelayPacket
- CapabilityProfile
- Timestamp/expiry

No Bluetooth code yet.

### Block 2 — Dynamic graph engine

Support:

- add node;
- update node;
- remove/expire node;
- add edge;
- update edge;
- expire edge;
- get neighbors;
- connected components;
- graph snapshots.

### Block 3 — Relationship store

Support:

- measurement insertion;
- timestamping;
- replacement/merging;
- aging;
- expiry;
- source tracking.

### Block 4 — SOS engine

Support:

- create SOS;
- assign Hop 0;
- version updates;
- propagate logically;
- TTL;
- deduplication;
- expiration;
- multiple simultaneous SOS events.

### Block 5 — Routing/gradient engine

Support:

- compute hop distance on the current graph;
- identify lower-hop neighbors;
- retain multiple equal-cost choices optionally;
- update when topology changes.

### Block 6 — Protocol encoder/decoder

Binary protocol with explicit schema versioning.

Implement round-trip tests:

`object -> bytes -> object`

### Block 7 — BLE abstraction

Define:

- scanner interface;
- advertiser interface;
- peer connection interface;
- transport interface.

Use mock transport first.

### Block 8 — Simulation

Build fake radios and synthetic movement.

The graph/emergency logic must run identically on simulation transport and real transport.

### Block 9 — Diagnostics

Show:

- nodes;
- edges;
- hop values;
- message flow;
- stale edges;
- component splits;
- reconnections.

### Block 10 — Device capability probe

Create a page/tool that reports:

- Bluetooth support;
- scan support;
- advertising support;
- connection support;
- sensors;
- UWB;
- Wi-Fi peer capabilities;
- OS version;
- background capability assumptions.

---

# 64. IMPORTANT SOFTWARE DESIGN RULE

The core domain code must never call Bluetooth APIs directly.

Instead:

```text
Core Graph
   ↑
Transport Interface
   ↑
Android BLE / iOS BLE / Simulation
```

This lets us test 1,000 fake nodes without needing 1,000 phones.

Similarly:

```text
Core Spatial Engine
   ↑
Sensor Interface
   ↑
Android sensors / iOS sensors / simulated measurements
```

And:

```text
Terminal Guidance Interface
   ↑
BLE direction / UWB / acoustic / optical / simulated
```

This prevents experimental technologies from infecting the core architecture.

---

# 65. DATA MODEL PRINCIPLES

Use explicit optional fields.

Bad:

`distance = 0`

when distance is unknown.

Good:

`distance = null`

and:

`distanceStatus = UNKNOWN`

Likewise:

`direction = null`

must not mean `direction = 0 degrees`.

Every measurement should have a timestamp and source.

---

# 66. GRAPH UPDATE EVENTS

Create event types such as:

- NodeDiscovered
- NodeUpdated
- NodeStale
- NodeExpired
- EdgeCreated
- EdgeUpdated
- EdgeStale
- EdgeExpired
- ComponentSplit
- ComponentMerged
- SOSCreated
- SOSUpdated
- SOSExpired
- RouteChanged

This will make debugging much easier.

---

# 67. RESEARCH NOTE SYSTEM

Every unresolved question should have a research record:

```text
Question:
Why does this matter?
Current assumption:
Evidence required:
Experiment:
Metric:
Expected outcome:
Actual outcome:
Decision:
Status:
```

Statuses:

- OPEN
- RESEARCHING
- TESTABLE
- EXPERIMENTAL
- VERIFIED UNDER CONDITIONS
- REJECTED
- REPLACED

Do not write “SOLVED” unless the conditions are clearly stated.

---

# 68. ARCHITECTURE DECISION RECORDS

Create ADRs for major decisions:

- why BLE is primary transport;
- why there is no permanent anchor requirement;
- why topology and geometry are separated;
- why SOS uses a hop gradient;
- why RSSI is not the primary distance model;
- whether vector chaining remains optional;
- whether UWB is optional;
- whether iOS support is full or phased;
- packet encoding choice;
- security model;
- privacy/identity model.

---

# 69. THE MOST IMPORTANT RESEARCH QUESTIONS — NAVIGATION

The coding/research agent must answer these in order.

### Level 1 — Basic graph

1. Can nodes join/leave without corrupting the graph?
2. Can the graph survive anchor disappearance?
3. Can two components reconnect?
4. Can a new node understand the network after joining?
5. Can the graph maintain multiple possible paths?

### Level 2 — Basic SOS topology

6. Can an SOS create a stable Hop-0 reference?
7. Does BFS-style hop propagation behave correctly under topology changes?
8. How quickly does the gradient converge?
9. What happens when the shortest path disappears?
10. Can a responder joining later obtain a valid gradient?

### Level 3 — Spatial relationships

11. What local measurement can provide useful distance information?
12. What local measurement can provide useful direction information?
13. Can measurements be composed across graph paths?
14. How quickly does spatial error accumulate?
15. Can redundant paths reduce error?

### Level 4 — Physical navigation

16. How can a responder identify the physical direction of a lower-hop neighbor?
17. Can phone orientation + a local direction measurement solve this?
18. Can UWB help on capable devices?
19. Can BLE direction finding help on capable devices?
20. What happens on phones with neither?

### Level 5 — Terminal target

21. How does the responder know they are near the target?
22. How do we identify the actual target device?
23. Can acoustic, optical, BLE, or UWB methods work?
24. What works when there is no line of sight?

---

# 70. THE MOST IMPORTANT RESEARCH QUESTIONS — CROWD CONDITIONS

1. What happens with 10 phones?
2. 50?
3. 100?
4. 500?
5. 1,000?
6. 10,000 in a simulation?
7. What is the practical peer visibility distribution?
8. What is the average degree of the graph?
9. What density creates useful redundancy?
10. At what density does traffic become congested?
11. How often do links change in walking crowds?
12. How much packet loss occurs with bodies blocking the signal?
13. How much battery does relay mode cost?
14. Does longer range improve or harm the graph?
15. Does aggressive scanning overload the phone?

---

# 71. THE MOST IMPORTANT RESEARCH QUESTIONS — PLATFORM

1. Android scan permissions.
2. Android advertise permissions.
3. Android connection permissions.
4. Android background behavior.
5. Foreground-service requirements.
6. OEM power management.
7. Screen-off operation.
8. App restart behavior.
9. iOS central background behavior.
10. iOS peripheral background behavior.
11. iOS discovery throttling/coalescing.
12. iOS capability differences.
13. Cross-platform protocol compatibility.
14. Bluetooth address randomization.
15. Device capability detection.

Official current platform documentation should be checked during implementation because these behaviors are version-dependent.

---

# 72. MOST IMPORTANT RESEARCH QUESTIONS — PRIVACY/SECURITY

1. How do ephemeral IDs rotate?
2. How does a peer know that two IDs belong to the same live session without creating permanent identity?
3. How do we authenticate SOS events?
4. How do we stop replay?
5. How do we stop fake hop updates?
6. How do we stop malicious routing?
7. How do we limit malicious broadcast traffic?
8. How do responders prove they are authorized?
9. How long is data kept?
10. How is event data deleted?
11. Can ordinary users opt out of relaying?
12. Does opting out destroy network utility?
13. Can the protocol minimize personal metadata?

---

# 73. ERROR HANDLING PRINCIPLES

Never assume every measurement is correct.

Use categories:

- UNKNOWN;
- STALE;
- CONFLICTING;
- UNAVAILABLE;
- ESTIMATED;
- MEASURED;
- VERIFIED UNDER TEST.

A failed sensor should not crash the graph.

A failed BLE link should not crash the emergency engine.

A missing physical direction should degrade the navigation layer while leaving the SOS topology active.

---

# 74. FAILURE MODES TO MODEL

At minimum:

- Bluetooth disabled;
- permissions denied;
- background process killed;
- phone battery low;
- phone reboots;
- random identifier changes;
- device leaves;
- relay leaves;
- network partitions;
- packet corruption;
- packet duplication;
- packet replay;
- fake SOS;
- malicious relay;
- crowded RF environment;
- body blocking;
- multiple floors;
- poor compass calibration;
- IMU drift;
- UWB unavailable;
- terminal sensor unavailable;
- target phone screen off;
- target phone app backgrounded;
- target phone speaker/microphone blocked;
- responder joins late.

---

# 75. PRODUCT STATES

The app should expose system state clearly.

Possible states:

`OFFLINE_IDLE`

`SCANNING`

`MESH_FORMING`

`MESH_ACTIVE`

`SOS_ACTIVE`

`RESPONDER_MODE`

`TERMINAL_MODE`

`NO_NETWORK`

`PARTIAL_NETWORK`

`CAPABILITY_LIMITED`

`EMERGENCY_RESOLVED`

These are operational states, not scientific claims.

---

# 76. UI/UX QUESTIONS SOMEONE WILL ASK

- Why do I need Bluetooth?
- Why do I need nearby-device permission?
- Why should my phone relay other people's messages?
- Does relaying reveal my location?
- Will it drain my battery?
- Does the system work if the internet is down?
- Does it work when the screen is off?
- Does it work with Airplane Mode?
- Does every phone need the app?
- Does everyone in the venue need the app?
- What happens if only some phones have it?
- Can I opt out of relaying?
- Can an attacker track me?
- Can an attacker fake an SOS?
- What happens if the network is split?
- What happens if the target's phone dies?
- What happens if the responder's phone does not support advanced positioning?
- Why does the app show hops instead of meters?
- What does “near target” actually mean?
- How do I know when the target is found?

The app documentation should answer these honestly.

---

# 77. WHAT SHOULD BE A DEMO VS WHAT SHOULD BE THE REAL SYSTEM

### Demo layer

Can use simulation or controlled data to show:

- graph creation;
- dynamic node movement;
- joining/leaving;
- SOS gradient;
- responder route;
- packet propagation;
- graph visualization.

### Real hardware layer

Must validate:

- discovery;
- advertising;
- relaying;
- latency;
- packet loss;
- battery;
- background behavior;
- crowd obstruction.

Never present simulator accuracy as real-world accuracy.

---

# 78. BUILD ROADMAP

## Phase 0 — Repository understanding

OpenCode must first inspect the existing repository.

Do not assume language/framework.

Document:

- current files;
- package manager;
- build system;
- app platforms;
- existing UI;
- existing BLE code;
- existing dependencies;
- existing project documentation.

Do not delete or rewrite working components without evidence.

## Phase 1 — Core graph simulator

Build the dynamic graph without Bluetooth.

Deliver:

- nodes;
- edges;
- join/leave;
- split/reconnect;
- timestamps;
- expiry;
- BFS hop graph.

## Phase 2 — Protocol

Build the binary message model and tests.

## Phase 3 — Simulated mesh

Use fake radio transport.

Measure:

- packet propagation;
- duplicates;
- TTL;
- route changes;
- SOS convergence.

## Phase 4 — Android BLE proof-of-concept

Start with a small device set.

## Phase 5 — Dynamic real-device tests

Two -> three -> five -> ten phones.

## Phase 6 — Spatial experiments

Add local measurements and IMU.

## Phase 7 — Direction research

Test supported device technologies.

## Phase 8 — Terminal guidance experiments

Test UWB / BLE direction / acoustic / optical options.

## Phase 9 — Security/privacy

Harden before public deployment.

## Phase 10 — Large-scale simulation

Only after real transport behavior is measured.

---

# 79. INITIAL SUCCESS CRITERIA

Do not call Crowd Compass “working” simply because two phones exchange a packet.

A meaningful early milestone is:

> A small group of real phones can discover one another, exchange small application messages, relay an SOS across multiple hops, recover from at least one relay disappearing, allow a late responder to join, and correctly compute the current logical hop relationship to the SOS.

A later milestone is:

> The system can add local physical relationships and demonstrate a measurable method for selecting a physically meaningful direction toward a lower-hop route.

A later milestone still is:

> The system can locate/identify the target reliably enough in a controlled crowd environment, with measured error and known limitations.

---

# 80. CURRENT CORE RESEARCH THESIS

The project should currently be tested around this question:

> Can a dynamic smartphone mesh create and maintain a useful emergency navigation gradient without requiring GPS or a permanent global coordinate anchor, while local spatial relationships and optional stronger sensing provide the physical direction and terminal guidance needed by a responder?

That is the core thesis.

---

# 81. IMPORTANT: DO NOT GET TOO COMPLEX TOO EARLY

The project previously became confusing because every unresolved problem was immediately attacked with advanced solutions.

The intended order is:

```text
communication
   ↓
graph
   ↓
dynamic graph
   ↓
SOS propagation
   ↓
hop gradient
   ↓
local physical direction
   ↓
terminal guidance
   ↓
3D / security / optimization / scale
```

Do not jump to:

- AI localization;
- neural networks;
- fancy confidence models;
- reinforcement learning;
- full 3D SLAM;
- complex sensor fusion;

until the basic graph and emergency routing work.

---

# 82. OPENCODE WORKING RULES

OpenCode should:

1. Inspect before changing.
2. Build base modules before feature UI.
3. Keep simulation and real transport interchangeable.
4. Keep research assumptions in documentation.
5. Add unit tests for every graph operation.
6. Add simulation tests for every topology failure case.
7. Never hardcode a permanent anchor requirement.
8. Never treat hop count as metres.
9. Never treat RSSI as exact physical distance.
10. Never assume UWB or BLE direction finding exists on every phone.
11. Never assume Android and iOS background behavior is identical.
12. Never claim experimental methods are solved.
13. Record unknowns rather than inventing behavior.
14. Build instrumentation before optimization.
15. Use real measurements to update assumptions.

---

# 83. FIRST TASK FOR OPENCODE

Before writing production code, create:

`docs/PROJECT_STATUS.md`

containing:

- what is conceptual;
- what is implemented;
- what is experimental;
- what is unknown.

Create:

`docs/CORE_PROBLEM.md`

with the original problem and all core subproblems.

Create:

`docs/ARCHITECTURE.md`

with the layered system.

Create:

`docs/RESEARCH_QUESTIONS.md`

with every unresolved question from this document.

Create:

`docs/PROTOCOL.md`

for the packet/data model.

Create:

`docs/EXPERIMENT_PLAN.md`

for simulations and real device tests.

Create:

`docs/DECISIONS/`

for architecture decisions.

Then build the pure graph simulator.

Do not start with the fancy navigation layer.

---

# 84. FIRST GRAPH TESTS

The first tests should prove:

### Test A

Add nodes and edges.

### Test B

Remove a node and ensure unrelated edges survive.

### Test C

Split one graph into two components.

### Test D

Reconnect two components.

### Test E

Create an SOS at a node.

### Test F

Compute hop 0/1/2/3/...

### Test G

Remove the shortest-path relay and ensure the route changes.

### Test H

Add a new node after the SOS already exists and ensure it can learn the current gradient.

### Test I

Run two SOS events simultaneously.

### Test J

Expire an old SOS.

### Test K

Flood a dense graph and measure duplicate suppression.

### Test L

Simulate packet loss.

These should all run without any physical radio hardware.

---

# 85. THE KEY MATHEMATICAL OPERATIONS TO IMPLEMENT FIRST

Only the simplest ones.

## Graph connectivity

`neighbors(v)`

## Path existence

`isReachable(a,b)`

## Connected components

`components(G)`

## Hop distance

`hop(s,v)` via BFS on an unweighted graph.

## Next-hop set

`nextHops(v,s) = neighbors of v with hop = hop(v)-1`

## Relationship composition

For compatible vector relationships:

`R(A,C) = R(A,B) + R(B,C)`

but only after all vectors are expressed in the same reference frame.

## Relationship freshness

`age = now - timestamp`

## Expiry

`expired = age > expiryWindow`

This is enough for the first mathematical prototype.

---

# 86. QUESTIONS THAT MUST NEVER BE HIDDEN

These are the “hard truths” the product documentation should keep visible:

- Bluetooth range in a crowd is variable.
- RSSI is not a reliable universal metre measurement.
- Hop count is not physical distance.
- Standard smartphones do not necessarily expose Bluetooth AoA/AoD functionality needed for direction.
- Android and iOS background rules differ and are version-dependent.
- UWB is hardware-dependent and cannot be assumed universally.
- A graph can tell us network topology without automatically telling a responder which way to walk.
- A perfect indoor map is not automatically achievable from local phone-to-phone measurements.
- Real crowd conditions must be tested.
- Emergency systems require security and failure handling.

---

# 87. CURRENT BIGGEST OPEN TECHNICAL QUESTION

The current biggest unresolved technical question is:

> Once the responder knows that a lower-hop neighbor leads toward the SOS, how can an ordinary phone determine the physical direction of that neighbor reliably enough for navigation, especially when the phones are moving, bodies block RF signals, the environment is crowded, and the phone may not support specialized direction-finding hardware?

This should be attacked separately from the graph problem.

Potential research branches:

1. BLE direction finding where supported.
2. UWB where supported.
3. Sensor-assisted local direction.
4. Relative movement inference.
5. Acoustic terminal assist.
6. Optical terminal assist.
7. A hybrid method.

---

# 88. CURRENT SECOND BIGGEST OPEN TECHNICAL QUESTION

> How large and dynamic can the phone graph become before app-level relaying, BLE scanning/advertising, battery usage, and packet collisions make the system impractical?

This needs simulation plus real-device measurements.

---

# 89. CURRENT THIRD BIGGEST OPEN TECHNICAL QUESTION

> Can the emergency gradient remain usable when the network is continuously changing because people move, phones disappear, groups split, groups merge, and new responders join?

This is primarily a topology/algorithm problem before it is a hardware problem.

---

# 90. FINAL SYSTEM PICTURE

The current design should be understood as:

```text
                    CROWD COMPASS
                          │
                          ▼
              PHONE-FIRST LOCAL MESH
                          │
                          ▼
                 DYNAMIC GRAPH
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
      LOCAL RELATIONSHIPS        SOS GRADIENT
             │                         │
     distance/direction         Hop 0,1,2,3...
     movement/time                    │
             │                         │
             └────────────┬────────────┘
                          ▼
                   LOCAL GUIDANCE
                          │
                          ▼
                   TERMINAL FINDER
                          │
                          ▼
                     🚨 TARGET
```

The global-coordinate problem is no longer the mandatory centerpiece.

The dynamic relationship graph remains useful for spatial reasoning and private-group mapping.

The SOS gradient is the simpler emergency topology layer.

The physical-direction problem is the next major research problem.

---

# 91. SOURCE CHECKS TO KEEP CURRENT

Implementation research should consult current official platform/specification documentation, because platform capabilities and restrictions change.

Key references checked during creation of this document include:

- Android Bluetooth permissions and current Bluetooth API documentation.
- Android Bluetooth GATT/MTU documentation.
- Android Wi-Fi Aware documentation.
- Apple Core Bluetooth documentation and background execution documentation.
- Apple Nearby Interaction/UWB documentation.
- Bluetooth SIG documentation for LE Direction Finding, LE advertising, and transport constraints.

The project should re-check these sources during each major implementation phase rather than relying on an old assumption.

---

# 92. HANDOFF INSTRUCTION

OpenCode: treat this file as the current project truth, but not as proof of feasibility.

Your job is to:

1. inspect the repository;
2. organize the codebase around modular base blocks;
3. create the documentation structure;
4. implement the pure graph simulator;
5. implement the protocol model;
6. implement the logical SOS/hop engine;
7. write exhaustive tests for joining, leaving, moving, splitting, merging, anchor loss, late responder arrival, multiple SOS events, packet duplicates, TTL and expiry;
8. only then begin the real BLE transport;
9. maintain a research ledger for every unresolved hardware/platform question;
10. never replace unknown behavior with a fake implementation or a confident assumption.

The project should be built in a way that allows experimental navigation methods to be added later without rewriting the core graph and emergency system.
