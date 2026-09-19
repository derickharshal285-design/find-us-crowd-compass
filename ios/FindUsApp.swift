//
//  FindUsApp.swift
//  Find Us / Crowd Compass — iOS App
//

import SwiftUI
import CoreBluetooth
import CoreMotion
import CoreLocation
import FindUsPacket

@main
struct FindUsApp: App {
    @StateObject private var bleManager = BLEManager()
    @StateObject private var motionManager = MotionManager()
    @StateObject private var guidanceEngine = GuidanceEngine()
    @StateObject private var locationManager = LocationManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(bleManager)
                .environmentObject(motionManager)
                .environmentObject(guidanceEngine)
                .environmentObject(locationManager)
        }
    }
}

// ─── BLE Manager (Dual-AD Advertising + Scanning) ───
class BLEManager: NSObject, ObservableObject, CBPeripheralManagerDelegate, CBCentralManagerDelegate {
    @Published var isAdvertising = false
    @Published var isScanning = false
    @Published var discoveredGradients: [GradientInfo] = []
    @Published var connectionState = "Disconnected"

    private var peripheralManager: CBPeripheralManager!
    private var centralManager: CBCentralManager!
    private let serviceUUID = CBUUID(string: "FC00")  // 0xFC00
    private let sessionKey: Data

    override init() {
        self.sessionKey = Data("crowd_compass_session_key_2026".utf8)
        super.init()
        peripheralManager = CBPeripheralManager(delegate: self, queue: nil)
        centralManager = CBCentralManager(delegate: self, queue: nil)
    }

    func startAdvertising(sosId: UInt16, role: NodeRole) {
        guard peripheralManager.state == .poweredOn else { return }

        // Build Packet v2 beacon
        var pkt = try! PacketV2(
            pktType: role == .target ? PacketType.liveGradient.rawValue : PacketType.cachedMuleBurst.rawValue,
            sosId: sosId,
            hopCount: role == .target ? 0 : 1,
            baroDiff: 0,
            flags: role == .mule ? Flags.muleStoreForward.rawValue : 0,
            epoch: currentEpoch(),
            age: AgeBucket.live.rawValue,
            reserved: 0,
            envelopeMac: computeMAC(sosId: sosId, epoch: currentEpoch())
        )

        let raw = pkt.pack()
        let fec = HammingFEC.encode(raw)
        let advData = BLEFraming.iosBackgroundSafe(payload: fec)

        let adv = [CBAdvertisementDataServiceUUIDsKey: [serviceUUID],
                   CBAdvertisementDataManufacturerDataKey: advData] as [String: Any]
        peripheralManager.startAdvertising(adv)
        isAdvertising = true
        connectionState = "Advertising as \(role)"
    }

    func stopAdvertising() {
        peripheralManager.stopAdvertising()
        isAdvertising = false
    }

    func startScanning() {
        guard centralManager.state == .poweredOn else { return }
        centralManager.scanForPeripherals(withServices: [serviceUUID], options: [
            CBCentralManagerScanOptionAllowDuplicatesKey: true
        ])
        isScanning = true
        connectionState = "Scanning..."
    }

    func stopScanning() {
        centralManager.stopScan()
        isScanning = false
    }

    // CBPeripheralManagerDelegate
    func peripheralManagerDidUpdateState(_ peripheral: CBPeripheralManager) {
        connectionState = peripheral.state == .poweredOn ? "Ready" : "Bluetooth Off"
    }

