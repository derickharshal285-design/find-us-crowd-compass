import Foundation

/// Parity battery — repeats the assertions the Python reference certifies
/// (core/security._test, app/devices connectivity + incident tests).
public enum EngineSelfTest {

    public struct Report: Equatable {
        public let checks: Int
    }

    public enum BatteryError: Error, CustomStringConvertible {
        case failed(String)
        public var description: String {
            if case .failed(let name) = self { return "assertion failed: \(name)" }
            return "battery failed"
        }
    }

    public static func run() throws -> Report {
        var checks = 0
        func ok(_ cond: Bool, _ name: String) throws {
            checks += 1
            if !cond { throw BatteryError.failed(name) }
        }

        try runDirectionCompatParity(checks: &checks, ok: ok)

        let link = IncidentSession.makeSession(incidentId: "evt-STADIUM").toLink()
        let session = try IncidentSession.parseLink(link)
        try ok(session.incidentId == "evt-STADIUM", "link round-trips incident id")
        try ok(session.linkTtl == 8 && session.linkLife == 900.0, "link carries parameters")

        let zeroSalt = IncidentSession.makeSession(incidentId: "nul-salt",
                                                   salt: Data(repeating: 0, count: 16))
        let zeroParsed = try IncidentSession.parseLink(zeroSalt.toLink())
        try ok(zeroParsed.incidentId == "nul-salt" &&
                zeroParsed.salt == Data(repeating: 0, count: 16),
            "salt containing 0x00 bytes still round-trips (no separator ambiguity)")

        let pkt = RelayPacket(messageType: .sosUpdate, eventId: SosId("evt-STADIUM-001"),
                              sender: NodeId(session.pseudonym(installKey: Data("install-A".utf8))),
                              sourceVersion: 1, hop: 3, ttl: 8,
                              timestamp: EngineConstants.epoch + 1000.0)
        let signed = session.attach(pkt)
        try ok(session.verify(signed), "valid MAC verifies")
        var tampered = signed
        tampered.hop = 9
        try ok(!session.verify(tampered), "tampered hop fails MAC")

        let codec = ProtocolWire()
        let wire = try codec.decode(codec.encode(signed))
        try ok(session.verify(wire), "MAC survives full wire round-trip")
        try ok(wire.authTag?.count == 8, "wire carries 8-byte auth tag")
        try ok(wire.hop == 3 && wire.messageType == .sosUpdate, "header fields decode")

        // regression: real-world (post-2020) timestamps must MAC via uint32
        let real = RelayPacket(messageType: .sosUpdate, eventId: SosId("evt-STADIUM-001"),
                               sender: NodeId(session.pseudonym(installKey: Data("install-A".utf8))),
                               sourceVersion: 1, hop: 2, ttl: 8, timestamp: 1789690000.0)
        let realWire = try codec.decode(codec.encode(session.attach(real)))
        try ok(session.verify(realWire), "MAC verified at real-world timestamps (uint32 canonical)")

        let evil = IncidentSession.makeSession(incidentId: "other-incident")
        try ok(!evil.verify(wire), "foreign session fails MAC")

        let i1 = IncidentSession.makeSession(incidentId: "inc-A")
        let i2 = IncidentSession.makeSession(incidentId: "inc-B")
        let key = Data("install-X".utf8)
        try ok(i1.pseudonym(installKey: key) == i1.pseudonym(installKey: key),
               "pseudonym stable within an incident")
        try ok(i1.pseudonym(installKey: key) != i2.pseudonym(installKey: key),
               "pseudonym differs across incidents")

        // connectivity: join -> bidirectional link -> silence ages it out
        let a = DeviceApp(id: NodeId("A"), nodeExpireAfter: 10.0, edgeExpireAfter: 5.0)
        let b = DeviceApp(id: NodeId("B"), nodeExpireAfter: 10.0, edgeExpireAfter: 5.0)
        let shared = IncidentSession.makeSession(incidentId: "conn-check")
        a.joinIncident(shared); b.joinIncident(shared)
        try ok(a.wireId.value != "A" && a.wireId.value.count == 8,
               "pseudonym is incident-scoped (8 chars)")
        try ok(b.wireId.value != "A", "distinct install keys => distinct pseudonyms")

        a.startSos("PING")
        exchange(a, b, rounds: 3)
        try ok(a.graph.isEdgeLive(a.wireId, b.wireId), "link forms A-side")
        try ok(b.graph.isEdgeLive(b.wireId, a.wireId), "link forms B-side")
        let ea = a.graph.getEdge(a.wireId, b.wireId)!
        let eb = b.graph.getEdge(b.wireId, a.wireId)!
        try ok(ea.lastBidirectionalExchange == eb.lastBidirectionalExchange,
               "bidirectional exchange timestamps agree")
        try ok(a.sosEngine.hopOf("PING", node: a.wireId) == 0, "origin holds hop 0")

        var tick = 5.0
        for _ in 0..<16 {
            a.beginTick(tick)
            a.signalSeen(a.wireId, tick: tick)
            tick += 1.0
        }
        let aged = a.graph.getNode(b.wireId)
        try ok(aged == nil || aged.lifecycle == .expired, "aged-out node not live")
        try ok(!a.graph.isEdgeLive(a.wireId, b.wireId), "aged-out link does not route")

        // relationship memory: B signals again after full expiry and returns
        b.beginTick(21.0); a.beginTick(21.0)
        for blob in b.outgoing() { _ = a.onPacket(remoteId: b.wireId, blob: blob) }
        b.beginTick(22.0); a.beginTick(22.0)
        for blob in b.outgoing() { _ = a.onPacket(remoteId: b.wireId, blob: blob) }
        a.graph.refresh(t: 22.0)
        try ok(a.graph.getNode(b.wireId)?.lifecycle == .active,
               "re-signaling peer re-admitted after expiry (relationship memory)")
        try ok(a.graph.isEdgeLive(a.wireId, b.wireId), "revived edge routes again")

        let g = a.guidance("PING")
        try ok(g.mode != "NAVIGATING", "no route after link expiry")

        let outsider = IncidentSession.makeSession(incidentId: "some-other-incident")
        let forge = outsider.attach(RelayPacket(
            messageType: .sosUpdate, eventId: SosId("PING"), sender: NodeId("EVIL0001"),
            sourceVersion: 99, hop: 0, ttl: 8, timestamp: a.t))
        let before = a.rejectedMacs
        _ = a.onPacket(remoteId: NodeId("EVIL0001"), blob: codec.encode(forge))
        try ok(a.rejectedMacs == before + 1, "foreign-session packet rejected")
        try ok(!a.graph.hasNode(NodeId("EVIL0001")), "forgery never touches the graph")

        // ghost-kill: origin ends the incident; downstream must stop
        // advertising it within (hops x routeFreshness), not the lifetime
        let t2 = DeviceApp(nodeId: NodeId("T"), edgeExpireAfter: 5.0, nodeExpireAfter: 10.0)
        let m2 = DeviceApp(nodeId: NodeId("M"), edgeExpireAfter: 5.0, nodeExpireAfter: 10.0)
        let ghost = IncidentSession.makeSession(incidentId: "ghost-test")
        t2.joinIncident(ghost); m2.joinIncident(ghost)
        t2.startSos("DONE")
        exchange(t2, m2, rounds: 3)
        try ok(m2.guidance("DONE").mode == "NAVIGATING", "ghost pre-end route is live")
        _ = t2.endSos("DONE")
        var gt = 4.0
        for _ in 0..<30 {
            t2.beginTick(gt); m2.beginTick(gt)
            for blob in t2.outgoing() { _ = m2.onPacket(remoteId: t2.wireId, blob: blob) }
            for blob in m2.outgoing() { _ = t2.onPacket(remoteId: m2.wireId, blob: blob) }
            gt += 1.0
        }
        let ghostAds = m2.outgoing().filter { bl ->
            let p = try! codec.decode(bl)
            return p.messageType == .sosUpdate && p.eventId?.value == "DONE"
        }
        try ok(ghostAds.isEmpty, "relay stops advertising an ended incident")
        try ok(m2.guidance("DONE").mode != "NAVIGATING",
               "no ghost route after the origin ends")

        return Report(checks: checks)
    }

