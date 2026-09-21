import Foundation

/// Direction-finding parity port of core/direction.py.
///
/// BLE4/5 phone-to-phone direction has no angle hardware: the handset is rotated
/// for a few seconds and the RSSI-vs-heading pattern peaks when the phone faces
/// the neighbor (DirectionSweep). All constants and results must match the
/// verified Python reference exactly.
public enum DirectionMath {
    public static let rssiAt1mDbm = -59.0
    public static let pathLossN = 2.2
    public static let bandNearM = 5.0
    public static let bandMediumM = 20.0
    public static let sweepWindowS = 10.0
    public static let sweepMinSamples = 12
    public static let sweepBinDeg = 45
    public static let sweepMinBinCount = 2

    public static func wrap360(_ deg: Double) -> Double {
        var d = deg.truncatingRemainder(dividingBy: 360.0)
        if d < 0 { d += 360.0 }
        return d
    }

    public static func opposite(_ bearing: Double) -> Double {
        wrap360(bearing + 180.0)
    }

    public static func rssiToMeters(_ rssiDbm: Double, aDbm: Double = rssiAt1mDbm,
                                    n: Double = pathLossN) -> Double {
        let meters = pow(10.0, (aDbm - rssiDbm) / (10.0 * n))
        return rssiDbm >= aDbm ? max(0.5, meters) : meters
    }

    public static func metersToBand(_ distanceM: Double) -> String {
        if distanceM < bandNearM { return "NEAR" }
        if distanceM < bandMediumM { return "MEDIUM" }
        return "FAR"
    }

    public static func confidenceToSigmaDeg(_ confidence: Double) -> Double {
        let c = min(1.0, max(0.0, confidence))
        return 5.0 + 90.0 * (1.0 - c)
    }
}

public struct SweepEstimate {
    public let detected: Bool
    public let bearingDeg: Double
    public let confidence: Double
    public let samples: Int
    public let occupiedBins: Int

    public init(detected: Bool, bearingDeg: Double = 0.0, confidence: Double = 0.0,
                samples: Int = 0, occupiedBins: Int = 0) {
        self.detected = detected
        self.bearingDeg = bearingDeg
        self.confidence = confidence
        self.samples = samples
        self.occupiedBins = occupiedBins
    }

    public var sigmaDeg: Double? {
        detected ? DirectionMath.confidenceToSigmaDeg(confidence) : nil
    }
}

/// Rotate-scan bearing estimator (parity of core/direction.DirectionSweep).
public struct DirectionSweep {
    private struct Sample {
        let ts: Double
        let rssi: Double
        let heading: Double
    }

    private var samples: [Sample] = []
    private let sweepWindowS: Double
    private let binDeg: Int

    public init(sweepWindowS: Double = DirectionMath.sweepWindowS,
                binDeg: Int = DirectionMath.sweepBinDeg) {
        self.sweepWindowS = sweepWindowS
        self.binDeg = binDeg
    }

    public mutating func addSample(rssiDbm: Double, headingDeg: Double, ts: Double) {
        samples.append(Sample(ts: ts, rssi: rssiDbm,
                              heading: DirectionMath.wrap360(headingDeg)))
        if samples.count > 400 { samples.removeFirst(samples.count - 400) }
    }

    public func estimate(now: Double) -> SweepEstimate {
        let cutoff = now - sweepWindowS
        let recent = samples.filter { $0.ts >= cutoff }
        if recent.count < DirectionMath.sweepMinSamples {
            return SweepEstimate(detected: false, samples: recent.count)
        }

        let nBins = 360 / binDeg
        var binSum = [Double](repeating: 0.0, count: nBins)
        var binCnt = [Int](repeating: 0, count: nBins)
        for sample in recent {
            let idx = Int((sample.heading.truncatingRemainder(dividingBy: 360.0)
                + Double(binDeg) / 2.0) / Double(binDeg)) % nBins
            binSum[idx] += sample.rssi
            binCnt[idx] += 1
        }
        var peak = 0
        for i in 1..<nBins {
            let a = binCnt[peak] > 0 ? binSum[peak] / Double(binCnt[peak]) : 0.0
            let b = binCnt[i] > 0 ? binSum[i] / Double(binCnt[i]) : 0.0
            if b > a { peak = i }
        }
        if binCnt[peak] < DirectionMath.sweepMinBinCount {
            return SweepEstimate(detected: false, samples: recent.count,
                                 occupiedBins: binCnt.filter { $0 > 0 }.count)
        }

        var hi = Double.leastNormalMagnitude
        var lo = Double.greatestFiniteMagnitude
        for i in 0..<nBins {
            let m = binCnt[i] > 0 ? binSum[i] / Double(binCnt[i]) : 0.0
            hi = max(hi, m)
            lo = min(lo, m)
        }
        let spread = hi - lo
        let confidence = min(1.0, max(0.0, spread / max(10.0, abs(spread))))
        let bearing = Double((peak * binDeg) % 360)
        return SweepEstimate(detected: true, bearingDeg: bearing, confidence: confidence,
                             samples: recent.count, occupiedBins: binCnt.filter { $0 > 0 }.count)
    }
}

/// Weighted circular fusion + reciprocal (peer-opposite) boost.
public enum BearingFusion {
    public struct Fused {
        public let meanDeg: Double
        public let sigmaDeg: Double
    }

    public static func fusepatches(_ pairs: [(bearing: Double, weight: Double)]) -> Fused? {
        var s = 0.0
        var c = 0.0
        var wsum = 0.0
        for (b, w) in pairs {
            let rad = b * .pi / 180.0
            s += w * sin(rad)
            c += w * cos(rad)
            wsum += w
        }
        if wsum <= 0.0 { return nil }
        let r = hypot(s, c) / wsum
        if r <= 1e-9 { return Fused(meanDeg: 0.0, sigmaDeg: 90.0) }
        let radians = sqrt(max(0.0, -2.0 * log(min(1.0, r))))
        let sigma = max(5.0, min(90.0, radians * 180.0 / .pi))
        let mean = atan2(s / wsum, c / wsum) * 180.0 / .pi
        return Fused(meanDeg: (mean + 360.0).truncatingRemainder(dividingBy: 360.0),
                     sigmaDeg: sigma)
    }

    public static func reciprocalBoost(selfBearing: Double?,
                                        peerBearingToMe: Double?,
                                        weightSelf: Double = 2.0,
                                        weightPeer: Double = 1.0) -> Fused? {
        var pairs: [(bearing: Double, weight: Double)] = []
        if let selfBearing { pairs.append((selfBearing, weightSelf)) }
        if let peerBearingToMe {
            pairs.append((DirectionMath.opposite(peerBearingToMe), weightPeer))
        }
        return fusepatches(pairs)
    }
}

/// Stationarity gate for keeping the sweep honest while the user walks.
public struct StationarityGate {
    private var samples: [Double] = []
    private let window: Int
    private let varianceThreshold: Double

    public init(window: Int = 20, varianceThreshold: Double = 0.10) {
        self.window = window
        self.varianceThreshold = varianceThreshold
    }

    public mutating func addAccel(magnitudeG: Double) {
        samples.append(magnitudeG)
        if samples.count > window { samples.removeFirst(samples.count - window) }
    }

    public func isStationary() -> Bool {
        guard samples.count >= 4 else { return false }
        let mean = samples.reduce(0.0, +) / Double(samples.count)
        let variance = samples.reduce(0.0) { acc, x in
            acc + (x - mean) * (x - mean)
        } / Double(samples.count)
        return variance <= varianceThreshold
    }
}