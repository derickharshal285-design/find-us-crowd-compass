import Foundation

/// Systematic Hamming(7,4) FEC — nibble-wise encoding/decoding
/// 14 nibbles × 7 bits = 98 code bits + 6 pad bits = 104 bits = 13 bytes
public enum HammingFEC {
    /// Encodes 7-byte raw payload (14 nibbles) into 13-byte coded frame
    public static func encode(_ raw: Data) -> Data {
        precondition(raw.count == 7, "Expected 7 raw bytes, got \(raw.count)")

        var nibbles: [UInt8] = []
        nibbles.reserveCapacity(14)
        for b in raw {
            nibbles.append((b >> 4) & 0x0F)
            nibbles.append(b & 0x0F)
        }

        var total: UInt128 = 0
        for n in nibbles {
            total = (total << 7) | UInt128(encodeNibble(n))
        }
        total <<= 6 // 6 trailing zero padding bits

        // Convert UInt128 to 13-byte big-endian Data
        var result = Data(capacity: 13)
        for i in (0..<13).reversed() {
            result.append(UInt8((total >> (8 * i)) & 0xFF))
        }
        return result
    }

    /// Decodes 13-byte coded frame back into 7-byte raw payload
    /// Corrects any 1-bit error per nibble block (up to 14 bit errors across frame)
    public static func decode(_ coded: Data) -> (Data, Int) {
        precondition(coded.count == 13, "Expected 13 coded bytes, got \(coded.count)")

        // Load as UInt128
        var total: UInt128 = 0
        for b in coded {
            total = (total << 8) | UInt128(b)
        }
        total >>= 6 // Remove 6 padding bits

        // Extract 14 blocks of 7 bits (LSB first, then reverse)
        var blocks: [UInt8] = []
        blocks.reserveCapacity(14)
        for _ in 0..<14 {
            blocks.append(UInt8(total & 0x7F))
            total >>= 7
        }
        blocks.reverse()

        // Decode each nibble
        var decodedNibbles: [UInt8] = []
        var totalCorrected = 0
        for b in blocks {
            let (d, err) = decodeNibble(b)
            decodedNibbles.append(d)
            totalCorrected += err
        }

        // Reassemble 7 bytes from 14 nibbles
        var raw = Data(capacity: 7)
        for i in 0..<7 {
            raw.append((decodedNibbles[2 * i] << 4) | decodedNibbles[2 * i + 1])
        }
        return (raw, totalCorrected)
    }

    // MARK: - Internal

    private static func encodeNibble(_ d: UInt8) -> UInt8 {
        let d1 = (d >> 3) & 1
        let d2 = (d >> 2) & 1
        let d3 = (d >> 1) & 1
        let d4 = d & 1
        let p1 = d1 ^ d2 ^ d4
        let p2 = d1 ^ d3 ^ d4
        let p3 = d2 ^ d3 ^ d4
        return (d1 << 6) | (d2 << 5) | (d3 << 4) | (d4 << 3) | (p1 << 2) | (p2 << 1) | p3
    }

    private static func decodeNibble(_ c: UInt8) -> (UInt8, Int) {
        let r1 = (c >> 6) & 1
        let r2 = (c >> 5) & 1
        let r3 = (c >> 4) & 1
        let r4 = (c >> 3) & 1
        let r5 = (c >> 2) & 1
        let r6 = (c >> 1) & 1
        let r7 = c & 1

        let s1 = r1 ^ r2 ^ r4 ^ r5
        let s2 = r1 ^ r3 ^ r4 ^ r6
        let s3 = r2 ^ r3 ^ r4 ^ r7
        let syndrome = (s1 << 2) | (s2 << 1) | s3

        var corrected = c
        var err = 0
        if syndrome != 0 {
            let bitToFlip: Int
            switch syndrome {
            case 1: bitToFlip = 0
            case 2: bitToFlip = 1
            case 3: bitToFlip = 4
            case 4: bitToFlip = 2
            case 5: bitToFlip = 5
            case 6: bitToFlip = 6
            case 7: bitToFlip = 3
            default: bitToFlip = -1
            }
            if bitToFlip >= 0 {
                corrected ^= (1 << bitToFlip)
                err = 1
            }
        }
        return ((corrected >> 3) & 0x0F, err)
    }
}

/// Swift 128-bit unsigned integer for FEC bit manipulation
struct UInt128: Comparable {
    var hi: UInt64 = 0
    var lo: UInt64 = 0

    init() {}
    init(_ value: UInt64) { self.lo = value }
    init(_ hi: UInt64, _ lo: UInt64) { self.hi = hi; self.lo = lo }

    static func << (lhs: UInt128, rhs: Int) -> UInt128 {
        var r = lhs
        if rhs >= 64 {
            r.hi = lhs.lo << (rhs - 64)
            r.lo = 0
        } else if rhs > 0 {
            r.hi = (lhs.hi << rhs) | (lhs.lo >> (64 - rhs))
            r.lo = lhs.lo << rhs
        }
        return r
    }

    static func >> (lhs: UInt128, rhs: Int) -> UInt128 {
        var r = lhs
        if rhs >= 64 {
            r.lo = lhs.hi >> (rhs - 64)
            r.hi = 0
        } else if rhs > 0 {
            r.lo = (lhs.lo >> rhs) | (lhs.hi << (64 - rhs))
            r.hi = lhs.hi >> rhs
        }
        return r
    }

    static func | (lhs: UInt128, rhs: UInt128) -> UInt128 {
        UInt128(lhs.hi | rhs.hi, lhs.lo | rhs.lo)
    }

    static func & (lhs: UInt128, rhs: UInt128) -> UInt128 {
        UInt128(lhs.hi & rhs.hi, lhs.lo & rhs.lo)
    }

    static func ^ (lhs: UInt128, rhs: UInt128) -> UInt128 {
        UInt128(lhs.hi ^ rhs.hi, lhs.lo ^ rhs.lo)
    }

    static func == (lhs: UInt128, rhs: UInt128) -> Bool {
        lhs.hi == rhs.hi && lhs.lo == rhs.lo
    }

    static func < (lhs: UInt128, rhs: UInt128) -> Bool {
        lhs.hi < rhs.hi || (lhs.hi == rhs.hi && lhs.lo < rhs.lo)
    }

    var bytes: [UInt8] {
        var result: [UInt8] = []
        for i in (0..<16).reversed() {
            let shift = i * 8
            if shift >= 64 {
                result.append(UInt8((hi >> (shift - 64)) & 0xFF))
            } else {
                result.append(UInt8((lo >> shift) & 0xFF))
            }
        }
        return result
    }
}

extension UInt128 {
    init(_ value: UInt8) { self.lo = UInt64(value) }
    init(_ value: UInt16) { self.lo = UInt64(value) }
    init(_ value: UInt32) { self.lo = UInt64(value) }
    init(_ value: UInt64) { self.lo = value }
    init(hi: UInt64, lo: UInt64) { self.hi = hi; self.lo = lo }

    static func | (lhs: UInt128, rhs: UInt8) -> UInt128 {
        UInt128(lhs.hi, lhs.lo | UInt64(rhs))
    }
    static func | (lhs: UInt128, rhs: UInt16) -> UInt128 {
        UInt128(lhs.hi, lhs.lo | UInt64(rhs))
    }
    static func | (lhs: UInt128, rhs: UInt32) -> UInt128 {
        UInt128(lhs.hi, lhs.lo | UInt64(rhs))
    }
    static func | (lhs: UInt128, rhs: UInt64) -> UInt128 {
        UInt128(lhs.hi, lhs.lo | rhs)
    }
}