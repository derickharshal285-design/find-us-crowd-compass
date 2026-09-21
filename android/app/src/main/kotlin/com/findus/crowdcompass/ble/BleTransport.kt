package com.findus.crowdcompass.ble

import android.bluetooth.BluetoothAdapter
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
import android.os.ParcelUuid
import android.util.Log
import java.util.UUID

/**
 * One BLE transport: we ADVERTISE our identity+hops and we SCAN for others,
 * both at the same time (dual role). A frame is a short adv packet; receivers
 * re-verify the canonical MAC before ANY graph write (DeviceApp does that,
 * never this layer). Full frames >20 B flow on a short connect exchange.
 */
object BleTransport {

    const val SERVICE_UUID = "6e897e00-0001-4a2a-8f6f-6669756e6473" // "findus"
    val serviceParcel: ParcelUuid = ParcelUuid.fromString(SERVICE_UUID)

    fun interface Sink {
        /** Called when a raw v3 frame blob arrived from `remote`. */
        fun onFrame(remote: String, blob: ByteArray)
    }

    fun start(context: Context, sink: Sink, frames: () -> List<ByteArray>) {
        val bm = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager ?: return
        val adapter: BluetoothAdapter = bm.adapter ?: return
        _sink = sink
        startScanning(adapter)
        startAdvertising(adapter, frames)
    }

    fun stop() {
        _advertiser?.stopAdvertising(_advCallback)
        _scanner?.stopScan(_scanCallback)
        _advertiser = null; _scanner = null; _sink = null
    }

    // ---- advertising (identity + first frame inside the adv window) ----
    private var _advertiser: BluetoothLeAdvertiser? = null
    private val _advCallback = object : AdvertiseCallback() {
        override fun onStartSuccess(s: AdvertiseSettings) = Unit
        override fun onStartFailure(err: Int) {
            Log.w(TAG, "advertise failed to start (code=$err)")
        }
    }

    private fun startAdvertising(adapter: BluetoothAdapter, frames: () -> List<ByteArray>) {
        _advertiser = adapter.bluetoothLeAdvertiser ?: return
        val blob = frames().firstOrNull() ?: return
        // Keep the adv in the non-connectable band: ≤ 20 B of user payload.
        val advBytes = blob.copyOf(20)
        val settings = AdvertiseSettings.Builder()
            .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_POWER)
            .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_LOW)
            .setConnectable(false)
            .build()
        val data = AdvertiseData.Builder()
            .addServiceUuid(serviceParcel)
            .addServiceData(serviceParcel, advBytes)
            .build()
        _advertiser!!.startAdvertising(settings, data, _advCallback)
    }

    // ---- scanning (hear others) ----
    private var _scanner: BluetoothLeScanner? = null
    private val _scanCallback = object : ScanCallback() {
        override fun onScanResult(code: Int, result: ScanResult) {
            val raw = result.scanRecord?.getServiceData(serviceParcel) ?: return
            _sink?.onFrame(result.device.address, raw)
        }
    }

    private fun startScanning(adapter: BluetoothAdapter) {
        _scanner = adapter.bluetoothLeScanner ?: return
        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()
        val filter = ScanFilter.Builder()
            .setServiceUuid(serviceParcel)
            .build()
        _scanner!!.startScan(listOf(filter), settings, _scanCallback)
    }

    private var _sink: Sink? = null

    const val TAG = "FindUsBLE"
}