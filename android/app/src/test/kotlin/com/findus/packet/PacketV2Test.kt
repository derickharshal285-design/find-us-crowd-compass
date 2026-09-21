package com.findus.packet

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** JVM parity gate: the Kotlin 56-bit PDU layer re-certifies on the test JVM. */
class PacketV2Test {
    @Test
    fun canonicalVectorMatchesPython() {
        assertEquals(CanonicalVectors.EXPECTED_HEX, CanonicalVectors.hex(CanonicalVectors.referencePacket.pack()))
        assertTrue(CanonicalVectors.verify())
    }

    @Test
    fun packetSelfTestBatteryPasses() {
        val report = PacketSelfTest.run(iterations = 20000)
        assertEquals("PacketSelfTest", report.name)
        assertTrue("battery checks all pass", report.checks >= 20)
    }
}