package com.findus.packet

import java.security.SecureRandom

/**
 * JVM/on-device verification of the 56-bit packet layer, mirroring
 * packet_v2.py's suite. Surfaced in the app's Diagnostics screen so a phone can
 * re-certify the wire format it is actually transmitting.
 */
object PacketSelfTest {

    data class Report(val name: String, val checks: Int) {
        override fun toString(): String = "$name: $checks checks PASSED"
    }

    fun run(iterations: Int = 20000): Report {
        val checks = mutableListOf<String>()
        fun ok(cond: Boolean, name: String) {
            checks += name
            check(cond) { name }
        }

        ok(CanonicalVectors.verify(), "canonical vector hex+bits match Python/Swift")
        ok(CanonicalVectors.hex(CanonicalVectors.referencePacket.pack()) ==
            CanonicalVectors.EXPECTED_HEX,             "canonical hex is ${CanonicalVectors.EXPECTED_HEX}")

        val ref = CanonicalVectors.referencePacket
        ok(PacketV2.unpack(ref.pack()) == ref, "reference round-trips")
        ok(PacketV2.fromBitString(ref.toBitString()) == ref, "bitstring round-trips")

        // Boundary ranges on every field.
        var boundary = 0
        for (baro in intArrayOf(-32, -31, -1, 0, 1, 30, 31)) {
            for (sos in intArrayOf(0, 1, 2047, 4094, 4095)) {
                for (hop in intArrayOf(0, 1, 14, 15)) {
                    for (epoch in intArrayOf(0, 15)) {
                        val p = PacketV2(PacketType.ACK.value, sos, hop, baro, 0x3F, epoch, 3, 3, 0xFFFF)
                        ok(PacketV2.unpack(p.pack()) == p, "boundary case packs/unpacks")
                        boundary++
                    }
                }
            }
        }

        val rng = SecureRandom()
        repeat(iterations) {
            val p = PacketV2(
                pktType = rng.nextInt(16),
                sosId = rng.nextInt(4096),
                hopCount = rng.nextInt(16),
                baroDiff = rng.nextInt(64) - 32,
                flags = rng.nextInt(64),
                epoch = rng.nextInt(16),
                age = rng.nextInt(4),
                reserved = rng.nextInt(4),
                envelopeMac = rng.nextInt(65536),
            )
            check(PacketV2.unpack(p.pack()) == p) { "random roundtrip failed" }
        }
        ok(true, "random roundtrip ($iterations packets)")

        // FEC: inject exactly one bit error per 7-bit block (14 flips/frame).
        var fecOk = true
        repeat(200) {
            val raw = ByteArray(7).also { rng.nextBytes(it) }
            val coded = HammingFEC.encode(raw)
            val (clean, errs0) = HammingFEC.decode(coded)
            if (clean != raw || errs0 != 0) fecOk = false
            var value = java.math.BigInteger(1, coded)
            for (block in 0 until 14) {
                val bitInBlock = rng.nextInt(7)
                val bitPos = 6 + (13 - block) * 7 + bitInBlock
                value = value.xor(java.math.BigInteger.ONE.shiftLeft(bitPos))
            }
            val corrupted = leftPad(value, 13)
            val (fixed, errs) = HammingFEC.decode(corrupted)
            if (fixed != raw || errs != 14) fecOk = false
        }
        ok(fecOk, "FEC corrects 14 bit flips per frame")

        // Rolling envelope MAC.
        val key = "crowd-compass-test-key".toByteArray()
        val mac = EnvelopeMAC.compute(key, 0x512, 7, PacketType.LIVE_GRADIENT.value)
        ok(EnvelopeMAC.verify(key, 0x512, 7, PacketType.LIVE_GRADIENT.value, mac), "MAC verifies")
        ok(!EnvelopeMAC.verify(key, 0x513, 7, PacketType.LIVE_GRADIENT.value, mac), "forged SOS_ID rejected")
        ok(!EnvelopeMAC.verify(key, 0x512, 8, PacketType.LIVE_GRADIENT.value, mac), "replayed epoch rejected")
        ok(!EnvelopeMAC.verify("other-key".toByteArray(), 0x512, 7,
            PacketType.LIVE_GRADIENT.value, mac), "foreign key rejected")

        // BLE GAP budgets + decode round-trip.
        val rawPacket = ref.pack()
        val fecPacket = HammingFEC.encode(rawPacket)
        val budgets = BLEFraming.verifyBudgets(rawPacket, fecPacket)
        ok(budgets.mfrRawSlack == 20 && budgets.mfrFECSlack == 14,
            "legacy adv slack: raw ${budgets.mfrRawSlack}, fec ${budgets.mfrFECSlack}")
        ok(budgets.iosRawSlack == 16 && budgets.iosFECSlack == 10,
            "iOS-safe adv slack: raw ${budgets.iosRawSlack}, fec ${budgets.iosFECSlack}")

        val framed = BLEFraming.manufacturerData(fecPacket)
        ok(BLEFraming.decode(framed)?.contentEquals(rawPacket) == true,
            "manufacturer frame decodes+FEC to raw")
        val iosFramed = BLEFraming.iosBackgroundSafe(fecPacket)
        ok(BLEFraming.decode(iosFramed)?.contentEquals(rawPacket) == true,
            "iOS dual-AD frame decodes+FEC to raw")

        return Report("PacketSelfTest", checks.size)
    }

    private fun leftPad(value: java.math.BigInteger, size: Int): ByteArray {
        val raw = value.toByteArray()
        val out = ByteArray(size)
        if (raw.size >= size) {
            System.arraycopy(raw, raw.size - size, out, 0, size)
        } else {
            System.arraycopy(raw, 0, out, size - raw.size, raw.size)
        }
        return out
    }
}
