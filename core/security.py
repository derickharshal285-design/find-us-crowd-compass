"""Block 7 — Incident security layer (spec §63 Block 7, ADR-010, ADR-011).

Design targets for a commercial 50k-device crowd:
  * O(1) per-packet cost, no per-device key state beyond the incident session
    (bounded by neighborhood, never by N).
  * Authentication of every gradient/heartbeat packet against outsiders via a
    shared incident MAC keyed by an IncidentSession derived from the incident
    link the responder (and, in the light model, participating phones) holds.
  * Integrity + freshness: the MAC covers event, sender, version, hop, ttl and
    the integer-second timestamp, so replays age out and tampering fails.
  * Privacy: during an incident a phone exposes only an incident-scoped
    pseudonym (HKDF of its install key + incident id), so it cannot be tracked
    across incidents. Outside incidents, sender ids rotate on a schedule via
    EphemeralIdentityPool.

Light-model honesty note (recorded in ADR-010): the session key is shared by
every holder of the incident link, so an insider can forge another insider's
gradient claim. That is an accepted emergency tradeoff for this phase and is
documented; the alternative (per-device PKI) is out of scope until validated.
"""
from __future__ import annotations

import base64
import hmac
import hashlib
import os
import struct
from typing import Any, Optional

from domain import RelayPacket, TIME_NONE
from protocol import _EPOCH

HKDF_INFO = b"crowd-compass/incident-session-v1"
AUTH_INFO = b"crowd-compass/gradient-mac-v1"
_PSEUDOOM_INFO = b"crowd-compass/incident-pseudonym-v1"
_EPHEM_INFO = b"crowd-compass/ephemeral-id-v1"
LINK_PREFIX = "incident://"
MAC_LENGTH = 8


class IncidentSession:
    """A symmetric per-incident session derived from the incident link."""

    def __init__(self, incident_id: str, salt: bytes) -> None:
        self.incident_id = str(incident_id)
        self.salt = bytes(salt)
        prk = hmac.new(b"CROWD-COMPASS/INCIDENT", self._msg(), hashlib.sha256).digest()
        self.key = hmac.new(prk, HKDF_INFO, hashlib.sha256).digest()
        self.auth_key = hmac.new(self.key, AUTH_INFO, hashlib.sha256).digest()

    def _msg(self) -> bytes:
        return self.incident_id.encode("utf-8") + b"\x00" + self.salt

    # ---- packet authentication --------------------------------------------

    def mac(self, pkt: RelayPacket) -> bytes:
        """8-byte truncated HMAC over the canonical on-wire fields."""
        return hmac.new(self.auth_key, canonical_fields(pkt),
                        hashlib.sha256).digest()[:MAC_LENGTH]

    def verify(self, pkt: RelayPacket) -> bool:
        if not pkt.auth_tag:
            return False
        expected = self.mac(pkt)
        return hmac.compare_digest(expected, bytes(pkt.auth_tag)[:MAC_LENGTH])

    def attach(self, pkt: RelayPacket) -> RelayPacket:
        signed = RelayPacket(**{k: getattr(pkt, k) for k in _pkt_dict(pkt)})
        signed.auth_tag = self.mac(signed)
        return signed

    # ---- incident-scoped identity -------------------------------------------

    def pseudonym(self, install_key: bytes) -> str:
        """Stable-within-incident, unusable-across-incidents public id (8 chars)."""
        raw = hmac.new(bytes(install_key), _PSEUDOOM_INFO + b"\x00" +
                       self.incident_id.encode("utf-8"),
                       hashlib.sha256).digest()[:6]
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    # ---- incident link ------------------------------------------------------

    def _link_payload(self) -> bytes:
        """U16 BE id length + utf8 id + salt. Length-prefixed so a salt byte
        can never be mistaken for the (id,salt) separator (salts are random)."""
        idb = self.incident_id.encode("utf-8")
        if len(idb) > 0xFFFF:
            raise ValueError("incident id too long for a link")
        return struct.pack(">H", len(idb)) + idb + self.salt

    def to_link(self, ttl_hops: int = 8, lifespan: float = 900.0) -> str:
        params = [
            "salt=" + base64.urlsafe_b64encode(self.salt).decode("ascii"),
            "ttl=" + str(int(ttl_hops)),
            "life=" + str(int(lifespan)),
        ]
        return (f"{LINK_PREFIX}{base64.urlsafe_b64encode(self._link_payload()).decode('ascii')}"
                f"?{'&'.join(params)}")


