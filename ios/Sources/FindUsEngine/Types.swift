import Foundation

/// Value types mirroring core/domain.py (verified Python reference).
public enum EngineConstants {
    public static let protocolVersion: UInt8 = 3
    public static let authTagBytes = 8
    public static let epoch = 946684800.0
    public static let timeNone = -1.0
}

public struct NodeId: Hashable, Comparable, CustomStringConvertible {
    public let value: String
    public init(_ value: String) { self.value = value }
    public var description: String { value }
    public static func < (a: NodeId, b: NodeId) -> Bool { a.value < b.value }
}

public struct SosId: Hashable, Comparable, CustomStringConvertible {
    public let value: String
    public init(_ value: String) { self.value = value }
    public var description: String { value }
    public static func < (a: SosId, b: SosId) -> Bool { a.value < b.value }
}

public enum MessageType: Int, CaseIterable {
    case heartbeat = 1, advertisement = 2, sos = 3, sosUpdate = 4,
         relay = 5, relationship = 6, capability = 7, join = 8
    public init?(wire: UInt8) { self.init(rawValue: Int(wire)) }
}

public enum NodeLifecycle { case discovered, active, stale, expired }
public enum EdgeLifecycle { case seen, active, aging, expired }
public enum SosStatus { case active, expired }

public struct RelayPacket: Equatable {
    public var messageType: MessageType
    public var eventId: SosId?
    public var sender: NodeId?
    public var sourceVersion: Int
    public var hop: Int
    public var ttl: Int
    public var timestamp: Double
    public var authTag: Data?

    public init(messageType: MessageType = .heartbeat,
                eventId: SosId? = nil,
                sender: NodeId? = nil,
                sourceVersion: Int = 1,
                hop: Int = 0,
                ttl: Int = 8,
                timestamp: Double = EngineConstants.timeNone,
                authTag: Data? = nil) {
        self.messageType = messageType
        self.eventId = eventId
        self.sender = sender
        self.sourceVersion = sourceVersion
        self.hop = hop
        self.ttl = ttl
        self.timestamp = timestamp
        self.authTag = authTag
    }
}

public struct HopAdvertisement: Equatable {
    public let hop: Int
    public let version: Int
    public let t: Double
    public init(hop: Int, version: Int, t: Double) {
        self.hop = hop; self.version = version; self.t = t
    }
}

public struct HopState: Equatable {
    public let hop: Int
    public let version: Int
    public let updatedAt: Double
}

public final class Sos {
    public let id: SosId
    public let origin: NodeId
    public let createdAt: Double
    public var version: Int
    public let ttlHops: Int
    public let lifespanSeconds: Double?
    public var expiresAt: Double?
    public var status: SosStatus

    public init(id: SosId, origin: NodeId, createdAt: Double, version: Int = 1,
                ttlHops: Int = 8, lifespanSeconds: Double? = 900.0,
                expiresAt: Double? = nil, status: SosStatus = .active) {
        self.id = id; self.origin = origin; self.createdAt = createdAt
        self.version = version; self.ttlHops = ttlHops
        self.lifespanSeconds = lifespanSeconds
        self.expiresAt = expiresAt
        self.status = status
    }
}