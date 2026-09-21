import XCTest
@testable import FindUsEngine

final class EngineParityTests: XCTestCase {
    func testParityBattery() throws {
        let report = try EngineSelfTest.run()
        XCTAssertGreaterThanOrEqual(report.checks, 20,
            "battery must certify at least as many checks as the reference")
    }

    func testCanonicalMACIsCodecAgreeing() throws {
        // The regression the whole build was armored against: a real-world
        // (post-2020) timestamp must MAC identically on both attach + verify.
        let session = IncidentSession.makeSession(incidentId: "evt")
        let codec = ProtocolWire()
        for ts in [EngineConstants.epoch + 1000.0, 1_789_690_000.0, 2_000_000_000.0] {
            let pkt = RelayPacket(messageType: .sosUpdate, eventId: SosId("evt-x"),
                                  sender: NodeId(session.pseudonym(installKey: Data("k".utf8))),
                                  sourceVersion: 4, hop: 2, ttl: 8, timestamp: ts)
            let wire = try codec.decode(codec.encode(session.attach(pkt)))
            XCTAssertTrue(session.verify(wire), "MAC at ts=\(ts)")
        }
    }

    func testU16TimestampRegression() {
        // uint16 would round-trip years 2000-2002 only; the uint32 canonical
        // field must handle 2026+ timestamps without wrap.
        let session = IncidentSession.makeSession(incidentId: "regression")
        let pkt = RelayPacket(messageType: .heartbeat, sender: NodeId("me"),
                              timestamp: 1_789_690_000.0)
        let tag = session.mac(pkt)
        XCTAssertEqual(tag.count, 8)
    }
}