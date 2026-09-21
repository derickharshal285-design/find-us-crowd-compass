import Foundation

/// SOS gradient engine (port of core/sos.py): a device only holds the hops it
/// adopted itself; dedup is bounded.
public final class SosEngine {
    public let defaultTtlHops: Int
    public let defaultLifespan: Double?
    public let dedupWindow: Int

    public private(set) var events: [String: Sos] = [:]
    public private(set) var gradient: [String: [String: HopState]] = [:]
    public private(set) var adoptions = 0

    private var seen: Set<String> = []

    public init(defaultTtlHops: Int = 8, defaultLifespan: Double? = 900.0,
                dedupWindow: Int = 20000) {
        self.defaultTtlHops = defaultTtlHops
        self.defaultLifespan = defaultLifespan
        self.dedupWindow = dedupWindow
    }

    @discardableResult
    public func createSos(_ sosId: Any, origin: Any, t: Double, ttlHops: Int? = nil,
                          lifespan: Double? = nil) -> Sos {
        let sid = SosId(String(describing: sosId))
        let o = NodeId(String(describing: origin))
        let ttl = ttlHops ?? defaultTtlHops
        let life = lifespan ?? defaultLifespan
        let sos = Sos(id: sid, origin: o, createdAt: t, version: 1, ttlHops: ttl,
                      lifespanSeconds: life, expiresAt: life != nil ? t + life : nil)
        events[sid.value] = sos
        gradient[sid.value] = [o.value: HopState(hop: 0, version: 1, updatedAt: t)]
        return sos
    }

    public func isActive(_ sosId: Any, t: Double) -> Bool {
        guard let sos = events[String(describing: sosId)], sos.status == .active else {
            return false
        }
        guard let exp = sos.expiresAt else { return true }
        return t <= exp
    }

    public func activeSosIds(t: Double) -> [SosId] {
        events.values.filter {
            guard $0.status == .active else { return false }
            guard let exp = $0.expiresAt else { return true }
            return t <= exp
        }.map { $0.id }
    }

    @discardableResult
    public func expire(_ sosId: Any, t: Double) -> Bool {
        guard let sos = events[Self.key(for: sosId)] else { return false }
        sos.status = .expired
        gradient.removeValue(forKey: Self.key(for: sosId))
        return true
    }

    @discardableResult
    public func expireStale(t: Double) -> [SosId] {
        let dead = events.values.filter {
            guard $0.status == .active, let exp = $0.expiresAt else { return false }
            return t > exp
        }.map { $0.id }
        for sid in dead {
            events[sid.value]?.status = .expired
            gradient.removeValue(forKey: sid.value)
        }
        return dead
    }

    public func renew(_ sosId: Any, t: Double) -> Sos? {
        guard let sos = events[String(describing: sosId)], sos.status == .active else {
            return nil
        }
        sos.version += 1
        if sos.expiresAt != nil, let life = sos.lifespanSeconds {
            sos.expiresAt = t + life
        }
        return sos
    }

    /// Port of hear(): accepts only strictly-better routes.
    public func hear(_ sosId: Any, fromNode: Any, advertiserHop: Int, version: Int = 1,
                     t: Double, checkDuplicate: Bool = true) -> (Bool, Int?) {
        let sid = SosId(String(describing: sosId))
        let node = NodeId(String(describing: fromNode))
        guard isActive(sid, t) else { return (false, nil) }
        if checkDuplicate && markSeen(sid, version, String(describing: fromNode), advertiserHop) {
            return (false, nil)
        }
        guard let sos = events[sid.value] else { return (false, nil) }
        let candidate = advertiserHop + 1
        guard candidate <= sos.ttlHops else { return (false, nil) }
        if gradient[sid.value] == nil { gradient[sid.value] = [:] }
        let cur = gradient[sid.value]?[node.value]
        if let cur, version < cur.version { return (false, nil) }
        if let cur, candidate >= cur.hop { return (false, nil) }
        gradient[sid.value]?[node.value] = HopState(hop: candidate, version: version, updatedAt: t)
        adoptions += 1
        return (true, candidate)
    }

    private func markSeen(_ sid: SosId, _ version: Int, _ sender: String, _ hop: Int) -> Bool {
        let key = "\(sid.value)\u{0}\(version)\u{0}\(sender)\u{0}\(hop)"
        if seen.contains(key) { return true }
        if seen.count >= dedupWindow { seen.removeAll() }
        seen.insert(key)
        return false
    }

    public func hopOf(_ sosId: Any, node: Any) -> Int? {
        gradient[Self.key(for: sosId)]?[String(describing: node)]?.hop
    }

    static func key(for sosId: Any) -> String {
        if let s = sosId as? SosId { return s.value }
        return String(describing: sosId)
    }
}