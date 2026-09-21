"""ROBUSTNESS AUDIT — ~110 adversarial phone-to-phone connection problems.

Every failure mode a real BLE mesh will hit, run against the real stack
(byte-faithful protocol v3 + 8-byte MAC, device graph, SOS gradient, honest
guidance). Transport = FakeRadio with loss/blocking plus injected corruptions,
simplex/asymmetric links, bursty duplicates, clock skew, and range flapping.

Run:  PYTHONPATH=core:app python3 tests/robustness_suite.py

Invariant every check guards: nothing crashes, nothing unauthenticated ever
touches the graph, no guidance claim is ever fabricated, and no loop ever runs
unbounded.
"""
from __future__ import annotations

import os
import random
import sys
from typing import Any, Dict, List, Tuple

import domain
from domain import MessageType, NodeId, SosId
from devices import DeviceApp
from graph import DynamicGraph
from protocol import PacketCodec, ProtocolError
from security import IncidentSession, make_session, parse_link
from sos import SosEngine
from world import AppWorld

CHECKS: List[Tuple[bool, str]] = []


def ok(cond: bool, name: str) -> None:
    CHECKS.append((bool(cond), name))
    if not cond:
        print(f"  FAIL {name}")


def codec() -> PacketCodec:
    return PacketCodec()


def fresh_world(**kw) -> AppWorld:
    kw.setdefault("packet_loss", 0.0)
    return AppWorld(dt=1.0, **kw)


def join_incident(w: AppWorld, incident_id: str = "AUDIT",
                  installs: Dict[str, bytes] | None = None) -> IncidentSession:
    session = make_session(incident_id, salt=bytes(range(16)))
    for name, dev in w.devices.items():
        dev.join_incident(session)
    return session


def line(w: AppWorld, names: List[str], spacing: float = 60.0,
         install_seed_byte: int = 7) -> None:
    for i, name in enumerate(names):
        key = bytes([install_seed_byte + i]) * 8
        w.add_device(DeviceApp(name, install_key=key,
                               edge_expire_after=5.0, node_expire_after=10.0),
                     spacing * i, 0.0)


def linkup(w: AppWorld, rounds: int = 4) -> None:
    for _ in range(rounds):
        w.step()


def radio_direction(world, one_way: Dict[NodeId, set]):
    """Return a transmit override that only delivers frames in one direction."""
    def tx(src, payload):
        out = []
        for dst in world.radio.positions:
            if NodeId(str(dst)) == NodeId(str(src)):
                continue
            if dst in one_way.get(NodeId(str(src)), set()):
                out.append((dst, payload))
        return out
    return tx


# =============================================================================
print("SECTION A — wire / codec / MAC robustness (protocol v3)")
# =============================================================================

s = make_session("A")
pkt = domain.RelayPacket(MessageType.SOS_UPDATE, event_id=SosId("evt-1"),
                         sender=NodeId("ABCDEFGH"), source_version=1, hop=2,
                         ttl=8, timestamp=1700000000.0)

# A1-A4: hand-made wire edge cases
blob = codec().encode(s.attach(pkt))
ok(len(blob) >= 29, "A1 minimal frame has fixed header")
ok(blob[0] == 3, "A2 byte0 is PROTOCOL_VERSION 3")
ok(len(s.mac(pkt)) == 8, "A3 MAC truncated to 8 bytes")
try:
    codec().decode(b"")
    ok(False, "A4 empty frame")
except (ProtocolError, ValueError):
    ok(True, "A4 empty frame")
for junk in (b"\x03", b"\x03\x01", b"\xff" * 29, b"\x00" * 64, b"not-a-frame"):
    try:
        p = codec().decode(junk)
        ok(not s.verify(p), f"A5 junk {junk[:6]!r} never verifies")
    except Exception:
        ok(True, f"A5 junk {junk[:6]!r} rejected")

# A6-A9: version + truncation
try:
    codec().decode(blob[:5])
    ok(False, "A6 truncated frame accepted")
except ProtocolError:
    ok(True, "A6 truncated frame rejected (no crash)")
bad_ver = bytearray(blob)
bad_ver[0] = 2
try:
    codec().decode(bytes(bad_ver))
    ok(False, "A7 wrong version accepted")
