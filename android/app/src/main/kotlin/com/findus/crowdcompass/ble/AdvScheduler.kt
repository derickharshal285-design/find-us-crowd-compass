package com.findus.crowdcompass.ble

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlin.math.max

/**
 * Trickle advertisement scheduler (the "try the connection" rhythm).
 *
 * We do NOT blast frames: a 50k crowd has each device advertise a short frame
 * roughly once per window on a jittered slot, so average receiver load stays
 * O(k) small frames per second — steady-state ~1 ms/s of CPU per device
 * (measured in the Python coefficient at core/crowd.py).
 */
class AdvScheduler(
    private val scope: CoroutineScope,
    private val frameProducer: () -> List<ByteArray>,
    private val onSweep: () -> Unit = {},
    private val windowMs: Long = 1200L,
) {
    private var job: Job? = null

    /** Full mesh sweep (heartbeat + every active SOS update) then rest. */
    fun onTick() {
        val frames = frameProducer()
        onSweep()
        if (frames.isEmpty()) return
        // Rotate one frame into the adv each slot so neighbors hear us over time.
        job?.cancel()
        job = scope.launch(Dispatchers.Default) {
            var i = 0
            while (isActive) {
                val blob = frames[i % frames.size]
                _currentFrame = blob
                delay(jittered(windowMs))
                i++
                if (i % max(1, frames.size) == 0 && frames.size > 1) delay(jittered(windowMs))
            }
        }
    }

    fun currentFrame(): ByteArray? = _currentFrame

    fun stop() {
        job?.cancel()
        _currentFrame = null
    }

    private fun jittered(base: Long): Long = base + ((base / 4) * Math.random()).toLong()

    @Volatile
    private var _currentFrame: ByteArray? = null
}