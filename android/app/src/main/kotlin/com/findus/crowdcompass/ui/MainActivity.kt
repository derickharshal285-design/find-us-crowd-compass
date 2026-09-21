package com.findus.crowdcompass.ui

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.core.content.ContextCompat.startForegroundService
import com.findus.crowdcompass.engine.CapabilityRegistry
import com.findus.crowdcompass.engine.EngineSelfTest
import com.findus.crowdcompass.engine.NavTier
import com.findus.crowdcompass.service.Backend
import com.findus.crowdcompass.service.FindUsService
import com.findus.crowdcompass.service.SosUiState
import com.findus.packet.PacketSelfTest
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.sin

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { FindUsApp() } }
    }
}

private val TABS = listOf("Home", "Map", "Navigate", "Share", "More")

@Composable
fun FindUsApp() {
    val context = LocalContext.current
    val backend = remember { Backend.get(context) }
    val ui by backend.ui.collectAsState()

    // Host the service so the mesh keeps running with the screen open or not.
    LaunchedEffect(Unit) {
        startForegroundService(context, Intent(context, FindUsService::class.java))
    }
    rememberBlePermissions()

    var tab by remember { mutableStateOf(0) }
    Scaffold(
        bottomBar = {
            NavigationBar {
                TABS.forEachIndexed { i, label ->
                    NavigationBarItem(
                        selected = tab == i,
                        onClick = { tab = i },
                        icon = { Text(label.take(1)) },
                        label = { Text(label) },
                    )
                }
            }
        },
    ) { pad ->
        Box(Modifier.padding(pad)) {
            when (tab) {
                0 -> HomeScreen(ui, backend, context)
                1 -> MapScreen(ui)
                2 -> NavigateScreen(ui)
                3 -> ShareScreen(ui, backend, context)
                else -> MoreScreen(ui, backend, context)
            }
        }
    }
}

@Composable
fun rememberBlePermissions() {
    val context = LocalContext.current
    val needed = if (Build.VERSION.SDK_INT >= 31) listOf(
        Manifest.permission.BLUETOOTH_SCAN,
        Manifest.permission.BLUETOOTH_ADVERTISE,
        Manifest.permission.BLUETOOTH_CONNECT,
    ) else listOf(Manifest.permission.ACCESS_FINE_LOCATION)
    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()) { }
    val allGranted = needed.all {
        ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
    }
    if (!allGranted) LaunchedEffect(Unit) { launcher.launch(needed.toTypedArray()) }
}

// ───────────────────────────── Home ─────────────────────────────

@Composable
fun HomeScreen(ui: SosUiState, backend: Backend, context: Context) {
    LazyColumn(
        Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { Headline("FindUs — local mesh") }
        item {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Labeled("Incident", if (ui.joined) ui.incidentId else "not joined")
                    Labeled("Your wire id", ui.wireId.ifEmpty { "—" })
                    Labeled("Hop to emergency", ui.myHop?.toString() ?: "—")
                    Labeled("TTL (hop budget)", ui.ttlHops.toString())
                }
            }
        }
        item {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Labeled("Emergency", ui.sosEvent.ifEmpty { "none in range" })
                    Labeled("Mode", ui.mode)
                    if (ui.summary.isNotEmpty()) Text(ui.summary,
                        style = MaterialTheme.typography.bodyMedium)
                    if (ui.target != null) Labeled("Next hop target", ui.target!!)
                    if (ui.hint.isNotEmpty()) Text(ui.hint,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline)
                    Spacer(Modifier.height(4.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { backend.raiseSos() }, enabled = ui.joined) {
                            Text("Raise SOS")
                        }
                        OutlinedButton(onClick = { backend.endSos() }, enabled = ui.sosActive) {
                            Text("Mark safe")
                        }
                    }
                }
            }
        }
        item {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Labeled("Neighbors (direct radio)", ui.neighbors.size.toString())
                    if (ui.neighbors.isEmpty()) {
                        Text("none yet — move around; sensing is continuous",
                            style = MaterialTheme.typography.bodySmall)
                    } else {
                        ui.neighbors.forEach { n ->
                            val h = ui.neighborHops[n]
                            Text(if (h != null) "$n  ·  hop $h" else n,
                                style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }
        }
        item {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Labeled("Security", "foreign frames rejected: ${ui.rejectedMacs}")
                    Labeled("Gradient adoptions", ui.adoption.toString())
                    Text("Every frame is MAC-checked against the incident key before it can " +
                        "touch the graph.", style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline)
                }
            }
        }
    }
}

// ───────────────────────────── Map ─────────────────────────────

