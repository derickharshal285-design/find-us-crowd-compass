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
            JoinView().tabItem { Label("Join", systemImage: "link") }.tag(1)
            SettingsView().tabItem { Label("Settings", systemImage: "gearshape") }.tag(2)
        }
    }
}

struct MeshView: View {
    @EnvironmentObject var model: SosViewModel

    var body: some View {
        NavigationStack {
            List {
                Section("Incident") {
                    LabeledContent("Status", value: model.joined ? model.incidentId : "not joined")
                    LabeledContent("Wire id", value: model.wireId)
                }
                Section("Emergency") {
                    LabeledContent("Event", value: model.sosEvent.isEmpty ? "—" : model.sosEvent)
                    LabeledContent("Mode", value: model.mode)
                    LabeledContent("Hop", value: model.myHop.map(String.init) ?? "—")
                    LabeledContent("Target", value: model.target ?? "—")
                    if !model.hint.isEmpty {
                        Text(model.hint).font(.footnote).foregroundStyle(.secondary)
                    }
                }
                Section("Neighbors") {
                    if model.neighbors.isEmpty {
                        Text("none").foregroundStyle(.secondary)
                    } else {
                        ForEach(model.neighbors, id: \.self) { Text($0) }
                    }
                }
                Section("Security") {
                    LabeledContent("MAC rejections", value: String(model.rejectedMacs))
                    LabeledContent("SOS adoptions", value: String(model.adoptions))
                }
                Section {
                    Button("Raise SOS") { model.raiseSos() }
                    Button("Leave incident", role: .destructive) { model.leave() }
                }
            }
            .navigationTitle("Local mesh")
        }
    }
}

struct JoinView: View {
    @EnvironmentObject var model: SosViewModel
    @State private var link = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text("Paste the incident link you received. Every phone in the "
                         + "crowd uses the SAME link, so all hands share the team key.")
                        .font(.footnote)
                }
                Section {
                    TextField("incident://…", text: $link, axis: .vertical)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                    Button("Join") { model.join(link) }
                        .disabled(link.trimmingCharacters(in: .whitespaces).isEmpty)
                }
                if model.mode == "BAD_LINK" {
                    Section { Text("That is not a valid incident link.")
                        .foregroundStyle(.red) }
                }
            }
            .navigationTitle("Join an incident")
        }
    }
}

struct SettingsView: View {
    @EnvironmentObject var model: SosViewModel
    @State private var result = "tap to run parity self-test"

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text("The engine is a Swift port of the verified Python "
                         + "reference. This self-test re-certifies the same "
                         + "assertions on this device.")
                        .font(.footnote)
                }
                Section {
                    Button("Run parity self-test") {
                        result = model.runSelfTest()
                    }
                    if !result.isEmpty {
                        Text(result).font(.footnote)
                    }
                }
            }
            .navigationTitle("Settings & self-test")
        }
    }
}