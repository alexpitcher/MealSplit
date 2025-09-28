import SwiftUI

struct SetupWizardView: View {
    @ObservedObject private var settings = SettingsStore.shared
    @EnvironmentObject private var apiService: APIService
    @State private var step: Int = 0
    @State private var serverURL: String = SettingsStore.shared.baseURL
    @State private var allowInsecure: Bool = SettingsStore.shared.allowInsecureTLS
    @State private var householdId: String = String(SettingsStore.shared.householdId)
    @State private var cachingEnabled: Bool = SettingsStore.shared.cachingEnabled
    @State private var email: String = ""
    @State private var password: String = ""
    @State private var testing = false
    @State private var testResult: String?
    @State private var serverOK = false
    @State private var loginOK = false
    @State private var householdOK = false

    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                header
                content
                Spacer()
                controls
            }
            .padding()
            .navigationBarTitleDisplayMode(.inline)
        }
        .preferredColorScheme(.dark)
        .onAppear {
            serverURL = settings.baseURL
            allowInsecure = settings.allowInsecureTLS
            householdId = String(settings.householdId)
            cachingEnabled = settings.cachingEnabled
        }
    }

    private var header: some View {
        VStack(spacing: 8) {
            Text("MealSplit Setup")
                .font(.largeTitle)
                .fontWeight(.bold)
            Text("Step \(step+1) of 4")
                .foregroundStyle(.secondary)
        }
    }

    @ViewBuilder
    private var content: some View {
        switch step {
        case 0: welcome
        case 1: server
        case 2: auth
        default: preferences
        }
    }

    private var welcome: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Welcome")
                .font(.title2)
                .fontWeight(.semibold)
            Text("Let's connect to your MealSplit server and get you set up.")
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var server: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Server Connection")
                .font(.title2)
                .fontWeight(.semibold)
            TextField("Server URL (e.g., http://localhost:8000/api/v1)", text: $serverURL)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .padding()
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
            Toggle("Allow insecure connections (disable SSL validation)", isOn: $allowInsecure)
            Button(action: testConnection) {
                HStack { if testing { ProgressView() } ; Text("Test Connection") }
            }
            .buttonStyle(.borderedProminent)
            if let result = testResult {
                Text(result).foregroundStyle(.secondary)
            }
        }
    }

    private var auth: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Authentication")
                .font(.title2)
                .fontWeight(.semibold)
            TextField("Email", text: $email)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .padding()
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
            SecureField("Password", text: $password)
                .padding()
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
            HouseholdSelector(selectedId: $householdId)
            Text("Your credentials are used to authenticate API requests.")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
    }

    private var preferences: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Preferences")
                .font(.title2)
                .fontWeight(.semibold)
            Toggle("Enable offline caching", isOn: $cachingEnabled)
            Text("When enabled, the app caches recent responses and uses them if the server is unavailable.")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
    }

    private var controls: some View {
        HStack {
            if step > 0 {
                Button("Back") { step -= 1 }
            }
            Spacer()
            Button(step == 3 ? "Finish" : "Next") {
                if step == 1 { saveServerAndProceed() }
                else if step == 2 { saveAuthAndProceed() }
                else if step == 3 { finishSetup() } else { step += 1 }
            }
            .buttonStyle(.borderedProminent)
            .disabled((step == 1 && (!serverOK || serverURL.isEmpty)) || (step == 2 && !loginOK))
        }
    }

    private func testConnection() {
        testing = true
        testResult = nil
        Task {
            do {
                try await apiService.testConnection(baseURL: serverURL)
                await MainActor.run { testing = false; serverOK = true; testResult = "Connected" }
            } catch {
                await MainActor.run { testing = false; serverOK = false; testResult = "Failed: \(error.localizedDescription)" }
            }
        }
    }

    private func saveServerAndProceed() {
        settings.baseURL = serverURL
        settings.allowInsecureTLS = allowInsecure
        if serverOK { step += 1 } else { testConnection() }
    }

    private func saveAuth() {
        settings.householdId = Int(householdId) ?? 1
    }

    private func saveAuthAndProceed() {
        settings.householdId = Int(householdId) ?? 1
        Task {
            do {
                try await apiService.login(email: email, password: password)
                await MainActor.run { loginOK = true }
                // Attempt to load households to validate selection
                do {
                    _ = try await apiService.getHouseholds()
                    await MainActor.run { householdOK = true }
                } catch {
                    // Default to 1 silently if fetch fails
                    await MainActor.run { householdId = householdId.isEmpty ? "1" : householdId; householdOK = true }
                }
                await MainActor.run { step += 1 }
            } catch {
                await MainActor.run { loginOK = false; testResult = "Login failed: \(error.localizedDescription)" }
            }
        }
    }

    private func finishSetup() {
        settings.cachingEnabled = cachingEnabled
        settings.setupComplete = true
    }
}
