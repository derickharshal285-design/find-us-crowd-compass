# RESEARCH QUESTIONS

Every unresolved question in `docs/MASTER_SPEC.md` is collected here. Track
each item with the research-note record (spec §67):

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

Statuses (spec §67): OPEN · RESEARCHING · TESTABLE · EXPERIMENTAL ·
VERIFIED UNDER CONDITIONS · REJECTED · REPLACED. Do not write "SOLVED" unless
the conditions are clearly stated. All questions below are **OPEN** by default.

## A. Navigation — in priority order (spec §69)

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

## B. Crowd conditions (spec §70)

25. What happens with 10 / 50 / 100 / 500 / 1,000 / 10,000 (simulation) phones?
26. What is the practical peer visibility distribution?
27. What is the average degree of the graph?
28. What density creates useful redundancy?
29. At what density does traffic become congested?
30. How often do links change in walking crowds?
31. How much packet loss occurs with bodies blocking the signal?
32. How much battery does relay mode cost?
33. Does longer range improve or harm the graph?
34. Does aggressive scanning overload the phone?

## C. Platform (spec §71)

35–49. Android scan/advertise/connection permissions; Android background
behavior; foreground-service requirements; OEM power management; screen-off
operation; app restart; iOS central/peripheral background behavior; iOS
discovery throttling/coalescing; iOS capability differences; cross-platform
protocol compatibility; Bluetooth address randomization; device capability
detection. Official current platform docs must be re-checked at
implementation time — behaviors are version-dependent (spec §91).

## D. Privacy/security (spec §72)

50. How do ephemeral IDs rotate?
51. How does a peer know two IDs belong to the same live session without
    creating permanent identity?
52. How do we authenticate SOS events?
53. How do we stop replay?
54. How do we stop fake hop updates?
55. How do we stop malicious routing?
56. How do we limit malicious broadcast traffic?
57. How do responders prove they are authorized?
58. How long is data kept?
59. How is event data deleted?
60. Can ordinary users opt out of relaying?
61. Does opting out destroy network utility?
62. Can the protocol minimize personal metadata?

## E. Bluetooth specifics (spec §25–28, §32)

63. What is the real advertising/scan duty cycle relationship on Android/iOS?
64. Legacy adv (31-byte) vs BLE 5 extended advertising vs GATT MTU: what fits
    the packet model (§23)? Verified packet-size architecture is RED (unproven).
65. RSSI "waterbag" problem (§32): can RSSI be used only for robust near/far
    classification, never as metre ground truth?
66. BLE AoA/AoD direction finding: which hardware actually exposes it (§26)?
67. UWB as optional ranged layer (§27): which devices, what accuracy?
68. Wi-Fi Aware/Direct as richer local transport (§28)?

## F. Spatial relationship engine (spec §30–31, §33–37)

69. Relative vector chaining: error growth and drift.
70. Dead reckoning / phone IMU integration quality (§33).
71. Inertial trust / static-node assistance (§34).
72. Magnetic fingerprinting viability (§35).
73. Vertical / z-axis problem: floors, stairs, barometric climbing (§36).
74. Graph consistency checks (§37).
75. Spatial error accumulation over multi-hop composition (Level 3 Q14).

## G. Emergency system (spec §40–44)

76. Multiple simultaneous SOS events (§40): how are they kept independent?
77. SOS lifetime and expiry policy (§41).
78. Relay storm / spectrum collapse mitigation (§42).
79. Store-and-forward trade-offs (§43).
80. Relay selection / density-aware policies (§44): how many alternate paths to
    maintain, full tree vs next-hop set, state bound (§21).

## H. Terminal navigation (spec §47–49)

81. Ultrasonic terminal guidance (§47).
82. Optical/strobe target handoff (§48).
83. BLE/UWB terminal localization (§49).

## I. The three biggest open technical questions (spec §87–89)

**Q1 (biggest).** Once the responder knows a lower-hop neighbor leads toward
the SOS, how can an ordinary phone determine the physical direction of that
neighbor reliably enough for navigation — especially when phones move, bodies
block RF, the environment is crowded, and the phone has no direction-finding
hardware? Branches: BLE direction finding (supported), UWB (supported),
sensor-assisted local direction, relative movement inference, acoustic assist,
optical assist, hybrid.

**Q2.** How large and dynamic can the phone graph become before app-level
relaying, BLE scanning/advertising, battery, and packet collisions make the
system impractical?

**Q3.** Can the emergency gradient remain usable when the network continuously
changes (movement, disappearing phones, splits, merges, late responders)?

## Reference notes

- Every sub-repository `research/` document should map back to one of the
  numbered questions above.
- A question earns a status change only when its Experiment + Metric + Actual
  outcome are recorded.