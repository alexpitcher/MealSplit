import SwiftUI

struct HouseholdSelector: View {
    @Binding var selectedId: String
    @State private var households: [APIService.HouseholdDTO] = []
    @State private var loading = false
    @State private var error: String?
    @EnvironmentObject private var apiService: APIService

    // Uses APIService.HouseholdDTO as the model

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Household")
                .font(.subheadline)
                .fontWeight(.medium)

            if loading {
                ProgressView()
            } else if !households.isEmpty {
                Picker("Household", selection: $selectedId) {
                    ForEach(households) { h in
                        Text(h.name).tag(String(h.id))
                    }
                }
                .pickerStyle(.menu)
            }

            HStack(spacing: 8) {
                Button("Load Households") { fetch() }
                    .buttonStyle(.glass)
                TextField("Or enter ID", text: $selectedId)
                    .keyboardType(.numberPad)
                    .padding(8)
                    .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 8))
            }

            if let e = error { Text(e).font(.footnote).foregroundStyle(.secondary) }
        }
        .onAppear { if households.isEmpty { fetch() } }
    }

    private func fetch() {
        loading = true
        error = nil
        Task {
            do {
                let hs = try await apiService.getHouseholds()
                await MainActor.run {
                    households = hs
                    if selectedId.isEmpty, let first = hs.first { selectedId = String(first.id) }
                    loading = false
                }
            } catch {
                await MainActor.run { loading = false; self.error = error.localizedDescription }
            }
        }
    }
}
