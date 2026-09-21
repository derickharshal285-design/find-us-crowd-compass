package com.findus.packet

import java.security.MessageDigest
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/**
 * Rolling 16-bit outer-envelope MAC over origin invariants
 * (SOS_ID || EPOCH || PKT_TYPE). Port of packet_v2.py; byte-faithful so a
 * frame forged in any language is rejected in every other.
 */
object EnvelopeMAC {

    fun compute(key: ByteArray, sosId: Int, epoch: Int, pktType: Int): Int {
        val msg = byteArrayOf(
            ((sosId and 0x0FFF) ushr 8).toByte(),
            (sosId and 0xFF).toByte(),
            (epoch and 0x0F).toByte(),
            (pktType and 0x0F).toByte(),
        )
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(key, "HmacSHA256"))
        val digest = mac.doFinal(msg)
        return ((digest[0].toInt() and 0xFF) shl 8) or (digest[1].toInt() and 0xFF)
    }

    fun verify(key: ByteArray, sosId: Int, epoch: Int, pktType: Int, receivedMac: Int): Boolean {
        val expected = compute(key, sosId, epoch, pktType)
        return MessageDigest.isEqual(
            byteArrayOf((expected ushr 8).toByte(), expected.toByte()),
            byteArrayOf(((receivedMac ushr 8) and 0xFF).toByte(), (receivedMac and 0xFF).toByte()),
        )
    }
}
