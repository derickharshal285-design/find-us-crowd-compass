# ADR-008 — iOS support is phased, not assumed

**Status:** Pending

**Context (spec §71, §60 RED):** iOS central/peripheral background behavior,
discovery throttling, and capability differences are version-dependent; the
repo has only static Swift fixtures (no build toolchain available). Universal
Android/iOS background equivalence is an unsolved item.

**Decision:** iOS is a phased research track, not a launch commitment.
Priority: Android BLE proof-of-concept first (phase 4–5, §78); iOS probes
capability and background behavior (C39–43 questions) before any iOS app work.
No iOS behavior is assumed before official docs are checked (spec §91).

**Consequences:** `tests/cross_language_test.py` keeps Swift fixtures as
static/format-fidelity checks only; they are skipped when no toolchain exists.
Repository commits to keep the cross-platform packet format in sync
(`core/python/packet_v2.py` ↔ Swift/Kotlin fixtures).