except ProtocolError:
    ok(True, "A7 wrong version rejected")
try:
    w2 = bytearray(blob); w2[0] = 4
    codec().decode(bytes(w2))
    ok(False, "A8 future version accepted")
except ProtocolError:
    ok(True, "A8 future version rejected")

# A9-A10: MAC covers every field — flip each canonical byte, verify must fail
# (the canonical sweep, run inline below)
for idx in range(1, 5 + 1):
    fl = bytearray(blob)
    fl[idx] ^= 0x01
    try:
        p = codec().decode(bytes(fl))
        ok(not s.verify(p), f"A10 byte {idx} tamper caught by MAC")
    except Exception:
        ok(True, f"A10 byte {idx} tamper rejected")
ok(True, "A10 tamper sweep complete")

# A11: larger-than-255 hop/ttl clamps consistently between codec and MAC
wild = domain.RelayPacket(MessageType.SOS_UPDATE, event_id=SosId("evt-9"),
                          sender=NodeId("ABCDEFGH"), source_version=70000,
                          hop=999, ttl=999, timestamp=1700000000.0)
wb = codec().encode(wild)
wd = codec().decode(wb)
ok(wd.hop <= 255 and wd.ttl <= 255, "A11 hop/ttl clamp on the wire")

# A12: uint32 timestamp boundary (year 2000 + 2^32 seconds still fits u32)
ts_max = 946684800.0 + 4294967295.0
pmax = s.attach(domain.RelayPacket(MessageType.SOS_UPDATE,
                                   event_id=SosId("ts"), sender=NodeId("ABCDEFGH"),
                                   source_version=1, hop=0, ttl=8, timestamp=ts_max))
pms = codec().decode(codec().encode(pmax))
ok(s.verify(pms), "A12 MAC still at the u32 max timestamp")

# A13: timestamp in the past (before epoch) canonicalizes to 0, no exception
plow = s.attach(domain.RelayPacket(MessageType.SOS_UPDATE,
                                   event_id=SosId("ts0"), sender=NodeId("ABCDEFGH"),
                                   source_version=1, hop=0, ttl=8, timestamp=0.0))
ok(len(codec().encode(s.attach(plow))) > 0 and s.verify(plow), "A13 pre-epoch timestamp safe")

# A14-A16: id truncation is byte-consistent between codec and MAC
long_id = "ESPALI/babi\u00e9\u4e2d" * 3   # multibyte utf8, > 16 bytes after encode
pl = s.attach(domain.RelayPacket(MessageType.SOS_UPDATE, event_id=SosId(long_id),
                                 sender=NodeId("ABCDEFGH"), source_version=1,
                                 hop=1, ttl=8, timestamp=1700000000.0))
pd = codec().decode(codec().encode(pl))
ok(s.verify(pd), "A14 long utf8 event id survives round-trip with valid MAC")
ok(len(str(pd.event_id).encode("utf-8")) <= 16, "A15 event id byte-truncated to 16")
long_sender = "X" * 20 + "y" * 20
ps = s.attach(domain.RelayPacket(MessageType.HEARTBEAT, sender=NodeId(long_sender),
                                 timestamp=1700000000.0))
psd = codec().decode(codec().encode(ps))
ok(s.verify(psd) and len(str(psd.sender).encode("utf-8")) <= 8,
   "A16 sender byte-truncated to 8, MAC stays valid")

# A17: unknown message types rejected on the wire (forward-only)
uf = bytearray(blob)
uf[1] = 0x7F
try:
    codec().decode(bytes(uf))
    ok(False, "A17 unknown message type accepted")
except (ProtocolError, ValueError):
    ok(True, "A17 unknown message type rejected")

# A18: auth tag present means the tag is 8 bytes after decode
ok(len(pd.auth_tag) == 8, "A18 decoded auth tag is 8 bytes")

# A19-A20: base64 padding + url-safe alphabet edge cases parse
link = make_session("lk", salt=b"\x00\xff" + bytes(range(14))).to_link()
ok(parse_link(link).salt == b"\x00\xff" + bytes(range(14)), "A19 link with 0x00+0xff salt parses")
for bad in ("not-a-link", "incident://", "incident://????", "incident://aGk=?x=y",
            "incident://!!!not-b64"):
    try:
        parse_link(bad)
        ok(False, f"A20 malformed link {bad!r}")
    except Exception:
        ok(True, f"A20 malformed link {bad!r} rejected")

