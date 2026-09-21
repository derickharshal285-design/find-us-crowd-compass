package com.findus.crowdcompass.engine

/** Value types and enums mirroring the verified Python reference (core/domain.py). */
object Engine {

    const val PROTOCOL_VERSION = 3
    const val AUTH_TAG_BYTES = 8
    const val EPOCH = 946684800.0
    const val TIME_NONE = -1.0
}

/** Fixed-size string ids. Wire/adjacency always use the String value. */
data class NodeId(val value: String) {
    override fun toString(): String = value
}

data class SosId(val value: String) {
    override fun toString(): String = value
}

enum class MessageType(val wire: Int) {
    HEARTBEAT(1), ADVERTISEMENT(2), SOS(3), SOS_UPDATE(4),
    RELAY(5), RELATIONSHIP(6), CAPABILITY(7), JOIN(8);

    companion object {
        fun fromWire(v: Int): MessageType? = entries.firstOrNull { it.wire == v }
    }
}

enum class NodeLifecycle { DISCOVERED, ACTIVE, STALE, EXPIRED }

enum class EdgeLifecycle { SEEN, ACTIVE, AGING, EXPIRED }

enum class SosStatus { ACTIVE, EXPIRED }

/** A single wire frame. `timestamp` is wall-clock seconds (float); auth_tag is 8 bytes. */
data class RelayPacket(
    val messageType: MessageType = MessageType.HEARTBEAT,
    val eventId: SosId? = null,
    val sender: NodeId? = null,
    val sourceVersion: Int = 1,
    val hop: Int = 0,
    val ttl: Int = 8,
    val timestamp: Double = Engine.TIME_NONE,
    val authTag: ByteArray? = null,
) {
    override fun equals(other: Any?): Boolean = other is RelayPacket &&
        messageType == other.messageType && eventId == other.eventId &&
        sender == other.sender && sourceVersion == other.sourceVersion &&
        hop == other.hop && ttl == other.ttl && timestamp == other.timestamp &&
        authTag?.contentEquals(other.authTag ?: ByteArray(0)) == true

    override fun hashCode(): Int {
        var h = 31 * messageType.hashCode() + (eventId?.hashCode() ?: 0)
        h = 31 * h + (sender?.hashCode() ?: 0)
        h = 31 * h + sourceVersion + hop + ttl
        h = 31 * h + timestamp.toInt()
        h = 31 * h + (authTag?.contentHashCode() ?: 0)
        return h
    }
}

/** A perceived SOS hop claim, as heard on the wire by THIS device (spec §53). */
data class HopAdvertisement(val hop: Int, val version: Int, val t: Double)

data class HopState(val hop: Int, val version: Int, val updatedAt: Double)

data class Sos(
    val id: SosId,
    val origin: NodeId,
    val createdAt: Double,
    var version: Int = 1,
    val ttlHops: Int = 8,
    val lifespanSeconds: Double? = 900.0,
    var expiresAt: Double? = null,
    var status: SosStatus = SosStatus.ACTIVE,
)