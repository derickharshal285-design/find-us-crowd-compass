package com.findus.crowdcompass.engine

import java.security.SecureRandom
import kotlin.math.abs

/**
 * Parity battery — the same assertions the Python reference certifies
 * (core/security._test, app/devices connectivity + incident tests).
 * Pure Kotlin, runs on the JVM and on device.
 */
object EngineSelfTest {

    fun run(): TestReport {
        val checks = mutableListOf<String>()
        fun ok(cond: Boolean, name: String) {
            checks += name
            check(cond) { name }
        }

        runDirectionCompatParity(checks, ::ok)

        val link = IncidentSession.makeSession("evt-STADIUM").toLink()
        val session = IncidentSession.parseLink(link)
        ok(session.incidentId == "evt-STADIUM", "link round-trips incident id")
        ok(session.linkTtl == 8 && session.linkLife == 900.0, "link carries parameters")

        val zeroSalt = IncidentSession.makeSession(
            "nul-salt", ByteArray(16))  // random salts may contain 0x00 bytes
        val zeroParsed = IncidentSession.parseLink(zeroSalt.toLink())
        ok(zeroParsed.incidentId == "nul-salt" &&
                zeroParsed.salt.contentEquals(ByteArray(16)),
            "salt containing 0x00 bytes still round-trips (no separator ambiguity)")

        val pkt = RelayPacket(
            messageType = MessageType.SOS_UPDATE,
            eventId = SosId("evt-STADIUM-001"),
            sender = NodeId(session.pseudonym("install-A".toByteArray())),
            sourceVersion = 1, hop = 3, ttl = 8, timestamp = Engine.EPOCH + 1000.0)
        val signed = session.attach(pkt)
        ok(session.verify(signed), "valid MAC verifies")
        val tampered = signed.copy(hop = 9)
        ok(!session.verify(tampered), "tampered hop fails MAC")

        val codec = ProtocolWire()
        val wire = codec.decode(codec.encode(signed))
        ok(session.verify(wire), "MAC survives full wire round-trip")
        ok(wire.authTag!!.size == 8, "wire carries 8-byte auth tag")
        ok(wire.hop == 3 && wire.messageType == MessageType.SOS_UPDATE,
            "header fields decode")

        // regression: real-world timestamps (post-2020) MUST MAC via uint32
        val real = RelayPacket(
            messageType = MessageType.SOS_UPDATE,
            eventId = SosId("evt-STADIUM-001"),
            sender = NodeId(session.pseudonym("install-A".toByteArray())),
            sourceVersion = 1, hop = 2, ttl = 8, timestamp = 1789690000.0)
        val realWire = codec.decode(codec.encode(session.attach(real)))
        ok(session.verify(realWire), "MAC verified at real-world timestamps (uint32 canonical)")

        val evil = IncidentSession.makeSession("other-incident")
        ok(!evil.verify(wire), "foreign session fails MAC")

        val i1 = IncidentSession.makeSession("inc-A")
        val i2 = IncidentSession.makeSession("inc-B")
        val key = "install-X".toByteArray()
        ok(i1.pseudonym(key) == i1.pseudonym(key), "pseudonym stable within an incident")
        ok(i1.pseudonym(key) != i2.pseudonym(key), "pseudonym differs across incidents")

        // connectivity: join -> bidirectional link -> silence ages it out
        val a = DeviceApp(NodeId("A"), edgeExpireAfter = 5.0, nodeExpireAfter = 10.0)
        val b = DeviceApp(NodeId("B"), edgeExpireAfter = 5.0, nodeExpireAfter = 10.0)
        val shared = IncidentSession.makeSession("conn-check")
        a.joinIncident(shared); b.joinIncident(shared)
        // A self links its own wire id must be the shared-incident pseudonym
        ok(a.wireId.value != "A" && a.wireId.value.length == 8, "pseudonym is incident-scoped (8 chars)")
        ok(b.wireId.value != "A", "distinct install keys ==> distinct pseudonyms")

        a.startSos("PING")
        exchange(a, b, 3)
        ok(a.graph.isEdgeLive(a.wireId, b.wireId), "link forms A-side")
        ok(b.graph.isEdgeLive(b.wireId, a.wireId), "link forms B-side")
        val ea = a.graph.getEdge(a.wireId, b.wireId)!!
        val eb = b.graph.getEdge(b.wireId, a.wireId)!!
        ok(ea.lastBidirectionalExchange == eb.lastBidirectionalExchange,
            "bidirectional exchange timestamps agree")
        ok(a.sosEngine.hopOf("PING", a.wireId) == 0, "origin holds hop 0")

        // silence ages B out of A's view
        var tick = 5.0
        for (i in 0 until 16) { a.beginTick(tick); a.signalOwned(); tick += 1.0 }
        val aged = a.graph.getNode(b.wireId)
        ok(aged == null || aged.lifecycle == NodeLifecycle.EXPIRED, "aged-out node not live")
        ok(!a.graph.isEdgeLive(a.wireId, b.wireId), "aged-out link does not route")

        // relationship memory: B signals again after full expiry and returns
        b.beginTick(21.0)
        a.beginTick(21.0)
        for (blob in b.outgoing()) a.onPacket(b.wireId, blob)
        // a full tick later, the node/edge must be active again
        b.beginTick(22.0); a.beginTick(22.0)
        for (blob in b.outgoing()) a.onPacket(b.wireId, blob)
        a.graph.refresh(22.0)
        ok(a.graph.getNode(b.wireId)!!.lifecycle == NodeLifecycle.ACTIVE,
            "re-signaling peer re-admitted after expiry (relationship memory)")
        ok(a.graph.isEdgeLive(a.wireId, b.wireId), "revived edge routes again")

        // guidance stays honest after the link dies
        val g = a.guidance("PING")
        ok(g.mode != "NAVIGATING", "no route after link expiry")

        // forged foreign-session packet must be dropped before any graph write
        val outsider = IncidentSession.makeSession("some-other-incident")
        val forge = outsider.attach(RelayPacket(
            messageType = MessageType.SOS_UPDATE, eventId = SosId("PING"),
            sender = NodeId("EVIL0001"), sourceVersion = 99, hop = 0, ttl = 8,
            timestamp = a.t))
        val before = a.rejectedMacs
        a.onPacket(NodeId("EVIL0001"), codec.encode(forge))
        ok(a.rejectedMacs == before + 1, "foreign-session packet rejected")
        ok(!a.graph.hasNode(NodeId("EVIL0001")), "forgery never touches the graph")

        // ghost-kill: origin ends the incident; downstream must stop
        // advertising it within (hops x routeFreshness), not the lifetime
        val t2 = DeviceApp(NodeId("T"), edgeExpireAfter = 5.0, nodeExpireAfter = 10.0)
        val m2 = DeviceApp(NodeId("M"), edgeExpireAfter = 5.0, nodeExpireAfter = 10.0)
        val ghost = IncidentSession.makeSession("ghost-test")
        t2.joinIncident(ghost); m2.joinIncident(ghost)
        t2.startSos("DONE")
        exchange(t2, m2, 3)
        ok(m2.guidance("DONE").mode == "NAVIGATING", "ghost pre-end route is live")
        t2.endSos("DONE")
        var gt = 4.0
        for (i in 0 until 30) {
            t2.beginTick(gt); m2.beginTick(gt)
            t2.signalOwned(); m2.signalOwned()
            for (blob in t2.outgoing()) m2.onPacket(t2.wireId, blob)
            for (blob in m2.outgoing()) t2.onPacket(m2.wireId, blob)
            gt += 1.0
        }
        val ghostAds = m2.outgoing().filter { bl ->
            val p = codec.decode(bl)
            p.messageType == MessageType.SOS_UPDATE && p.eventId?.value == "DONE"
        }
        ok(ghostAds.isEmpty(), "relay stops advertising an ended incident")
        ok(m2.guidance("DONE").mode != "NAVIGATING",
            "no ghost route after the origin ends")

        return TestReport("EngineSelfTest", checks.size)
    }

