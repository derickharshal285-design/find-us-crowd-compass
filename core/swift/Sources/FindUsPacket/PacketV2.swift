import Foundation
import Crypto

/// Find Us / Crowd Compass — Packet v2 Canonical Wire Format (56 bits / 7.0 bytes)
/// Matches Python reference implementation: 16-bit MAC, Hamming(7,4) FEC, Dual-AD BLE framing
public struct PacketV2: Equatable, Sendable {
    public let pktType: UInt8        // 4 bits  [3:0]   0..15
    public let sosId: UInt16         // 12 bits [15:4]  0..4095
    public let hopCount: UInt8       // 4 bits  [19:16] 0..15
    public let baroDiff: Int8        // 6 bits  [25:20] -32..+31 (0.5 hPa units, ~4.2 m)
    public let flags: UInt8          // 6 bits  [31:26] 0..63
    public let epoch: UInt8          // 4 bits  [35:32] 0..15
    public let age: UInt8            // 2 bits  [37:36] 0..3
    public let reserved: UInt8       // 2 bits  [39:38] 0..3
    public let envelopeMac: UInt16   // 16 bits [55:40] 0..65535

    /// Designated initializer with full validation
    public init(
        pktType: UInt8,
        sosId: UInt16,
        hopCount: UInt8,
        baroDiff: Int8,
        flags: UInt8,
        epoch: UInt8,
        age: UInt8,
        reserved: UInt8 = 0,
        envelopeMac: UInt16 = 0
    ) throws {
        guard pktType <= 0x0F else { throw PacketError.pktTypeOutOfRange }
        guard sosId <= 0x0FFF else { throw PacketError.sosIdOutOfRange }
        guard hopCount <= 0x0F else { throw PacketError.hopCountOutOfRange }
        guard (-32...31).contains(baroDiff) else { throw PacketError.baroDiffOutOfRange }
        guard flags <= 0x3F else { throw PacketError.flagsOutOfRange }
        guard epoch <= 0x0F else { throw PacketError.epochOutOfRange }
        guard age <= 0x03 else { throw PacketError.ageOutOfRange }
        guard reserved <= 0x03 else { throw PacketError.reservedOutOfRange }
        // envelopeMac is UInt16 → 0..65535 always valid

        self.pktType = pktType
        self.sosId = sosId
        self.hopCount = hopCount
        self.baroDiff = baroDiff
        self.flags = flags
        self.epoch = epoch
        self.age = age
        self.reserved = reserved
        self.envelopeMac = envelopeMac
    }

    /// Pack into exactly 7 bytes (56 bits) — big-endian network order
    public func pack() -> Data {
        // 6-bit signed two's complement encoding for baroDiff
        let rawBaro = UInt16(bitPattern: Int16(baroDiff)) & 0x3F

        let word0 = UInt16(pktType) << 12 | sosId
        let word1 = UInt16(hopCount) << 12 | rawBaro << 6 | UInt16(flags)
        let word2 = UInt16(epoch) << 12 | UInt16(age) << 10 | UInt16(reserved) << 8 | (envelopeMac >> 8)
        let macLo = UInt8(envelopeMac & 0xFF)

        var data = Data(capacity: 7)
        data.append(contentsOf: word0.bigEndian.bytes)
        data.append(contentsOf: word1.bigEndian.bytes)
        data.append(contentsOf: word2.bigEndian.bytes)
        data.append(macLo)
        return data
    }

    /// Unpack exactly 7 bytes (56 bits) into PacketV2
    public static func unpack(_ raw: Data) throws -> PacketV2 {
        guard raw.count == 7 else { throw PacketError.invalidLength(expected: 7, actual: raw.count) }

        let word0 = UInt16(bigEndian: raw[0..<2].load(as: UInt16.self))
        let word1 = UInt16(bigEndian: raw[2..<4].load(as: UInt16.self))
        let word2 = UInt16(bigEndian: raw[4..<6].load(as: UInt16.self))
        let macLo = raw[6]

        let pktType = UInt8((word0 >> 12) & 0x0F)
        let sosId = word0 & 0x0FFF

        let hopCount = UInt8((word1 >> 12) & 0x0F)
        let rawBaro = UInt8((word1 >> 6) & 0x3F)
        let baroDiff: Int8 = (rawBaro & 0x20) != 0
            ? Int8(Int16(rawBaro) - 64)
            : Int8(rawBaro)
        let flags = UInt8(word1 & 0x3F)

        let epoch = UInt8((word2 >> 12) & 0x0F)
        let age = UInt8((word2 >> 10) & 0x03)
        let reserved = UInt8((word2 >> 8) & 0x03)
        let envelopeMac = (UInt16(word2 & 0xFF) << 8) | UInt16(macLo)

        return try PacketV2(
            pktType: pktType,
            sosId: sosId,
            hopCount: hopCount,
            baroDiff: baroDiff,
            flags: flags,
            epoch: epoch,
            age: age,
            reserved: reserved,
            envelopeMac: envelopeMac
        )
    }

