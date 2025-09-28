import SwiftUI

struct SettingsView: View {
    @ObservedObject private var settings = SettingsStore.shared
    @EnvironmentObject private var apiService: APIService
    @State private var baseURL: String = SettingsStore.shared.baseURL
    @State private var allowInsecure = SettingsStore.shared.allowInsecureTLS
    @State private var cachingEnabled = SettingsStore.shared.cachingEnabled
    @State private var householdId: String = String(SettingsStore.shared.householdId)
    @State private var email: String = ""
    @State private var password: String = ""
    @State private var status: String?
    @State private var busy = false

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Server")) {
                    TextField("Base URL", text: $baseURL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    Toggle("Allow insecure TLS", isOn: $allowInsecure)
                    HStack {
                        Button("Test") { test() }
                        Spacer()
                        if busy { ProgressView() }
                    }
                    if let status = status { Text(status).font(.footnote).foregroundStyle(.secondary) }
                    Button("Save") { saveServer() }
                }

                Section(header: Text("Authentication")) {
                    SecureField("Password", text: $password)
                    TextField("Email", text: $email)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    Button("Login") { login() }
                }

                Section(header: Text("Household")) {
                    HouseholdSelector(selectedId: $householdId)
                    Button("Set Default Household") { settings.householdId = Int(householdId) ?? 1 }
                }

                Section(header: Text("Preferences")) {
                    Toggle("Enable offline caching", isOn: $cachingEnabled)
                }
            }
            .navigationTitle("Settings")
        }
        .onAppear {
            baseURL = settings.baseURL
            allowInsecure = settings.allowInsecureTLS
            cachingEnabled = settings.cachingEnabled
            householdId = String(settings.householdId)
        }
    }

    private func saveServer() {
        settings.baseURL = baseURL
        settings.allowInsecureTLS = allowInsecure
        settings.cachingEnabled = cachingEnabled
        settings.householdId = Int(householdId) ?? 1
        status = "Saved"
    }

    private func test() {
        busy = true; status = nil
        Task {
            do { try await apiService.testConnection(baseURL: baseURL); await MainActor.run { status = "Connected"; busy = false } }
            catch { await MainActor.run { status = "Failed: \(error.localizedDescription)"; busy = false } }
        }
    }

    private func login() {
        busy = true; status = nil
        Task {
            do { try await apiService.login(email: email, password: password); await MainActor.run { status = "Logged in"; busy = false } }
            catch { await MainActor.run { status = "Login failed: \(error.localizedDescription)"; busy = false } }
        }
    }
}

