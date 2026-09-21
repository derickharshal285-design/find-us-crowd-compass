package com.findus.crowdcompass.engine

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** JVM parity gate: one gradle test runs the same battery a phone would. */
class EngineSelfTestTest {
    @Test
    fun parityBatteryPasses() {
        val report = EngineSelfTest.run()
        assertEquals("EngineSelfTest", report.name)
        assertTrue("battery checks all pass", report.checks >= 14)
    }
}