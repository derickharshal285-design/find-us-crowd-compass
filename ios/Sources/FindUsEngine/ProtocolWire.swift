import Foundation

/// Byte-faithful v3 codec (port of core/protocol.py).
public struct ProtocolWire {

    public struct ProtocolError: Error, CustomStringConvertible {
        public let message: String
        public var description: String { message }
    }

    public init() {}

    public func encode(_ pkt: RelayPacket) -> Data {
        var flags: UInt8 = 0
        var authBlock = Data()
        if let tag = pkt.authTag {
            flags |= 0x04
            authBlock = tag.prefix(8)
            if authBlock.count < EngineConstants.authTagBytes {
                authBlock.append(Data(repeating: 0, count: EngineConstants.authTagBytes - authBlock.count))
            }
        }
        var header = Data()
        header.append(EngineConstants.protocolVersion)
        header.append(UInt8(pkt.messageType.rawValue))
        header.append(packID(pkt.eventId?.value ?? "", width: 16))
        header.append(packID(pkt.sender?.value ?? "", width: 8))
        header.append(packU16(pkt.sourceVersion.clamped(to: 0, 0xFFFF)))
        header.append(UInt8(pkt.hop.clamped(to: 0, 0xFF)))
        header.append(UInt8(pkt.ttl.clamped(to: 0, 0xFF)))
        header.append(packU32(packTime(pkt.timestamp)))
        header.append(flags)
        header.append(authBlock)
        return header
    }

    public func decode(_ blob: Data) throws -> RelayPacket {
        guard blob.count >= 35 else {
            throw ProtocolError(message: "header needs 35 bytes, got \(blob.count)")
        }
        var pos = 0
        let ver = blob[pos]; pos += 1
        guard ver == EngineConstants.protocolVersion else {
            throw ProtocolError(message: "unsupported version \(ver)")
        }
        let mtype = blob[pos]; pos += 1
        guard let mt = MessageType(wire: mtype) else {
            throw ProtocolError(message: "unknown message type \(mtype)")
        }
        let eventBytes = blob[pos..<(pos + 16)]; pos += 16
        let senderBytes = blob[pos..<(pos + 8)]; pos += 8
        let srcVer = unpackU16(blob[pos..<(pos + 2)]); pos += 2
        let hop = Int(blob[pos]); pos += 1
        let ttl = Int(blob[pos]); pos += 1
        let ts = unpackU32(blob[pos..<(pos + 4)]); pos += 4
        let flags = blob[pos]; pos += 1
        if flags & 0x01 != 0 { pos = try skipMeasurement(blob, at: pos) }
        if flags & 0x02 != 0 { pos = try skipMeasurement(blob, at: pos) }
        var auth: Data? = nil
        if flags & 0x04 != 0 {
            guard pos + EngineConstants.authTagBytes <= blob.count else {
                throw ProtocolError(message: "auth tag truncated")
            }
            auth = blob[pos..<(pos + EngineConstants.authTagBytes)]
        }
        return RelayPacket(
            messageType: mt,
            eventId: unpad(eventBytes).map(SosId.init),
            sender: unpad(senderBytes).map(NodeId.init),
            sourceVersion: Int(srcVer),
            hop: hop,
            ttl: ttl,
            timestamp: ts != 0 ? Double(ts) + EngineConstants.epoch : EngineConstants.timeNone,
            authTag: auth)
    }

    private func skipMeasurement(_ blob: Data, at pos0: Int) throws -> Int {
        guard pos0 + 8 <= blob.count else {
            throw ProtocolError(message: "measurement block truncated")
        }
        var pos = pos0 + 8
        let hasDist = blob[pos - 2] != 0
        let hasDir = blob[pos - 1] != 0
        if hasDist { pos += 4 }
        if hasDir { pos += 4 }
        guard pos <= blob.count else {
            throw ProtocolError(message: "measurement trailing data truncated")
        }
        return pos
    }

    private func packID(_ value: String, width: Int) -> Data {
        var out = Data(repeating: 0, count: width)
        let raw = Data(value.utf8)
        for i in 0..<min(raw.count, width) { out[i] = raw[raw.index(raw.startIndex, offsetBy: i)] }
        return out
    }

    private func unpad(_ raw: Data) -> String? {
        var end = raw.count
        while end > 0 && raw[raw.index(raw.startIndex, offsetBy: end - 1)] == 0 { end -= 1 }
        guard end > 0 else { return nil }
        return String(data: raw.subdata(in: raw.startIndex..<raw.index(raw.startIndex, offsetBy: end)), encoding: .utf8)
    }

    private func packTime(_ t: Double) -> UInt32 {
        guard t != EngineConstants.timeNone, t > 0 else { return 0 }
        let v = (t - EngineConstants.epoch).rounded()
        return UInt32(clamping: Int64(v))
    }

    private func packU16(_ v: Int) -> Data {
        Data([UInt8((v >> 8) & 0xFF), UInt8(v & 0xFF)])
    }
    private func packU32(_ v: UInt32) -> Data {
        Data([UInt8((v >> 24) & 0xFF), UInt8((v >> 16) & 0xFF), UInt8((v >> 8) & 0xFF), UInt8(v & 0xFF)])
    }
    private func unpackU16(_ d: Data) -> UInt16 {
        UInt16(d[d.startIndex]) << 8 | UInt16(d[d.index(d.startIndex, offsetBy: 1)])
    }
    private func unpackU32(_ d: Data) -> UInt32 {
        let v = d.map { UInt32($0) }
        return v[0] << 24 | v[1] << 16 | v[2] << 8 | v[3]
    }
}

private extension FixedWidthInteger {
    func clamped(to range: ClosedRange<Self>) -> Self {
        min(max(self, range.lowerBound), range.upperBound)
    }
}