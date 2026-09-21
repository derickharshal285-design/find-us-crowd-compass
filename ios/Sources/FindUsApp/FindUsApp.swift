import SwiftUI
import UIKit
import FindUsEngine
import FindUsBLE

@main
struct FindUsApp: App {
    @StateObject private var model = SosViewModel()

    var body: some Scene {
        WindowGroup {
            RootView().environmentObject(model)
                .onAppear { model.start() }
        }
    }
}

struct RootView: View {
    @EnvironmentObject var model: SosViewModel
    @State private var tab = 0

    var body: some View {
        TabView(selection: $tab) {
            MeshView().tabItem { Label("Mesh", systemImage: "antenna.radiowaves.left.and.right") }.tag(0)
            MapView().tabItem { Label("Map", systemImage: "map") }.tag(1)
            GuideView().tabItem { Label("Navigate", systemImage: "location.north.line") }.tag(2)
            ShareView().tabItem { Label("Share", systemImage: "link") }.tag(3)
            MoreView().tabItem { Label("More", systemImage: "gearshape") }.tag(4)
        }
    }
}

// ───────────────────────────── Mesh ─────────────────────────────

struct MeshView: View {
    @EnvironmentObject var model: SosViewModel

    var body: some View {
        NavigationStack {
            List {
                Section("Incident") {
                    LabeledContent("Status", value: model.joined ? model.incidentId : "not joined")
                    LabeledContent("Wire id", value: model.wireId)
                    LabeledContent("Hop to emergency", value: model.myHop.map(String.init) ?? "—")
                    LabeledContent("TTL (hop budget)", value: String(model.ttlHops))
                }
                Section("Emergency") {
                    LabeledContent("Event", value: model.sosEvent.isEmpty ? "none in range" : model.sosEvent)
                    LabeledContent("Mode", value: model.mode)
                    if !model.summary.isEmpty { Text(model.summary).font(.footnote) }
                    LabeledContent("Next hop target", value: model.target ?? "—")
                    if !model.hint.isEmpty {
                        Text(model.hint).font(.footnote).foregroundStyle(.secondary)
                    }
                    HStack {
                        Button("Raise SOS") { model.raiseSos() }.disabled(!model.joined)
                        Spacer()
                        Button("Mark safe") { model.endSos() }.disabled(!model.sosActive)
                    }
                }
                Section("Neighbors (direct radio)") {
                    if model.neighbors.isEmpty {
                        Text("none yet — move around").foregroundStyle(.secondary)
                    } else {
                        ForEach(model.neighbors, id: \.self) { n in
                            if let h = model.neighborHops[n] {
                                Text("\(n)  ·  hop \(h)")
                            } else { Text(n) }
                        }
                    }
                }
                Section("Security") {
                    LabeledContent("MAC rejections", value: String(model.rejectedMacs))
                    LabeledContent("SOS adoptions", value: String(model.adoptions))
                    Text("Every frame is MAC-checked against the incident key before "
                         + "it can touch the graph.").font(.caption).foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Local mesh")
        }
    }
}

// ───────────────────────────── Map ─────────────────────────────

struct MapView: View {
    @EnvironmentObject var model: SosViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Topology view: ring distance is HOP COUNT, not metres. No device "
                         + "here claims a physical position — a graph is not a walking direction.")
                        .font(.caption).foregroundStyle(.secondary)
                    TopologyCanvas().padding(.top, 4)
                    LegendRow()
                    Divider()
                    Text("Gradient hops known: \(model.gradientHops.count)")
                        .font(.headline)
                    ForEach(model.gradientHops.sorted(by: { $0.value < $1.value }),
                            id: \.key) { item in
                        Text("\(item.key)  ·  hop \(item.value)").font(.footnote)
                    }
                    if model.gradientHops.isEmpty {
                        Text("No emergency gradient heard yet.").font(.footnote).foregroundStyle(.secondary)
                    }
                }.padding()
            }
            .navigationTitle("Relative map")
        }
    }
}

struct TopologyCanvas: View {
    @EnvironmentObject var model: SosViewModel

    var body: some View {
        Canvas { ctx, size in
            let cx = size.width / 2
            let cy = size.height / 2
            let maxR = min(cx, cy) * 0.86
            for ring in 1...3 {
                let r = maxR * CGFloat(ring) / 3
                ctx.stroke(Path(ellipseIn: CGRect(x: cx - r, y: cy - r, width: r * 2, height: r * 2)),
                           with: .color(.gray.opacity(0.35)), lineWidth: 1)
            }
            ctx.fill(Path(ellipseIn: CGRect(x: cx - 14, y: cy - 14, width: 28, height: 28)),
                     with: .color(.green))
            let denom = CGFloat(max(1, model.ttlHops))
            let entries = model.neighborHops.sorted(by: { $0.key < $1.key })
            for (i, e) in entries.enumerated() {
                let hop = e.value
                let angle = 2.0 * .pi * Double(i) / Double(max(1, entries.count)) - .pi / 2
                let r = maxR * CGFloat(Double(hop).clamped(to: 1...model.ttlHops)) / denom
                let dx = CGFloat(cos(angle)) * r
                let dy = CGFloat(sin(angle)) * r
                let isTarget = model.target.map { $0 == e.key } ?? false
                let color: Color = isTarget ? .red : (hop <= 1 ? .green : .yellow)
                var path = Path()
                path.move(to: CGPoint(x: cx, y: cy))
                path.addLine(to: CGPoint(x: cx + dx, y: cy + dy))
                ctx.stroke(path, with: .color(.gray.opacity(0.4)), lineWidth: 3)
                ctx.fill(Path(ellipseIn: CGRect(x: cx + dx - 9, y: cy + dy - 9,
                                                width: 18, height: 18)), with: .color(color))
            }
        }
        .frame(height: 280)
    }
}

