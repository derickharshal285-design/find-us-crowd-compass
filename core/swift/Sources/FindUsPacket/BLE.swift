import Foundation
import Crypto

/// BLE GAP Advertising Encapsulation — Dual-AD Structure for iOS Background Safety
/// Packet v2: 7 bytes raw → 13 bytes Hamming(7,4) coded
/// iOS Mode C ceiling: 23 bytes (31 - 4 Service UUID AD - 4 header)
/// Dual-AD: [AD1: 16-bit Service UUID 0xFC00] + [AD2: Manufacturer Data 0xFFFF + payload]
public enum BLEFraming {
    /// Legacy Manufacturer Data framing (27-byte payload budget)
    /// Header: [Len, 0xFF, CoID_lo, CoID_hi] = 4 bytes
    public static func manufacturerData(payload: Data, companyID: UInt16 = 0xFFFF) -> Data {
        let totalLen = payload.count + 3
        precondition(totalLen <= 27, "Payload \(payload.count) + 3 header exceeds 27-byte manufacturer budget")
        var adv = Data(capacity: 4 + payload.count)
        adv.append(UInt8(totalLen))
        adv.append(0xFF)
        adv.append(UInt8(companyID & 0xFF))
        adv.append(UInt8(companyID >> 8))
        adv.append(payload)
        return adv
    }

    /// iOS Background-Safe Dual-AD Structure (23-byte payload budget)
    /// AD1: 16-bit Service UUID filter anchor [0x03, 0x03, UUID_lo, UUID_hi] = 4 bytes
    /// AD2: Manufacturer Specific Data carrier [Len, 0xFF, CoID_lo, CoID_hi, Payload] = 4 + len bytes
    /// Total budget: 31 - 4 - 4 = 23 bytes for payload
    public static func iosBackgroundSafe(
        payload: Data,
        serviceUUID: UInt16 = 0xFC00,
        companyID: UInt16 = 0xFFFF
    ) -> Data {
        precondition(payload.count <= 23, "Payload \(payload.count) exceeds 23-byte iOS background-safe budget")

        var adv = Data()

        // AD Structure 1: 16-bit Service UUID (Type 0x03)
        adv.append(0x03)        // Length = 3 (Type + 2-byte UUID)
        adv.append(0x03)        // AD Type = 0x03 (16-bit Service UUIDs)
        adv.append(UInt8(serviceUUID & 0xFF))
        adv.append(UInt8(serviceUUID >> 8))

        // AD Structure 2: Manufacturer Specific Data (Type 0xFF)
        let ad2Len = payload.count + 3
        adv.append(UInt8(ad2Len))
        adv.append(0xFF)
        adv.append(UInt8(companyID & 0xFF))
        adv.append(UInt8(companyID >> 8))
        adv.append(payload)

        return adv
    }

    /// Slack calculations for budget verification
    public struct BudgetSlack {
        public let mfrRawTotal: Int      // 4 + 7 = 11
        public let mfrRawSlack: Int      // 31 - 11 = 20
        public let mfrFECTotal: Int      // 4 + 13 = 17
        public let mfrFECSlack: Int      // 31 - 17 = 14
        public let iosRawTotal: Int      // 4 + 4 + 7 = 15
        public let iosRawSlack: Int      // 31 - 15 = 16 (or 23 - 7 = 16 for payload-only)
        public let iosFECTotal: Int      // 4 + 4 + 13 = 21
        public let iosFECSlack: Int      // 31 - 21 = 10 (or 23 - 13 = 10 for payload-only)
    }

    public static func verifyBudgets(rawPacket: Data, fecPacket: Data) -> BudgetSlack {
        let mfrRaw = manufacturerData(payload: rawPacket)
        let mfrFEC = manufacturerData(payload: fecPacket)
        let iosRaw = iosBackgroundSafe(payload: rawPacket)
        let iosFEC = iosBackgroundSafe(payload: fecPacket)

        return BudgetSlack(
            mfrRawTotal: mfrRaw.count,
            mfrRawSlack: 31 - mfrRaw.count,
            mfrFECTotal: mfrFEC.count,
            mfrFECSlack: 31 - mfrFEC.count,
            iosRawTotal: iosRaw.count,
            iosRawSlack: 23 - rawPacket.count,
            iosFECTotal: iosFEC.count,
            iosFECSlack: 23 - fecPacket.count
        )
    }
}

/// Anti-Spoofing Rolling Outer-Envelope MAC (16-bit HMAC-SHA256)
/// Keyed with shared session secret K_session over (SOS_ID || EPOCH || PKT_TYPE)
public enum EnvelopeMAC {
    public static func compute(key: Data, sosId: UInt16, epoch: UInt8, pktType: UInt8) -> UInt16 {
        var msg = Data(capacity: 4)
        msg.append(contentsOf: sosId.bigEndian.bytes)
        msg.append(epoch)
        msg.append(pktType)

        let hmac = HMAC<SHA256>.authenticationCode(for: msg, using: SymmetricKey(data: key))
        // Truncate to 16 bits (first 2 bytes of SHA-256)
        return UInt16(hmac[0]) << 8 | UInt16(hmac[1])
    }

    public static func verify(key: Data, sosId: UInt16, epoch: UInt8, pktType: UInt8, received: UInt16) -> Bool {
        let expected = compute(key: key, sosId: sosId, epoch: epoch, pktType: pktType)
        // Constant-time comparison
        var diff: UInt16 = 0
        diff |= expected ^ received
        return diff == 0
    }
}