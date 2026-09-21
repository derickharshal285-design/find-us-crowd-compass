package com.findus.crowdcompass.engine

/**
 * SOS gradient engine port of core/sos.py. A device only ever holds the hops it
 * personally adopted (spec §53); dedup is bounded.
 */
class SosEngine(
    val defaultTtlHops: Int = 8,
    val defaultLifespan: Double? = 900.0,
    val dedupWindow: Int = 20000,
) {
    val events = linkedMapOf<String, Sos>()
    val gradient = linkedMapOf<String, LinkedHashMap<String, HopState>>()
    private val seen = linkedSetOf<String>()
    var adoptions = 0

    fun createSos(sosId: Any, origin: Any, t: Double, ttlHops: Int? = null,
                  lifespan: Double? = null): Sos {
        val sid = SosId(sosId.toString())
        val o = NodeId(origin.toString())
        val ttl = ttlHops ?: defaultTtlHops
        val life = lifespan ?: defaultLifespan
        val sos = Sos(sid, o, createdAt = t, version = 1, ttlHops = ttl,
            lifespanSeconds = life, expiresAt = if (life != null) t + life else null)
        events[sid.value] = sos
        gradient[sid.value] = linkedMapOf(o.value to HopState(0, 1, t))
        return sos
    }

    fun isActive(sosId: Any, t: Double): Boolean {
        val sos = events[sosId.toString()] ?: return false
        if (sos.status != SosStatus.ACTIVE) return false
        val exp = sos.expiresAt ?: return true
        return t <= exp
    }

    fun activeSosIds(t: Double): List<SosId> =
        events.values.filter {
            if (it.status != SosStatus.ACTIVE) return@filter false
            val exp = it.expiresAt
            exp == null || t <= exp
        }.map { it.id }

    fun expire(sosId: Any, t: Double): Boolean {
        val sos = events[sosId.toString()] ?: return false
        sos.status = SosStatus.EXPIRED
        gradient.remove(sosId.toString())
        return true
    }

    fun expireStale(t: Double): List<SosId> {
        val dead = events.values.filter {
            if (it.status != SosStatus.ACTIVE) return@filter false
            val exp = it.expiresAt
            exp != null && t > exp
        }.map { it.id }
        for (sid in dead) {
            events[sid.value]?.status = SosStatus.EXPIRED
            gradient.remove(sid.value)
        }
        return dead
    }

    fun renew(sosId: Any, t: Double): Sos? {
        val sos = events[sosId.toString()] ?: return null
        if (sos.status != SosStatus.ACTIVE) return null
        sos.version += 1
        if (sos.expiresAt != null && sos.lifespanSeconds != null) {
            sos.expiresAt = t + sos.lifespanSeconds
        }
        return sos
    }

    /** Port of hear(): accepts only strictly-better routes. */
    fun hear(sosId: Any, fromNode: Any, advertiserHop: Int, version: Int = 1,
             t: Double, checkDuplicate: Boolean = true): Pair<Boolean, Int?> {
        val sid = SosId(sosId.toString())
        val node = NodeId(fromNode.toString())
        if (!isActive(sid, t)) return false to null
        if (checkDuplicate && markSeen(sid, version, fromNode.toString(), advertiserHop)) {
            return false to null
        }
        val sos = events[sid.value]!!  // isActive implies present
        val candidate = advertiserHop + 1
        if (candidate > sos.ttlHops) return false to null
        val g = gradient.getOrPut(sid.value) { linkedMapOf() }
        val cur = g[node.value]
        if (cur != null && version < cur.version) return false to null
        if (cur != null && candidate >= cur.hop) return false to null
        g[node.value] = HopState(candidate, version, t)
        adoptions += 1
        return true to candidate
    }

    private fun markSeen(sid: SosId, version: Int, sender: String, hop: Int): Boolean {
        val key = "${sid.value}\u0000$version\u0000$sender\u0000$hop"
        if (key in seen) return true
        if (seen.size >= dedupWindow) seen.clear()  // bounded memory (reference semantics)
        seen.add(key)
        return false
    }

    fun hopOf(sosId: Any, node: Any): Int? =
        gradient[sosId.toString()]?.get(node.toString())?.hop
}