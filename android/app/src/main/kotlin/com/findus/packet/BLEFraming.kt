package com.findus.packet

/**
 * BLE GAP advertising encapsulation — port of packet_v2.py's BLEFraming.
 *
 * Two budgets matter: 31-byte legacy advertisement (27 B manufacturer payload)
 * and the 23-byte iOS background-safe dual-AD form (16-bit service UUID anchor
 * + manufacturer carrier). Both are enforced, not assumed.
 */
object BLEFraming {

    const val LEGACY_ADV_LIMIT = 31
    const val MFR_MAX_PAYLOAD = 27
    const val IOS_MAX_PAYLOAD = 23

    fun manufacturerData(payload: ByteArray, companyId: Int = 0xFFFF): ByteArray {
        require(payload.size <= MFR_MAX_PAYLOAD) {
            "Payload ${payload.size} exceeds 27-byte manufacturer budget"
        }
        val out = ByteArray(4 + payload.size)
        out[0] = (payload.size + 3).toByte()
        out[1] = 0xFF.toByte()
        out[2] = (companyId and 0xFF).toByte()
        out[3] = ((companyId ushr 8) and 0xFF).toByte()
        System.arraycopy(payload, 0, out, 4, payload.size)
        return out
    }

    fun iosBackgroundSafe(payload: ByteArray, serviceUuid: Int = 0xFC00,
                          companyId: Int = 0xFFFF): ByteArray {
        require(payload.size <= IOS_MAX_PAYLOAD) {
            "Payload ${payload.size} exceeds 23-byte iOS background-safe budget"
        }
        val ad1 = byteArrayOf(
            0x03, 0x03,
            (serviceUuid and 0xFF).toByte(),
            ((serviceUuid ushr 8) and 0xFF).toByte(),
        )
        val ad2 = ByteArray(4 + payload.size)
        ad2[0] = (payload.size + 3).toByte()
        ad2[1] = 0xFF.toByte()
        ad2[2] = (companyId and 0xFF).toByte()
        ad2[3] = ((companyId ushr 8) and 0xFF).toByte()
        System.arraycopy(payload, 0, ad2, 4, payload.size)
        val out = ByteArray(ad1.size + ad2.size)
        System.arraycopy(ad1, 0, out, 0, ad1.size)
        System.arraycopy(ad2, 0, out, ad1.size, ad2.size)
        return out
    }

    /** Reverse-decodes a manufacturer-data carrier back to its payload. */
    fun decodeGapAdvertisement(adv: ByteArray): ByteArray? {
        if (adv.size < 3) return null
        if ((adv[0].toInt() and 0xFF) == adv.size - 1 && adv[1] == 0xFF.toByte()) {
            return if (adv.size > 4) adv.copyOfRange(4, adv.size) else ByteArray(0)
        }
        var i = 0
        while (i < adv.size) {
            val length = adv[i].toInt() and 0xFF
            if (length == 0) break
            if (i + 1 + length > adv.size) return null
            val adType = adv[i + 1].toInt() and 0xFF
            if (adType == 0xFF && length >= 3) {
                return adv.copyOfRange(i + 4, i + 1 + length)
            }
            i += length + 1
        }
        return null
    }

    /** Any received frame -> the canonical 7-byte raw packet, FEC-decoding if needed. */
    fun decode(frame: ByteArray): ByteArray? {
        if (frame.size < 7) return null
        if (frame.size == 7) return frame.copyOf()
        if (frame.size == 13) {
            return runCatching { HammingFEC.decode(frame).first }.getOrNull()
                ?.takeIf { it.size == 7 }
        }
        val payload = decodeGapAdvertisement(frame) ?: return null
        val raw = if (payload.size == 13) {
            runCatching { HammingFEC.decode(payload).first }.getOrNull() ?: return null
        } else {
            payload
        }
        return raw.takeIf { it.size == 7 }
    }

    data class Budget(
        val mfrRawSlack: Int,
        val mfrFECSlack: Int,
        val iosRawSlack: Int,
        val iosFECSlack: Int,
    )

    fun verifyBudgets(raw: ByteArray, fec: ByteArray): Budget = Budget(
        mfrRawSlack = LEGACY_ADV_LIMIT - manufacturerData(raw).size,
        mfrFECSlack = LEGACY_ADV_LIMIT - manufacturerData(fec).size,
        iosRawSlack = LEGACY_ADV_LIMIT - iosBackgroundSafe(raw).size,
        iosFECSlack = LEGACY_ADV_LIMIT - iosBackgroundSafe(fec).size,
    )
}