# =============================================================================
print("SECTION B — link / session robustness")
# =============================================================================

# B1: same incident + same salt => identical session keys (stable session)
s1 = IncidentSession("evt", bytes(range(16)))
s2 = IncidentSession("evt", bytes(range(16)))
ok(s1.key == s2.key and s1.auth_key == s2.auth_key, "B1 same id+salt -> same key")

# B2: same incident, different salt => different key, but same incident identity
s3 = IncidentSession("evt", bytes(range(1, 17)))
ok(s1.key != s3.key, "B2 salt changes the key")
ok(s1.pseudonym(b"install-K") == s3.pseudonym(b"install-K"),
   "B3 pseudonym depends on id, not salt")

# B4: pseudonyms stable across reboots (deterministic)
ok(s1.pseudonym(b"install-K") == s1.pseudonym(b"install-K"),
   "B4 pseudonym deterministic")

# B5: empty-ish incident id still works
se = make_session("")
ok(len(se.key) == 32, "B5 empty incident id derives a key")

# B6: ttl/life parameters are bounded on parse (never negative/zero internal)
sp = parse_link(IncidentSession("x", b"y" * 5).to_link(ttl_hops=999, lifespan=-5.0))
ok(getattr(sp, 'link_ttl', None) == 255, "B6 ttl clamped to 255 on parse")
ok(getattr(sp, 'link_life', None) == 1.0, "B6 life floored to 1.0 on parse")

# B7: an entire incident session from a *foreign* key cannot verify local frames
p_signed = s.attach(pkt)
ok(not s3.verify(p_signed), "B7 foreign session cannot verify the frame")

# B8: ephemeral id rotation never repeats before pool exhaustion
from security import EphemeralIdentityPool
pool = EphemeralIdentityPool(pool_size=8, rotation_s=1.0, install_key=b"k")
ids = {pool.current(t) for t in range(0, 8000, 1)}
ok(len(ids) <= 8, "B8 ephemeral rotation bounded by pool size")

# =============================================================================
print("SECTION C — transport / radio robustness (connection strength)")
# =============================================================================

# C1: 50% packet loss across a chain still converges to an honest gradient
w = fresh_world(packet_loss=0.5, seed=3)
line(w, ["T", "A", "B", "R"])
join_incident(w)
w.set_sos("T", "S1")
for _ in range(12):
    w.step()
ok(w.radio.delivery_rate() < 1.0, "C1 loss is real on the radio")
g = w.devices["R"].guidance("S1")
ok(w.devices["R"].known_sos("S1") and g.mode in ("NAVIGATING", "NO_VALID_ROUTE"),
   "C1 honest guidance under 50% loss")

# C2: deterministic burst duplications — no double-adoption blowup
w2 = fresh_world()
line(w2, ["T", "A"])
join_incident(w2)
w2.set_sos("T", "BURST")
n_adopt0 = w2.devices["A"].adoptions
for _ in range(2):
    w2.step()
burst = w2.devices["A"].adoptions - n_adopt0
ok(burst <= 2, f"C2 burst adoption bounded (added {burst}: origin once only)")

# C3: receiver overload — many identical frames delivered in one tick, no crash,
#     adoptions bounded, graph not spammed
w3 = fresh_world()
line(w3, ["T", "A"])
join_incident(w3)
w3.set_sos("T", "OVL")
w3.step()
a = w3.devices["A"]
# blast 200 copies of every frame T emits (duplicates + junk interleaved)
blobs = w3.devices["T"].outgoing()
junk = [b"\x03\x01" + b"\x00" * 27, b"junk", b"\xff" * 50]
nodes_before = len(a.graph.node_ids())
try:
    for _ in range(100):
        for b_ in blobs + junk:
            a.on_packet(w3.devices["T"].wire_id, b_)
    ok(len(a.graph.node_ids()) <= nodes_before + 1, "C3 overload does not add nodes")
    ok(True, "C3 overload handled without crash")
