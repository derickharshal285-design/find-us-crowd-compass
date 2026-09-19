package com.findus.packet

import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/**
 * BLE GAP Advertising Encapsulation — Dual-AD Structure for iOS Background Safety
 * Packet v2: 7 bytes raw → 13 bytes Hamming(7,4) coded
 * iOS Mode C ceiling: 23 bytes (31 - 4 Service UUID AD - 4 header)
 * Dual-AD: [AD1: 16-bit Service UUID 0xFC00] + [AD2: Manufacturer Data 0xFFFF + payload]
 */
object BLEFraming {

    /** Legacy Manufacturer Data framing (27-byte payload budget) */
    fun manufacturerData(payload: ByteArray, companyID: Int = 0xFFFF): ByteArray {
        val totalLen = payload.size + 3
        require(totalLen <= 27) { "Payload ${payload.size} + 3 header exceeds 27-byte manufacturer budget" }
        val adv = ByteArray(4 + payload.size)
        adv[0] = totalLen.toByte()
        adv[1] = 0xFF.toByte()
        adv[2] = (companyID and 0xFF).toByte()
        adv[3] = (companyID shr 8).toByte()
        System.arraycopy(payload, 0, adv, 4, payload.size)
        return adv
    }

    /** iOS Background-Safe Dual-AD Structure (23-byte payload budget)
     * AD1: 16-bit Service UUID filter anchor [0x03, 0x03, UUID_lo, UUID_hi] = 4 bytes
     * AD2: Manufacturer Specific Data carrier [Len, 0xFF, CoID_lo, CoID_hi, Payload] = 4 + len bytes
     * Total budget: 31 - 4 - 4 = 23 bytes for payload
     */
    fun iosBackgroundSafe(
        payload: ByteArray,
        serviceUUID: Int = 0xFC00,
        companyID: Int = 0xFFFF
    ): ByteArray {
        require(payload.size <= 23) { "Payload ${payload.size} exceeds 23-byte iOS background-safe budget" }

        val adv = ByteArray(4 + 4 + payload.size)
        // AD Structure 1: 16-bit Service UUID (Type 0x03)
        adv[0] = 0x03.toByte()        // Length = 3
        adv[1] = 0x03.toByte()        // AD Type = 0x03
        adv[2] = (serviceUUID and 0xFF).toByte()
        adv[3] = (serviceUUID shr 8).toByte()

        // AD Structure 2: Manufacturer Specific Data (Type 0xFF)
        val ad2Len = payload.size + 3
        adv[4] = ad2Len.toByte()
        adv[5] = 0xFF.toByte()
        adv[6] = (companyID and 0xFF).toByte()
        adv[7] = (companyID shr 8).toByte()
        System.arraycopy(payload, 0, adv, 8, payload.size)

        return adv
    }

    /** Budget verification helper */
    data class BudgetSlack(
        val mfrRawTotal: Int,      // 4 + 7 = 11
        val mfrRawSlack: Int,      // 31 - 11 = 20
        val mfrFECTotal: Int,      // 4 + 13 = 17
        val mfrFECSlack: Int,      // 31 - 17 = 14
        val iosRawTotal: Int,      // 4 + 4 + 7 = 15
        val iosRawSlack: Int,      // 23 - 7 = 16
        val iosFECTotal: Int,      // 4 + 4 + 13 = 21
        val iosFECSlack: Int       // 23 - 13 = 10
    )

    fun verifyBudgets(rawPacket: ByteArray, fecPacket: ByteArray): BudgetSlack {
        val mfrRaw = manufacturerData(rawPacket)
        val mfrFEC = manufacturerData(fecPacket)
        val iosRaw = iosBackgroundSafe(rawPacket)
        val iosFEC = iosBackgroundSafe(fecPacket)

        return BudgetSlack(
            mfrRawTotal = mfrRaw.size,
            mfrRawSlack = 31 - mfrRaw.size,
            mfrFECTotal = mfrFEC.size,
            mfrFECSlack = 31 - mfrFEC.size,
            iosRawTotal = iosRaw.size,
            iosRawSlack = 23 - rawPacket.size,
            iosFECTotal = iosFEC.size,
            iosFECSlack = 23 - fecPacket.size
        )
    }
}

/** Anti-Spoofing Rolling Outer-Envelope MAC (16-bit HMAC-SHA256)
 * Keyed with shared session secret K_session over (SOS_ID || EPOCH || PKT_TYPE) */
object EnvelopeMAC {

    private const val HMAC_ALGO = "HmacSHA256"

    fun compute(key: ByteArray, sosId: Int, epoch: Int, pktType: Int): Int {
        val msg = ByteArray(4)
        msg[0] = (sosId shr 8).toByte()
        msg[1] = (sosId and 0xFF).toByte()
        msg[2] = epoch.toByte()
        msg[3] = pktType.toByte()

        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(key, "HmacSHA256"))
        val hmac = mac.doFinal(msg)
        // Truncate to 16 bits (first 2 bytes of SHA-256)
        return ((hmac[0].toInt() and 0xFF) shl 8) or (hmac[1].toInt() and 0xFF)
    }

    fun verify(key: ByteArray, sosId: Int, epoch: Int, pktType: Int, received: Int): Boolean {
        val expected = compute(key, sosId, epoch, pktType)
        // Constant-time comparison
        var diff = 0
        diff = diff or (expected xor received)
        return diff == 0
    }
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