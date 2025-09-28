import SwiftUI

struct ReceiptsListView: View {
    @EnvironmentObject private var apiService: APIService
    @EnvironmentObject private var receiptsState: ReceiptsState
    @Binding var selectedTab: Int
    @State private var receipts: [APIService.ReceiptListItemDTO] = []
    @State private var loading = false
    @State private var error: String?

    var body: some View {
        ZStack {
            LiquidGlassBackground()
            if loading {
                GlassLoadingOverlay(message: "Loading receipts...")
            }
            ScrollView {
                LazyVStack(spacing: 12) {
                    GlassSectionHeader(title: "Receipts")
                    if let e = error {
                        Text(e).foregroundStyle(.secondary)
                    }
                    ForEach(receipts) { r in
                        Button(action: { select(r) }) {
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(r.storeName ?? (r.filename ?? "Receipt #\(r.id)"))
                                        .font(.headline)
                                    HStack(spacing: 12) {
                                        if let s = r.ocrStatus { Text(s.capitalized).font(.caption).foregroundStyle(.secondary) }
                                        if let t = r.totalAmount { Text(String(format: "£%.2f", t)).font(.caption).foregroundStyle(.secondary) }
                                    }
                                }
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .foregroundStyle(.secondary)
                            }
                            .padding()
                            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
                        }
                    }
                }
                .padding()
            }
        }
        .onAppear { load() }
    }

    private func load() {
        loading = true; error = nil
        Task {
            do {
                let data = try await apiService.getReceipts()
                await MainActor.run { receipts = data; loading = false }
            } catch {
                await MainActor.run { loading = false; self.error = error.localizedDescription }
            }
        }
    }

    private func select(_ r: APIService.ReceiptListItemDTO) {
        receiptsState.selectedReceiptId = r.id
        selectedTab = 2 // switch to Review tab
    }
}