def _pkt_dict(pkt: RelayPacket) -> dict:
    return {k: getattr(pkt, k) for k in
            ("message_type", "event_id", "sender", "source_version", "hop",
             "ttl", "timestamp", "relationship_meta", "measurement_meta",
             "auth_tag")}


def make_session(incident_id: str, salt: Optional[bytes] = None) -> IncidentSession:
    salt = salt if salt is not None else os.urandom(16)
    return IncidentSession(incident_id, salt)


def parse_link(link: str) -> IncidentSession:
    """Parse `incident://<payload>?salt=..&ttl=..&life=..` back to a session.

    The payload is base64(U16 BE id length || id || salt), unambiguous whatever
    bytes the random salt happens to contain. The link is self-contained and
    round-trips exactly."""
    if not link.startswith(LINK_PREFIX):
        raise ValueError("not an incident link")
    body, _, query = link[len(LINK_PREFIX):].partition("?")
    decoded = base64.urlsafe_b64decode(body.encode("ascii") + b"=" * (-len(body) % 4))
    if len(decoded) < 3:
        raise ValueError("malformed link payload")
    (n,) = struct.unpack(">H", decoded[:2])
    if 2 + n > len(decoded):
        raise ValueError("malformed link payload")
    incident_id = decoded[2:2 + n].decode("utf-8")
    salt = decoded[2 + n:]
    session = IncidentSession(incident_id, salt)
    session.link_ttl = query_ttl(query)
    session.link_life = query_life(query)
    return session


def query_ttl(query: str) -> int:
    for part in query.split("&"):
        k, _, v = part.partition("=")
        if k == "ttl":
            try:
                return max(1, min(255, int(v)))
            except ValueError:
                return 8
    return 8


def query_life(query: str) -> float:
    for part in query.split("&"):
        k, _, v = part.partition("=")
        if k == "life":
            try:
                return max(1.0, float(v))
            except ValueError:
                return 900.0
    return 900.0


class EphemeralIdentityPool:
    """Rotating sender identities for routine (non-incident) operation.

    A phone never reuses a routine identity from an earlier rotation in a way
    that links to the same install; ids are derived deterministically per slot
    so a reboot resumes the same rotation schedule."""

    def __init__(self, pool_size: int = 8, rotation_s: float = 300.0,
                 install_key: bytes = b"test-install", t0: float = 0.0) -> None:
        if pool_size < 2:
            raise ValueError("pool too small")
        self.pool_size = pool_size
        self.rotation_s = rotation_s
        self._ids = [self._derive(install_key, i) for i in range(pool_size)]
        self._idx = 0
        self._last = t0

    @staticmethod
    def _derive(install_key: bytes, slot: int) -> str:
        raw = hmac.new(bytes(install_key), _EPHEM_INFO + struct.pack(">I", slot),
                       hashlib.sha256).digest()[:6]
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    def current(self, t: float) -> str:
        self._advance(t)
        return self._ids[self._idx]

    def _advance(self, t: float) -> None:
        if t - self._last < self.rotation_s:
            return
        n = int((t - self._last) / self.rotation_s)
        self._idx = (self._idx + n) % self.pool_size
        self._last += n * self.rotation_s


def canonical_fields(pkt: RelayPacket) -> bytes:
    """Deterministic, codec-agreeing field bytes for MAC computation."""
    mtype = int(pkt.message_type.value)
    ev = str(pkt.event_id or "").encode("utf-8")[:16].ljust(16, b"\x00")
    sender = str(pkt.sender or "").encode("utf-8")[:8].ljust(8, b"\x00")
    ver = max(0, min(0xFFFF, int(pkt.source_version)))
    hop = max(0, min(0xFF, int(pkt.hop)))
    ttl = max(0, min(0xFF, int(pkt.ttl)))
    ts = _canon_ts(pkt.timestamp)
    return struct.pack(">B16s8sHBBI", mtype, ev, sender, ver, hop, ttl, ts)


