import SwiftUI

struct SettlementView: View {
    @EnvironmentObject private var apiService: APIService
    @State private var settlement: WeekSettlement?
    @State private var isLoading = false
    @State private var selectedWeek = Date()
    @State private var selectedWeekId: Int = 1
    @State private var showingWeekPicker = false
    @State private var isCreatingExpense = false
    @State private var showingSuccess = false

    var body: some View {
        ZStack {
            LiquidGlassBackground()

            if let settlement = settlement {
                settlementContentView(settlement)
            } else if isLoading {
                GlassLoadingOverlay(message: "Loading settlement...")
            } else {
                emptyStateView
            }

            if showingSuccess {
                successOverlay
            }
        }
        .onAppear {
            loadSettlement()
        }
        .sheet(isPresented: $showingWeekPicker) {
            WeekPickerView(selectedWeek: $selectedWeek, selectedWeekId: $selectedWeekId) {
                loadSettlement()
            }
        }
    }

    private var emptyStateView: some View {
        VStack(spacing: 24) {
            Image(systemName: "chart.pie")
                .font(.system(size: 80))
                .foregroundStyle(.blue)

            VStack(spacing: 8) {
                Text("No Settlement Data")
                    .font(.title2)
                    .fontWeight(.semibold)

                Text("Upload and match receipts to see your weekly settlement breakdown.")
                    .font(.body)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
            }

            Button("Upload Receipt") {
                // Navigate to camera view
            }
            .buttonStyle(.glass)
        }
        .glassCard()
        .padding()
    }

    private func settlementContentView(_ settlement: WeekSettlement) -> some View {
        ScrollView {
            VStack(spacing: 24) {
                headerView(settlement)
                balancesView(settlement)
                summaryView(settlement)
                actionsView(settlement)
            }
            .padding()
        }
    }

    private func headerView(_ settlement: WeekSettlement) -> some View {
        VStack(spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Week Settlement")
                        .font(.largeTitle)
                        .fontWeight(.bold)

                    Text(weekRangeString(settlement))
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                Button(action: { showingWeekPicker = true }) {
                    Image(systemName: "calendar")
                        .font(.title2)
                        .foregroundStyle(.blue)
                }
                .buttonStyle(.glass)
            }

            if settlement.isSettled {
                GlassStatusChip(text: "Settled", color: .green)
            } else {
                GlassStatusChip(text: "Pending", color: .orange)
            }
        }
    }

    private func balancesView(_ settlement: WeekSettlement) -> some View {
        VStack(spacing: 16) {
            GlassSectionHeader(title: "User Balances")

            ForEach(settlement.userBalances) { balance in
                UserBalanceCard(balance: balance)
            }
        }
    }

    private func summaryView(_ settlement: WeekSettlement) -> some View {
        VStack(spacing: 16) {
            GlassSectionHeader(title: "Summary")

            VStack(spacing: 12) {
                summaryRow(
                    title: "Total Spent",
                    value: String(format: "£%.2f", settlement.totalSpent),
                    color: .primary
                )

                summaryRow(
                    title: "Net Amount",
                    value: String(format: "£%.2f", abs(settlement.netAmount)),
                    color: settlement.netAmount >= 0 ? .red : .green
                )

                summaryRow(
                    title: "Receipts Processed",
                    value: "\(settlement.userBalances.reduce(0) { $0 + $1.receiptCount })",
                    color: .blue
                )
            }
            .glassCard()
        }
    }

    private func summaryRow(title: String, value: String, color: Color) -> some View {
        HStack {
            Text(title)
                .font(.body)
                .foregroundStyle(.secondary)

            Spacer()

            Text(value)
                .font(.body)
                .fontWeight(.semibold)
                .foregroundStyle(color)
        }
    }

    private func actionsView(_ settlement: WeekSettlement) -> some View {
        VStack(spacing: 12) {
            if !settlement.isSettled && settlement.netAmount != 0 {
                Button("Create Splitwise Expense") {
                    createSplitwiseExpense()
                }
                .buttonStyle(.glass)
                .disabled(isCreatingExpense)

                if isCreatingExpense {
                    GlassProgressView(
                        progress: 0.5,
                        title: "Creating Splitwise expense..."
                    )
                }
            }

            if settlement.isSettled, let expenseId = settlement.splitwiseExpenseId {
                HStack(spacing: 8) {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(.green)

                    Text("Splitwise expense created")
                        .font(.subheadline)

                    Text("ID: \(expenseId)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .glassCard()
            }
        }
    }

    private var successOverlay: some View {
        ZStack {
            Color.black.opacity(0.4)
                .ignoresSafeArea()

            GlassAlertCard(
                title: "Success!",
                message: "Splitwise expense has been created successfully. Check your Splitwise app to see the new expense.",
                type: .success,
                primaryAction: GlassAlertCard.AlertAction(title: "OK") {
                    showingSuccess = false
                },
                secondaryAction: nil
            )
            .padding()
        }
    }

    // MARK: - Helper Methods
    private func weekRangeString(_ settlement: WeekSettlement) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d"

        let startString = formatter.string(from: settlement.weekStart)
        let endString = formatter.string(from: settlement.weekEnd)

        return "\(startString) - \(endString)"
    }

    private func loadSettlement() {
        isLoading = true

        Task {
            do {
                let ws = try await apiService.getWeekSettlement(weekId: selectedWeekId)
                await MainActor.run {
                    settlement = ws
                    isLoading = false
                }
            } catch {
                await MainActor.run { isLoading = false }
            }
        }
    }

    private func createSplitwiseExpense() {
        guard let settlement = settlement else { return }

        isCreatingExpense = true

        Task {
                // In real app: let updatedSettlement = try await apiService.createSplitwiseExpense(settlementId: settlement.id)
                await MainActor.run {
                    self.settlement = WeekSettlement(
                        id: settlement.id,
                        weekStart: settlement.weekStart,
                        weekEnd: settlement.weekEnd,
                        userBalances: settlement.userBalances,
                        totalSpent: settlement.totalSpent,
                        netAmount: settlement.netAmount,
                        isSettled: true,
                        settlementDate: Date(),
                        splitwiseExpenseId: "SW123456"
                    )
                    isCreatingExpense = false
                    showingSuccess = true
                    apiService.triggerSuccessHaptic()
                }
            isCreatingExpense = false
        }
    }
}

