package com.findus.crowdcompass.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.findus.crowdcompass.R
import com.findus.crowdcompass.ble.AdvScheduler
import com.findus.crowdcompass.ble.BleTransport
import com.findus.crowdcompass.data.IncidentStore
import com.findus.crowdcompass.engine.DeviceApp
import com.findus.crowdcompass.engine.GuidanceInstruction
import com.findus.crowdcompass.engine.NodeId
import com.findus.crowdcompass.ui.MainActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.Base64

/**
 * The on-device backend. Runs the DeviceApp engine in a foreground service,
 * feeds it from the BLE transport, and publishes a snapshot StateFlow for UI.
 * No cloud: everything happens on the phone itself.
 */
class FindUsService : Service() {

    object State {
        val instance = SosUiState()
    }

    val backend: Backend = Backend()

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createChannel()
        startForeground(NOTIFICATION_ID, buildNotification("starting local mesh…"))
        backend.start(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(NOTIFICATION_ID, buildNotification(summaryText()))
        return START_STICKY
    }

    override fun onDestroy() {
        backend.stop()
        super.onDestroy()
    }

    private fun buildNotification(text: String): Notification {
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE)
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.icon_findus)
            .setContentTitle("FindUs Crowd")
            .setContentText(text)
            .setContentIntent(open)
            .setOngoing(true)
            .build()
    }

    private fun createChannel() {
        val mgr = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        mgr.createNotificationChannel(NotificationChannel(
            CHANNEL_ID, "FindUs mesh", NotificationManager.IMPORTANCE_LOW))
    }

    private fun summaryText(): String {
        val s = State.instance
        return when {
            s.mode == "NO_SOS_KNOWN" -> "listening, no emergency in range"
            s.mode == "NAVIGATING" -> "route to emergency: hop ${s.myHop}"
            s.mode == "AT_TARGET" -> "at/origin of the emergency"
            else -> s.mode
        }
    }

    companion object {
        private const val CHANNEL_ID = "findus-mesh"
        private const val NOTIFICATION_ID = 41
    }
}

/** UI-visible snapshot of the local mesh, published every engine tick. */
data class SosUiState(
    val joined: Boolean = false,
    val incidentId: String = "",
    val wireId: String = "",
    val sosEvent: String = "",
    val mode: String = "NO_SOS_KNOWN",
    val myHop: Int? = null,
    val target: String? = null,
    val neighbors: List<String> = emptyList(),
    val rejectedMacs: Int = 0,
    val adoption: Int = 0,
    val hint: String = "",
)

/** Engine looped by the service; holds no Android UI references. */
class Backend {

    private var scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var device: DeviceApp = DeviceApp(NodeId("local"))
    private var scheduler: AdvScheduler? = null
    private var tick = 0.0

    private val _ui = MutableStateFlow(SosUiState())
    val ui: StateFlow<SosUiState> = _ui.asStateFlow()

    fun start(context: Context) {
        val store = IncidentStore(context)
        scope.launch {
            val joined = store.load()
            var dev = device
            if (joined != null) {
                @Suppress("DEPRECATION")
                val install = Base64.getUrlDecoder().decode(joined.installKeyB64)
                dev = DeviceApp(NodeId("local"), installKey = install)
                dev.joinIncident(joined.session)
            } else {
                dev = DeviceApp(NodeId("local"), installKey = freshInstallKey())
            }
            device = dev
            _ui.value = SosUiState(
                joined = joined != null,
                incidentId = dev.incident?.incidentId.orEmpty(),
                wireId = dev.wireId.value,
            )
            scheduler = AdvScheduler(scope, { device.outgoing() }) { publish() }
            scheduler!!.onTick()
            startTransport(context)
            loop()
        }
    }

    fun join(link: String, context: Context) {
        scope.launch {
            val session = try {
                IncidentSession.parseLink(link)
            } catch (e: Exception) {
                _ui.value = _ui.value.copy(mode = "BAD_LINK")
                return@launch
            }
            device.joinIncident(session)
            IncidentStore(context).saveLink(link, b64(device.installKey))
            _ui.value = _ui.value.copy(joined = true, incidentId = session.incidentId,
                wireId = device.wireId.value)
            scheduler?.onTick()
        }
    }

    fun leave(context: Context) {
        scope.launch {
            IncidentStore(context).clear()
            device = DeviceApp(NodeId("local"), installKey = freshInstallKey())
            _ui.value = _ui.value.copy(joined = false, incidentId = "",
                wireId = device.wireId.value, mode = "NO_SOS_KNOWN")
            scheduler?.onTick()
        }
    }

    fun raiseSos() {
        device.startSos("EVENT-" + System.currentTimeMillis().toString().takeLast(8))
        scheduler?.onTick()
    }

    private fun startTransport(context: Context) {
        BleTransport.start(context, { _, blob -> device.onPacket(NodeId("remote"), blob) }) {
            scheduler?.currentFrame()?.let { listOf(it) } ?: emptyList()
        }
    }

    private fun loop() {
        scope.launch {
            while (true) {
                tick += 1.0
                device.beginTick(tick)
                scheduler?.onTick()
                publish()
                kotlinx.coroutines.delay(1000)
            }
        }
    }

    private fun publish() {
        val sos = device.sosEngine.activeSosIds(device.t).firstOrNull()
        val g: GuidanceInstruction? = sos?.let { device.guidance(it) }
        _ui.value = SosUiState(
            joined = device.incident != null,
            incidentId = device.incident?.incidentId.orEmpty(),
            wireId = device.wireId.value,
            sosEvent = sos?.value.orEmpty(),
            mode = g?.mode ?: "NO_SOS_KNOWN",
            myHop = g?.myHop,
            target = g?.target?.value,
            neighbors = device.graph.neighbors(device.wireId).map { it.value },
            rejectedMacs = device.rejectedMacs,
            adoption = device.sosEngine.adoptions,
            hint = g?.hint.orEmpty(),
        )
    }

    fun stop() {
        BleTransport.stop()
        scheduler?.stop()
        scope.cancel()
    }

    private fun freshInstallKey(): ByteArray {
        val rng = java.security.SecureRandom()
        val key = ByteArray(32); rng.nextBytes(key)
        return key
    }

    private fun b64(b: ByteArray): String =
        Base64.getUrlEncoder().withoutPadding().encodeToString(b)
}