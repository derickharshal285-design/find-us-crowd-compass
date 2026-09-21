package com.findus.crowdcompass.engine

/**
 * Navigation-tier capability negotiation (parity of core/compat.py).
 *
 * BLE4 and BLE5 phones must keep working together (and with BLE6/UWB later):
 * every phone advertises what its navigation can actually measure, and both
 * ends of a link run CapabilityRegistry to agree on the *lowest* mutually
 * measurable tier. Older builds only ever see measurables they already know,
 * so nothing upstream breaks.
 */
enum class NavTier(val rank: Int) {
    UWB(6),
    COMPASS_CS(5),
    MOTION_VECTOR(4),
    HEADING_REL(3),
    RSSI_LOGDIST(2),
    RSSI_BAND(1),
    HOP_GRADIENT(0);

    companion object {
        fun best(a: NavTier, b: NavTier): NavTier = if (a.rank <= b.rank) a else b
    }
}

/** Measurables a build can derive, mirroring core/compat.CapabilityRegistry. */
class CapabilityRegistry(
    val advertising: Boolean,
    val scanning: Boolean,
    val imu: Boolean,
    val compass: Boolean,
    val rotate: Boolean,
    val haveCs: Boolean,
) {
    fun availableTiers(peer: CapabilityRegistry?): List<NavTier> {
        val out = mutableListOf<NavTier>()
        out += NavTier.RSSI_BAND
        if (peer == null || peer.scanning) out += NavTier.RSSI_LOGDIST
        if (compass) out += NavTier.HEADING_REL
        if (imu) out += NavTier.MOTION_VECTOR
        if (haveCs && peer != null && peer.haveCs) out += NavTier.COMPASS_CS
        return out.sortedBy { it.rank }
    }

    fun bestTier(peer: CapabilityRegistry?): NavTier? =
        availableTiers(peer).sortedBy { it.rank }.lastOrNull()
}

/**
 * OOB sideband for the CS/UWB reciprocity bonus: a peer shares its bearing
 * *back to us* (opposite of what it sees). Text-frame, versioned (parity of
 * core/compat.OobSideband).
 */
object OobSideband {
    const val PREFIX_OOB = "FINDUS/OOB/1\n"

    fun serialize(peerBearingToMeDeg: Double): String =
        PREFIX_OOB + peerBearingToMeDeg.toString()

    fun parse(raw: String): Double? {
        if (!raw.startsWith(PREFIX_OOB)) return null
        return try {
            val v = raw.removePrefix(PREFIX_OOB).trim().toDouble()
            if (!v.isFinite() || v < 0.0 || v >= 360.0) null else v
        } catch (_: NumberFormatException) {
            null
        }
    }
}