    private static func runDirectionCompatParity(checks: inout Int,
                                                  ok: (Bool, String) throws -> Void) throws {
        var sweep = DirectionSweep()
        var ts = 1000.0
        var deg = 0
        while deg < 360 {
            let sep = abs(((deg - 120 + 540) % 360) - 180)
            sweep.addSample(rssiDbm: -55.0 - Double(sep) * 0.5,
                            headingDeg: Double(deg), ts: ts)
            ts += 0.05
            deg += 15
        }
        let est = sweep.estimate(now: ts + 0.01)
        try ok(est.detected && abs(est.bearingDeg - 120.0) <= 22.5,
               "sweep recovers 120 deg (got \(est.bearingDeg))")
        try ok(est.confidence > 0.0 && est.sigmaDeg != nil,
               "sweep confidence -> sigma")
        try ok(!sweep.estimate(now: ts + 20.0).detected,
               "stale sweep reports not-detected")

        let fused = BearingFusion.fusepatches([(90.0, 1.0), (95.0, 1.0)])
        try ok(fused != nil && abs(fused!.meanDeg - 92.5) < 3.0,
               "fusion mean ~92.5")
        try ok(fused!.sigmaDeg < 30.0, "fusion sigma tight (\(fused!.sigmaDeg))")
        let boost = BearingFusion.reciprocalBoost(selfBearing: 90.0,
                                                  peerBearingToMe: 265.0)
        try ok(boost != nil && abs(boost!.meanDeg - 88.3) < 3.0,
               "reciprocal boost mean ~88.3 (got \(boost!.meanDeg))")

        let ble4 = CapabilityRegistry(advertising: true, scanning: true, imu: false,
                                      compass: false, rotate: false, haveCS: false)
        let ble5 = CapabilityRegistry(advertising: true, scanning: true, imu: true,
                                      compass: true, rotate: true, haveCS: false)
        let csPhone = CapabilityRegistry(advertising: true, scanning: true, imu: true,
                                         compass: true, rotate: true, haveCS: true)
        try ok(ble4.bestTier(peer: ble5) == .rssiLogdist,
               "ble4+ble5 -> RSSI log-distance")
        try ok(csPhone.bestTier(peer: ble4) == .rssiLogdist,
               "CS not used until peer has CS")
        try ok(csPhone.bestTier(peer: csPhone) == .compassCS,
               "two CS phones negotiate CS tier")

        let oob = OobSideband.serialize(peerBearingToMeDeg: 84.5)
        try ok(abs(OobSideband.parse(oob)! - 84.5) < 1e-9,
               "OOB sideband round-trips")
        try ok(OobSideband.parse("SOMETHING/ELSE") == nil,
               "foreign sideband rejected")
    }

    private static func exchange(_ va: DeviceApp, _ vb: DeviceApp, rounds: Int) {
        var tick = 1.0
        for _ in 0..<rounds {
            va.beginTick(tick); vb.beginTick(tick)
            for blob in va.outgoing() { _ = vb.onPacket(remoteId: va.wireId, blob: blob) }
            for blob in vb.outgoing() { _ = va.onPacket(remoteId: vb.wireId, blob: blob) }
            tick += 1.0
        }
    }
}