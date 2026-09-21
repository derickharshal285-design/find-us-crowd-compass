import Foundation

/// Guidance instruction — honest by construction (port of app/guidance.py).
public struct GuidanceInstruction {
    public let sosId: SosId
    public let mode: String       // NO_SOS_KNOWN | NO_VALID_ROUTE | NAVIGATING | AT_TARGET
    public let summary: String
    public let myHop: Int?
    public let target: NodeId?
    public let targetIsOrigin: Bool
    public let hint: String
}

/// One phone (port of app/devices.py): everything is this device's local view.
public final class DeviceApp {
    public let id: NodeId
    public var t: Double = 0.0
    public let ttlHops: Int
    public let lifespan: Double
    public let nodeExpireAfter: Double
    public let edgeExpireAfter: Double
    public let hasDirectionSensor: Bool
    public let installKey: Data

    public var incident: IncidentSession?
    public let graph = DynamicGraph()
    public let sosEngine = SosEngine()
    public let codec = ProtocolWire()
    public private(set) var rejectedMacs = 0
    public private(set) var advertisements: [String: [String: HopAdvertisement]] = [:]

    public var wireId: NodeId {
        guard let inc = incident else { return id }
        return NodeId(inc.pseudonym(installKey: installKey))
    }

    public init(id: NodeId, ttlHops: Int = 8, lifespan: Double = 900.0,
                nodeExpireAfter: Double = 120.0, edgeExpireAfter: Double = 60.0,
                hasDirectionSensor: Bool = false, installKey: Data? = nil) {
        self.id = id
        self.ttlHops = ttlHops
        self.lifespan = lifespan
        self.nodeExpireAfter = nodeExpireAfter
        self.edgeExpireAfter = edgeExpireAfter
        self.hasDirectionSensor = hasDirectionSensor
        self.installKey = installKey ?? Data("crowd-install:\(id.value)".utf8)
        graph.addNode(wireId, t: t)
    }

    public func joinIncident(_ session: IncidentSession) {
        incident = session
        graph.addNode(wireId, t: t)
    }

    public func beginTick(_ tick: Double) {
        t = tick
        graph.touchNode(wireId, t: tick)
        graph.refresh(t: tick)
        _ = sosEngine.expireStale(t: tick)
    }

    // ---- SOS lifecycle (origin role) ----
    @discardableResult
    public func startSos(_ sosId: Any, ttl: Int? = nil, life: Double? = nil) -> Sos {
        sosEngine.createSos(SosId(String(describing: sosId)), origin: wireId, t: t,
                            ttlHops: ttl ?? ttlHops, lifespan: life ?? lifespan)
    }
    public func renewSos(_ sosId: Any) -> Sos? { sosEngine.renew(sosId, t: t) }
    @discardableResult
    public func endSos(_ sosId: Any) -> Bool { sosEngine.expire(sosId, t: t) }

    // ---- advertise ----
    // ---- advertise ----
    public func outgoing() -> [Data] {
        var out: [Data] = []
        out.append(encodeSigned(RelayPacket(messageType: .heartbeat, sender: wireId,
                                            timestamp: t)))
        for sid in sosEngine.activeSosIds(t: t) {
            guard let hop = sosEngine.hopOf(sid, node: wireId),
                  let ev = sosEngine.events[SosEngine.key(for: sid)] else { continue }
            // spec §53/§20: never advertise a hop you cannot back with a live
            // fresher claim, so ghosts don't propagate after the origin stops
            // signaling. Mirrors Python and Kotlin.
            if hop > 0 && bestHopAdvert(sid, wantHop: hop - 1) == nil { continue }
            out.append(encodeSigned(RelayPacket(
                messageType: .sosUpdate, eventId: sid, sender: wireId, hop: hop,
                ttl: ev.ttlHops, sourceVersion: ev.version, timestamp: t)))
        }
        return out
    }

    private func bestHopAdvert(_ sid: SosId, wantHop: Int) -> HopAdvertisement? {
        var best: HopAdvertisement? = nil
        for nb in graph.neighbors(wireId) {
            guard let ad = advertised(sid, node: nb), ad.hop == wantHop else { continue }
            if t - ad.t > nodeExpireAfter { continue }
            if best == nil || ad.t > best!.t { best = ad }
        }
        return best
    }

    private func encodeSigned(_ pkt: RelayPacket) -> Data {
        let signed = incident?.attach(pkt) ?? pkt
        return codec.encode(signed)
    }

    // ---- receive ----
    @discardableResult
    public func onPacket(remoteId: NodeId, blob: Data) -> Int {
        guard let pkt = try? codec.decode(blob), let src = pkt.sender else { return 0 }
        if let inc = incident, !inc.verify(pkt) {
            rejectedMacs += 1
            return 0
        }
        signalSeen(src, tick: t)
        if let sid = pkt.eventId,
           pkt.messageType == .sos || pkt.messageType == .sosUpdate || pkt.messageType == .relay {
            recordAdvertisement(sid, src: src, hop: pkt.hop, version: pkt.sourceVersion, tick: t)
            ensureEvent(sid, version: pkt.sourceVersion, ttl: pkt.ttl > 0 ? pkt.ttl : ttlHops)
            let (accepted, _) = sosEngine.hear(sid, fromNode: wireId, advertiserHop: pkt.hop,
                                               version: pkt.sourceVersion, t: t,
                                               checkDuplicate: true)
            return accepted ? 1 : 0
        }
        return 0
    }

