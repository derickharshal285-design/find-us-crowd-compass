"""Block 6 — Versioned binary protocol codec (spec §63 Block 6, §23, ADR-009).

Deterministic binary layout, explicit schema version, unknown versions are
rejected. Round-trip contract: object -> bytes -> object.

Layout (fixed header + optional blocks):
  byte0      PROTOCOL_VERSION (== 3, Protocol v3 / ADR-010)
  byte1      message_type
  byte2..17  event_id      (16B ascii, NUL padded; zeros if absent)
  byte18..25 sender node   (8B ascii, NUL padded; zeros if absent)
  byte26..27 source_version (uint16 BE)
  byte28     hop
  byte29     ttl
  byte30..33 timestamp     (uint32 BE, seconds since 2000-01-01; 0 if absent)
  byte34     flags
               bit0 has_relationship
               bit1 has_measurement
               bit2 has_auth_tag
  [measurement blocks, each:]
               b0 source
               b1 measurement status
               b2 distance_status
               b3 direction_status
               b4 quality       (int8, -128 => None)
               b5 floor         (int8,  -128 => None)
               b6 has_distance  (0/1)
               b7 has_direction (0/1)
               b8..+3 float32 distance   (if has_distance)
               b12..+3 float32 direction (if has_direction)
  [auth tag: 8 bytes if flag bit2]
"""
from __future__ import annotations

import math
import struct
from typing import Any, Optional, Tuple

from domain import (
    MeasurementSource, MeasurementStatus, MessageType, NodeId, RelayPacket,
    RelationshipMeasurement, SosId, TIME_NONE,
)

PROTOCOL_VERSION = 3
_EPOCH = 946684800.0  # 2000-01-01T00:00:00Z


_SOURCES = list(MeasurementSource)
_STATUSES = list(MeasurementStatus)


class ProtocolError(ValueError):
    pass


class ProtocolVersionError(ProtocolError):
    pass


class ProtocolTruncationError(ProtocolError):
    pass


def _pack_id(s: Any, length: int) -> bytes:
    raw = s.encode("utf-8") if isinstance(s, str) else bytes(s)
    return raw[:length].ljust(length, b"\x00")


