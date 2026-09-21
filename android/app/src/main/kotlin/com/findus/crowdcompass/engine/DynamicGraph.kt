package com.findus.crowdcompass.engine

/**
 * Device-local communication graph port of core/graph.py (spec §18-20).
 * Holds only what THIS device hears: neighbors + their edges (O(k), never O(N)).
 */
class NodeEntry(val id: NodeId, var lifecycle: NodeLifecycle,
                var lastSeen: Double, val firstSeen: Double)

class EdgeEntry(val endpoints: Pair<NodeId, NodeId>, var lifecycle: EdgeLifecycle,
                val firstSeen: Double, var lastSeen: Double,
                var lastBidirectionalExchange: Double = 0.0)

class DynamicGraph(
    val nodeStaleAfter: Double = 60.0,
    val nodeExpireAfter: Double = 120.0,
    val edgeStaleAfter: Double = 60.0,
    val edgeExpireAfter: Double = 60.0,
) {
    private val nodes = linkedMapOf<String, NodeEntry>()
    private val edges = linkedMapOf<String, EdgeEntry>()

    fun addNode(nodeId: NodeId, t: Double): NodeId {
        val nid = NodeId(nodeId.value)
        val existing = nodes[nid.value]
        if (existing == null) {
            nodes[nid.value] = NodeEntry(nid, NodeLifecycle.DISCOVERED, t, t)
        } else {
            existing.lastSeen = t
        }
        return nid
    }

    fun touchNode(nodeId: NodeId, t: Double) {
        nodes[nodeId.value]?.lastSeen = t
    }

    fun hasNode(nodeId: NodeId): Boolean = nodes.containsKey(nodeId.value)

    fun getNode(nodeId: NodeId): NodeEntry? = nodes[nodeId.value]

    fun nodeIds(): List<NodeId> = nodes.values.map { it.id }

    /** Join-on-first-relationship: an unheard node is created the first time it is seen. */
    fun addEdge(u: NodeId, v: NodeId, t: Double): Pair<NodeId, NodeId>? {
        if (!nodes.containsKey(u.value)) addNode(u, t)
        if (!nodes.containsKey(v.value)) addNode(v, t)
        val key = edgeKey(u, v)
        val existing = edges[key]
        if (existing != null) {
            if (existing.lifecycle == EdgeLifecycle.EXPIRED) {
                existing.lifecycle = EdgeLifecycle.SEEN
            }
            existing.lastSeen = t
            return existing.endpoints
        }
        val endpoints = edgeEndpoints(u, v)
        edges[key] = EdgeEntry(endpoints, EdgeLifecycle.SEEN, t, t)
        return endpoints
    }

    fun touchEdge(u: NodeId, v: NodeId, t: Double, bidirectional: Boolean): Boolean {
        val key = edgeKey(u, v)
        val st = edges[key] ?: return false
        st.lastSeen = t
        if (bidirectional) st.lastBidirectionalExchange = t
        refreshLifecycles(t)
        return true
    }

    fun getEdge(u: NodeId, v: NodeId): EdgeEntry? = edges[edgeKey(u, v)]

    fun hasEdge(u: NodeId, v: NodeId): Boolean = edges.containsKey(edgeKey(u, v))

    fun isEdgeLive(u: NodeId, v: NodeId): Boolean {
        val st = getEdge(u, v) ?: return false
        return st.lifecycle != EdgeLifecycle.EXPIRED &&
            isLive(st.endpoints.first) && isLive(st.endpoints.second)
    }

    fun neighbors(v: NodeId): List<NodeId> {
        val out = linkedSetOf<String>()
        for (st in edges.values) {
            if (st.lifecycle == EdgeLifecycle.EXPIRED) continue
            val (a, b) = st.endpoints
            if (!isLive(a) || !isLive(b)) continue
            when (v.value) {
                a.value -> out.add(b.value)
                b.value -> out.add(a.value)
            }
        }
        return out.map { NodeId(it) }
    }

    fun isLive(nid: NodeId): Boolean =
        nodes[nid.value]?.lifecycle != NodeLifecycle.EXPIRED

    /** Refresh lifecycles: silence ages, signaling refreshes (spec §19-20). */
    fun refresh(t: Double) {
        refreshLifecycles(t)
    }

    private fun refreshLifecycles(t: Double) {
        for (st in nodes.values) {
            // NOT skipped when EXPIRED: freshly-touched nodes (authenticated
            // radio contact resumed) drop back under the thresholds and are
            // re-admitted (relationship memory); untouched ones stay EXPIRED
            // since their age is still past the hard threshold.
            val age = t - st.lastSeen
            val newLife = when {
                age > nodeExpireAfter -> NodeLifecycle.EXPIRED
                age > nodeStaleAfter -> NodeLifecycle.STALE
                else -> NodeLifecycle.ACTIVE
            }
            if (newLife != st.lifecycle) {
                st.lifecycle = newLife
                if (newLife == NodeLifecycle.EXPIRED) {
                    for (e in edges.values) {
                        if (e.endpoints.first.value == st.id.value ||
                            e.endpoints.second.value == st.id.value
                        ) {
                            e.lifecycle = EdgeLifecycle.EXPIRED
                        }
                    }
                }
            }
        }
        for (e in edges.values) {
            // EXPIRED edges stick until addEdge explicitly re-arms them (.SEEN)
            // on a fresh received signal (same rule as the Python engine).
            if (e.lifecycle == EdgeLifecycle.EXPIRED) continue
            val age = t - e.lastSeen
            val newLife = when {
                age > edgeExpireAfter -> EdgeLifecycle.EXPIRED
                age > edgeStaleAfter -> EdgeLifecycle.AGING
                else -> EdgeLifecycle.ACTIVE
            }
            if (newLife != e.lifecycle) e.lifecycle = newLife
        }
    }

    companion object {
        private const val SEP = '\u0000'
        fun edgeKey(u: NodeId, v: NodeId): String {
            val (a, b) = if (u.value <= v.value) u.value to v.value else v.value to u.value
            return a + SEP + b
        }
        fun edgeEndpoints(u: NodeId, v: NodeId): Pair<NodeId, NodeId> =
            if (u.value <= v.value) u to v else v to u
    }
}