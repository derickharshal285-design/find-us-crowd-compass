package com.findus.crowdcompass.guidance

import com.findus.packet.BLEFraming
import com.findus.packet.EnvelopeMAC
import com.findus.packet.HammingFEC
import com.findus.packet.PacketV2
import com.findus.packet.PacketType
import com.findus.packet.AgeBucket
import com.findus.packet.Flags
import com.findus.packet.ReservedBits
import com.findus.packet.CanonicalVectors
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicReference

/**
 * Responder Guidance Engine — Kotlin port of the Python reference
 * AR-gated PDR + Multi-Level Barometric Floor Gating + Multi-Second RF Confirmation + Terminal Handoff
 */
class GuidanceEngine(
    private val sessionKey: ByteArray
) {

    // ─── Constants from verified research ───
    private val ACTIVITY_WINDOW_S = 2.0
    private val AR_GATE_THRESHOLD = 0.85
    private val RF_CONFIRM_WINDOW_S = 2.0
    private val RF_MIN_PACKETS = 4
    private val BARO_FLOOR_THRESHOLD_HPA = 0.35
    private val BARO_SAME_FLOOR_HPA = 0.25
    private val TERMINAL_HOP_THRESHOLD = 1
    private val BEARING_COHERENCE_THRESHOLD = 0.6
    private val RSSI_VARIANCE_THRESHOLD = 4.8
    private val WALL_BLEED_RSSI_MIN = -99
    private val WALL_BLEED_RSSI_MAX = -89.5
    private val RPA_ROTATION_S = 15.0

    // ─── State ───
    enum class GuidanceMode {
        MACRO_GRADIENT,      // Hop descent (macro: 500m → 15m)
        STAIRWELL_PORTAL,    // Vertical transition
        RF_CONFIRMATION,     // Multi-second RF fusion (15m → 5m)
        TERMINAL_HANDOFF     // Torso shadowing + visual (final 15m → 0m)
    }

    enum class ActivityClass {
        NAVIGATING_WALK,
        MOSH_PIT_BOUNCE,
        POCKET_DRUNK_SHUFFLE,
        TORSO_SPIN_SEARCH,
        STATIONARY_IDLE
    }

    // ─── Internal State ───
    private val activityRecognizer = ActivityRecognizer()
    private val floorEstimator = BarometricFloorEstimator()
    private val rfConfirmation = RFConfirmationEngine()
    private val terminalHandoff = TerminalHandoffEngine()

    private val gradients = ConcurrentHashMap<Int, GradientEntry>()
    private val _state = MutableStateFlow(GuidanceState())
    val stateFlow = _state.asStateFlow()

    data class GuidanceState(
        val mode: GuidanceMode = GuidanceMode.MACRO_GRADIENT,
        val targetSosId: Int = 0,
        val currentHop: Int = 255,
        val currentFloor: Int = 0,
        val targetFloor: Int = 0,
        val activity: ActivityClass = ActivityClass.NAVIGATING_WALK,
        val arGatePass: Boolean = false,
        val action: String = "SEARCHING",
        val bearing: String = "SCAN",
        val warning: String? = null,
        val visualRunwayActive: Boolean = false
    )

    data class GradientEntry(
        val sosId: Int,
        var hop: Int,
        var baroDiff: Int,
        var flags: Int,
        var epoch: Int,
        var age: Int,
        var reserved: Int,
        var envelopeMac: Int,
        var lastRxTime: Long = System.currentTimeMillis()
    )

    // ─── Public API ───
    fun processPacket(rawPacket: ByteArray, rssi: Int, channel: Int) {
        if (rawPacket.size < 7) return
        val pkt = try { PacketV2.unpack(rawPacket.copyOf(7)) } catch (e: Exception) { return }

        // Verify MAC if hop would decrease
        if (!EnvelopeMAC.verify(sessionKey, pkt.sosId, pkt.epoch, pkt.pktType, pkt.envelopeMac)) return

        val existing = gradients[pkt.sosId]
        val shouldUpdate = existing == null || pkt.hopCount < existing.hop
        if (shouldUpdate) {
            gradients[pkt.sosId] = GradientEntry(
                sosId = pkt.sosId,
                hop = pkt.hopCount,
                baroDiff = pkt.baroDiff,
                flags = pkt.flags,
                epoch = pkt.epoch,
                age = pkt.age,
                reserved = pkt.reserved,
                envelopeMac = pkt.envelopeMac,
                lastRxTime = System.currentTimeMillis()
            )
        } else if (existing != null) {
            // Update mutable fields
            existing.baroDiff = pkt.baroDiff
            existing.flags = pkt.flags
            existing.epoch = pkt.epoch
            existing.age = pkt.age
        }

        // Feed RF confirmation engine
        rfConfirmation.addSample(RSSISample(
            timestamp = System.currentTimeMillis(),
            rssi = rssi,
            channel = channel,
            hop = pkt.hopCount,
            sosId = pkt.sosId
        ))
    }

    fun addIMUSample(sample: IMUSample) {
        activityRecognizer.addSample(sample)
    }

    fun setEntranceGateReference(pressureHpa: Double) {
        floorEstimator.setEntranceGateReference(pressureHpa)
    }

    fun addPeerPressure(peerId: Int, pressureHpa: Double) {
        floorEstimator.addPeerPressure(peerId, pressureHpa)
    }

    fun update() {
        // AR gating
        val (activity, arConfidence) = activityRecognizer.classify()
        val arGatePass = arConfidence >= AR_GATE_THRESHOLD

        // Floor estimation (current pressure would come from sensor)
        val currentPressure = 1013.25 // Placeholder
        val (floor, _) = floorEstimator.estimateFloor(currentPressure)

        // Select best gradient
        val best = gradients.values.minOrNull { it.hop } ?: return

        val currentHop = best.hop
        var mode = GuidanceState.GuidanceMode.MACRO_GRADIENT

        // Mode transitions
        if (currentHop > 3) {
            mode = GuidanceState.GuidanceMode.MACRO_GRADIENT
        } else if (abs(best.baroDiff * 0.5) > BARO_FLOOR_THRESHOLD_HPA) {
            mode = GuidanceState.GuidanceMode.STAIRWELL_PORTAL
        } else if (currentHop <= 2) {
            mode = GuidanceState.GuidanceMode.RF_CONFIRMATION
        } else if (currentHop <= 1) {
            mode = GuidanceState.GuidanceMode.TERMINAL_HANDOFF
        }

        // Generate guidance output
        var action = "DESCEND_HOP"
        var bearing = "FOLLOW_GRADIENT"
        var warning: String? = null
        var visualRunway = false

        when (mode) {
            GuidanceState.GuidanceMode.MACRO_GRADIENT -> {
                action = "DESCEND_HOP"
                bearing = "FOLLOW_GRADIENT"
            }
            GuidanceState.GuidanceMode.STAIRWELL_PORTAL -> {
                action = "NAVIGATE_STAIRWELL"
                bearing = "STAIRWELL_CORRIDOR"
            }
            GuidanceState.GuidanceMode.RF_CONFIRMATION -> {
                rfConfirmation.evaluate(best.sosId)?.let { rf ->
                    if (rf.isMultipath) {
                        action = "REJECT_MULTIPATH"
                        warning = "Multipath bounce detected — do not follow"
                    } else if (rf.isWallBleed) {
                        action = "WALL_ALERT"
                        bearing = "PERIMETER"
                    } else if (rf.isLosGap) {
                        action = "SHORTCUT_CONFIRMED"
                        bearing = "THROUGH_GAP"
                    } else {
                        action = "CONTINUE_GRADIENT"
                    }
                }
            }
            GuidanceState.GuidanceMode.TERMINAL_HANDOFF -> {
                val (shadow, bearingDeg) = terminalHandoff.detectTorsoShadow()
                if (shadow) {
                    action = "TORSO_SHADOW_DETECTED"
                    bearing = "TORSO_SHADOW $bearingDeg°"
                    terminalHandoff.activateVisualRunway()
                } else if (_state.value.visualRunwayActive) {
                    action = "VISUAL_RUNWAY_ACTIVE"
                } else {
                    action = "TERMINAL_SEARCH"
                }
            }
        }

        _state.value = GuidanceState(
            mode = mode,
            targetSosId = best.sosId,
            currentHop = currentHop,
            currentFloor = floor,
            targetFloor = 0,
            activity = activity,
            arGatePass = arGatePass,
            action = action,
            bearing = bearing,
            warning = warning,
            visualRunwayActive = _state.value.visualRunwayActive
        )
    }

    // ─── Sub-components ───
    private class ActivityRecognizer {
        private val window = mutableListOf<IMUSample>()
        private val maxWindow = 100

        fun addSample(sample: IMUSample) {
            window.add(sample)
            if (window.size > maxWindow) window.removeFirst()
        }

        fun classify(): Pair<ActivityClass, Double> {
            if (window.size < 20) return ActivityClass.NAVIGATING_WALK to 0.5

            val accelMags = window.map { Math.sqrt(it.accelX * it.accelX + it.accelY * it.accelY + it.accelZ * it.accelZ) }
            val mean = accelMags.average()
            val variance = accelMags.map { (it - mean) * (it - mean) }.average()
            val std = Math.sqrt(variance)

            return when {
                mean > 2.5 && std > 1.5 -> ActivityClass.MOSH_PIT_BOUNCE to 0.95
                std > 0.8 -> ActivityClass.POCKET_DRUNK_SHUFFLE to 0.90
                mean < 1.1 && std < 0.1 -> ActivityClass.STATIONARY_IDLE to 0.90
                else -> ActivityClass.NAVIGATING_WALK to 0.88
            }
        }
    }

    private class BarometricFloorEstimator {
        private var referencePressure: Double? = null
        private var referenceTimestamp = 0L
        private val peerPressures = mutableMapOf<Int, MutableList<Double>>()

        fun setEntranceGateReference(pressureHpa: Double) {
            referencePressure = pressureHpa
            referenceTimestamp = System.currentTimeMillis()
        }

        fun addPeerPressure(peerId: Int, pressureHpa: Double) {
            peerPressures.getOrPut(peerId) { mutableListOf() }.add(pressureHpa)
        }

        fun estimateFloor(currentPressureHpa: Double): Pair<Int, Double> {
            referencePressure?.let { ref ->
                val delta = ref - currentPressureHpa
                val floor = (delta / 0.413).roundToInt()
                return floor to 0.95 // Protocol 2: 75.6% exact, 100% ±1
            }
            return 0 to 0.0
        }
    }

    private class RFConfirmationEngine {
        private val samples = mutableMapOf<Int, MutableList<RSSISample>>()

        fun addSample(sample: RSSISample) {
            samples.getOrPut(sample.sosId) { mutableListOf() }.add(sample)
        }

        fun evaluate(sosId: Int): RFResult? {
            val list = samples[sosId] ?: return null
            val now = System.currentTimeMillis()
            val recent = list.filter { now - it.timestamp <= (RF_CONFIRM_WINDOW_S * 1000).toLong() }
            if (recent.size < RF_MIN_PACKETS) return null

            val rssis = recent.map { it.rssi.toDouble() }
            val meanRssi = rssis.average()
            val stdRssi = if (rssis.size > 1) Math.sqrt(rssis.map { (it - meanRssi) * (it - meanRssi) }.average()) else 0.0
            val hop = recent.groupBy { it.hop }.maxByOrNull { it.value.size }?.key ?: 0

            val isMultipath = stdRssi > RSSI_VARIANCE_THRESHOLD
            val isWallBleed = meanRssi in WALL_BLEED_RSSI_MIN..WALL_BLEED_RSSI_MAX && stdRssi <= RSSI_VARIANCE_THRESHOLD
            val isLosGap = meanRssi > WALL_BLEED_RSSI_MAX && stdRssi <= RSSI_VARIANCE_THRESHOLD

            return RFResult(meanRssi, stdRssi, hop, isMultipath, isWallBleed, isLosGap)
        }

        fun clear(sosId: Int) { samples.remove(sosId) }
    }

    private class TerminalHandoffEngine {
        private val rssiHistory = mutableListOf<Pair<Long, Int>>()

        fun addRSSI(rssi: Int, timestamp: Long = System.currentTimeMillis()) {
            rssiHistory.add(timestamp to rssi)
            if (rssiHistory.size > 30) rssiHistory.removeFirst()
        }

        fun detectTorsoShadow(): Pair<Boolean, Double> {
            if (rssiHistory.size < 10) return false to 0.0
            val recent = rssiHistory.takeLast(10)
            val rssis = recent.map { it.second.toDouble() }
            val mean = rssis.average()
            val std = if (rssis.size > 1) Math.sqrt(rssis.map { (it - mean) * (it - mean) }.average()) else 0.0

            if (std > 8.0 && mean < -85) {
                return true to 0.0 // Placeholder bearing
            }
            return false to 0.0
        }

        fun activateVisualRunway() {
            // Trigger phone torch/strobe via platform API
        }
    }

    // ─── Data Classes ───
    data class IMUSample(
        val timestamp: Long,
        val accelX: Double,
        val accelY: Double,
        val accelZ: Double,
        val gyroX: Double,
        val gyroY: Double,
        val gyroZ: Double
    )

    data class RSSISample(
        val timestamp: Long,
        val rssi: Int,
        val channel: Int,
        val hop: Int,
        val sosId: Int
    )

    data class RFResult(
        val meanRssi: Double,
        val stdRssi: Double,
        val hop: Int,
        val isMultipath: Boolean,
        val isWallBleed: Boolean,
        val isLosGap: Boolean
    )
}