    // CBCentralManagerDelegate
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        connectionState = central.state == .poweredOn ? "Scanning Ready" : "Bluetooth Off"
        if central.state == .poweredOn && isScanning {
            startScanning()
        }
    }

    func centralManager(_ central: CBCentralManager,
                       didDiscover peripheral: CBPeripheral,
                       advertisementData: [String: Any],
                       rssi RSSI: NSNumber) {
        guard let mfrData = advertisementData[CBAdvertisementDataManufacturerDataKey] as? Data else { return }
        // Parse Packet v2 from manufacturer data
        if let gradient = parseGradient(from: mfrData, rssi: RSSI.intValue, peripheral: peripheral) {
            DispatchQueue.main.async {
                if let idx = self.discoveredGradients.firstIndex(where: { $0.sosId == gradient.sosId }) {
                    self.discoveredGradients[idx] = gradient
                } else {
                    self.discoveredGradients.append(gradient)
                }
            }
        }
    }

    private func parseGradient(from data: Data, rssi: Int, peripheral: CBPeripheral) -> GradientInfo? {
        // Extract Packet v2 from manufacturer data (skip 4-byte header)
        guard data.count >= 13 + 4 else { return nil }
        let payload = data[4...]
        // Decode FEC then packet
        // ... implementation
        return nil
    }

    private func currentEpoch() -> UInt8 {
        return UInt8((Int(Date().timeIntervalSince1970) / 15) & 0xF)
    }

    private func computeMAC(sosId: UInt16, epoch: UInt8) -> UInt16 {
        let pkt = try! PacketV2(
            pktType: PacketType.liveGradient.rawValue,
            sosId: sosId, hopCount: 0, baroDiff: 0,
            flags: 0, epoch: epoch, age: AgeBucket.live.rawValue,
            reserved: 0, envelopeMac: 0
        )
        return EnvelopeMAC.compute(key: sessionKey, sosId: sosId, epoch: epoch, pktType: pkt.pktType)
    }
}

enum NodeRole { case target, relay, mule }

// ─── Motion Manager (AR-gated PDR) ───
class MotionManager: NSObject, ObservableObject {
    @Published var activity: ActivityClass = .navigatingWalk
    @Published var arConfidence: Float = 0.0
    @Published var gatePass = false

    private let motion = CMMotionManager()
    private let activityRecognizer = ActivityRecognizer()

    override init() {
        super.init()
        motion.accelerometerUpdateInterval = 0.02  // 50 Hz
        motion.gyroUpdateInterval = 0.02
        motion.magnetometerUpdateInterval = 0.02
    }

    func start() {
        motion.startAccelerometerUpdates(to: .main) { [weak self] data, _ in
            guard let data = data else { return }
            let sample = IMUSample(
                timestamp: Date().timeIntervalSince1970,
                accel: (data.acceleration.x, data.acceleration.y, data.acceleration.z),
                gyro: (0, 0, 0),  // Gyro handled separately
                mag: (0, 0, 0)
            )
            self?.activityRecognizer.addSample(sample)
        }
        motion.startGyroUpdates(to: .main) { [weak self] data, _ in
            // Add gyro to last sample
        }
    }

    func stop() {
        motion.stopAccelerometerUpdates()
        motion.stopGyroUpdates()
        motion.stopMagnetometerUpdates()
    }

    private func updateActivity() {
        let (act, conf) = activityRecognizer.classify()
        DispatchQueue.main.async {
            self.activity = act
            self.arConfidence = Float(conf)
            self.gatePass = conf >= 0.85
        }
    }
}

class ActivityRecognizer {
    private var window: [IMUSample] = []
    private let maxWindow = 100  // 2.0 s @ 50 Hz

    func addSample(_ sample: IMUSample) {
        window.append(sample)
        if window.count > maxWindow { window.removeFirst() }
    }

    func classify() -> (ActivityClass, Double) {
        guard window.count >= 20 else { return (.navigatingWalk, 0.5) }
        let accelMags = window.map { sqrt($0.accel.0*$0.accel.0 + $0.accel.1*$0.accel.1 + $0.accel.2*$0.accel.2) }
        let mean = accelMags.reduce(0, +) / Double(accelMags.count)
        let std = sqrt(accelMags.map { ($0 - mean)*($0 - mean) }.reduce(0, +) / Double(accelMags.count - 1))

        if mean > 2.5 && std > 1.5 { return (.moshPitBounce, 0.95) }
        if std > 0.8 { return (.pocketDrunkShuffle, 0.90) }
        if mean < 1.1 && std < 0.1 { return (.stationaryIdle, 0.90) }
        return (.navigatingWalk, 0.88)
    }
}