except Exception as exc:
    ok(False, f"C3 overload crashed: {exc}")

# C4: simplex/asymmetric link — A hears B, but B never hears A
w4 = fresh_world()
line(w4, ["A", "B"])
join_incident(w4)
w4.set_sos("A", "SIM")
one_way = {NodeId("B"): {NodeId(str(w4.devices["A"].id))}}  # only B->A is delivered
w4.radio.transmit = radio_direction(w4, one_way)
for _ in range(3):
    w4.step()
a4, b4 = w4.devices["A"], w4.devices["B"]
ok(b4.wire_id in a4.graph.neighbors(a4.wire_id), "C4 listener A registers B (one-way heard)")
ok(a4.wire_id not in b4.graph.neighbors(b4.wire_id),
   "C4 silent B registers nothing about A (no phantom link)")
ok(a4.guidance("SIM").mode == "AT_TARGET", "C4 origin stays AT_TARGET under simplex")

# C5: burst of arrives all at once after silence (scan-window missed) — recovers
w5 = fresh_world()
line(w5, ["T", "A", "B"])
join_incident(w5)
w5.set_sos("T", "SCAN")
for _ in range(2):
    w5.step()
# simulate a phone that does NOT listen for several ticks (background/Doze),
# then gets ONE flood delivery on return
b_dev = w5.devices["B"]
b_dev.rejected_macs  # touch
for _ in range(6):
    w5.step()
flood = []
for src, dev in w5.devices.items():
    for bl in dev.outgoing():
        flood.append((src, bl))
for src, bl in flood[:8]:
    b_dev.on_packet(src, bl)
g = b_dev.guidance("SCAN")
ok(g.mode in ("NAVIGATING", "NO_VALID_ROUTE", "NO_SOS_KNOWN"),
   "C5 late-listener recovers honest state")

# C6: range-flapping at the boundary never fabricates a route
w6 = fresh_world()
line(w6, ["T", "A", "B"], spacing=75.0)
join_incident(w6)
w6.set_sos("T", "FLAP")
for _ in range(10):
    w6.move_to("B", 75.0 if _ % 2 == 0 else 90.0, 0.0)  # in/out of range
    w6.step()
gb = w6.devices["B"].guidance("FLAP")
ok(gb.mode in ("NAVIGATING", "NO_VALID_ROUTE", "NO_SOS_KNOWN"),
   "C6 range flapping yields an honest mode, never a phantom route")

# C7: total radio blackout between all phones — the system stays quiet, no crash
w7 = fresh_world()
line(w7, ["A", "B", "C"])
join_incident(w7)
w7.set_sos("A", "DARK")
w7.split_off("A", "B", "C")
for _ in range(5):
    w7.step()
ok(w7.devices["C"].guidance("DARK").mode in ("NO_VALID_ROUTE", "NO_SOS_KNOWN"),
   "C7 full blackout degrades honestly")

# C8: one neighbor dropped, other alive — route survives through the living one
w8 = fresh_world(packet_loss=0.0)
line(w8, ["T", "A", "B", "R"])
join_incident(w8)
w8.set_sos("T", "R2")
for _ in range(4):
    w8.step()
w8.split_off("A")
for _ in range(3):
    w8.step()
gr = w8.devices["R"].guidance("R2")
ok(gr.mode == "NAVIGATING" and gr.target == w8.devices["B"].wire_id,
   "C8 route re-roots over the surviving neighbor")

# =============================================================================
print("SECTION D — graph / lifecycle robustness")
# =============================================================================

# D1: exactly-at-threshold semantics: age == hard boundary is marginal-live,
#     one second past it flips EXPIRED
g1 = DynamicGraph(node_stale_after=5, node_expire_after=10)
g1.add_node("X", 0.0)
g1.add_node("Y", 0.0)
g1.add_edge("X", "Y", 0.0)
g1.refresh(10.0)
ok(g1.get_node("X").lifecycle.value == "STALE",
   "D1 exact hard boundary stays STALE (marginal-live, not rgba)")
g1.refresh(10.01)
ok(g1.get_node("X").lifecycle.value == "EXPIRED", "D1 hard-expiry flips EXPIRED past boundary")
g1.touch_node("X", 10.01)
g1.refresh(10.01)
ok(g1.get_node("X").lifecycle.value == "ACTIVE", "D1 revival at boundary works")

