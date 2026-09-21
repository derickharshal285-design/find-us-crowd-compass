"""Block 1 — Domain types (spec §63 Block 1, §65, §73).

Pure type definitions. No Bluetooth code. Every optional measurement is an
explicit null with an explicit status -- never 0 (spec §65, ADR-003/005).
"""
from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any, Optional

TIME_NONE = None  # explicit "no timestamp" marker (spec §65: null, not 0)


def now() -> float:
    return time.time()


# ---- Identifiers ---------------------------------------------------------

class NodeId(str):
    """Ephemeral identifier for a phone/node in the graph.

    Ephemeral by policy (spec §18, ADR-011): keys must not be permanent
    personal identities.
    """


class EdgeId(str):
    """Undirected edge identifier. Canonical form: 'u->v' with u < v."""


def edge_id(u: Any, v: Any) -> EdgeId:
    a, b = str(u), str(v)
    return EdgeId(f"{a}->{b}" if a < b else f"{b}->{a}")


class SosId(str):
    """Identifier of a single emergency event."""


# ---- Lifecycle / status enums (spec §19, §65, §73) -----------------------

class NodeLifecycle(enum.Enum):
    DISCOVERED = "DISCOVERED"
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    EXPIRED = "EXPIRED"


class EdgeLifecycle(enum.Enum):
    SEEN = "SEEN"
    ACTIVE = "ACTIVE"
    AGING = "AGING"
    EXPIRED = "EXPIRED"


class MeasurementStatus(enum.Enum):
    """spec §73 error-handling categories."""
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    CONFLICTING = "CONFLICTING"
    UNAVAILABLE = "UNAVAILABLE"
    ESTIMATED = "ESTIMATED"
    MEASURED = "MEASURED"
    VERIFIED_UNDER_TEST = "VERIFIED UNDER TEST"


class MeasurementSource(enum.Enum):
    BLE_RSSI = "BLE_RSSI"
    UWB = "UWB"
    DIRECTION_FINDING = "DIRECTION_FINDING"
    BAROMETER = "BAROMETER"
    IMU = "IMU"
    GPS = "GPS"
    WIFI = "WIFI"
    ACOUSTIC = "ACOUSTIC"
    OPTICAL = "OPTICAL"
    USER = "USER"
    SIMULATED_GROUND_TRUTH = "SIMULATED_GROUND_TRUTH"


class SosStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"


class MessageType(enum.Enum):
    HEARTBEAT = 1
    ADVERTISEMENT = 2
    SOS = 3
    SOS_UPDATE = 4
    RELAY = 5
    RELATIONSHIP = 6
    CAPABILITY = 7
    JOIN = 8


# ---- Domain records ------------------------------------------------------

@dataclass
class CapabilityProfile:
    """spec §54 capability negotiation data."""
    device_id: str
    ble_support: bool = False
    scan_support: bool = False
    advertise_support: bool = False
    connect_support: bool = False
    uwb: bool = False
    wifi_peer: bool = False
    has_sensors: bool = False
    os: Optional[str] = None
    os_version: Optional[str] = None
    background_assumptions: str = "unknown"


@dataclass
class PeerState:
    """State of a node in the graph (spec §18, §19, §24H)."""
    node_id: NodeId
    lifecycle: NodeLifecycle = NodeLifecycle.DISCOVERED
    first_seen: Optional[float] = None
    last_seen: Optional[float] = None
    capabilities: Optional[CapabilityProfile] = None
    position: Optional[tuple] = None  # optional simulated/measured position

    def age(self, t: Optional[float] = None) -> Optional[float]:
        if self.last_seen is None:
            return None
        return (t if t is not None else now()) - self.last_seen


@dataclass
class EdgeState:
    """State of a communication relationship (spec §18–21)."""
    edge_id: EdgeId
    endpoints: tuple
    lifecycle: EdgeLifecycle = EdgeLifecycle.SEEN
    first_seen: Optional[float] = None
    last_seen: Optional[float] = None
    last_bidirectional_exchange: Optional[float] = None
    source: str = "transport"

    def age(self, t: Optional[float] = None) -> Optional[float]:
        if self.last_seen is None:
            return None
        return (t if t is not None else now()) - self.last_seen


@dataclass
class RelationshipMeasurement:
    """A single local spatial measurement (spec §18, §65).

    distance and direction are explicit Optionals. Never 0 when unknown.
    """
    a: Any
    b: Any
    source: MeasurementSource = MeasurementSource.BLE_RSSI
    status: MeasurementStatus = MeasurementStatus.ESTIMATED
    distance: Optional[float] = None
    distance_status: MeasurementStatus = MeasurementStatus.UNKNOWN
    direction: Optional[float] = None
    direction_status: MeasurementStatus = MeasurementStatus.UNKNOWN
    timestamp: Optional[float] = None
    quality: Optional[float] = None
    floor: Optional[int] = None  # None == unknown

    def age(self, t: Optional[float] = None) -> Optional[float]:
        if self.timestamp is None:
            return None
        return (t if t is not None else now()) - self.timestamp


@dataclass
class GraphSnapshot:
    """Immutable read of the graph (spec §63 Block 2)."""
    generated_at: float
    nodes: dict = field(default_factory=dict)
    edges: dict = field(default_factory=dict)
    components: list = field(default_factory=list)
    hop_from: Optional[Any] = None  # source SOS/origin when computed

    def summary(self) -> str:
        return (f"GraphSnapshot(nodes={len(self.nodes)}, edges={len(self.edges)}, "
                f"components={len(self.components)})")


@dataclass
class SOS:
    """A single emergency event (spec §22, §40–41)."""
    sos_id: SosId
    origin: NodeId
    created_at: float
    version: int = 1
    status: SosStatus = SosStatus.ACTIVE
    ttl_hops: int = 8              # max hop count for propagation
    lifespan_seconds: Optional[float] = 900.0
    expires_at: Optional[float] = None
    metadata: dict = field(default_factory=dict)

    def remaining_seconds(self, t: Optional[float] = None) -> Optional[float]:
        if self.expires_at is None:
            return None
        t = t if t is not None else now()
        return max(0.0, self.expires_at - t)


@dataclass
class SOSUpdate:
    """Versioned gradient update (spec §22, §63 Block 4)."""
    sos_id: SosId
    sender: NodeId
    hop: int
    version: int = 1
    ttl: int = 8
    timestamp: float = TIME_NONE
    seen: bool = False  # simulator: duplicate already handled


@dataclass
class RelayPacket:
    """Protocol payload (spec §23, §63 Block 6).

    Carries no state of its own; the transport layer handles framing.
    """
    message_type: MessageType = MessageType.HEARTBEAT
    event_id: Optional[SosId] = None
    sender: Optional[NodeId] = None
    source_version: int = 0    # origin/event sequence or version (§23)
    hop: int = 0
    ttl: int = 8
    timestamp: float = TIME_NONE
    relationship_meta: Optional[RelationshipMeasurement] = None
    measurement_meta: Optional[RelationshipMeasurement] = None
    auth_tag: Optional[bytes] = None  # 8-byte incident MAC (ADR-010, Protocol v3)