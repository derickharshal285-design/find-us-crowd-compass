import Foundation

/// Navigation-tier capability negotiation (parity of core/compat.py).
///
/// BLE4 and BLE5 phones must keep working together (and with BLE6/UWB later):
/// every phone advertises what its navigation can actually measure, and both
/// ends of a link run `CapabilityRegistry` to agree on the *lowest* mutually
/// measurable tier. Older builds only ever see measurables they already know,
/// so nothing upstream breaks.
public enum NavTier: Int, Comparable {
    case uwb = 6
    case compassCS = 5
    case motionVector = 4
    case headingRel = 3
    case rssiLogdist = 2
    case rssiBand = 1
    case hopGradient = 0

    public static func < (lhs: NavTier, rhs: NavTier) -> Bool {
        lhs.rawValue < rhs.rawValue
    }

    public static func best(_ a: NavTier, _ b: NavTier) -> NavTier {
        a <= b ? a : b
    }
}

/// Measurables a build can derive, mirroring core/compat.CapabilityRegistry.
public struct CapabilityRegistry {
    public let advertising: Bool
    public let scanning: Bool
    public let imu: Bool
    public let compass: Bool
    public let rotate: Bool
    public let haveCS: Bool

    public init(advertising: Bool, scanning: Bool, imu: Bool,
                compass: Bool, rotate: Bool, haveCS: Bool) {
        self.advertising = advertising
        self.scanning = scanning
        self.imu = imu
        self.compass = compass
        self.rotate = rotate
        self.haveCS = haveCS
    }

    public func availableTiers(peer: CapabilityRegistry?) -> [NavTier] {
        var out: [NavTier] = [.rssiBand]
        if peer == nil || peer!.scanning { out.append(.rssiLogdist) }
        if compass { out.append(.headingRel) }
        if imu { out.append(.motionVector) }
        if haveCS && peer != nil && peer!.haveCS { out.append(.compassCS) }
        return out.sorted()
    }

    public func bestTier(peer: CapabilityRegistry?) -> NavTier? {
        availableTiers(peer: peer).sorted().last
    }
}

/// OOB sideband for the CS/UWB reciprocity bonus: a peer shares its bearing
/// *back to us* (opposite of what it sees). Text-frame, versioned (parity of
/// core/compat.OobSideband).
public enum OobSideband {
    public static let prefixOOB = "FINDUS/OOB/1\n"

    public static func serialize(peerBearingToMeDeg: Double) -> String {
        prefixOOB + String(peerBearingToMeDeg)
    }

    public static func parse(_ raw: String) -> Double? {
        guard raw.hasPrefix(prefixOOB) else { return nil }
        let value = Double(raw.dropFirst(prefixOOB.count).trimmingCharacters(
            in: .whitespacesAndNewlines))
        guard let value, value.isFinite, value >= 0.0, value < 360.0 else { return nil }
        return value
    }
}