package com.findus.crowdcompass.engine

import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Byte-faithful v3 codec port of core/protocol.py. */
class ProtocolWire {

    class ProtocolError(message: String) : Exception(message)

    fun encode(pkt: RelayPacket): ByteArray {
        var flags = 0
        var authBlock = ByteArray(0)
        if (pkt.authTag != null) {
            flags = flags or 0x04
            authBlock = pkt.authTag.copyOf(8).also { if (it.size < 8) it.fill(0, it.size, 8) }
        }
        val timestamp = packTime(pkt.timestamp)
        val header = ByteBuffer.allocate(35).order(ByteOrder.BIG_ENDIAN)
            .put(Engine.PROTOCOL_VERSION.toByte())
            .put(pkt.messageType.wire.toByte())
            .put(packId(pkt.eventId?.value.orEmpty(), 16))
            .put(packId(pkt.sender?.value.orEmpty(), 8))
            .putShort(sourceVersion(pkt.sourceVersion))
            .put(pkt.hop.coerceIn(0, 255).toByte())
            .put(pkt.ttl.coerceIn(0, 255).toByte())
            .putInt(timestamp)
            .put(flags.toByte())
            .array()
        val out = ByteArrayOutputStream(header.size + authBlock.size)
        out.write(header)
        out.write(authBlock)
        return out.toByteArray()
    }

    fun decode(blob: ByteArray): RelayPacket {
        if (blob.size < 35) throw ProtocolError("header needs 35 bytes, got ${blob.size}")
        val h = ByteBuffer.wrap(blob).order(ByteOrder.BIG_ENDIAN)
        val ver = h.get().toInt() and 0xFF
        if (ver != Engine.PROTOCOL_VERSION) {
            throw ProtocolError("unsupported version $ver (this codec: ${Engine.PROTOCOL_VERSION})")
        }
        val mtype = MessageType.fromWire(h.get().toInt() and 0xFF)
            ?: throw ProtocolError("unknown message type")
        val eventBytes = ByteArray(16).also { h.get(it) }
        val senderBytes = ByteArray(8).also { h.get(it) }
        val srcVer = h.short.toInt() and 0xFFFF
        val hop = h.get().toInt() and 0xFF
        val ttl = h.get().toInt() and 0xFF
        val ts = h.int.toLong() and 0xFFFFFFFFL
        val flags = h.get().toInt() and 0xFF
        var pos = 35
        if (flags and 0x01 != 0) pos = skipMeasurement(blob, pos)
        if (flags and 0x02 != 0) pos = skipMeasurement(blob, pos)
        if (flags and 0x04 != 0) {
            if (pos + Engine.AUTH_TAG_BYTES > blob.size) {
                throw ProtocolError("auth tag truncated")
            }
            val auth = blob.copyOfRange(pos, pos + Engine.AUTH_TAG_BYTES)
            return RelayPacket(
                messageType = mtype,
                eventId = unpad(eventBytes)?.let { SosId(it) },
                sender = unpad(senderBytes)?.let { NodeId(it) },
                sourceVersion = srcVer,
                hop = hop,
                ttl = ttl,
                timestamp = if (ts != 0L) ts + Engine.EPOCH else Engine.TIME_NONE,
                authTag = auth,
            )
        }
        return RelayPacket(
            messageType = mtype,
            eventId = unpad(eventBytes)?.let { SosId(it) },
            sender = unpad(senderBytes)?.let { NodeId(it) },
            sourceVersion = srcVer,
            hop = hop,
            ttl = ttl,
            timestamp = if (ts != 0L) ts + Engine.EPOCH else Engine.TIME_NONE,
        )
    }

    private fun skipMeasurement(blob: ByteArray, pos: Int): Int {
        if (pos + 8 > blob.size) throw ProtocolError("measurement block truncated")
        var p = pos + 8
        val hasDist = blob[p - 2].toInt() != 0
        val hasDir = blob[p - 1].toInt() != 0
        if (hasDist) p += 4
        if (hasDir) p += 4
        if (p > blob.size) throw ProtocolError("measurement trailing data truncated")
        return p
    }

    private fun packId(value: String, width: Int): ByteArray {
        val raw = value.toByteArray(Charsets.UTF_8)
        val out = ByteArray(width)
        for (i in 0 until minOf(raw.size, width)) out[i] = raw[i]
        return out
    }

    private fun unpad(raw: ByteArray): String? {
        var end = raw.size
        while (end > 0 && raw[end - 1] == 0.toByte()) end--
        if (end == 0) return null
        return String(raw, 0, end, Charsets.UTF_8)
    }

    private fun packTime(t: Double): Int {
        if (t == Engine.TIME_NONE || t <= 0.0) return 0
        val v = Math.round(t - Engine.EPOCH)
        return v.coerceIn(0, 0xFFFFFFFFL).toInt()
    }

    private fun sourceVersion(v: Int): Short =
        v.coerceIn(0, 0xFFFF).toShort()
}