import Foundation
import CoreBluetooth
import FindUsEngine

/// Scans for other FindUs devices and forwards their adv-payload frames.
/// Receivers re-verify the canonical MAC in DeviceApp before any graph write.
public final class BeaconScanner: NSObject {
    public typealias FrameHandler = (String, Data) -> Void

    private var central: CBCentralManager?
    private let centralQueue = DispatchQueue(label: "com.findus.scan")
    private var onFrame: FrameHandler?

    public override init() {
        super.init()
    }

    public func start(onFrame: @escaping FrameHandler) {
        self.onFrame = onFrame
        let options: [String: Any] = [CBCentralManagerOptionScanOption: NSNumber(value: false)]
        central = CBCentralManager(delegate: self, queue: centralQueue,
                                   options: options)
    }

    public func stop() {
        central?.stopScan()
        central = nil
    }
}

extension BeaconScanner: CBCentralManagerDelegate {
    public func centralManagerDidUpdateState(_ central: CBCentralManager) {
        guard central.state == .poweredOn else { return }
        central.scanForPeripherals(withServices: [BeaconAdvertiser.serviceUUID],
                                   options: [CBCentralManagerScanOptionAllowDuplicatesKey: true])
    }

    public func centralManager(_ central: CBCentralManager,
                               didDiscover peripheral: CBPeripheral,
                               advertisementData: [String: Any], rssi RSSI: NSNumber) {
        guard let raw = (advertisementData[CBAdvertisementDataServiceDataKey] as? [CBUUID: Data])
            ?[BeaconAdvertiser.serviceUUID] else { return }
        onFrame?(peripheral.identifier.uuidString, raw)
    }
}