struct IMUSample {
    let timestamp: TimeInterval
    let accel: (Double, Double, Double)
    let gyro: (Double, Double, Double)
    let mag: (Double, Double, Double)
}

enum ActivityClass: Int, CaseIterable {
    case navigatingWalk = 0, moshPitBounce = 1, pocketDrunkShuffle = 2, torsoSpinSearch = 3, stationaryIdle = 4
}

// ─── Guidance Engine (Swift port) ───
class GuidanceEngine: ObservableObject {
    @Published var currentGuidance: GuidanceOutput = .searching
    @Published var currentFloor = 0
    @Published var targetHop = 255

    private var gradients: [UInt16: GradientEntry] = [:]
    private let rfConfirmation = RFConfirmationEngine()
    private let terminalHandoff = TerminalHandoffEngine()

    func processPacket(_ data: Data, rssi: Int, channel: Int) {
        // Parse packet, verify MAC, update gradient, feed RF engine
    }

    func update() {
        // Main guidance loop
    }
}

// ─── Location Manager (Barometric + GPS fallback) ───
class LocationManager: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published var currentFloor = 0
    @Published var floorConfidence: Float = 0.0
    @Published var entranceGateSet = false

    private let locationManager = CLLocationManager()
    private let altimeter = CMAltimeter()
    private var referencePressure: Double?

    override init() {
        super.init()
        locationManager.delegate = self
        locationManager.requestWhenInUseAuthorization()
    }

    func start() {
        if CMAltimeter.isRelativeAltitudeAvailable() {
            altimeter.startRelativeAltitudeUpdates(to: .main) { [weak self] data, _ in
                guard let data = data, let self = self else { return }
                let pressure = data.pressure.doubleValue * 1000  // kPa → hPa
                self.updateFloor(pressure: pressure)
            }
        }
    }

    func setEntranceGateReference() {
        if let pressure = altimeter.relativeAltitude {
            referencePressure = pressure.doubleValue * 1000
            entranceGateSet = true
        }
    }

    private func updateFloor(pressure: Double) {
        // Protocol 2: Entrance gate baseline
        // Protocol 3: Peer consensus
    }
}

// ─── Supporting Types ───
struct GradientInfo: Identifiable {
    let id = UUID()
    let sosId: UInt16
    let hop: UInt8
    let rssi: Int
    let timestamp: Date
}

struct GradientEntry {
    let sosId: UInt16
    var hop: UInt8
    var baroDiff: Int8
    var flags: UInt8
    var epoch: UInt8
    var age: UInt8
    var reserved: UInt8
    var envelopeMac: UInt16
    var lastRxTime: TimeInterval
}

struct GuidanceOutput {
    let mode: GuidanceMode
    let action: String
    let bearing: String?
    let warning: String?

    static let searching = GuidanceOutput(mode: .macroGradient, action: "SCANNING", bearing: nil, warning: nil)
}

enum GuidanceMode {
    case macroGradient, stairwellPortal, rfConfirmation, terminalHandoff
}

class RFConfirmationEngine {
    func addSample(sosId: UInt16, rssi: Int, hop: UInt8, channel: Int) {}
    func evaluate(sosId: UInt16) -> RFResult? { return nil }
}

struct RFResult {
    let meanRSSI: Double
    let stdRSSI: Double
    let hop: UInt8
    let isMultipath: Bool
    let isWallBleed: Bool
    let isLosGap: Bool
}

class TerminalHandoffEngine {
    func addRSSI(_ rssi: Int) {}
    func detectTorsoShadow() -> (Bool, Double) { return (false, 0) }
    func activateVisualRunway() {}
}