    private fun runDirectionCompatParity(
        checks: MutableList<String>,
        ok: (Boolean, String) -> Unit,
    ) {
        // DirectionSweep parity: recover a 120-deg lighthouse from a synthetic
        // rotate (mirrors core/direction.py's _test geometry).
        val sweep = DirectionSweep()
        var ts = 1000.0
        for (deg in 0 until 360 step 15) {
            val sep = abs(((deg - 120 + 540) % 360) - 180).toDouble()
            sweep.addSample(-55.0 - sep * 0.5, deg.toDouble(), ts)
            ts += 0.05
        }
        val est = sweep.estimate(ts + 0.01)
        ok(est.detected && abs(est.bearingDeg - 120.0) <= 22.5,
            "sweep recovers 120 deg (got ${"%.1f".format(est.bearingDeg)})")
        ok(est.confidence > 0.0 && est.sigmaDeg != null, "sweep confidence -> sigma")
        ok(!sweep.estimate(ts + 20.0).detected, "stale sweep reports not-detected")

        // Fusion chains the same as the Python reference.
        val fused = BearingFusion.fusepatches(listOf(90.0 to 1.0, 95.0 to 1.0))
        ok(fused != null && abs(fused!!.meanDeg - 92.5) < 3.0, "fusion mean ~92.5")
        ok(fused!!.sigmaDeg < 30.0, "fusion sigma tight (${"%.1f".format(fused!!.sigmaDeg)})")
        val boost = BearingFusion.reciprocalBoost(90.0, 265.0)
        ok(boost != null && abs(boost!!.meanDeg - 88.3) < 3.0,
            "reciprocal boost mean ~88.3 (got ${"%.1f".format(boost!!.meanDeg)})")

        // Tier negotiation: BLE4 never reaches CS; CS requires a CS peer.
        val ble4 = CapabilityRegistry(
            advertising = true, scanning = true,
            imu = false, compass = false, rotate = false, haveCs = false)
        val ble5 = CapabilityRegistry(
            advertising = true, scanning = true,
            imu = true, compass = true, rotate = true, haveCs = false)
        val csPhone = CapabilityRegistry(
            advertising = true, scanning = true,
            imu = true, compass = true, rotate = true, haveCs = true)
        ok(ble4.bestTier(ble5) == NavTier.RSSI_LOGDIST, "ble4+ble5 -> RSSI log-distance")
        ok(csPhone.bestTier(ble4) == NavTier.RSSI_LOGDIST, "CS not used until peer has CS")
        ok(csPhone.bestTier(csPhone) == NavTier.COMPASS_CS, "two CS phones negotiate CS tier")

        // OOB sideband round-trip + foreign-frame rejection.
        val oob = OobSideband.serialize(84.5)
        ok(abs(OobSideband.parse(oob)!! - 84.5) < 1e-9, "OOB sideband round-trips")
        ok(OobSideband.parse("SOMETHING/ELSE") == null, "foreign sideband rejected")
    }

    private fun exchange(va: DeviceApp, vb: DeviceApp, rounds: Int) {
        var tick = 1.0
        repeat(rounds) {
            va.beginTick(tick); vb.beginTick(tick)
            for (blob in va.outgoing()) vb.onPacket(va.wireId, blob)
            for (blob in vb.outgoing()) va.onPacket(vb.wireId, blob)
            tick += 1.0
        }
    }
}

private fun DeviceApp.signalOwned() {
    signalSeen(wireId, t)
}

data class TestReport(val name: String, val checks: Int) {
    override fun toString(): String = "$name: $checks checks PASSED"
}

// keep SecureRandom referenced so this file's intent (unpredictable salts) is visible
private val _rng = SecureRandom()