import SwiftUI

struct ContentView: View {
    @State private var selectedTab = 0
    @EnvironmentObject private var receiptsState: ReceiptsState

    var body: some View {
        TabView(selection: $selectedTab) {
            CameraView()
                .tabItem {
                    Image(systemName: "camera")
                    Text("Capture")
                }
                .tag(0)

            ReceiptsListView(selectedTab: $selectedTab)
                .tabItem {
                    Image(systemName: "doc.text")
                    Text("Receipts")
                }
                .tag(1)

            MatchReviewView()
                .tabItem {
                    Image(systemName: "checkmark.circle")
                    Text("Review")
                }
                .tag(2)

            SettlementView()
                .tabItem {
                    Image(systemName: "chart.pie")
                    Text("Settlement")
                }
                .tag(3)

            SettingsView()
                .tabItem {
                    Image(systemName: "gear")
                    Text("Settings")
                }
                .tag(4)
        }
        .preferredColorScheme(.dark) // Glass effects work best in dark mode
    }
}

#Preview {
    ContentView()
        .environmentObject(APIService())
}