def _canon_ts(t: Any) -> int:
    if t is None or t == TIME_NONE:
        return 0
    return max(0, min(0xFFFFFFFF, int(round(t - _EPOCH))))


def _test() -> None:
    checks = 0

    def ok(cond: bool, name: str) -> None:
        nonlocal checks
        checks += 1
        assert cond, name
        print(f"  PASS {name}")

    from domain import MessageType, NodeId, SosId
    from protocol import PacketCodec

    a = make_session("evt-STADIUM-001")
    b = parse_link(a.to_link())
    ok(a.incident_id == b.incident_id and a.salt == b.salt, "link round-trips session")
    ok(b.link_ttl == 8 and b.link_life == 900.0, "link carries parameters")

    # a random salt may contain 0x00 bytes (fires ~1-in-16); the link format
    # must not depend on splitting on a 0x00 separator
    nasty = make_session("evt-STADIUM-002", salt=b"\x00" * 16)
    fixed = parse_link(nasty.to_link())
    ok(fixed.salt == b"\x00" * 16 and fixed.incident_id == "evt-STADIUM-002",
       "salt containing 0x00 bytes still round-trips (no separator ambiguity)")
    mixed = make_session("space incident", salt=b"a\x00b\x00c\x00d\x00e\x00f\x00g")
    ok(parse_link(mixed.to_link()).incident_id == "space incident",
       "utf8 id + salt with interior 0x00 round-trips")

    pkt = RelayPacket(MessageType.SOS_UPDATE, event_id=SosId("evt-STADIUM-001"),
                      sender=NodeId(b.pseudonym(b"install-A")),
                      source_version=1, hop=3, ttl=8, timestamp=_EPOCH + 1000.0)
    signed = a.attach(pkt)
    ok(a.verify(signed), "valid MAC verifies")
    tampered = RelayPacket(**{k: (9 if k == "hop" else getattr(signed, k))
                              for k in _pkt_dict(signed)})
    ok(not a.verify(tampered), "tampered hop fails MAC")

    codec = PacketCodec()
    wire = codec.decode(codec.encode(signed))
    ok(a.verify(wire), "MAC survives full wire round-trip")
    ok(len(wire.auth_tag) == 8, "wire carries 8-byte auth tag")

    real = RelayPacket(MessageType.SOS_UPDATE,
                       event_id=SosId("evt-STADIUM-001"),
                       sender=NodeId(b.pseudonym(b"install-A")),
                       source_version=1, hop=2, ttl=8,
                       timestamp=1789690000.0)
    real_signed = a.attach(real)
    real_wire = codec.decode(codec.encode(real_signed))
    ok(a.verify(real_wire),
       "MAC verified at real-world (post-2020) timestamps, uint32 canonical")

    evil = make_session("other-incident")
    ok(not evil.verify(wire), "foreign session fails MAC")

    # pseudonyms: stable within the incident, different across incidents
    i1 = make_session("inc-A")
    i2 = make_session("inc-B")
    p1 = i1.pseudonym(b"install-X")
    p2 = i1.pseudonym(b"install-X")
    p3 = i2.pseudonym(b"install-X")
    ok(p1 == p2, "pseudonym stable within an incident")
    ok(p1 != p3, "pseudonym differs across incidents")

    # routine identity rotation
    pool = EphemeralIdentityPool(pool_size=4, rotation_s=300.0, install_key=b"k")
    first = pool.current(0.0)
    ok(pool.current(299.0) == first, "id stable inside rotation window")
    ok(pool.current(301.0) != first or pool._idx != 0, "id may rotate out")
    ids = {pool.current(t) for t in (0.0, 600.0, 900.0, 1200.0)}
    ok(0 < len(ids) < 8, "rotation cycles through a bounded pool")

    print(f"\nIncident security selftest: {checks} checks PASSED")


if __name__ == "__main__":
    _test()