class PacketCodec:
    def version(self) -> int:
        return PROTOCOL_VERSION

    # ---- encoding ---------------------------------------------------------

    def encode(self, pkt: RelayPacket) -> bytes:
        flags = 0
        rel_block = b""
        if pkt.relationship_meta is not None:
            flags |= 0x01
            rel_block = self._encode_measurement(pkt.relationship_meta)
        if pkt.measurement_meta is not None:
            flags |= 0x02
            meas_block = self._encode_measurement(pkt.measurement_meta)
            rel_block += meas_block
        auth_block = b""
        if pkt.auth_tag is not None:
            flags |= 0x04
            auth_block = bytes(pkt.auth_tag)[:8].ljust(8, b"\x00")

        event_id = _pack_id(pkt.event_id or "", 16)
        sender = _pack_id(pkt.sender or "", 8)
        timestamp = self._pack_time(pkt.timestamp)
        header = struct.pack(
            ">BB16s8sHBBIB",
            PROTOCOL_VERSION,
            pkt.message_type.value,
            event_id,
            sender,
            max(0, min(65535, int(pkt.source_version))),
            max(0, min(255, int(pkt.hop))),
            max(0, min(255, int(pkt.ttl))),
            timestamp,
            flags,
        )
        return header + rel_block + auth_block

    @staticmethod
    def _pack_time(t: Optional[float]) -> int:
        if not t:
            return 0
        return max(0, min(0xFFFFFFFF, int(round(t - _EPOCH))))

    @staticmethod
    def _clamp_i8(v: int) -> int:
        return max(-128, min(127, int(v)))

    @staticmethod
    def _encode_measurement(m: RelationshipMeasurement) -> bytes:
        has_dist = 1 if m.distance is not None else 0
        has_dir = 1 if m.direction is not None else 0
        quality = (PacketCodec._clamp_i8(round(m.quality))
                   if m.quality is not None else -128)
        floor = (PacketCodec._clamp_i8(m.floor)
                 if m.floor is not None else -128)
        src = _SOURCES.index(m.source)
        status = _STATUSES.index(m.status)
        dstatus = _STATUSES.index(m.distance_status)
        rstatus = _STATUSES.index(m.direction_status)
        head = struct.pack(
            ">BBBBbbBB",
            src,
            status,
            dstatus,
            rstatus,
            quality,
            floor,
            has_dist,
            has_dir,
        )
        body = b""
        if has_dist:
            body += struct.pack(">f", float(m.distance))
        if has_dir:
            body += struct.pack(">f", math.fmod(float(m.direction), 360.0))
        return head + body

    # ---- decoding ---------------------------------------------------------

    def decode(self, blob: bytes) -> RelayPacket:
        if len(blob) < 35:
            raise ProtocolTruncationError(
                f"header needs 35 bytes, got {len(blob)}")
        (ver, mtype, event_id, sender, src_ver, hop, ttl, ts, flags) = \
            struct.unpack(">BB16s8sHBBIB", blob[:35])
        if ver != PROTOCOL_VERSION:
            raise ProtocolVersionError(
                f"unsupported version {ver} (this codec: {PROTOCOL_VERSION})")
        pos = 35
        rel = None
        meas = None
        if flags & 0x01:
            rel, pos = self._decode_measurement(blob, pos)
        if flags & 0x02:
            meas, pos = self._decode_measurement(blob, pos)
        auth = None
        if flags & 0x04:
            auth = blob[pos:pos + 8]
            pos += 8
        return RelayPacket(
            message_type=MessageType(mtype),
            event_id=SosId(event_id.decode("utf-8").rstrip("\x00"))
            if event_id.rstrip(b"\x00") else None,
            sender=NodeId(sender.decode("utf-8").rstrip("\x00"))
            if sender.rstrip(b"\x00") else None,
            source_version=src_ver,
            hop=hop,
            ttl=ttl,
            timestamp=(ts + _EPOCH) if ts else TIME_NONE,
            relationship_meta=rel,
            measurement_meta=meas,
            auth_tag=auth,
        )

    @staticmethod
    def _decode_measurement(blob: bytes, pos: int) -> Tuple[RelationshipMeasurement, int]:
        if pos + 8 > len(blob):
            raise ProtocolTruncationError("measurement block truncated")
        (src, status, dist_st, dir_st, quality_raw, floor_raw, has_dist,
         has_dir) = struct.unpack(">BBBBbbBB", blob[pos:pos + 8])
        pos += 8
        distance = None
        direction = None
        if has_dist:
            if pos + 4 > len(blob):
                raise ProtocolTruncationError("distance float truncated")
            (distance,) = struct.unpack(">f", blob[pos:pos + 4])
            pos += 4
        if has_dir:
            if pos + 4 > len(blob):
                raise ProtocolTruncationError("direction float truncated")
            (direction,) = struct.unpack(">f", blob[pos:pos + 4])
            pos += 4
        m = RelationshipMeasurement(
            a="", b="",  # endpoints are graph-side context, not over the air
            source=_SOURCES[src],
            status=_STATUSES[status],
            distance=distance,
            distance_status=_STATUSES[dist_st],
            direction=direction,
            direction_status=_STATUSES[dir_st],
            timestamp=TIME_NONE,  # carried at packet level
            quality=quality_raw if quality_raw != -128 else None,
            floor=floor_raw if floor_raw != -128 else None,
        )
        return m, pos

    def roundtrip(self, pkt: RelayPacket) -> RelayPacket:
        return self.decode(self.encode(pkt))


def _approx_equal(a: Optional[float], b: Optional[float]) -> bool:
    if a is None or b is None:
        return a is b
    return math.isclose(a, b, rel_tol=1e-3)