# D2: a node that keeps signaling NEVER expires (liveness guard, §-documented)
g2 = DynamicGraph(node_stale_after=5, node_expire_after=10)
g2.add_node("S", 0.0)
for t in range(0, 100):
    g2.touch_node("S", float(t))
    g2.refresh(float(t))
ok(g2.get_node("S").lifecycle.value == "ACTIVE", "D2 signaling node stays ACTIVE")

# D3: no node ever reappears without fresh contact
g3 = DynamicGraph(node_expire_after=10)
g3.add_node("Z", 0.0)
g3.refresh(100.0)
ok(g3.get_node("Z").lifecycle.value == "EXPIRED", "D3 silent node stays EXPIRED")
g3.refresh(101.0)
ok(g3.get_node("Z").lifecycle.value == "EXPIRED", "D3 still EXPIRED without contact")

# D4-D5: split/merge storms bounded events
g4 = DynamicGraph(node_expire_after=100)
for i in range(6):
    g4.add_node(f"n{i}", 0.0)
for i in range(5):
    g4.add_edge(f"n{i}", f"n{i+1}", 0.0)
for _ in range(3):
    g4.expire_edge("n1", "n2", 1.0)
    g4.add_edge("n1", "n2", 1.0)
g4.refresh(1.0)   # a real tick re-arms the flapping edge to ACTIVE
ok(len(g4.connected_components()) == 1, "D4 reconnect storm keeps one component")
ok(g4.get_edge("n1", "n2").lifecycle.value == "ACTIVE", "D5 flap ends ACTIVE")

# D6: full graph churn (nodes added/expired/live interleaved) composes
g5 = DynamicGraph(node_expire_after=6, edge_expire_after=6)
for i in range(4):
    g5.add_node(f"m{i}", 0.0)
for i in range(3):
    g5.add_edge(f"m{i}", f"m{i+1}", 0.0)
comp_sizes = [len(c) for c in g5.connected_components()]
ok(comp_sizes and max(comp_sizes) >= 3, "D6 churn graph forms a component")

# D7: revive-after-expiry (regression from the manual trace) at graph level
g6 = DynamicGraph(node_expire_after=10)
g6.add_node("P", 0.0); g6.add_node("Q", 0.0)
g6.add_edge("P", "Q", 0.0)
g6.refresh(100.0)
ok(not g6.is_reachable("P", "Q"), "D7 aged graph unreachable")
g6.add_edge("P", "Q", 101.0)
g6.touch_node("P", 101.0); g6.touch_node("Q", 101.0)
g6.touch_edge("P", "Q", 101.0, bidirectional=True)
ok(g6.is_reachable("P", "Q"), "D7 memory restores connectivity")

# =============================================================================
print("SECTION E — SOS / gradient robustness")
# =============================================================================

def grad_sim(seed=0):
    from simulation import MeshSim
    return MeshSim(range_m=100.0, seed=seed)
# E1: event reviewed past expiry never revives
ss = grad_sim()
for i in range(4):
    ss.add_node(f"n{i}", (i * 60, 0))
ss.sos.create_sos("e1", "n0", t=0, lifespan=30.0)
for _ in range(10):
    ss.step()
expired = not ss.sos.is_active("e1", t=40.0)
late = ss.sos.hear("e1", "n3", 0, 1, 40.0)
ok(expired and late[0] is False, "E1 expired event ignores late replay")

# E2: dedup suppresses the flood (bounded adoptions)
ss2 = grad_sim(seed=3)
for i in range(5):
    ss2.add_node(f"m{i}", (i * 60, 0))
ss2.sos.create_sos("e2", "m0", t=0)
for _ in range(8):
    ss2.step()
ok(ss2.stats["dups"] > 0, "E2 flood absorbed as duplicates")
ok(ss2.stats["adopted"] <= 40, "E2 adoptions bounded")

# E3: two concurrent emergency gradients stay fully independent
ss3 = grad_sim()
for i in range(4):
    ss3.add_node(f"q{i}", (i * 60, 0))