    public func signalSeen(_ src: NodeId, tick: Double) {
        if !graph.hasNode(src) { graph.addNode(src, t: tick) }
        graph.touchNode(src, t: tick)
        if graph.addEdge(wireId, src, t: tick) != nil {
            graph.touchEdge(wireId, src, t: tick, bidirectional: true)
        }
    }

    public func recordAdvertisement(_ sid: SosId, src: NodeId, hop: Int, version: Int, tick: Double) {
        if advertisements[sid.value] == nil { advertisements[sid.value] = [:] }
        let prev = advertisements[sid.value]?[src.value]
        if prev == nil || version > prev!.version || tick > prev!.t {
            advertisements[sid.value]?[src.value] = HopAdvertisement(hop: hop, version: version, t: tick)
        }
    }

    public func advertised(_ sid: Any, node: Any) -> HopAdvertisement? {
        advertisements[String(describing: sid)]?[String(describing: node)]
    }

    public func ensureEvent(_ sid: SosId, version: Int, ttl: Int) {
        var ev = sosEngine.events[sid.value]
        if ev == nil {
            ev = Sos(id: sid, origin: NodeId("<unknown>"), createdAt: t,
                     version: max(1, version), ttlHops: max(1, ttl),
                     lifespanSeconds: lifespan, expiresAt: t + lifespan)
            sosEngine.events[sid.value] = ev
            sosEngine.gradient[sid.value] = [:]
            return
        }
        if version > ev.version {
            ev.version = version
            if ev.lifespanSeconds != nil { ev.expiresAt = t + ev.lifespanSeconds }
        }
    }

    // ---- reading ----
    public func knownSos(_ sosId: Any) -> Bool {
        guard let ev = sosEngine.events[String(describing: sosId)],
              ev.status == .active else { return false }
        guard let exp = ev.expiresAt else { return true }
        return t <= exp
    }

    public func hopMap(_ sosId: Any) -> [String: Int] {
        (sosEngine.gradient[String(describing: sosId)] ?? [:])
            .mapValues { $0.hop }
    }

    public func guidance(_ sosId: Any) -> GuidanceInstruction {
        let sid = SosId(String(describing: sosId))
        let me = wireId
        guard let ev = sosEngine.events[sid.value], ev.status == .active else {
            return GuidanceInstruction(sosId: sid, mode: "NO_SOS_KNOWN",
                                       summary: "no such emergency signal in range",
                                       myHop: nil, target: nil, targetIsOrigin: false, hint: "")
        }
        guard sosEngine.isActive(sid, t: t) else {
            return GuidanceInstruction(sosId: sid, mode: "NO_SOS_KNOWN",
                                       summary: "emergency signal has expired",
                                       myHop: nil, target: nil, targetIsOrigin: false, hint: "")
        }
        guard let myHop = sosEngine.hopOf(sid, node: me) else {
            return GuidanceInstruction(sosId: sid, mode: "NO_VALID_ROUTE",
                                       summary: "signal heard, no route adopted yet",
                                       myHop: nil, target: nil, targetIsOrigin: false, hint: "")
        }
        let origin = ev.origin.value != "<unknown" && !ev.origin.value.isEmpty ? ev.origin : nil
        if myHop == 0 {
            return GuidanceInstruction(sosId: sid, mode: "AT_TARGET",
                                       summary: "you are the origin of \(sid)",
                                       myHop: 0, target: nil, targetIsOrigin: true, hint: "")
        }
        let cands = candidates(sid, me: me, myHop: myHop).sorted { $0.1 > $1.1 }
        if cands.isEmpty {
            return GuidanceInstruction(sosId: sid, mode: "NO_VALID_ROUTE",
                                       summary: "route broken at hop \(myHop): no live hop-\(myHop - 1) advertiser",
                                       myHop: myHop, target: nil, targetIsOrigin: false, hint: "")
        }
        let best = cands[0].0
        let detail = "emergency at hop \(myHop); move toward device '\(best.value)' " +
            "(\(cands.count) route(s) of hop \(myHop - 1))"
        return GuidanceInstruction(sosId: sid, mode: "NAVIGATING", summary: detail,
                                   myHop: myHop, target: best,
                                   targetIsOrigin: origin != nil && best == origin,
                                   hint: directionHint())
    }

    private func candidates(_ sid: SosId, me: NodeId, myHop: Int) -> [(NodeId, Double)] {
        var out: [(NodeId, Double)] = []
        for nb in graph.neighbors(me) {
            guard let ad = advertised(sid, node: nb) else { continue }
            guard ad.hop == myHop - 1 else { continue }
            guard t - ad.t <= nodeExpireAfter else { continue }
            out.append((nb, ad.t))
        }
        return out
    }

    private func directionHint() -> String {
        hasDirectionSensor
            ? "measured bearing (needs RESPONDER-GRADE validation)"
            : "physical direction on a plain phone is UNPROVEN (research); walk and check which route stays freshest"
    }
}