def _test() -> None:
    checks = 0

    def ok(cond: bool, name: str) -> None:
        nonlocal checks
        checks += 1
        assert cond, name
        print(f"  PASS {name}")

    codec = PacketCodec()
    rel = RelationshipMeasurement(
        a="n1", b="n2", source=MeasurementSource.BLE_RSSI,
        status=MeasurementStatus.ESTIMATED,
        distance=5.5, distance_status=MeasurementStatus.ESTIMATED,
        direction=90.0, direction_status=MeasurementStatus.UNKNOWN,
        timestamp=TIME_NONE, quality=42, floor=3,
    )
    pkt = RelayPacket(
        message_type=MessageType.SOS_UPDATE,
        event_id=SosId("sos-abc123"),
        sender=NodeId("node42"),
        source_version=7,
        hop=3,
        ttl=8,
        timestamp=_EPOCH + 123456.789,
        relationship_meta=rel,
        measurement_meta=None,
        auth_tag=b"\xde\xad\xbe\xef",
    )
    blob = codec.encode(pkt)
    back = codec.roundtrip(pkt)
    ok(back.message_type == MessageType.SOS_UPDATE, "roundtrip: message_type")
    ok(str(back.event_id) == "sos-abc123", "roundtrip: event_id")
    ok(str(back.sender) == "node42", "roundtrip: sender")
    ok(back.source_version == 7, "roundtrip: source_version")
    ok(back.hop == 3 and back.ttl == 8, "roundtrip: hop/ttl")
    ok(abs(back.timestamp - (_EPOCH + 123456.789)) < 1.0, "roundtrip: timestamp")
    ok(back.auth_tag == b"\xde\xad\xbe\xef".ljust(8, b"\x00"),
       "roundtrip: auth_tag is 8 bytes wire format")
    ok(back.relationship_meta is not None, "roundtrip: relationship present")
    m = back.relationship_meta
    ok(m.source == MeasurementSource.BLE_RSSI, "roundtrip: meta source")
    ok(_approx_equal(m.distance, 5.5), "roundtrip: meta distance")
    ok(_approx_equal(m.direction, 90.0), "roundtrip: meta direction")
    ok(m.quality == 42, "roundtrip: meta quality")
    ok(m.floor == 3, "roundtrip: meta floor")

    # absent optional fields survive as explicit None
    bare = RelayPacket(message_type=MessageType.HEARTBEAT, sender=NodeId("x"))
    back2 = codec.roundtrip(bare)
    ok(back2.relationship_meta is None, "roundtrip: none relationship stays None")
    ok(back2.measurement_meta is None, "roundtrip: none measurement stays None")
    ok(back2.auth_tag is None, "roundtrip: no auth when absent")
    ok(back2.event_id is None, "roundtrip: absent event_id is None")

    # explicit-null data rule (spec §65): None must not become 0
    rawnull = RelationshipMeasurement(
        a="a", b="b", source=MeasurementSource.GPS,
        distance=None, distance_status=MeasurementStatus.UNKNOWN,
        direction=None, direction_status=MeasurementStatus.UNKNOWN,
    )
    b3 = codec.roundtrip(
        RelayPacket(message_type=MessageType.ADVERTISEMENT,
                    sender=NodeId("s"), relationship_meta=rawnull))
    ok(b3.relationship_meta.distance is None, "null distance stays null")
    ok(b3.relationship_meta.direction is None, "null direction stays null")
    ok(b3.relationship_meta.direction_status == MeasurementStatus.UNKNOWN,
       "UNKNOWN status preserved")

    # unknown version rejected (spec §63 Block 6)
    evil = bytearray(blob)
    evil[0] = 99
    try:
        codec.decode(bytes(evil))
        ok(False, "unknown version must raise ProtocolVersionError")
    except ProtocolVersionError:
        ok(True, "unknown version rejected")

    # truncation rejected
    try:
        codec.decode(blob[:8])
        ok(False, "short blob must raise ProtocolTruncationError")
    except (ProtocolTruncationError, ProtocolVersionError):
        ok(True, "truncated blob rejected")

    # deterministic encoding
    ok(codec.encode(bare) == codec.encode(bare), "encoding is deterministic")

    print(f"\nProtocol codec selftest: {checks} checks PASSED")


if __name__ == "__main__":
    _test()