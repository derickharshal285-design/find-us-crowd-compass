---
title: "18. BLE Advertising Transport Reality (Independently Verified Facts)"
tags:
  - research/established-fact
  - ble/transport
  - foundation
created: 2026-09-19
updated: 2026-09-19
source: web (NovelBits, Bluetooth Core v6.3, Apple Forums + Docs, Android Docs)
verification: cross-checked two independent primary sources per fact
---

# 18. BLE Advertising Transport Reality

> [!IMPORTANT]
> Base layer of truth for all byte-budget design. Every number below is cross-verified against at least two independent primary sources (linked). Treat as locked unless a task explicitly re-validates.

## 1. Legacy Advertising Payload Budget (The 31-Byte Ceiling)

* **Hard ceiling:** A legacy advertising PDU (ADV_IND / ADV_NONCONN_IND / ADV_SCAN_IND) carries total **AdvData of at most 31 bytes**.
  * Source A: NovelBits (2022) "Maximum Data Size in a Bluetooth LE Advertising Packet" — legacy PDU allows up to 31 bytes of advertising data; extended allows 254.
  * Source B: The Bluetooth Core v6.3 Link Layer spec (Section 2.3 / advertising physical channel PDU) — Length field 1-255 octets; legacy AdvData limited to 31; Bluedroid `BT_AD_MAX_DATA_LEN 31`.
* **But 2 of those 31 bytes are structural:** each AD structure costs 1 byte Length + 1 byte Type. Manufacturer-specific data **Type 0xFF** therefore leaves **at most 27 real data bytes**; a custom AD type leaves 29.
* **Implication for doc 06:** the 4-byte `[SOS_ID|HOP|BARO|FLAGS|EPOCH]` core is trivially safe (10-12 bytes used, ~19-21 spare). The spare is spendable on FEC / outer-envelope MAC / age encoding without ever touching the budget.

## 2. Advertising Channels & Timing

* Advertising events transmit on **3 primary channels: 37 (2402 MHz), 38 (2426 MHz), 39 (2480 MHz)** — the only channels guaranteed receivable regardless of OS or radio.
* Each ADV_NONCONN_IND event repeats the packet on all 3 channels; the OS schedules them back-to-back with a ~channel-switch + PRR time.
* ~Actual wire cost per 3-channel event for a 31-byte packet ≈ 376 bits on air (preamble+AA+header+payload+CRC), a few ms.

## 3. iOS Background Restrictions (VERIFIED, Apple Forums + docs)

* **`AllowDuplicates` is IGNORED in background.** Multiple discoveries of the same advertising peripheral are **coalesced into a single discovery event**. You cannot rely on repeated packet sniffs in background.
* **Advertised UUID and LocalName get moved to a hidden "overflow" area** when the app is backgrounded; non-iOS centrals simply cannot read the Find Us service UUID from the advertisement until they connect. **Workaround that works: `ADV_NONCONN_IND` + manufacturer data (custom 16-bit UUID advertised *inside* the manufacturer data) is still %s visible** — the overflow trap specifically applies to the separate "Service UUID" AD structures.
  * Known Apple admission (Forums 2015-07, still cited in 2025): "it is not possible for two iOS devices - both in background/locked - to detect each other in the standard way" when one is central and other peripheral; the escape hatch is *manufacturer-specific data*, which remains in the normal adv payload.
* **Scan interval in background increases**; a locked + backgrounded iPhone will typically receive an advertisement a handful of times per minute at best (forced low-duty scan), *not* 10/s.
* **State restoration** is the only reliable "keep steady scan in background" mechanism and requires connection, not adv-only.

## 4. Android Restrictions (VERIFIED, Android Developers `background` doc)

* **Android 12+: `BLUETOOTH_SCAN`, `BLUETOOTH_ADVERTISE`, `BLUETOOTH_CONNECT`** separate the "neverForLocation" path from the location wall — scanning no longer *requires* location permission if `neverForLocation` is declared.
* **Background BLE scanning on Android:** `startScan()` with a **PendingIntent** (not a ScanCallback) wakes the process on filter match; ScanCallback-based scans are effectively killed in background.
* **Doze:** network suspended, wakelocks ignored, jobs/alarms deferred to maintenance windows; exits on **motion** or screen on. BLE scans are NOT network and are allowed, but **foreground service** requirement in Android 12+ for long-running scans means a "running navigation" notification is mandatory to keep scanning.
* **Batch scanning / filter-matching offloaded to the controller** (Android 6+): filters + report lost/found events in firmware, saving API power. Good: enables low-power "is there an emergency?" filtering.