@Composable
fun MapScreen(ui: SosUiState) {
    Column(
        Modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Headline("Relative map")
        Text("Topology view: ring distance is HOP COUNT, not metres. No device here " +
            "claims a physical position — a graph is not a walking direction.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.outline)
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(8.dp)) {
                TopologyCanvas(ui)
                Spacer(Modifier.height(8.dp))
                LegendRow()
            }
        }
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Labeled("Gradient hops known", ui.gradientHops.size.toString())
                ui.gradientHops.entries.sortedBy { it.value }.forEach { (id, hop) ->
                    Text("$id  ·  hop $hop", style = MaterialTheme.typography.bodyMedium)
                }
                if (ui.gradientHops.isEmpty()) {
                    Text("No emergency gradient heard yet.",
                        style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}

@Composable
fun TopologyCanvas(ui: SosUiState) {
    Canvas(Modifier.fillMaxWidth().height(280.dp)) {
        val cx = size.width / 2f
        val cy = size.height / 2f
        val maxR = minOf(cx, cy) * 0.86f
        for (ring in 1..3) {
            drawCircle(Color(0x33888888), radius = maxR * ring / 3f,
                center = Offset(cx, cy), style = Stroke(width = 1.5f))
        }
        drawCircle(Color(0xFF2E7D32), radius = 16f, center = Offset(cx, cy))
        val entries = ui.neighborHops.entries.toList()
        val denom = max(1, ui.ttlHops).toFloat()
        entries.forEachIndexed { i, e ->
            val hop = e.value
            val angle = (2.0 * Math.PI * i / max(1, entries.size)) - Math.PI / 2
            val r = maxR * (hop.coerceIn(1, ui.ttlHops) / denom)
            val dx = (r * cos(angle)).toFloat()
            val dy = (r * sin(angle)).toFloat()
            val color = when {
                e.key == ui.target -> Color(0xFFD32F2F)
                hop <= 1 -> Color(0xFF388E3C)
                else -> Color(0xFFF9A825)
            }
            drawLine(Color(0x55888888), Offset(cx, cy), Offset(cx + dx, cy + dy),
                strokeWidth = 3f)
            drawCircle(color, radius = 11f, center = Offset(cx + dx, cy + dy))
        }
    }
}

@Composable
fun LegendRow() {
    Row(horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalAlignment = Alignment.CenterVertically) {
        LegendDot(Color(0xFF2E7D32), "you")
        LegendDot(Color(0xFFD32F2F), "next hop")
        LegendDot(Color(0xFF388E3C), "hop 1")
        LegendDot(Color(0xFFF9A825), "hop 2+")
    }
}

@Composable
fun LegendDot(color: Color, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.width(10.dp).height(10.dp).padding(0.dp)) {
            Canvas(Modifier.fillMaxSize()) { drawCircle(color, radius = size.minDimension / 2f) }
        }
        Spacer(Modifier.width(6.dp))
        Text(label, style = MaterialTheme.typography.labelSmall)
    }
}

// ─────────────────────────── Navigate ───────────────────────────

@Composable
fun NavigateScreen(ui: SosUiState) {
    Column(
        Modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Headline("Navigate to the emergency")
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(ui.mode, style = MaterialTheme.typography.headlineSmall)
                Text(ui.summary.ifEmpty { "No active emergency signal in range." },
                    style = MaterialTheme.typography.bodyLarge)
                if (ui.myHop != null) {
                    Labeled("Your hop", ui.myHop.toString())
                    Labeled("Next hop target", ui.target ?: "—")
                }
            }
        }
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Labeled("Physical bearing", "NOT CLAIMED")
                Text("Commodity phones do not expose BLE angle-of-arrival. This build walks " +
                    "the hop gradient: move toward the neighbor advertising the lower hop, " +
                    "then re-check which route stays freshest. Rotate-to-find bearing exists " +
                    "in the engine but is RSSI-tier and awaits field validation.",
                    style = MaterialTheme.typography.bodySmall)
                if (ui.hint.isNotEmpty()) {
                    HorizontalDivider()
                    Text(ui.hint, style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline)
                }
            }
        }
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Labeled("Route integrity", if (ui.sosActive) "route adopted" else "no route")
                Labeled("Live gradient entries", ui.gradientHops.size.toString())
                Labeled("Neighbors", ui.neighbors.size.toString())
            }
        }
    }
}

// ───────────────────────────── Share ─────────────────────────────

