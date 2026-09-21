import Foundation
import CryptoKit

/// Incident session (port of core/security.py): double-HMAC key derivation —
/// byte-for-byte identical to Python/Kotlin so one link authenticates on every OS.
public final class IncidentSession {
    public static let macLength = 8
    public static let linkPrefix = "incident://"
    private static let incidentFixedKey = "CROWD-COMPASS/INCIDENT"
    private static let hkdfInfo = "crowd-compass/incident-session-v1"
    private static let authInfo = "crowd-compass/gradient-mac-v1"
    private static let pseudonymInfo = "crowd-compass/incident-pseudonym-v1"

    public let incidentId: String
    public let salt: Data
    public var linkTtl: Int
    public var linkLife: Double
    public let key: Data
    public let authKey: Data

    public init(incidentId: String, salt: Data, linkTtl: Int = 8, linkLife: Double = 900.0) {
        self.incidentId = incidentId
        self.salt = salt
        self.linkTtl = linkTtl
        self.linkLife = linkLife
        let msg = Data(incidentId.utf8) + Data([0]) + salt
        let prk = Self.hmac(key: Data(Self.incidentFixedKey.utf8), data: msg)
        self.key = Self.hmac(key: prk, data: Data(Self.hkdfInfo.utf8))
        self.authKey = Self.hmac(key: self.key, data: Data(Self.authInfo.utf8))
    }

    private static func hmac(key: Data, data: Data) -> Data {
        let mac = HMAC<SHA256>.authenticationCode(for: data, using: SymmetricKey(data: key))
        return Data(mac)
    }

    public func mac(_ pkt: RelayPacket) -> Data {
        let full = Self.hmac(key: authKey, data: canonicalFields(pkt))
        return full.prefix(Self.macLength)
    }

    public func verify(_ pkt: RelayPacket) -> Bool {
        guard let tag = pkt.authTag else { return false }
        return mac(pkt) == tag.prefix(Self.macLength)
    }

    public func attach(_ pkt: RelayPacket) -> RelayPacket {
        var signed = pkt
        signed.authTag = mac(pkt)
        return signed
    }

    public func pseudonym(installKey: Data) -> String {
        let raw = Self.hmac(key: installKey,
                            data: Data(Self.pseudonymInfo.utf8) + Data([0]) + Data(incidentId.utf8))
        return base64URL(raw.prefix(6))
    }

    public func toLink(ttlHops: Int = 8, lifespan: Double = 900.0) -> String {
        let idData = Data(incidentId.utf8)
        var payload = Data()
        UInt16(idData.count).bigEndian.withUnsafeBytes { payload.append(contentsOf: $0) }
        payload.append(idData)
        payload.append(salt)
        let saltB64 = base64URL(salt)
        return "\(Self.linkPrefix)\(base64URL(payload))?salt=\(saltB64)&ttl=\(ttlHops)&life=\(Int(lifespan))"
    }

    public static func makeSession(incidentId: String, salt: Data = randomSalt()) -> IncidentSession {
        IncidentSession(incidentId: incidentId, salt: salt)
    }

    public static func randomSalt(size: Int = 16) -> Data {
        var bytes = [UInt8](repeating: 0, count: size)
        _ = SecRandomCopyBytes(kSecRandomDefault, size, &bytes)
        return Data(bytes)
    }

    public static func parseLink(_ link: String) throws -> IncidentSession {
        guard link.hasPrefix(linkPrefix) else {
            throw LinkError.invalid("not an incident link")
        }
        let rest = String(link.dropFirst(linkPrefix.count))
        let query = rest.split(separator: "?", maxSplits: 1)
        let body = String(query.first ?? "")
        let params = query.count > 1 ? parseParams(String(query[1])) : [:]
        let decoded = try base64URLData(body)
        guard decoded.count >= 3 else {
            throw LinkError.invalid("malformed link payload")
        }
        guard decoded.count >= 2 else {
            throw LinkError.invalid("malformed link payload")
        }
        let header = Array(decoded.prefix(2))
        let idLen = Int(UInt16(header[0]) << 8 | UInt16(header[1]))
        guard 2 + idLen <= decoded.count else {
            throw LinkError.invalid("malformed link payload")
        }
        guard let incidentId = String(data: decoded.dropFirst(2).prefix(idLen), encoding: .utf8) else {
            throw LinkError.invalid("bad incident id encoding")
        }
        let salt = decoded.dropFirst(2 + idLen)
        let session = IncidentSession(incidentId: incidentId, salt: Data(salt))
        session.linkTtl = Int(params["ttl"] ?? "") ?? 8
        session.linkLife = Double(params["life"] ?? "") ?? 900.0
        return session
    }

    /// Canonical on-wire fields: U8 type | 16B event | 8B sender | U16 ver | U8 hop | U8 ttl | U32 ts.
    public func canonicalFields(_ pkt: RelayPacket) -> Data {
        var out = Data()
        out.append(UInt8(pkt.messageType.rawValue))
        out.append(Self.padID(pkt.eventId?.value ?? "", width: 16))
        out.append(Self.padID(pkt.sender?.value ?? "", width: 8))
        out.append(UInt8((pkt.sourceVersion >> 8) & 0xFF))
        out.append(UInt8(pkt.sourceVersion & 0xFF))
        out.append(UInt8(min(max(pkt.hop, 0), 0xFF)))
        out.append(UInt8(min(max(pkt.ttl, 0), 0xFF)))
        out.append(canonTS(pkt.timestamp))
        return out
    }

    private func canonTS(_ t: Double) -> Data {
        guard t != EngineConstants.timeNone, t > 0 else {
            return Data([0, 0, 0, 0])
        }
        let v = UInt32(clamping: Int64((t - EngineConstants.epoch).rounded()))
        return Data([UInt8((v >> 24) & 0xFF), UInt8((v >> 16) & 0xFF),
                     UInt8((v >> 8) & 0xFF), UInt8(v & 0xFF)])
    }

    private static func padID(_ value: String, width: Int) -> Data {
        var out = Data(repeating: 0, count: width)
        let raw = Data(value.utf8)
        for i in 0..<min(raw.count, width) {
            out[out.startIndex + i] = raw[raw.index(raw.startIndex, offsetBy: i)]
        }
        return out
    }

    public enum LinkError: Error {
        case invalid(String)
    }
}

// base64url helpers (shared with the app layer)
public func base64URL(_ data: Data) -> String {
    data.base64EncodedString()
        .replacingOccurrences(of: "+", with: "-")
        .replacingOccurrences(of: "/", with: "_")
        .replacingOccurrences(of: "=", with: "")
}

public func base64URLData(_ s: String) throws -> Data {
    var v = s
        .replacingOccurrences(of: "-", with: "+")
        .replacingOccurrences(of: "_", with: "/")
    while v.count % 4 != 0 { v.append("=") }
    guard let d = Data(base64Encoded: v) else {
        throw IncidentSession.LinkError.invalid("bad base64")
    }
    return d
}

private func parseParams(_ query: String) -> [String: String] {
    var out: [String: String] = [:]
    for part in query.split(separator: "&") {
        let kv = part.split(separator: "=", maxSplits: 1)
        if kv.count == 2 { out[String(kv[0])] = String(kv[1]) }
    }
    return out
}