import Foundation
import CoreBluetooth
import FindUsEngine

/// Advertises our pseudonymous presence + a frame inside the adv payload.
/// Dual role means we also scan — CB keeps both running on separate queues.
public final class BeaconAdvertiser: NSObject {
    public static let serviceUUID = CBUUID(string: "6E897E00-0001-4A2A-8F6F-6669756E6473")

    private var peripheral: CBPeripheralManager?
    private let managerQueue = DispatchQueue(label: "com.findus.adv")
    private var frameProvider: (() -> Data)?

    public override init() {
        super.init()
    }

    public func start(frameProvider: @escaping () -> Data?) {
        self.frameProvider = frameProvider
        peripheral = CBPeripheralManager(delegate: self, queue: managerQueue)
    }

    public func stop() {
        peripheral?.stopAdvertising()
        peripheral = nil
    }

    private func refresh() {
        guard let m = peripheral, m.state == .poweredOn else { return }
        guard let blob = frameProvider?(), !blob.isEmpty else { return }
        let advData: [String: Any] = [
            CBAdvertisementDataServiceUUIDsKey: [Self.serviceUUID],
            CBAdvertisementDataServiceDataKey: [Self.serviceUUID: blob.prefix(20)],
        ]
        m.stopAdvertising()
        m.startAdvertising(advData)
    }
}

extension BeaconAdvertiser: CBPeripheralManagerDelegate {
    public func peripheralManagerDidUpdateState(_ peripheral: CBPeripheralManager) {
        refresh()
    }
    public func peripheralManagerDidStartAdvertising(_ peripheral: CBPeripheralManager, error: Error?) {
        if let error {
            assertionFailure("advertising failed: \(error)")
        }
    }
}