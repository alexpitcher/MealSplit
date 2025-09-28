import SwiftUI

@main
struct MealSplitApp: App {
    @StateObject private var apiService = APIService()
    @StateObject private var receiptsState = ReceiptsState()
    @ObservedObject private var settings = SettingsStore.shared

    var body: some Scene {
        WindowGroup {
            Group {
                if settings.setupComplete {
                    ContentView()
                } else {
                    SetupWizardView()
                }
            }
            .environmentObject(apiService)
            .environmentObject(receiptsState)
        }
    }
}