    /// Returns 56-character binary string
    public var bitString: String {
        let data = pack()
        return data.map { String($0, radix: 2).leftPadded(to: 8, with: "0") }.joined()
    }

    /// Parse 56-bit binary string back into PacketV2
    public static func fromBitString(_ bitStr: String) throws -> PacketV2 {
        let clean = bitStr.replacingOccurrences(of: " ", with: "").replacingOccurrences(of: "_", with: "")
        guard clean.count == 56 else { throw PacketError.invalidBitStringLength(clean.count) }
        let value = UInt64(clean, radix: 2)!
        var data = Data(capacity: 7)
        for i in (0..<7).reversed() {
            data.append(UInt8((value >> (8 * i)) & 0xFF))
        }
        return try unpack(data)
    }
}

public enum PacketError: Error, CustomStringConvertible {
    case pktTypeOutOfRange, sosIdOutOfRange, hopCountOutOfRange, baroDiffOutOfRange, flagsOutOfRange
    case epochOutOfRange, ageOutOfRange, reservedOutOfRange
    case invalidLength(expected: Int, actual: Int)
    case invalidBitStringLength(Int)
    case macVerificationFailed

    public var description: String {
        switch self {
        case .pktTypeOutOfRange: return "pkt_type out of 4-bit range [0, 15]"
        case .sosIdOutOfRange: return "sos_id out of 12-bit range [0, 4095]"
        case .hopCountOutOfRange: return "hop_count out of 4-bit range [0, 15]"
        case .baroDiffOutOfRange: return "baro_diff out of 6-bit signed range [-32, 31]"
        case .flagsOutOfRange: return "flags out of 6-bit range [0, 63]"
        case .epochOutOfRange: return "epoch out of 4-bit range [0, 15]"
        case .ageOutOfRange: return "age out of 2-bit range [0, 3]"
        case .reservedOutOfRange: return "reserved out of 2-bit range [0, 3]"
        case .invalidLength(let exp, let act): return "Expected \(exp) bytes, got \(act)"
        case .invalidBitStringLength(let len): return "Expected 56 bits, got \(len)"
        case .macVerificationFailed: return "MAC verification failed"
        }
    }
}

/// Packet Type enum (4 bits)
public enum PacketType: UInt8, Sendable {
    case liveGradient       = 0x0
    case cachedMuleBurst    = 0x1
    case discoveryProbe     = 0x2
    case ack                = 0x3
    case cancel             = 0x4
    case heartbeat          = 0x5
    case diagnostic         = 0x6
}

/// Age Bucket enum (2 bits)
public enum AgeBucket: UInt8, Sendable {
    case live           = 0  // < 10 s
    case under1Min      = 1  // 10 s – < 60 s
    case under5Min      = 2  // 1 min – < 5 min
    case over5Min       = 3  // >= 5 min
}

/// Flags bitmask (6 bits)
public struct Flags: OptionSet, Sendable {
    public let rawValue: UInt8
    public init(rawValue: UInt8) { self.rawValue = rawValue }

    public static let emergencyType      = Flags(rawValue: 0x01) // Bit 0
    public static let visualRunway       = Flags(rawValue: 0x02) // Bit 1
    public static let severeUrgency      = Flags(rawValue: 0x04) // Bit 2
    public static let ackReceived        = Flags(rawValue: 0x08) // Bit 3
    public static let cancelResolved     = Flags(rawValue: 0x10) // Bit 4
    public static let muleStoreForward   = Flags(rawValue: 0x20) // Bit 5
}

/// Reserved bits (2 bits)
public struct ReservedBits: OptionSet, Sendable {
    public let rawValue: UInt8
    public init(rawValue: UInt8) { self.rawValue = rawValue }

    public static let secondaryPhy       = ReservedBits(rawValue: 0x01)
    public static let collisionExpedite  = ReservedBits(rawValue: 0x02)
}

/// Canonical reference vector (for cross-language verification)
public struct CanonicalVectors {
    public static let referencePacket = try! PacketV2(
        pktType: PacketType.cachedMuleBurst.rawValue, // 1
        sosId: 0x7A5,                                 // 1957
        hopCount: 3,
        baroDiff: -5,
        flags: Flags.muleStoreForward.rawValue | Flags.visualRunway.rawValue, // 0x22
        epoch: 9,
        age: AgeBucket.under5Min.rawValue,            // 2
        reserved: ReservedBits.secondaryPhy.rawValue, // 1
        envelopeMac: 0x8F42                           // 16-bit MAC
    )

    public static let expectedHex = "17a53ee2998f42"
    public static let expectedBits = "00010111101001010011111011100010100110011000111101000010"
}

extension UInt16 {
    var bytes: [UInt8] { [UInt8(self >> 8), UInt8(self & 0xFF)] }
}

extension Data {
    func load<T>(as type: T.Type) -> T where T: ExpressibleByIntegerLiteral {
        var value: T = 0
        _ = Swift.withUnsafeMutableBytes(of: &value) { self.copyBytes(to: $0) }
        return value
    }
}

extension String {
    func leftPadded(to length: Int, with char: Character) -> String {
        return count >= length ? self : String(repeating: char, count: length - count) + self
    }
}