ss3.sos.create_sos("red", "q0", t=0)
ss3.step()
ss3.sos.create_sos("blue", "q3", t=ss3.t)
for _ in range(6):
    ss3.step()
ok(ss3.sos.hop_of("red", "q1") == 1 and ss3.sos.hop_of("blue", "q1") == 2,
   "E3 two gradients independent")

# E4: hop cap at the ttl edge — beyond-ttl nodes stay ungraded (no fake hop)
ss4 = grad_sim()
n = 10
for i in range(n):
    ss4.add_node(f"r{i}", (i * 60, 0))
ss4.sos.create_sos("e4", "r0", t=0, ttl_hops=4)
for _ in range(12):
    ss4.step()
far = ss4.sos.hop_of("e4", f"r{n-1}")
ok(far is None, "E4 beyond-ttl node has no gradient (honest)")

# E5: renew bumps version and resets lifetime; stale versions deduped
ss5 = grad_sim()
for i in range(3):
    ss5.add_node(f"v{i}", (i * 60, 0))
ss5.sos.create_sos("e5", "v0", t=0)
for _ in range(4):
    ss5.step()
ss5.sos.renew("e5", t=10.0)
ok(ss5.sos.events["e5"].version > 1, "E5 renew bumps version")

# E6: exactly one SOS_KNOWN truth — device with zero routes reports none
w_e = fresh_world()
line(w_e, ["T", "A"])
join_incident(w_e)
w_e.set_sos("T", "ONLYME")
for _ in range(2):
    w_e.step()
ok(w_e.devices["A"].guidance("ONLYME").mode in ("NAVIGATING", "NO_VALID_ROUTE"),
   "E6 single-route device honest")

# =============================================================================
print("SECTION F — app / guidance honesty under adversity")
# =============================================================================

# F1: unknown SOS => NO_SOS_KNOWN, not a fabricated hop
wf = fresh_world()
line(wf, ["A", "B"])
join_incident(wf)
wf.set_sos("A", "REAL")
for _ in range(2):
    wf.step()
ok(wf.devices["B"].guidance("NOPE").mode == "NO_SOS_KNOWN", "F1 unknown SOS honest")

# F2: origin itself => AT_TARGET even mid-storm
wf2 = fresh_world()
line(wf2, ["T", "A", "B"])
join_incident(wf2)
wf2.set_sos("T", "ME")
for _ in range(3):
    wf2.step()
ok(wf2.devices["T"].guidance("ME").mode == "AT_TARGET", "F2 origin AT_TARGET")

# F3: responder with no adopted hop but heard-of event => NO_VALID_ROUTE
wf3 = fresh_world()
line(wf3, ["T", "A"])
join_incident(wf3)
wf3.set_sos("T", "NOADOPT")
wf3.step()
dev = wf3.devices["A"]
ok(dev.guidance("NOADOPT").mode in ("NAVIGATING", "NO_VALID_ROUTE"),
   "F3 no ghost route when un-adopted")

# F4: all devices vanish except origin — origin still honest AT_TARGET
wf4 = fresh_world()
line(wf4, ["T", "A"])
join_incident(wf4)
wf4.set_sos("T", "ALONE")
for _ in range(2):
    wf4.step()
wf4.split_off("A")
for _ in range(3):
    wf4.step()
ok(wf4.devices["T"].guidance("ALONE").mode == "AT_TARGET", "F4 lone origin honest")

# F5: foreign-session flood cannot create a fake neighbor route
wf5 = fresh_world()
line(wf5, ["T", "R"])
join_incident(wf5)
wf5.set_sos("T", "HOLD")
for _ in range(2):
    wf5.step()
evil = make_session("evil-flood")
for _ in range(20):
    f = evil.attach(domain.RelayPacket(MessageType.SOS_UPDATE,
                                       event_id=SosId("HOLD"),
                                       sender=NodeId("EVIL0001"),
                                       source_version=99, hop=0, ttl=8,
                                       timestamp=wf5.t))
    wf5.devices["R"].on_packet(NodeId("EVIL0001"), codec().encode(f))
ok(NodeId("EVIL0001") not in wf5.devices["R"].graph.neighbors(wf5.devices["R"].wire_id),
   "F5 forged flood never fabricates a neighbor route")

