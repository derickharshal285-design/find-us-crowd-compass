package com.findus.crowdcompass.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.core.content.ContextCompat.startForegroundService
import com.findus.crowdcompass.engine.EngineSelfTest
import com.findus.crowdcompass.service.Backend
import com.findus.crowdcompass.service.FindUsService
import com.findus.crowdcompass.service.SosUiState

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { FindUsApp() }
    }
}

@Composable
fun FindUsApp() {
    val context = LocalContext.current
    val backend = remember { Backend() }
    val ui by backend.ui.collectAsState()

    // host the service so the mesh keeps running with the screen open or not
    LaunchedEffect(Unit) {
        val intent = Intent(context, FindUsService::class.java)
        startForegroundService(context, intent)
        backend.start(context)
    }

    var tab by remember { mutableStateOf(0) }
    rememberBlePermission()

    Scaffold(
        bottomBar = {
            NavigationBar {
                NavigationBarItem(selected = tab == 0, onClick = { tab = 0 },
                    icon = { Text("Mesh") }, label = { Text("Mesh") })
                NavigationBarItem(selected = tab == 1, onClick = { tab = 1 },
                    icon = { Text("Join") }, label = { Text("Join") })
                NavigationBarItem(selected = tab == 2, onClick = { tab = 2 },
                    icon = { Text("Settings") }, label = { Text("Settings") })
            }
        }
    ) { pad ->
        Box(Modifier.padding(pad)) {
            when (tab) {
                0 -> IncidentScreen(ui, backend, context)
                1 -> JoinScreen(ui, backend, context)
                else -> SettingsScreen(backend)
            }
        }
    }
}

@Composable
fun rememberBlePermission() {
    val context = LocalContext.current
    val permission = when {
        Build.VERSION.SDK_INT >= 31 -> Manifest.permission.BLUETOOTH_SCAN
        else -> Manifest.permission.ACCESS_FINE_LOCATION
    }
    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()) { }
    val granted = ContextCompat.checkSelfPermission(context, permission) ==
        PackageManager.PERMISSION_GRANTED
    if (!granted) {
        LaunchedEffect(Unit) { launcher.launch(permission) }
    }
}

@Composable
fun IncidentScreen(ui: SosUiState, backend: Backend, context: android.content.Context) {
    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        item { Headline("Local mesh") }
        item { Labeled("Incident", if (ui.joined) ui.incidentId else "not joined") }
        item { Labeled("Wire id", ui.wireId) }
        item { Labeled("Event", ui.sosEvent.ifEmpty { "—" }) }
        item { Labeled("Mode", ui.mode) }
        item { Labeled("Hop", ui.myHop?.toString().orEmpty().ifEmpty { "—" }) }
        item { Labeled("Target", ui.target.ifEmpty { "—" }) }
        item { Labeled("Neighbors", ui.neighbors.joinToString(", ").ifEmpty { "none" }) }
        item { Labeled("MAC rejections", ui.rejectedMacs.toString()) }
        item { Labeled("SOS adoptions", ui.adoption.toString()) }
        item { Text(ui.hint, style = MaterialTheme.typography.bodySmall) }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { backend.raiseSos() }) { Text("Raise SOS") }
                OutlinedButton(onClick = { backend.leave(context) }) { Text("Leave") }
            }
        }
    }
}

@Composable
fun JoinScreen(ui: SosUiState, backend: Backend, context: android.content.Context) {
    var link by remember { mutableStateOf("") }
    Column(Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Headline("Join an incident")
        Text("Paste the incident link you received (incident://…). Every phone in "
            + "the crowd uses the SAME link, so all hands share the team key.")
        OutlinedTextField(value = link, onValueChange = { link = it },
            modifier = Modifier.fillMaxWidth(), label = { Text("Incident link") })
        Button(onClick = { backend.join(link, context) }, enabled = link.isNotBlank()) {
            Text("Join")
        }
        if (ui.mode == "BAD_LINK") Text("That is not a valid incident link.",
            color = MaterialTheme.colorScheme.error)
    }
}

@Composable
fun SettingsScreen(backend: Backend) {
    var result by remember { mutableStateOf("tap to run parity self-test") }
    Column(Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Headline("Settings & self-test")
        Text("The engine is a Kotlin port of the verified Python reference. " +
            "This self-test re-certifies the same assertions on this device.")
        Button(onClick = {
            result = runCatching { EngineSelfTest.run().toString() }
                .getOrElse { "FAILED: ${it.message}" }
        }) { Text("Run parity self-test") }
        Text(result, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
fun Headline(text: String) = Text(text, style = MaterialTheme.typography.titleLarge)

@Composable
fun Labeled(label: String, value: String) {
    Column {
        Text(label.uppercase(), style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.outline)
        Text(value, style = MaterialTheme.typography.bodyLarge)
    }
}