import Foundation

/// Device-local dynamic graph (port of core/graph.py): holds only THIS
/// device's heard neighborhood — O(k), never O(N).
public final class NodeEntry {
    public let id: NodeId
    public var lifecycle: NodeLifecycle
    public var lastSeen: Double
    public let firstSeen: Double
    public init(id: NodeId, lifecycle: NodeLifecycle, lastSeen: Double, firstSeen: Double) {
        self.id = id; self.lifecycle = lifecycle
        self.lastSeen = lastSeen; self.firstSeen = firstSeen
    }
}

public final class EdgeEntry {
    public let endpoints: (NodeId, NodeId)
    public var lifecycle: EdgeLifecycle
    public let firstSeen: Double
    public var lastSeen: Double
    public var lastBidirectionalExchange: Double
    public init(endpoints: (NodeId, NodeId), lifecycle: EdgeLifecycle,
                firstSeen: Double, lastSeen: Double, lastBidirectionalExchange: Double = 0) {
        self.endpoints = endpoints; self.lifecycle = lifecycle
        self.firstSeen = firstSeen; self.lastSeen = lastSeen
        self.lastBidirectionalExchange = lastBidirectionalExchange
    }
}

public final class DynamicGraph {
    public let nodeStaleAfter: Double
    public let nodeExpireAfter: Double
    public let edgeStaleAfter: Double
    public let edgeExpireAfter: Double

    private var nodes: [String: NodeEntry] = [:]
    private var edges: [String: EdgeEntry] = [:]

    public init(nodeStaleAfter: Double = 60.0, nodeExpireAfter: Double = 120.0,
                edgeStaleAfter: Double = 60.0, edgeExpireAfter: Double = 60.0) {
        self.nodeStaleAfter = nodeStaleAfter
        self.nodeExpireAfter = nodeExpireAfter
        self.edgeStaleAfter = edgeStaleAfter
        self.edgeExpireAfter = edgeExpireAfter
    }

    @discardableResult
    public func addNode(_ nodeId: NodeId, t: Double) -> NodeId {
        if let existing = nodes[nodeId.value] {
            existing.lastSeen = t
        } else {
            nodes[nodeId.value] = NodeEntry(id: nodeId, lifecycle: .discovered,
                                            lastSeen: t, firstSeen: t)
        }
        return nodeId
    }

    public func touchNode(_ nodeId: NodeId, t: Double) {
        nodes[nodeId.value]?.lastSeen = t
    }

    public func hasNode(_ nodeId: NodeId) -> Bool { nodes[nodeId.value] != nil }
    public func getNode(_ nodeId: NodeId) -> NodeEntry? { nodes[nodeId.value] }
    public func nodeIds() -> [NodeId] { nodes.values.map { $0.id } }

    @discardableResult
    public func addEdge(_ u: NodeId, _ v: NodeId, t: Double) -> (NodeId, NodeId)? {
        if nodes[u.value] == nil { addNode(u, t: t) }
        if nodes[v.value] == nil { addNode(v, t: t) }
        let key = Self.edgeKey(u, v)
        if let existing = edges[key] {
            if existing.lifecycle == .expired { existing.lifecycle = .seen }
            existing.lastSeen = t
            return existing.endpoints
        }
        let endpoints = Self.edgeEndpoints(u, v)
        edges[key] = EdgeEntry(endpoints: endpoints, lifecycle: .seen,
                               firstSeen: t, lastSeen: t)
        return endpoints
    }

    @discardableResult
    public func touchEdge(_ u: NodeId, _ v: NodeId, t: Double, bidirectional: Bool) -> Bool {
        guard let st = edges[Self.edgeKey(u, v)] else { return false }
        st.lastSeen = t
        if bidirectional { st.lastBidirectionalExchange = t }
        refreshLifecycles(t)
        return true
    }

    public func getEdge(_ u: NodeId, _ v: NodeId) -> EdgeEntry? {
        edges[Self.edgeKey(u, v)]
    }

    public func isEdgeLive(_ u: NodeId, _ v: NodeId) -> Bool {
        guard let st = getEdge(u, v) else { return false }
        return st.lifecycle != .expired && isLive(st.endpoints.0) && isLive(st.endpoints.1)
    }

    public func neighbors(_ v: NodeId) -> [NodeId] {
        var out = Set<NodeId>()
        for st in edges.values {
            guard st.lifecycle != .expired else { continue }
            let (a, b) = st.endpoints
            guard isLive(a), isLive(b) else { continue }
            if a.value == v.value { out.insert(b) }
            else if b.value == v.value { out.insert(a) }
        }
        return out.sorted()
    }

    public func isLive(_ nid: NodeId) -> Bool {
        nodes[nid.value]?.lifecycle != .expired
    }

    public func refresh(t: Double) {
        refreshLifecycles(t)
    }

    private func refreshLifecycles(_ t: Double) {
        for st in nodes.values {
            // NOT skipped when .expired: if the node has since been freshly
            // touched (authenticated radio contact resumed) its age drops and
            // it is re-admitted (relationship memory); untouched nodes stay
            // expired because their age is still past the hard threshold.
            let age = t - st.lastSeen
            let newLife: NodeLifecycle =
                age > nodeExpireAfter ? .expired : (age > nodeStaleAfter ? .stale : .active)
            if newLife != st.lifecycle {
                st.lifecycle = newLife
                if newLife == .expired {
                    for e in edges.values where e.endpoints.0 == st.id || e.endpoints.1 == st.id {
                        e.lifecycle = .expired
                    }
                }
            }
        }
        for e in edges.values {
            // EXPIRED edges stick until addEdge explicitly re-arms them (.seen)
            // on a fresh received signal (same rule as the Python engine).
            guard e.lifecycle != .expired else { continue }
            let age = t - e.lastSeen
            e.lifecycle = age > edgeExpireAfter ? .expired
                : (age > edgeStaleAfter ? .aging : .active)
        }
    }

    private static let sep: Character = "\u{0}"
    static func edgeKey(_ u: NodeId, _ v: NodeId) -> String {
        let (a, b) = u.value <= v.value ? (u.value, v.value) : (v.value, u.value)
        return "\(a)\(sep)\(b)"
    }
    static func edgeEndpoints(_ u: NodeId, _ v: NodeId) -> (NodeId, NodeId) {
        u.value <= v.value ? (u, v) : (v, u)
    }
}