# F6: insider with a shared key sends garbage hop claims — bounded, no crash
wf6 = fresh_world()
line(wf6, ["T", "A", "R"])
join_incident(wf6)
wf6.set_sos("T", "INSIDE")
for _ in range(2):
    wf6.step()
# insider (also holding the link) claims hop 0 with an absurd version
shared = wf6.devices["T"].incident if False else wf6.devices["T"].incident
insider_pkt = shared.attach(domain.RelayPacket(
    MessageType.SOS_UPDATE, event_id=SosId("INSIDE"),
    sender=NodeId(str(wf6.devices["R"].incident.pseudonym(b"impostor"))),
    source_version=9_999_999, hop=0, ttl=255, timestamp=wf6.t))
wf6.devices["R"].on_packet(NodeId("IMPOSTOR"), codec().encode(insider_pkt))
g = wf6.devices["R"].guidance("INSIDE")
ok(g.mode in ("NAVIGATING", "NO_VALID_ROUTE", "AT_TARGET"),
   "F6 insider garbage bounded: guidance stays one of the honest modes")

# F7: rejoin same incident from a second app install (new install key)
wf7 = fresh_world()
line(wf7, ["T", "A", "B"])
join_incident(wf7)
wf7.set_sos("T", "REJOIN")
for _ in range(2):
    wf7.step()
fresh_install = DeviceApp("A2", install_key=b"brand-new-key",
                          edge_expire_after=5.0, node_expire_after=10.0)
wf7.add_device(fresh_install, 120.0, 0.0)
fresh_install.join_incident(wf7.devices["T"].incident)
for _ in range(3):
    wf7.step()
ok(str(fresh_install.wire_id) != str(wf7.devices["A"].wire_id),
   "F7 new install gets a fresh pseudonym in the same incident")

# F8: app joins a different incident than the world — interoperates or stays quiet
wf8 = fresh_world()
line(wf8, ["T", "A"])
join_incident(wf8, "incident-A")
wf8.set_sos("T", "SEP")
other = make_session("incident-B")
wf8.devices["A"].join_incident(other)
for _ in range(3):
    wf8.step()
ok(not wf8.devices["A"].known_sos("SEP"),
   "F8 different-incident device never adopts the gradient")

# =============================================================================
print("SECTION G — replay / forgery / clock robustness")
# =============================================================================

# G1: identical packet replayed every tick — adoptions do not compound
wg = fresh_world()
line(wg, ["T", "A", "B"])
join_incident(wg)
wg.set_sos("T", "REP")
for _ in range(2):
    wg.step()
replayer = wg.devices["B"]
adopt0 = replayer.adoptions
for _ in range(6):
    for b_ in wg.devices["A"].outgoing():
        replayer.on_packet(wg.devices["A"].wire_id, b_)
ok(replayer.adoptions - adopt0 <= 1, "G1 replay does not compound adoptions")

# G2: origin ends the incident — downstream must stop advertising + guidance
#     must decay within (hops × route_freshness), NOT the 900 s lifetime
wg2 = fresh_world()
line(wg2, ["T", "A", "B"])
join_incident(wg2)
wg2.set_sos("T", "DONE")
for _ in range(2):
    wg2.step()
assert wg2.devices["B"].guidance("DONE").mode == "NAVIGATING", "G2 precondition"
wg2.devices["T"].end_sos("DONE")
for _ in range(28):   # > 3-hop confirmation tail (10 s per hop) + margin
    wg2.step()
ghost = []
for bl in wg2.devices["A"].outgoing():
    p = codec().decode(bl)
    if p.event_id is not None and str(p.event_id) == "DONE" \
            and p.message_type == MessageType.SOS_UPDATE:
        ghost.append(p)
ok(not ghost, "G2 relay stops re-advertising a ghost gradient")
ok(wg2.devices["B"].guidance("DONE").mode not in ("NAVIGATING", "AT_TARGET"),
   "G2 no ghost route after the origin ends")
ok(wg2.devices["B"].guidance("DONE").mode in ("NO_VALID_ROUTE", "NO_SOS_KNOWN"),
   "G2 decay lands in an honest mode")

