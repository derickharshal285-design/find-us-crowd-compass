package com.findus.packet

import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Byte-faithful Kotlin port of core/python/packet_v2.py — the 56-bit (7-byte)
 * navigation packet. Cross-language canonical vector hex must stay
 * "17a53ee2998f42" (see CanonicalVectors); the JVM test enforces it.
 */

enum class PacketType(val value: Int) {
    LIVE_GRADIENT(0x0),
    CACHED_MULE_BURST(0x1),
    DISCOVERY_PROBE(0x2),
    ACK(0x3),
    CANCEL(0x4),
    HEARTBEAT(0x5),
    DIAGNOSTIC(0x6);

    companion object {
        fun of(value: Int): PacketType? = entries.firstOrNull { it.value == value }
    }
}

enum class AgeBucket(val value: Int) {
    LIVE(0),
    UNDER_1MIN(1),
    UNDER_5MIN(2),
    OVER_5MIN(3);

    companion object {
        fun of(value: Int): AgeBucket? = entries.firstOrNull { it.value == value }
    }
}

object Flags {
    const val EMERGENCY_TYPE = 0x01
    const val VISUAL_RUNWAY = 0x02
    const val SEVERE_URGENCY = 0x04
    const val ACK_RECEIVED = 0x08
    const val CANCEL_RESOLVED = 0x10
    const val MULE_STORE_FORWARD = 0x20
}

object ReservedBits {
    const val SECONDARY_PHY = 0x01
    const val COLLISION_EXPEDITE = 0x02
}

/**
 * Wire layout (big-endian, 56 bits):
 *   word0: PKT_TYPE[15:12] | SOS_ID[11:0]
 *   word1: HOP_COUNT[15:12] | BARO_DIFF[11:6] | FLAGS[5:0]
 *   word2: EPOCH[15:12] | AGE[11:10] | RESERVED[9:8] | MAC[15:8]
 *   byte6: MAC[7:0]
 */
data class PacketV2(
    val pktType: Int,
    val sosId: Int,
    val hopCount: Int,
    val baroDiff: Int,
    val flags: Int,
    val epoch: Int,
    val age: Int,
    val reserved: Int = 0,
    val envelopeMac: Int = 0,
) {
    fun validate() {
        require(pktType in 0x0..0xF) { "pkt_type $pktType out of 4-bit range" }
        require(sosId in 0x000..0xFFF) { "sos_id $sosId out of 12-bit range" }
        require(hopCount in 0x0..0xF) { "hop_count $hopCount out of 4-bit range" }
        require(baroDiff in -32..31) { "baro_diff $baroDiff out of 6-bit signed range" }
        require(flags in 0x00..0x3F) { "flags $flags out of 6-bit range" }
        require(epoch in 0x0..0xF) { "epoch $epoch out of 4-bit range" }
        require(age in 0x0..0x3) { "age $age out of 2-bit range" }
        require(reserved in 0x0..0x3) { "reserved $reserved out of 2-bit range" }
        require(envelopeMac in 0x0000..0xFFFF) { "envelope_mac $envelopeMac out of 16-bit range" }
    }

    fun pack(): ByteArray {
        validate()
        val rawBaro = baroDiff and 0x3F
        val word0 = (pktType shl 12) or sosId
        val word1 = (hopCount shl 12) or (rawBaro shl 6) or flags
        val word2 = (epoch shl 12) or (age shl 10) or (reserved shl 8) or (envelopeMac shr 8)
        val macLo = envelopeMac and 0xFF
        return ByteBuffer.allocate(7).order(ByteOrder.BIG_ENDIAN)
            .putShort(word0.toShort())
            .putShort(word1.toShort())
            .putShort(word2.toShort())
            .put(macLo.toByte())
            .array()
    }

    fun toBitString(): String = StringBuilder(56).also { sb ->
        for (b in pack()) {
            val bits = Integer.toBinaryString(b.toInt() and 0xFF)
            for (i in 0 until 8 - bits.length) sb.append('0')
            sb.append(bits)
        }
    }.toString()

    companion object {
        fun unpack(raw: ByteArray): PacketV2 {
            require(raw.size == 7) { "Expected 7 bytes, got ${raw.size}" }
            val buf = ByteBuffer.wrap(raw).order(ByteOrder.BIG_ENDIAN)
            val word0 = buf.short.toInt() and 0xFFFF
            val word1 = buf.short.toInt() and 0xFFFF
            val word2 = buf.short.toInt() and 0xFFFF
            val macLo = buf.get().toInt() and 0xFF
            val rawBaro = (word1 shr 6) and 0x3F
            return PacketV2(
                pktType = (word0 shr 12) and 0x0F,
                sosId = word0 and 0x0FFF,
                hopCount = (word1 shr 12) and 0x0F,
                baroDiff = if (rawBaro and 0x20 != 0) rawBaro - 64 else rawBaro,
                flags = word1 and 0x3F,
                epoch = (word2 shr 12) and 0x0F,
                age = (word2 shr 10) and 0x03,
                reserved = (word2 shr 8) and 0x03,
                envelopeMac = ((word2 and 0xFF) shl 8) or macLo,
            )
        }

        fun fromBitString(bitString: String): PacketV2 {
            val clean = bitString.replace(" ", "").replace("_", "")
            require(clean.length == 56) { "Expected 56 bits, got ${clean.length}" }
            val raw = ByteArray(7)
            for (i in 0 until 7) raw[i] = clean.substring(i * 8, i * 8 + 8).toInt(2).toByte()
            return unpack(raw)
        }
    }
}
