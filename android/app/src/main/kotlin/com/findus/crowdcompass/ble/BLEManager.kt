package com.findus.crowdcompass.ble

import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.le.AdvertiseCallback
import android.bluetooth.le.AdvertiseData
import android.bluetooth.le.AdvertiseSettings
import android.bluetooth.le.BluetoothLeAdvertiser
import android.bluetooth.le.BluetoothLeScanner
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.ParcelUuid
import android.util.Log
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleObserver
import androidx.lifecycle.OnLifecycleEvent
import com.findus.packet.BLEFraming
import com.findus.packet.EnvelopeMAC
import com.findus.packet.HammingFEC
import com.findus.packet.PacketV2
import com.findus.packet.PacketType
import com.findus.packet.AgeBucket
import com.findus.packet.Flags
import com.findus.packet.ReservedBits
import com.findus.packet.CanonicalVectors
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Find Us BLE Manager — Dual-AD Advertising & Service-UUID Filtered Scanning
 * Implements iOS Background-Safe Mode C (23-byte ceiling) and Android PendingIntent wake
 */
class BLEManager(
    private val context: Context,
    private val sessionKey: ByteArray
) : LifecycleObserver {

    private val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
    private val bluetoothAdapter = bluetoothManager.adapter
    private val advertiser = bluetoothAdapter.bluetoothLeAdvertiser
    private val scanner = bluetoothAdapter.bluetoothLeScanner

    private val serviceUuid = ParcelUuid.fromString("0000FC00-0000-1000-8000-00805F9B34FB") // 0xFC00
    private val companyId = 0xFFFF

    private var advertiseCallback: AdvertiseCallback? = null
    private var scanCallback: ScanCallback? = null
    private val isAdvertising = AtomicBoolean(false)
    private val isScanning = AtomicBoolean(false)

    // Callbacks
    var onGradientDiscovered: ((GradientInfo) -> Unit)? = null
    var onStateChange: ((String) -> Unit)? = null

    @OnLifecycleEvent(Lifecycle.Event.ON_START)
    fun start() {
        if (bluetoothAdapter == null || !bluetoothAdapter.isEnabled) {
            onStateChange?.invoke("Bluetooth unavailable")
            return
        }
    }

    @OnLifecycleEvent(Lifecycle.Event.ON_STOP)
    fun stop() {
        stopAdvertising()
        stopScanning()
    }

    // ─── Advertising (Dual-AD Structure) ───
    fun startAdvertising(sosId: Int, role: NodeRole) {
        if (isAdvertising.getAndSet(true)) return

        val epoch = currentEpoch()
        val pkt = buildPacket(sosId, role, epoch)
        val raw = pkt.pack()
        val fec = HammingFEC.encode(raw)
        val advPayload = BLEFraming.iosBackgroundSafe(fec, 0xFC00, companyId)

        val advertiseData = AdvertiseData.Builder().apply {
            // AD1: 16-bit Service UUID (0xFC00) — iOS background filter anchor
            addServiceUuid(serviceUuid)

            // AD2: Manufacturer Data (0xFF) with FEC-coded Packet v2
            val builder = AdvertiseData.Builder()
            builder.addManufacturerData(companyId, advPayload.toByteArray())
            // Note: Can't easily mix service UUID + mfr data in single AdvertiseData.Builder
            // Use setManufacturerData directly on AdvertiseData
        }.build()

        // Manual dual-AD construction for precise control
        val dualAdvData = buildDualAdvData(advPayload)

        val settings = AdvertiseSettings.Builder().apply {
            setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_LATENCY)
            setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_HIGH)
            setConnectable(false)
        }.build()

        advertiseCallback = object : AdvertiseCallback() {
            override fun onStartSuccess(settingsInEffect: AdvertiseSettings?) {
                onStateChange?.invoke("Advertising as ${role.name}")
                Log.d("BLEManager", "Advertising started: SOS=$sosId role=$role epoch=$epoch")
            }
            override fun onStartFailure(errorCode: Int) {
                isAdvertising.set(false)
                onStateChange?.invoke("Advertising failed: $errorCode")
                Log.e("BLEManager", "Advertising failed: $errorCode")
            }
        }

        try {
            // Use reflection or raw byte array for dual-AD on Android
            advertiser.startAdvertising(settings, dualAdvData, advertiseCallback!!)
        } catch (e: Exception) {
            Log.e("BLEManager", "startAdvertising failed", e)
            isAdvertising.set(false)
        }
    }

    private fun buildDualAdvData(payload: ByteArray): AdvertiseData {
        // Manual AD structure construction for dual-AD
        // AD1: [Len=3, Type=0x03, UUID_lo, UUID_hi]
        // AD2: [Len=4+payload, Type=0xFF, CoID_lo, CoID_hi, payload...]
        val ad1 = byteArrayOf(0x03, 0x03, 0x00.toByte(), 0xFC.toByte()) // 0xFC00 little-endian
        val ad2 = ByteBuffer.allocate(4 + payload.size).order(ByteOrder.LITTLE_ENDIAN).apply {
            put((3 + payload.size).toByte())      // Len
            put(0xFF.toByte())                    // Type = Manufacturer Data
            putShort(companyId.toShort())         // Company ID (0xFFFF little-endian)
            put(payload)                          // Payload
        }.array()

        val combined = ByteBuffer.allocate(ad1.size + ad2.size).apply {
            put(ad1)
            put(ad2)
        }.array()

        return AdvertiseData.Builder().apply {
            setManufacturerData(companyId, combined) // Single AD with combined structures
        }.build()
    }

    fun stopAdvertising() {
        if (!isAdvertising.getAndSet(false)) return
        advertiser.stopAdvertising(advertiseCallback!!)
        advertiseCallback = null
        onStateChange?.invoke("Advertising stopped")
    }

    // ─── Scanning (Service UUID Filter for Background) ───
    fun startScanning() {
        if (isScanning.getAndSet(true)) return

        val filter = ScanFilter.Builder().apply {
            setServiceUuid(serviceUuid)  // REQUIRED for background scanning on iOS, recommended on Android
        }.build()

        val settings = ScanSettings.Builder().apply {
            setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                setReportDelay(0) // Immediate reporting
            }
        }.build()

        scanCallback = object : ScanCallback() {
            override fun onScanResult(callbackType: Int, result: ScanResult) {
                val device = result.device
                val rssi = result.rssi
                val scanRecord = result.scanRecord

                // Parse manufacturer data (0xFF) from scan record
                scanRecord?.manufacturerSpecificData?.let { mfrData ->
                    for ((companyId, data) in mfrData) {
                        if (companyId == this@BLEManager.companyId) {
                            val gradient = parseGradient(data, rssi, device)
                            if (gradient != null) {
                                onGradientDiscovered?.invoke(gradient)
                            }
                        }
                    }
                }
            }

            override fun onBatchScanResults(results: List<ScanResult>) {
                results.forEach { onScanResult(ScanCallback.CALLBACK_TYPE_ALL_MATCHES, it) }
            }

            override fun onScanFailed(errorCode: Int) {
                onStateChange?.invoke("Scan failed: $errorCode")
            }
        }

        val filters = listOf(filter)
        scanner.startScan(filters, settings, scanCallback!!)
        onStateChange?.invoke("Scanning for gradients...")
    }

    fun stopScanning() {
        if (!isScanning.getAndSet(false)) return
        scanner.stopScan(scanCallback!!)
        scanCallback = null
        onStateChange?.invoke("Scanning stopped")
    }

    private fun parseGradient(data: ByteArray, rssi: Int, device: BluetoothDevice): GradientInfo? {
        // Expect: [4-byte header][13-byte FEC payload]
        if (data.size < 17) return null
        val fecPayload = data.copyOfRange(4, data.size)
        if (fecPayload.size != 13) return null

        val decoded = HammingFEC.decode(fecPayload)
        if (decoded.second > 0) {
            Log.d("BLEManager", "FEC corrected ${decoded.second} bit errors")
        }

        val rawPacket = decoded.first
        if (rawPacket.size != 7) return null

        val pkt = PacketV2.unpack(rawPacket)
        val macValid = EnvelopeMAC.verify(sessionKey, pkt.sosId, pkt.epoch, pkt.pktType, pkt.envelopeMac)
        if (!macValid) {
            Log.w("BLEManager", "MAC verification failed for SOS=${pkt.sosId}")
            return null
        }

        return GradientInfo(
            sosId = pkt.sosId,
            hop = pkt.hopCount.toByte(),
            rssi = rssi,
            device = device,
            timestamp = System.currentTimeMillis()
        )
    }

    // ─── Packet Building ───
    private fun buildPacket(sosId: Int, role: NodeRole, epoch: Int): PacketV2 {
        val mac = EnvelopeMAC.compute(sessionKey, sosId, epoch, PacketType.LIVE_GRADIENT.value)
        return PacketV2(
            pktType = when (role) {
                NodeRole.TARGET -> PacketType.LIVE_GRADIENT.value
                NodeRole.MULE -> PacketType.CACHED_MULE_BURST.value
                else -> PacketType.LIVE_GRADIENT.value
            },
            sosId = sosId,
            hopCount = when (role) {
                NodeRole.TARGET -> 0
                else -> 1
            },
            baroDiff = 0,
            flags = when (role) {
                NodeRole.MULE -> Flags.MULE_STORE_FORWARD
                else -> 0
            },
            epoch = epoch,
            age = AgeBucket.LIVE.value,
            reserved = 0,
            envelopeMac = mac
        )
    }

    private fun currentEpoch(): Int {
        return (System.currentTimeMillis() / 15000) and 0xF // 15 s epochs
    }

    // ─── Background Wake via PendingIntent (Android Doze) ───
    fun registerBackgroundScanPendingIntent(pendingIntent: PendingIntent) {
        val filter = ScanFilter.Builder().setServiceUuid(serviceUuid).build()
        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_POWER)
            .setReportDelay(60000) // Batch reports for Doze
            .build()

        scanner.startScan(listOf(filter), settings, pendingIntent)
    }

    // ─── Data Classes ───
    enum class NodeRole { TARGET, RELAY, MULE }

    data class GradientInfo(
        val sosId: Int,
        val hop: Byte,
        val rssi: Int,
        val device: BluetoothDevice,
        val timestamp: Long = System.currentTimeMillis()
    )
}