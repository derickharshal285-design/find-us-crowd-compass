package com.findus.crowdcompass.engine

/**
 * One phone. Mirrors app/devices.py + app/guidance.py: EVERYTHING is the
 * device's local view; never a hop it did not adopt, never a route it cannot
 * show (spec §53, §65).
 */
class GuidanceInstruction(
    val sosId: SosId,
    val mode: String,          // NO_SOS_KNOWN | NO_VALID_ROUTE | NAVIGATING | AT_TARGET
    val summary: String,
    val myHop: Int? = null,
    val target: NodeId? = null,
    val targetIsOrigin: Boolean = false,
    val hint: String = "",
) {
    override fun toString(): String = "[$mode] $summary"
}

class DeviceApp(
    val id: NodeId,
    var t: Double = 0.0,
    val ttlHops: Int = 8,
    val lifespan: Double = 900.0,
    val nodeExpireAfter: Double = 120.0,
    val edgeExpireAfter: Double = 60.0,
    val hasDirectionSensor: Boolean = false,
    installKey: ByteArray? = null,
) {
    val installKey: ByteArray = installKey ?: ("crowd-install:" + id.value).toByteArray()
    var incident: IncidentSession? = null
    val graph = DynamicGraph(nodeStaleAfter = 60.0, nodeExpireAfter = nodeExpireAfter,
        edgeStaleAfter = 60.0, edgeExpireAfter = edgeExpireAfter)
    val sosEngine = SosEngine(defaultTtlHops = ttlHops, defaultLifespan = lifespan)
    val codec = ProtocolWire()
    val routeFreshness = nodeExpireAfter
    val advertisements = linkedMapOf<String, LinkedHashMap<String, HopAdvertisement>>()
    var rejectedMacs = 0

    val wireId: NodeId
        get() = incident?.let { NodeId(it.pseudonym(installKey)) } ?: id

    init {
        graph.addNode(wireId, t)
    }

    fun joinIncident(session: IncidentSession) {
        incident = session
        graph.addNode(wireId, t)
    }

    fun beginTick(tick: Double) {
        t = tick
        graph.touchNode(wireId, tick)
        graph.refresh(tick)
        sosEngine.expireStale(tick)
    }

    // ---- SOS lifecycle (origin role) ----
    fun startSos(sosId: Any, ttl: Int? = null, life: Double? = null): Sos =
        sosEngine.createSos(sosId, wireId, t = t,
            ttlHops = ttl ?: ttlHops, lifespan = life ?: lifespan)

    fun renewSos(sosId: Any): Sos? = sosEngine.renew(sosId, t)
    fun endSos(sosId: Any): Boolean = sosEngine.expire(sosId, t)

    // ---- advertise ----
    fun outgoing(): List<ByteArray> {
        val out = mutableListOf<ByteArray>()
        val hb = RelayPacket(MessageType.HEARTBEAT, sender = wireId, timestamp = t)
        out.add(encodeSigned(hb))
        for (sid in sosEngine.activeSosIds(t)) {
            val hop = sosEngine.hopOf(sid, wireId) ?: continue
            val ev = sosEngine.events[sid.value] ?: continue
            if (hop > 0 && bestHopAdvert(sid, hop - 1) == null) {
                // spec §53/§20: never advertise a hop you cannot back with a
                // live fresher claim. Keeps ghosts from propagating after the
                // origin stops signaling (or an incident ends). Mirrors Python.
                continue
            }
            out.add(encodeSigned(RelayPacket(
                messageType = MessageType.SOS_UPDATE, eventId = sid,
                sender = wireId, hop = hop, ttl = ev.ttlHops,
                sourceVersion = ev.version, timestamp = t)))
        }
        return out
    }

    private fun bestHopAdvert(sid: SosId, wantHop: Int): HopAdvertisement? {
        var best: HopAdvertisement? = null
        for (nb in graph.neighbors(wireId)) {
            val ad = advertised(sid, nb) ?: continue
            if (ad.hop != wantHop) continue
            if (t - ad.t > routeFreshness) continue
            if (best == null || ad.t > best.t) best = ad
        }
        return best
    }

    private fun encodeSigned(pkt: RelayPacket): ByteArray {
        val signed = incident?.attach(pkt) ?: pkt
        return codec.encode(signed)
    }

    // ---- receive ----
    fun onPacket(remoteId: NodeId, blob: ByteArray): Int {
        val pkt = try { codec.decode(blob) } catch (e: ProtocolWire.ProtocolError) { return 0 }
        val src = pkt.sender ?: return 0
        if (incident != null && !incident!!.verify(pkt)) {
            rejectedMacs++
            return 0
        }
        signalSeen(src, t)
        if (pkt.eventId != null && pkt.messageType in setOf(
                MessageType.SOS, MessageType.SOS_UPDATE, MessageType.RELAY)) {
            val sid = SosId(pkt.eventId.value)
            recordAdvertisement(sid, src, pkt.hop, pkt.sourceVersion, t)
            ensureEvent(sid, pkt.sourceVersion, if (pkt.ttl > 0) pkt.ttl else ttlHops)
            val (accepted, _) = sosEngine.hear(
                sid, wireId, pkt.hop, pkt.sourceVersion, t, checkDuplicate = true)
            if (accepted) return 1
        }
        return 0
    }

    fun signalSeen(src: NodeId, tick: Double) {
        if (!graph.hasNode(src)) graph.addNode(src, tick)
        graph.touchNode(src, tick)
        val edge = graph.addEdge(wireId, src, tick)
        if (edge != null) graph.touchEdge(wireId, src, tick, bidirectional = true)
    }

    fun recordAdvertisement(sid: SosId, src: NodeId, hop: Int, version: Int, tick: Double) {
        val bucket = advertisements.getOrPut(sid.value) { linkedMapOf() }
        val prev = bucket[src.value]
        if (prev == null || version > prev.version || tick > prev.t) {
            bucket[src.value] = HopAdvertisement(hop, version, tick)
        }
    }

    fun advertised(sid: Any, node: Any): HopAdvertisement? =
        advertisements[sid.toString()]?.get(node.toString())

    fun ensureEvent(sid: SosId, version: Int, ttl: Int) {
        var ev = sosEngine.events[sid.value]
        if (ev == null) {
            ev = Sos(sid, NodeId("<unknown>"), createdAt = t, version = maxOf(1, version),
                ttlHops = maxOf(1, ttl), lifespanSeconds = lifespan,
                expiresAt = t + lifespan)
            sosEngine.events[sid.value] = ev
            sosEngine.gradient[sid.value] = linkedMapOf()
            return
        }
        if (version > ev.version) {
            ev.version = version
            val lifespan = ev.lifespanSeconds
            if (lifespan != null) ev.expiresAt = t + lifespan
        }
    }

    // ---- reading ----
    fun knownSos(sosId: Any): Boolean {
        val ev = sosEngine.events[sosId.toString()] ?: return false
        if (ev.status != SosStatus.ACTIVE) return false
        val exp = ev.expiresAt
        return exp == null || t <= exp
    }

    fun hopMap(sosId: Any): Map<String, Int> =
        sosEngine.gradient[sosId.toString()]?.entries?.associate { it.key to it.value.hop }.orEmpty()

    fun guidance(sosId: Any): GuidanceInstruction {
        val sid = SosId(sosId.toString())
        val me = wireId
        val ev = sosEngine.events[sid.value]
        if (ev == null || ev.status != SosStatus.ACTIVE) {
            return GuidanceInstruction(sid, "NO_SOS_KNOWN", "no such emergency signal in range")
        }
        if (!sosEngine.isActive(sid, t)) {
            return GuidanceInstruction(sid, "NO_SOS_KNOWN", "emergency signal has expired")
        }
        val myHop = sosEngine.hopOf(sid, me)
        if (myHop == null) {
            return GuidanceInstruction(sid, "NO_VALID_ROUTE", "signal heard, no route adopted yet")
        }
        val origin = if (ev.origin.value.isNotEmpty() && ev.origin.value != "<unknown>")
            ev.origin else null
        if (myHop == 0) {
            return GuidanceInstruction(sid, "AT_TARGET",
                "you are the origin of $sid", myHop = 0, targetIsOrigin = true)
        }
        val cands = thoughtOrderedCands(sid, me, myHop)
        if (cands.isEmpty()) {
            return GuidanceInstruction(sid, "NO_VALID_ROUTE",
                "route broken at hop $myHop: no live hop-${myHop - 1} advertiser", myHop = myHop)
        }
        val best = cands.first()
        val alternatives = cands.drop(1)
        val targetIsOrigin = origin != null && best == origin
        val detail = "emergency at hop $myHop; move toward device '${best.value}'" +
            " (${cands.size} route(s) of hop ${myHop - 1})"
        return GuidanceInstruction(sid, "NAVIGATING", detail, myHop = myHop,
            target = best, targetIsOrigin = targetIsOrigin, hint = directionHint())
    }

    private fun thoughtOrderedCands(sid: SosId, me: NodeId, myHop: Int): List<NodeId> {
        val cands = mutableListOf<Pair<NodeId, Double>>()
        for (nb in graph.neighbors(me)) {
            val ad = advertised(sid, nb) ?: continue
            if (ad.hop != myHop - 1) continue
            if (t - ad.t > routeFreshness) continue
            cands.add(nb to ad.t)
        }
        return cands.sortedByDescending { it.second }.map { it.first }
    }

    private fun directionHint(): String =
        if (hasDirectionSensor) {
            "measured bearing (needs RESPONDER-GRADE validation)"
        } else {
            "physical direction on a plain phone is UNPROVEN (research); walk and check which route stays freshest"
        }

    fun neighborsText(): String {
        val nbs = graph.neighbors(wireId)
        if (nbs.isEmpty()) return "none"
        return nbs.joinToString("; ") { nb ->
            val e = graph.getEdge(wireId, nb)
            if (e != null) "${nb.value} (t=${e.lastSeen.toLong()})" else nb.value
        }
    }
}