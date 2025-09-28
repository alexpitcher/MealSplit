import Foundation
import Combine

final class SettingsStore: ObservableObject {
    static let shared = SettingsStore()

    @Published var baseURL: String {
        didSet { UserDefaults.standard.set(baseURL, forKey: Keys.baseURL) }
    }
    @Published var allowInsecureTLS: Bool {
        didSet { UserDefaults.standard.set(allowInsecureTLS, forKey: Keys.allowInsecureTLS) }
    }
    @Published var householdId: Int {
        didSet { UserDefaults.standard.set(householdId, forKey: Keys.householdId) }
    }
    @Published var cachingEnabled: Bool {
        didSet { UserDefaults.standard.set(cachingEnabled, forKey: Keys.cachingEnabled) }
    }
    @Published var setupComplete: Bool {
        didSet { UserDefaults.standard.set(setupComplete, forKey: Keys.setupComplete) }
    }
    @Published var accessToken: String? {
        didSet { UserDefaults.standard.set(accessToken, forKey: Keys.accessToken) }
    }

    private struct Keys {
        static let baseURL = "ms_base_url"
        static let allowInsecureTLS = "ms_allow_insecure_tls"
        static let householdId = "ms_household_id"
        static let cachingEnabled = "ms_caching_enabled"
        static let setupComplete = "ms_setup_complete"
        static let accessToken = "ms_access_token"
    }

    private init() {
        self.baseURL = UserDefaults.standard.string(forKey: Keys.baseURL) ?? ""
        self.allowInsecureTLS = UserDefaults.standard.bool(forKey: Keys.allowInsecureTLS)
        let hid = UserDefaults.standard.integer(forKey: Keys.householdId)
        self.householdId = hid == 0 ? 1 : hid
        self.cachingEnabled = UserDefaults.standard.bool(forKey: Keys.cachingEnabled)
        self.setupComplete = UserDefaults.standard.bool(forKey: Keys.setupComplete)
        self.accessToken = UserDefaults.standard.string(forKey: Keys.accessToken)
    }
}

