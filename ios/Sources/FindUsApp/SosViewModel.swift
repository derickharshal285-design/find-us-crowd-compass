import Foundation
import Combine
import FindUsEngine
import FindUsBLE

/// The on-device backend, SwiftUI-facing: owns the DeviceApp engine, the BLE
/// dual-role transport, the trickle scheduler and — critically — nothing else.
/// No cloud, no account: everything happens on the phone itself.
@MainActor
public final class SosViewModel: ObservableObject {
    @Published var joined = false
    @Published var incidentId = ""
    @Published var incidentLink = ""
    @Published var wireId = ""
    @Published var sosEvent = ""
    @Published var sosActive = false
    @Published var mode = "NO_SOS_KNOWN"
    @Published var summary = ""
    @Published var myHop: Int?
    @Published var target: String?
    @Published var neighbors: [String] = []
    @Published var neighborHops: [String: Int] = [:]
    @Published var gradientHops: [String: Int] = [:]
    @Published var rejectedMacs = 0
    @Published var adoptions = 0
    @Published var tick = 0.0
    @Published var ttlHops = 8
    @Published var hint = ""

    private var device = DeviceApp(id: NodeId("local"))
    private let store = IncidentStore()
    private let advertisers = BeaconAdvertiser()
    private let scanner = BeaconScanner()
    private let scheduler = AdvScheduler()
    private var tick = 0.0
    private var loop: Task<Void, Never>?

    public init() {}

    public func start() {
        if let saved = store.load(),
           let install = try? base64URLData(saved.installKeyB64) {
            device = DeviceApp(id: NodeId("local"), installKey: install)
            if let session = try? IncidentSession.parseLink(saved.link) {
                device.joinIncident(session)
            }
        } else {
            device = DeviceApp(id: NodeId("local"), installKey: randomInstallKey())
        }
        scheduler.setFrames(device.outgoing())
        advertisers.start { [scheduler] in scheduler.currentFrame() }
        scanner.start { [weak self] _, blob in self?.receive(blob) }
        loop = Task { [weak self] in
            while !Task.isCancelled {
                guard let self else { return }
                self.tick += 1.0
                self.device.beginTick(self.tick)
                self.scheduler.setFrames(self.device.outgoing())
                self.publish()
                try? await Task.sleep(nanoseconds: 1_000_000_000)
            }
        }
    }

    public func join(_ link: String) {
        do {
            let session = try IncidentSession.parseLink(link)
            device.joinIncident(session)
            let install = device.installKey.base64EncodedString()
                .replacingOccurrences(of: "+", with: "-")
                .replacingOccurrences(of: "/", with: "_")
            try store.save(link: link, installKeyB64: install)
            joined = true
            incidentId = session.incidentId
            incidentLink = link
            wireId = device.wireId.value
            scheduler.setFrames(device.outgoing())
        } catch {
            mode = "BAD_LINK"
        }
    }

    public func leave() {
        store.clear()
        device = DeviceApp(id: NodeId("local"), installKey: randomInstallKey())
        joined = false
        incidentId = ""
        incidentLink = ""
        wireId = device.wireId.value
        mode = "NO_SOS_KNOWN"
        scheduler.setFrames(device.outgoing())
    }

    public func raiseSos() {
        device.startSos("EVENT-\(Int(Date().timeIntervalSince1970))")
        scheduler.setFrames(device.outgoing())
    }

    /// Origin role: mint a fresh incident, persist it, and publish its link.
    public func createIncident(named name: String) {
        let id = name.trimmingCharacters(in: .whitespacesAndNewlines)
            .isEmpty ? "INC-\(String(UInt64(Date().timeIntervalSince1970)).suffix(6))" : name
        let session = IncidentSession.makeSession(incidentId: id)
        let link = session.toLink()
        device.joinIncident(session)
        try? store.save(link: link, installKeyB64: device.installKey
            .base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_"))
        incidentLink = link
        incidentId = id
        joined = true
        wireId = device.wireId.value
        mode = "NO_SOS_KNOWN"
        scheduler.setFrames(device.outgoing())
    }

    /// Origin role: resolve/withdraw the active emergency (ghost-kill at source).
    public func endSos() {
        for sid in device.sosEngine.activeSosIds(t: device.t) {
            _ = device.endSos(sid)
        }
        scheduler.setFrames(device.outgoing())
        publish()
    }

    public func runSelfTest() -> String {
        do {
            let report = try EngineSelfTest.run()
            return "EngineSelfTest: \(report.checks) checks PASSED"
        } catch {
            return "FAILED: \(error)"
        }
    }

    private func receive(_ blob: Data) {
        _ = device.onPacket(remoteId: NodeId("remote"), blob: blob)
    }

    private func publish() {
        let sos = device.sosEngine.activeSosIds(t: device.t).first
        let g = sos.map { device.guidance($0) }
        sosEvent = sos?.value ?? ""
        sosActive = sos != nil
        mode = g?.mode ?? "NO_SOS_KNOWN"
        summary = g?.summary ?? ""
        myHop = g?.myHop
        target = g?.target?.value
        hint = g?.hint ?? ""
        wireId = device.wireId.value
        incidentId = device.incident?.incidentId ?? ""
        incidentLink = device.incident?.toLink() ?? ""
        joined = device.incident != nil
        ttlHops = device.ttlHops
        tick = device.t
        neighbors = device.graph.neighbors(device.wireId).map { $0.value }.sorted()
        gradientHops = sos.map { device.hopMap($0) } ?? [:]
        neighborHops = [:]
        for n in neighbors {
            if let h = gradientHops[n] { neighborHops[n] = h }
        }
        rejectedMacs = device.rejectedMacs
        adoptions = device.sosEngine.adoptions
    }

    private func randomInstallKey() -> Data {
        var bytes = [UInt8](repeating: 0, count: 32)
        _ = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
        return Data(bytes)
    }
}