struct LegendRow: View {
    var body: some View {
        HStack(spacing: 16) {
            LegendDot(color: .green, label: "you")
            LegendDot(color: .red, label: "next hop")
            LegendDot(color: .green.opacity(0.6), label: "hop 1")
            LegendDot(color: .yellow, label: "hop 2+")
        }
    }
}

struct LegendDot: View {
    let color: Color
    let label: String
    var body: some View {
        HStack(spacing: 4) {
            Circle().fill(color).frame(width: 10, height: 10)
            Text(label).font(.caption2)
        }
    }
}

// ─────────────────────────── Navigate ───────────────────────────

struct GuideView: View {
    @EnvironmentObject var model: SosViewModel

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text(model.mode).font(.title2.bold())
                    Text(model.summary.isEmpty ? "No active emergency signal in range." : model.summary)
                    if model.myHop != nil {
                        LabeledContent("Your hop", value: model.myHop.map(String.init) ?? "—")
                        LabeledContent("Next hop target", value: model.target ?? "—")
                    }
                }
                Section("Physical bearing") {
                    Text("NOT CLAIMED")
                        .foregroundStyle(.red)
                    Text("Commodity phones do not expose BLE angle-of-arrival. This build "
                         + "walks the hop gradient: move toward the neighbor advertising the "
                         + "lower hop, then re-check which route stays freshest.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                if !model.hint.isEmpty {
                    Section { Text(model.hint).font(.footnote).foregroundStyle(.secondary) }
                }
                Section("Route integrity") {
                    LabeledContent("Route", value: model.sosActive ? "adopted" : "no route")
                    LabeledContent("Live gradient entries", value: String(model.gradientHops.count))
                    LabeledContent("Neighbors", value: String(model.neighbors.count))
                }
            }
            .navigationTitle("Navigate to the emergency")
        }
    }
}

// ───────────────────────────── Share ─────────────────────────────

struct ShareView: View {
    @EnvironmentObject var model: SosViewModel
    @State private var name = ""
    @State private var link = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text("Every phone that scans the SAME link derives the same team key, "
                         + "so all hands authenticate one another with no server.")
                        .font(.footnote)
                }
                Section("Create") {
                    TextField("Incident name (optional)", text: $name)
                    Button("Create incident") { model.createIncident(named: name) }
                }
                if !model.incidentLink.isEmpty {
                    Section("Your incident link") {
                        Text(model.incidentLink).font(.footnote).textSelection(.enabled)
                        HStack {
                            Button("Copy") { UIPasteboard.general.string = model.incidentLink }
                            ShareLink(item: model.incidentLink) {
                                Label("Share", systemImage: "square.and.arrow.up")
                            }
                        }
                    }
                }
                Section("Join") {
                    TextField("incident://…", text: $link, axis: .vertical)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                    Button("Join") { model.join(link) }
                        .disabled(link.trimmingCharacters(in: .whitespaces).isEmpty)
                }
                if model.mode == "BAD_LINK" {
                    Section { Text("That is not a valid incident link.").foregroundStyle(.red) }
                }
            }
            .navigationTitle("Create or join")
        }
    }
}

// ───────────────────────────── More ─────────────────────────────

struct MoreView: View {
    @EnvironmentObject var model: SosViewModel
    @State private var result = "tap to run parity self-test"

    private let tier: NavTier? = CapabilityRegistry(
        advertising: true, scanning: true, imu: true, compass: true, rotate: true, haveCS: false
    ).bestTier(peer: nil)

    var body: some View {
        NavigationStack {
            Form {
                Section("Capabilities") {
                    LabeledContent("Navigation tier", value: tier.map(tierName) ?? "—")
                    Text("The tier is the LOWEST mutually measurable navigation signal "
                         + "on a link; BLE4 and BLE5 phones always interoperate.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                Section {
                    Text("The engine is a Swift port of the verified Python reference. "
                         + "This self-test re-certifies the same assertions on this device.")
                        .font(.footnote)
                    Button("Run engine parity self-test") {
                        result = model.runSelfTest()
                    }
                    Text(result).font(.footnote)
                } header: { Text("Engine self-test") }
                Section("Packet layer (56-bit PDU)") {
                    Text("The packet self-test (FEC, envelope MAC, GAP budgets, canonical "
                         + "vector) runs in the Android build's Diagnostics tab; Swift RE-AD "
                         + "parity is on the roadmap.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                Section("Privacy") {
                    Text("No account, no server, no cloud. Identity is per-incident: a "
                         + "pseudonym derived from a random install key and the incident id. "
                         + "Nothing leaves radio range unless you share a link.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                Section {
                    Button("Leave incident", role: .destructive) { model.leave() }
                        .disabled(!model.joined)
                    LabeledContent("Ticks since start", value: String(Int(model.tick)))
                }
            }
            .navigationTitle("Diagnostics & settings")
        }
    }

    private func tierName(_ tier: NavTier) -> String {
        switch tier {
        case .uwb: return "UWB (hardware)"
        case .compassCS: return "Compass + Channel Sounding"
        case .motionVector: return "Motion vector (IMU)"
        case .headingRel: return "Relative heading (compass)"
        case .rssiLogdist: return "RSSI log-distance"
        case .rssiBand: return "RSSI near/far band"
        case .hopGradient: return "Hop gradient only"
        }
    }
}