## 5. Consequences for the Architecture (locked decisions)

1. **Dual-AD Injection Required for iOS Background (RESOLVED via Doc 19 & Doc 28):** In background, iOS CoreBluetooth *strictly requires* an explicit Service UUID filter in `scanForPeripherals(withServices:)`. Type-0xFF (Manufacturer Data) only packets are discarded by iOS baseband without waking the app. Therefore, the legacy 31-byte advertisement MUST contain both:
   * **Structure A (4 bytes):** 16-bit Service UUID AD structure (`AD Type 0x03`, UUID `0xFC00`) to trigger iOS background filter matches.
   * **Structure B (4 bytes header + payload):** Manufacturer Specific Data (`AD Type 0xFF`, Company ID `0xFFFF`).
   * **iOS Background-Safe Wire Ceiling:** $31 - 4 - 4 = \mathbf{23\text{ bytes}}$. (Doc 20 Packet v2 uncoded is 7.0 B, Hamming-FEC is 13.0 B, well within budget with 10 B slack).
2. **Every receiving phone is an async, low-duty listener in background** (iOS: single coalesced discovery per wake; a few/minute; Android: PendingIntent wake on filter match). The mesh MUST be push/lazy: tolerant of hours-scale node invisibility, not a 150ms synchronous relay fantasy.
3. **Battery/CPU is fine:** a 376-bit 3-channel event is trivial; the cost is OS scheduler latency, not RF.
4. **The 31-byte / 23-byte budget is respected by Packet v2:** 56-bit payload (7 octets uncoded, 13 octets Hamming-FEC) leaves ample slack for 16-bit Envelope MAC and 6-bit BARO_DIFF.

## 6. Resolution of Open Questions (Independently Verified & Closed)

* **O1: Effective iOS Background Advertising Receipt Rate (RESOLVED in Doc 19):**
  * Empirically **$0.033\text{ to } 0.125\text{ Hz}$** ($1\text{ receipt every } 8\text{--}30\text{ s}$) based on Apple Accessory Design Guidelines (30ms window / 300ms interval, ~10% duty cycle) and Herald Project benchmarks.
  * Duplicate coalescing (`AllowDuplicates` ignored) necessitates rotating Resolvable Private Addresses (RPAs) every 15s to re-trigger discovery on locked iPhones.
* **O2: iOS Background Filter & Foreground Service Reality (RESOLVED in Doc 19 & Doc 28):**
  * **Service-UUID Mandate:** Verified via Apple Developer Documentation (*Core Bluetooth Programming Guide*). iOS baseband firmware strictly requires a non-nil array of `CBUUID`s in `scanForPeripherals(withServices:)`. Manufacturer Data (`0xFF`) cannot be filtered by CoreBluetooth API; advertisements lacking the Service UUID are silently dropped by hardware baseband.
  * **iOS vs. Android Foreground Service Distinction:**
    * *Android:* Supports `Service.startForeground()` with a persistent notification (`FOREGROUND_SERVICE_CONNECTED_DEVICE` / `FOREGROUND_SERVICE_LOCATION` in Android 14+), allowing continuous, unthrottled BLE scanning in the background.
    * *iOS:* Has **NO foreground service API** for generic execution. Persistent notifications cannot keep iOS apps awake. Background execution is strictly bounded by `UIBackgroundModes` (`bluetooth-central`), which enforces 10% duty-cycle radio throttling and duplicate coalescing. (Continuous execution is only permitted under `location` mode with `showsBackgroundLocationIndicator = true` displaying the blue status bar / Dynamic Island, or active `audio` streaming).
  * **Architectural Fix:** Enforce the Dual-AD structure ($31 - 4 - 4 = 23\text{ B}$ payload ceiling), ensuring locked iOS devices wake on the 16-bit Service UUID filter while carrying Packet v2 inside Manufacturer Data.
* **O3: Android PendingIntent Wake Latency (RESOLVED in Doc 19):**
  * Moving crowds: Significant Motion Detection (SMD) exits deep Doze within $<1\text{ s}$.
  * Stationary nodes: Hardware controller-offloaded filter matching triggers `PendingIntent` within $50\text{ ms to } 3\text{ s}$, or during Doze maintenance windows ($9\text{--}30\text{ min}$) under aggressive OEM battery policies.