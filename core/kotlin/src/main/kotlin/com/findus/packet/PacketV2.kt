package com.findus.packet

import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Find Us / Crowd Compass — Packet v2 Canonical Wire Format (56 bits / 7.0 bytes)
 * Kotlin implementation matching Python reference (16-bit MAC, Hamming(7,4) FEC, Dual-AD BLE)
 */
data class PacketV2(
    val pktType: Int,      // 4 bits  [3:0]   0..15
    val sosId: Int,        // 12 bits [15:4]  0..4095
    val hopCount: Int,     // 4 bits  [19:16] 0..15
    val baroDiff: Int,     // 6 bits  [25:20] -32..+31 (0.5 hPa units, ~4.2 m)
    val flags: Int,        // 6 bits  [31:26] 0..63
    val epoch: Int,        // 4 bits  [35:32] 0..15
    val age: Int,          // 2 bits  [37:36] 0..3
    val reserved: Int,     // 2 bits  [39:38] 0..3
    val envelopeMac: Int   // 16 bits [55:40] 0..65535
) {
    init {
        require(pktType in 0..0x0F) { "pkt_type out of 4-bit range [0, 15]" }
        require(sosId in 0..0x0FFF) { "sos_id out of 12-bit range [0, 4095]" }
        require(hopCount in 0..0x0F) { "hop_count out of 4-bit range [0, 15]" }
        require(baroDiff in -32..31) { "baro_diff out of 6-bit signed range [-32, 31]" }
        require(flags in 0..0x3F) { "flags out of 6-bit range [0, 63]" }
        require(epoch in 0..0x0F) { "epoch out of 4-bit range [0, 15]" }
        require(age in 0..0x03) { "age out of 2-bit range [0, 3]" }
        require(reserved in 0..0x03) { "reserved out of 2-bit range [0, 3]" }
        require(envelopeMac in 0..0xFFFF) { "envelope_mac out of 16-bit range [0, 65535]" }
    }

    /** Pack into exactly 7 bytes (56 bits) — big-endian network order */
    fun pack(): ByteArray {
        // 6-bit signed two's complement encoding for baroDiff
        val rawBaro = baroDiff and 0x3F

        val word0 = (pktType shl 12) or sosId
        val word1 = (hopCount shl 12) or (rawBaro shl 6) or flags
        val word2 = (epoch shl 12) or (age shl 10) or (reserved shl 8) or (envelopeMac shr 8)
        val macLo = envelopeMac and 0xFF

        return ByteBuffer.allocate(7).order(ByteOrder.BIG_ENDIAN).run {
            putShort(word0.toShort())
            putShort(word1.toShort())
            putShort(word2.toShort())
            put(macLo.toByte())
            array()
        }
    }

    /** Unpack exactly 7 bytes (56 bits) into PacketV2 */
    companion object {
        @JvmStatic
        fun unpack(raw: ByteArray): PacketV2 {
            require(raw.size == 7) { "Expected 7 bytes, got ${raw.size}" }

            val buf = ByteBuffer.wrap(raw).order(ByteOrder.BIG_ENDIAN)
            val word0 = buf.getShort().toInt() and 0xFFFF
            val word1 = buf.getShort().toInt() and 0xFFFF
            val word2 = buf.getShort().toInt() and 0xFFFF
            val macLo = buf.get().toInt() and 0xFF

            val pktType = (word0 shr 12) and 0x0F
            val sosId = word0 and 0x0FFF

            val hopCount = (word1 shr 12) and 0x0F
            val rawBaro = (word1 shr 6) and 0x3F
            val baroDiff = if ((rawBaro and 0x20) != 0) (rawBaro - 64) else rawBaro
            val flags = word1 and 0x3F

            val epoch = (word2 shr 12) and 0x0F
            val age = (word2 shr 10) and 0x03
            val reserved = (word2 shr 8) and 0x03
            val envelopeMac = ((word2 and 0xFF) shl 8) or macLo

            return PacketV2(
                pktType = pktType,
                sosId = sosId,
                hopCount = hopCount,
                baroDiff = baroDiff,
                flags = flags,
                epoch = epoch,
                age = age,
                reserved = reserved,
                envelopeMac = envelopeMac
            )
        }
    }

    /** Returns 56-character binary string */
    val bitString: String
        get() = pack().joinToString("") { "%08d".format(it.toInt().toString(2).padStart(8, '0')) }

    /** Parse 56-bit binary string back into PacketV2 */
    companion object {
        @JvmStatic
        fun fromBitString(bitStr: String): PacketV2 {
            val clean = bitStr.replace(" ", "").replace("_", "")
            require(clean.length == 56) { "Expected 56 bits, got ${clean.length}" }
            val value = clean.toULong(2)
            val bytes = ByteArray(7)
            for (i in 6 downTo 0) {
                bytes[i] = (value shr (8 * i) and 0xFFUL).toByte()
            }
            return unpack(bytes)
        }
    }
}

/** Packet Type enum (4 bits) */
enum class PacketType(val value: Int) {
    LIVE_GRADIENT(0x0),
    CACHED_MULE_BURST(0x1),
    DISCOVERY_PROBE(0x2),
    ACK(0x3),
    CANCEL(0x4),
    HEARTBEAT(0x5),
    DIAGNOSTIC(0x6)
}

/** Age Bucket enum (2 bits) */
enum class AgeBucket(val value: Int) {
    LIVE(0),          // < 10 s
    UNDER_1_MIN(1),   // 10 s – < 60 s
    UNDER_5_MIN(2),   // 1 min – < 5 min
    OVER_5_MIN(3)     // >= 5 min
}

/** Flags bitmask (6 bits) */
object Flags {
    const val EMERGENCY_TYPE      = 0x01  // Bit 0
    const val VISUAL_RUNWAY       = 0x02  // Bit 1
    const val SEVERE_URGENCY      = 0x04  // Bit 2
    const val ACK_RECEIVED        = 0x08  // Bit 3
    const val CANCEL_RESOLVED     = 0x10  // Bit 4
    const val MULE_STORE_FORWARD  = 0x20  // Bit 5
}

/** Reserved bits (2 bits) */
object ReservedBits {
    const val SECONDARY_PHY      = 0x01
    const val COLLISION_EXPEDITE = 0x02
}

/** Canonical reference vector for cross-language verification */
object CanonicalVectors {
    val referencePacket = PacketV2(
        pktType = PacketType.CACHED_MULE_BURST.value,
        sosId = 0x7A5,
        hopCount = 3,
        baroDiff = -5,
        flags = Flags.MULE_STORE_FORWARD or Flags.VISUAL_RUNWAY, // 0x22
        epoch = 9,
        age = AgeBucket.UNDER_5_MIN.value,
        reserved = ReservedBits.SECONDARY_PHY,
        envelopeMac = 0x8F42
    )

    const val EXPECTED_HEX = "17a53ee2998f42"
    const val EXPECTED_BITS = "00010111101001010011111011100010100110011000111101000010"
}