@Composable
fun ShareScreen(ui: SosUiState, backend: Backend, context: Context) {
    var name by remember { mutableStateOf("") }
    var link by remember { mutableStateOf("") }
    Column(
        Modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Headline("Create or join an incident")
        Text("Every phone that scans the SAME link derives the same team key, so all hands " +
            "authenticate one another with no server.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.outline)

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Labeled("Create", "start a new incident on this phone")
                OutlinedTextField(value = name, onValueChange = { name = it },
                    modifier = Modifier.fillMaxWidth(), label = { Text("Incident name (optional)") })
                Button(onClick = { backend.createIncident(name, context) }) {
                    Text("Create incident")
                }
            }
        }

        if (ui.incidentLink.isNotEmpty()) {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Labeled("Your incident link", ui.incidentId)
                    Text(ui.incidentLink, style = MaterialTheme.typography.bodySmall)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = { copyToClipboard(context, ui.incidentLink) }) {
                            Text("Copy")
                        }
                        Button(onClick = { shareLink(context, ui.incidentLink) }) {
                            Text("Share")
                        }
                    }
                }
            }
        }

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Labeled("Join", "paste a link you received")
                OutlinedTextField(value = link, onValueChange = { link = it },
                    modifier = Modifier.fillMaxWidth(), label = { Text("incident://…") })
                Button(onClick = { backend.join(link, context) }, enabled = link.isNotBlank()) {
                    Text("Join")
                }
                if (ui.mode == "BAD_LINK") {
                    Text("That is not a valid incident link.",
                        color = MaterialTheme.colorScheme.error)
                }
            }
        }
    }
}

// ───────────────────────────── More ─────────────────────────────

@Composable
fun MoreScreen(ui: SosUiState, backend: Backend, context: Context) {
    var engineResult by remember { mutableStateOf("") }
    var packetResult by remember { mutableStateOf("") }
    val local = CapabilityRegistry(
        advertising = true, scanning = true, imu = true, compass = true,
        rotate = true, haveCs = false)
    Column(
        Modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Headline("Diagnostics & settings")

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Labeled("Permissions", permissionSummary(context))
                Labeled("Capability tier", local.bestTier(null)?.let { tierName(it) } ?: "—")
                Text("The tier is the LOWEST mutually measurable navigation signal on a link; " +
                    "BLE4 and BLE5 phones always interoperate.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline)
            }
        }

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Labeled("Engine parity self-test", "Kotlin port vs Python reference")
                Button(onClick = {
                    engineResult = runCatching { EngineSelfTest.run().toString() }
                        .getOrElse { "FAILED: ${it.message}" }
                }) { Text("Run engine self-test") }
                if (engineResult.isNotEmpty()) Text(engineResult,
                    style = MaterialTheme.typography.bodySmall)
            }
        }

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Labeled("Packet layer self-test", "56-bit frame, FEC, envelope MAC, budgets")
                Button(onClick = {
                    packetResult = runCatching { PacketSelfTest.run().toString() }
                        .getOrElse { "FAILED: ${it.message}" }
                }) { Text("Run packet self-test") }
                if (packetResult.isNotEmpty()) Text(packetResult,
                    style = MaterialTheme.typography.bodySmall)
            }
        }

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Labeled("Privacy", "no account, no server, no cloud")
                Text("Identity is per-incident: a pseudonym derived from a random install key " +
                    "and the incident id. Nothing leaves the radio range unless you share a link.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline)
            }
        }

        val status = if (ui.joined) "Incident ${ui.incidentId}" else "Not joined"
        OutlinedButton(onClick = { backend.leave(context) }, enabled = ui.joined) {
            Text("Leave incident ($status)")
        }
        Text("Ticks since engine start: ${ui.tick.toInt()}",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.outline)
    }
}

// ───────────────────────────── helpers ─────────────────────────────

@Composable
fun Headline(text: String) = Text(text, style = MaterialTheme.typography.headlineSmall)

@Composable
fun Labeled(label: String, value: String) {
    Column {
        Text(label.uppercase(), style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.outline)
        Text(value, style = MaterialTheme.typography.bodyLarge)
    }
}

private fun copyToClipboard(context: Context, text: String) {
    val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    cm.setPrimaryClip(ClipData.newPlainText("incident link", text))
    Toast.makeText(context, "Incident link copied", Toast.LENGTH_SHORT).show()
}

private fun shareLink(context: Context, link: String) {
    val send = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(Intent.EXTRA_TEXT, link)
    }
    context.startActivity(Intent.createChooser(send, "Share incident link"))
}

private fun permissionSummary(context: Context): String {
    val list = if (Build.VERSION.SDK_INT >= 31) listOf(
        Manifest.permission.BLUETOOTH_SCAN,
        Manifest.permission.BLUETOOTH_ADVERTISE,
        Manifest.permission.BLUETOOTH_CONNECT,
    ) else listOf(Manifest.permission.ACCESS_FINE_LOCATION)
    val granted = list.count {
        ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
    }
    return "$granted/${list.size} granted"
}

private fun tierName(tier: NavTier): String = when (tier) {
    NavTier.UWB -> "UWB (hardware)"
    NavTier.COMPASS_CS -> "Compass + Channel Sounding"
    NavTier.MOTION_VECTOR -> "Motion vector (IMU)"
    NavTier.HEADING_REL -> "Relative heading (compass)"
    NavTier.RSSI_LOGDIST -> "RSSI log-distance"
    NavTier.RSSI_BAND -> "RSSI near/far band"
    NavTier.HOP_GRADIENT -> "Hop gradient only"
}
