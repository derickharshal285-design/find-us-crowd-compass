package com.findus.crowdcompass.engine

import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Direction-finding parity port of core/direction.py.
 *
 * BLE4/5 phone-to-phone direction has no angle hardware: the handset is rotated
 * for a few seconds and the RSSI-vs-heading pattern peaks when the phone faces
 * the neighbor (DirectionSweep). All wire tokens and constants below must match
 * the verified Python reference exactly.
 */
object DirectionMath {
    const val RSSI_AT_1M_DBM = -59.0
    const val PATH_LOSS_N = 2.2
    const val BAND_NEAR_M = 5.0
    const val BAND_MEDIUM_M = 20.0
    const val SWEEP_WINDOW_S = 10.0
    const val SWEEP_MIN_SAMPLES = 12
    const val SWEEP_BIN_DEG = 45
    const val SWEEP_MIN_BIN_COUNT = 2

    fun wrap360(deg: Double): Double {
        var d = deg % 360.0
        if (d < 0) d += 360.0
        return d
    }

    fun opposite(bearing: Double): Double = wrap360(bearing + 180.0)

    fun rssiToMeters(rssiDbm: Double, aDbm: Double = RSSI_AT_1M_DBM,
                     n: Double = PATH_LOSS_N): Double {
        val meters = 10.0.pow((aDbm - rssiDbm) / (10.0 * n))
        return if (rssiDbm >= aDbm) max(0.5, meters) else meters
    }

    fun metersToBand(distanceM: Double): String = when {
        distanceM < BAND_NEAR_M -> "NEAR"
        distanceM < BAND_MEDIUM_M -> "MEDIUM"
        else -> "FAR"
    }

    /** Bearing-to-sigma map used by SweepEstimate.sigmaDeg. */
    fun confidenceToSigmaDeg(confidence: Double): Double {
        val c = min(1.0, max(0.0, confidence))
        return 5.0 + 90.0 * (1.0 - c)
    }
}

class SweepEstimate(
    val detected: Boolean,
    val bearingDeg: Double,
    val confidence: Double,
    val samples: Int = 0,
    val occupiedBins: Int = 0,
) {
    val sigmaDeg: Double? = if (detected) DirectionMath.confidenceToSigmaDeg(confidence) else null

    init { require(bearingDeg.isFinite()) { "bearing must be finite" } }
}

/** Rotate-scan bearing estimator (parity of core/direction.DirectionSweep). */
class DirectionSweep(
    private val sweepWindowS: Double = DirectionMath.SWEEP_WINDOW_S,
    private val binDeg: Int = DirectionMath.SWEEP_BIN_DEG,
) {
    private data class Sample(val ts: Double, val rssi: Double, val heading: Double)

    private val samples = ArrayDeque<Sample>()

    fun addSample(rssiDbm: Double, headingDeg: Double, ts: Double) {
        samples.addLast(Sample(ts, rssiDbm, DirectionMath.wrap360(headingDeg)))
        if (samples.size > 400) samples.removeFirst()
    }

    fun estimate(now: Double): SweepEstimate {
        val cutoff = now - sweepWindowS
        val recent = samples.filter { it.ts >= cutoff }
        if (recent.size < DirectionMath.SWEEP_MIN_SAMPLES) {
            return SweepEstimate(false, 0.0, 0.0, samples = recent.size)
        }
        val nBins = 360 / binDeg
        val binSum = DoubleArray(nBins)
        val binCnt = IntArray(nBins)
        for ((_, r, h) in recent) {
            val idx = (((h % 360.0 + binDeg / 2.0) / binDeg).toInt()) % nBins
            binSum[idx] += r
            binCnt[idx] += 1
        }
        var peak = 0
        for (i in 1 until nBins) {
            // empty bins carry mean 0.0 (mirrors Python `bins_sum` guard)
            val a = if (binCnt[peak] > 0) binSum[peak] / binCnt[peak] else 0.0
            val b = if (binCnt[i] > 0) binSum[i] / binCnt[i] else 0.0
            if (b > a) peak = i
        }
        if (binCnt[peak] < DirectionMath.SWEEP_MIN_BIN_COUNT) {
            return SweepEstimate(
                false, 0.0, 0.0, samples = recent.size,
                occupiedBins = binCnt.count { it > 0 })
        }
        val spread = (0 until nBins).fold(Pair(Double.NEGATIVE_INFINITY, Double.POSITIVE_INFINITY)) {
                    (hi, lo), i ->
                    val m = if (binCnt[i] > 0) binSum[i] / binCnt[i] else 0.0
                    Pair(maxOf(hi, m), minOf(lo, m))
                }.let { (hi, lo) -> hi - lo }
        val confidence = min(1.0, max(0.0, spread / max(10.0, abs(spread))))
        val bearing = (peak * binDeg) % 360.0
        return SweepEstimate(
            true, bearing.toDouble(), confidence,
            samples = recent.size, occupiedBins = binCnt.count { it > 0 })
    }
}

/** Weighted circular fusion + reciprocal (peer-opposite) boost. */
object BearingFusion {
    data class Fused(val meanDeg: Double, val sigmaDeg: Double)

    fun fusepatches(pairs: List<Pair<Double, Double>>): Fused? {
        var s = 0.0
        var c = 0.0
        var wsum = 0.0
        for ((b, w) in pairs) {
            val rad = Math.toRadians(b)
            s += w * sin(rad)
            c += w * cos(rad)
            wsum += w
        }
        if (wsum <= 0.0) return null
        val r = hypot(s, c) / wsum
        if (r <= 1e-9) return Fused(0.0, 90.0)
        val mean = Math.toDegrees(atan2(s / wsum, c / wsum)) % 360.0
        return Fused(mean, fusedSigma(r))
    }

    fun reciprocalBoost(
        selfBearing: Double?,
        peerBearingToMe: Double?,
        weightSelf: Double = 2.0,
        weightPeer: Double = 1.0,
    ): Fused? {
        val pairs = mutableListOf<Pair<Double, Double>>()
        if (selfBearing != null) pairs += selfBearing to weightSelf
        if (peerBearingToMe != null) pairs += DirectionMath.opposite(peerBearingToMe) to weightPeer
        return fusepatches(pairs)
    }

    private fun fusedSigma(r: Double): Double {
        // parity of math.degrees(sqrt(max(0, -2 * ln(min(r,1))))); radians->degrees
        val radians = sqrt(max(0.0, -2.0 * Math.log(min(1.0, r))))
        return max(5.0, min(90.0, Math.toDegrees(radians)))
    }
}

/** Stationarity gate for keeping the sweep honest while the user walks. */
class StationarityGate(
    private val window: Int = 20,
    private val varianceThreshold: Double = 0.10,
) {
    private val samples = ArrayDeque<Double>()

    fun addAccel(magnitudeG: Double) {
        samples.addLast(magnitudeG)
        while (samples.size > window) samples.removeFirst()
    }

    fun isStationary(): Boolean {
        if (samples.size < 4) return false
        val mean = samples.average()
        val variance = samples.sumOf { (it - mean) * (it - mean) } / samples.size
        return variance <= varianceThreshold
    }
}