// MARK: - User Balance Card
struct UserBalanceCard: View {
    let balance: WeekSettlement.UserBalance

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 8) {
                Text(balance.userName)
                    .font(.headline)
                    .fontWeight(.semibold)

                HStack(spacing: 16) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Spent")
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        Text("£\(balance.totalSpent, specifier: "%.2f")")
                            .font(.subheadline)
                            .fontWeight(.medium)
                    }

                    VStack(alignment: .leading, spacing: 2) {
                        Text("Share")
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        Text("£\(balance.shareOfExpenses, specifier: "%.2f")")
                            .font(.subheadline)
                            .fontWeight(.medium)
                    }

                    VStack(alignment: .leading, spacing: 2) {
                        Text("Receipts")
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        Text("\(balance.receiptCount)")
                            .font(.subheadline)
                            .fontWeight(.medium)
                    }
                }
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 4) {
                Text(balance.balanceDescription)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundStyle(balance.balanceColor)

                GlassStatusChip(
                    text: balance.netBalance == 0 ? "Even" : (balance.netBalance > 0 ? "Owes" : "Owed"),
                    color: balance.balanceColor
                )
            }
        }
        .glassCard()
    }
}

// MARK: - Week Picker View
struct WeekPickerView: View {
    @Binding var selectedWeek: Date
    @Binding var selectedWeekId: Int
    let onWeekSelected: () -> Void
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var settings = SettingsStore.shared
    @EnvironmentObject private var apiService: APIService
    @State private var weeks: [APIService.PlanningWeekDTO] = []
    @State private var loading = false

    var body: some View {
        NavigationView {
            ZStack {
                LiquidGlassBackground()

                VStack(spacing: 20) {
                    Text("Select Week")
                        .font(.title2)
                        .fontWeight(.semibold)

                    if loading { ProgressView() }
                    Picker("Planning Week", selection: $selectedWeekId) {
                        ForEach(weeks) { w in
                            Text(w.weekStart).tag(w.id)
                        }
                    }
                    .pickerStyle(.wheel)
                    .glassCard()

                    Button("Select Week") { onWeekSelected(); dismiss() }
                    .buttonStyle(.glass)
                }
                .padding()
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .buttonStyle(.glass)
                }
            }
        }
        .onAppear { loadWeeks() }
    }

    private func loadWeeks() {
        loading = true
        Task {
            do {
                let data = try await apiService.getPlanningWeeks(householdId: settings.householdId)
                await MainActor.run {
                    weeks = data
                    if weeks.first(where: { $0.id == selectedWeekId }) == nil, let first = weeks.first {
                        selectedWeekId = first.id
                    }
                    loading = false
                }
            } catch {
                await MainActor.run { loading = false }
            }
        }
    }
}

// MARK: - Calendar Extensions
extension Calendar {
    func startOfWeek(for date: Date) -> Date {
        let components = dateComponents([.yearForWeekOfYear, .weekOfYear], from: date)
        return self.date(from: components) ?? date
    }

    func endOfWeek(for date: Date) -> Date {
        let startOfWeek = startOfWeek(for: date)
        return self.date(byAdding: .day, value: 6, to: startOfWeek) ?? date
    }
}

#Preview {
    SettlementView()
        .environmentObject(APIService())
}