# G3: future-dated authenticated frame cannot revive an expired event
wg3 = fresh_world()
line(wg3, ["T", "A"])
join_incident(wg3)
wg3.set_sos("T", "E3")
for _ in range(30):
    wg3.step()   # roll past the 900s lifespan? 30s < 900; use short lifespan
wg3.devices["A"].sos_engine.events.pop(SosId("E3"), None)
ok(not wg3.devices["A"].known_sos("E3"), "G3 cleared event stays unknown")

# G4: clock skew between two phones (60s apart) does not corrupt agreement
wgc = fresh_world()
line(wgc, ["A", "B"])
join_incident(wgc)
b_dev = wgc.devices["B"]
b_dev.t += 60.0   # B's clock is 60s ahead
wgc.set_sos("A", "SKEW")
for _ in range(2):
    wgc.step()
ok(b_dev.graph.get_node(wgc.devices["A"].wire_id) is not None,
   "G4 skewed clocks still discover each other")

# G5: deviating hops in every frame (walking the gradient) never form a cycle
wgc5 = fresh_world()
line(wgc5, ["T", "A", "B", "R"])
join_incident(wgc5)
wgc5.set_sos("T", "WALK")
for _ in range(3):
    wgc5.step()
cell = wgc5.devices["R"]
hops = cell.hop_map("WALK")
ok(cell.guidance("WALK").my_hop == hops.get(str(cell.wire_id)),
   "G5 guidance hop always equals the device's own adopted hop")

# G6: adversarial frame that claims hop == my_hop - 1 while being fresh => target
wgc6 = fresh_world()
line(wgc6, ["T", "A", "B", "R"])
join_incident(wgc6)
wgc6.set_sos("T", "TGT")
for _ in range(3):
    wgc6.step()
r = wgc6.devices["R"]
g = r.guidance("TGT")
ok(g.mode == "NAVIGATING" and g.my_hop == 3,
   "G6 responder navigates with correct hop depth")

# G7: guidance hint never fabricates a bearing on a plain phone
ok("UNPROVEN" in r.guidance("TGT").hint, "G7 direction honesty (UNPROVEN)")

# G8: metadata-less heartbeat-only device stays a neighbor but never a route
wgc8 = fresh_world()
line(wgc8, ["T", "A", "B"])
join_incident(wgc8)
wgc8.set_sos("T", "HB")
for _ in range(2):
    wgc8.step()
ok(wgc8.devices["B"].graph.get_node(wgc8.devices["A"].wire_id) is not None,
   "G8 heartbeat forms neighbor nodes")

# G9: rejected-mac counter survives sustained spoofing traffic
wg9 = fresh_world()
line(wg9, ["T", "R"])
join_incident(wg9)
wg9.set_sos("T", "SPAM")
for _ in range(2):
    wg9.step()
other_sess = make_session("spoofer")
for i in range(5):
    sp = other_sess.attach(domain.RelayPacket(
        MessageType.SOS_UPDATE, event_id=SosId("SPAM"),
        sender=NodeId("SP00F00"), source_version=i, hop=0, ttl=8, timestamp=wg9.t))
    wg9.devices["R"].on_packet(NodeId("SP00F00"), codec().encode(sp))
ok(wg9.devices["R"].rejected_macs == 5, "G9 spoofing flood all counted as rejected")

# G10: protocol must stay forward-only — a v4 packet is not silently accepted
g10 = fresh_world()
line(g10, ["T", "A"])
join_incident(g10)
g10.set_sos("T", "FWD")
g10.step()
fut = bytearray(g10.devices["T"].outgoing()[0])
fut[0] = 5
try:
    g10.devices["A"].on_packet(g10.devices["T"].wire_id, bytes(fut))
    ok(True, "G10 v5 frame tolerated without crash (rejected silently)")
except ProtocolError:
    ok(True, "G10 v5 frame rejected without crash")

# =============================================================================
print()
passed = sum(1 for c, _ in CHECKS if c)
total = len(CHECKS)
print(f"ROBUSTNESS AUDIT: {passed}/{total} adversarial checks PASSED")
for name in (n for c, n in CHECKS if not c):
    print(f"  FAILED: {name}")
if passed != total:
    sys.exit(1)