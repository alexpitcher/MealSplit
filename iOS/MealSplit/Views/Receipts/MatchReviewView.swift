import SwiftUI

struct MatchReviewView: View {
    @EnvironmentObject private var apiService: APIService
    @EnvironmentObject private var receiptsState: ReceiptsState
    struct LineSuggestions: Identifiable {
        let id: Int
        let line: APIService.ReceiptLineDTO
        let suggestions: [APIService.LineMatchSuggestionDTO]
    }
    @State private var items: [LineSuggestions] = []
    @State private var isLoading = false
    @State private var selectedReceiptId: Int?
    @State private var searchText = ""
    @State private var showingSearch = false

    var body: some View {
        ZStack {
            LiquidGlassBackground()

            if items.isEmpty && !isLoading {
                emptyStateView
            } else {
                mainContentView
            }

            if isLoading {
                GlassLoadingOverlay(message: "Loading matches...")
            }
        }
        .onAppear { loadIfSelected() }
        .onReceive(receiptsState.$selectedReceiptId) { _ in loadIfSelected() }
    }

    private var emptyStateView: some View {
        VStack(spacing: 24) {
            Image(systemName: "checkmark.circle.badge.questionmark")
                .font(.system(size: 80))
                .foregroundStyle(.blue)

            VStack(spacing: 8) {
                Text("No Matches to Review")
                    .font(.title2)
                    .fontWeight(.semibold)

                Text("Upload a receipt to start matching ingredients with your shopping list.")
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

    private var mainContentView: some View {
        ScrollView {
            LazyVStack(spacing: 16) {
                headerView

                if !items.isEmpty {
                    matchesListView
                }
            }
            .padding()
        }
    }

    private var headerView: some View {
        GlassSectionHeader(
            title: "Review Matches",
            subtitle: "\(items.count) items to review"
        )
    }

    private var matchesListView: some View {
        ForEach(items) { entry in
            MatchCardView(line: entry.line, suggestions: entry.suggestions) {
                // Reload or update list after confirm
                loadForSelectedReceipt()
            }
        }
    }

    private func loadForSelectedReceipt() {
        guard let rid = receiptsState.selectedReceiptId else { return }
        isLoading = true
        Task {
            do {
                let res = try await apiService.getPendingMatches(receiptId: rid, weekId: 1)
                let grouped = Dictionary(grouping: res.suggestedMatches, by: { $0.receiptLineId })
                let lines = res.receiptLines
                let mapped: [LineSuggestions] = lines.map { l in
                    LineSuggestions(id: l.id, line: l, suggestions: grouped[l.id] ?? [])
                }.filter { !$0.suggestions.isEmpty }
                await MainActor.run { items = mapped; isLoading = false }
            } catch {
                await MainActor.run { isLoading = false }
            }
        }
    }

    // Loading matches should be triggered from a selected receipt context
    private func loadIfSelected() {
        if receiptsState.selectedReceiptId != nil { loadForSelectedReceipt() }
    }
}

// MARK: - Match Card View
struct LegacyMatchCardView: View {
    let match: ReceiptLineMatch
    let onUpdate: (ReceiptLineMatch) -> Void

    @State private var selectedIngredient: Ingredient?
    @State private var showingSearch = false
    @State private var searchResults: [Ingredient] = []
    @State private var isConfirming = false
    @EnvironmentObject private var apiService: APIService

    init(match: ReceiptLineMatch, onUpdate: @escaping (ReceiptLineMatch) -> Void) {
        self.match = match
        self.onUpdate = onUpdate
        self._selectedIngredient = State(initialValue: match.matchedIngredient)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            receiptLineSection
            confidenceSection
            ingredientPickerSection
            confirmButtonSection
        }
        .glassCard()
        .sheet(isPresented: $showingSearch) {
            IngredientSearchView(
                initialQuery: match.receiptLine.normalizedText ?? "",
                onSelection: { ingredient in
                    selectedIngredient = ingredient
                    showingSearch = false
                }
            )
        }
    }

    private var receiptLineSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(match.receiptLine.rawText)
                    .font(.body)
                    .fontWeight(.medium)
                    .lineLimit(2)

                Spacer()

                Text("£\(match.receiptLine.linePrice ?? 0, specifier: "%.2f")")
                    .font(.title3)
                    .fontWeight(.semibold)
            }

            if let quantity = match.receiptLine.quantity,
               let unit = match.receiptLine.unit {
                Text("\(quantity, specifier: "%.0f") \(unit)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var confidenceSection: some View {
        HStack {
            Text("Confidence")
                .font(.caption)
                .foregroundStyle(.secondary)

            Spacer()

            GlassStatusChip(
                text: match.displayConfidence,
                color: match.confidenceColor
            )
        }
    }

    private var ingredientPickerSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Matched Ingredient")
                .font(.subheadline)
                .fontWeight(.medium)

            if let ingredient = selectedIngredient {
                selectedIngredientView(ingredient)
            } else {
                Button("Search Ingredients") {
                    showingSearch = true
                }
                .buttonStyle(.glass)
            }
        }
    }

    private func selectedIngredientView(_ ingredient: Ingredient) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(ingredient.name)
                    .font(.body)
                    .fontWeight(.medium)

                Text(ingredient.category)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Button("Change") {
                showingSearch = true
            }
            .buttonStyle(.glass)
        }
        .padding()
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 8))
    }

    private var confirmButtonSection: some View {
        HStack {
            if match.isConfirmed {
                HStack(spacing: 8) {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(.green)

                    Text("Confirmed")
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundStyle(.green)
                }
            } else {
                Button("Confirm Match") {
                    confirmMatch()
                }
                .buttonStyle(.glass)
                .disabled(selectedIngredient == nil || isConfirming)
            }

            Spacer()
        }
    }

    private func confirmMatch() {
        guard let ingredient = selectedIngredient else { return }

        isConfirming = true

        Task {
                // In real app, call API to confirm match
                // let confirmedMatch = try await apiService.confirmMatch(matchId: match.id, ingredientId: ingredient.id)
                await MainActor.run {
                    let confirmedMatch = ReceiptLineMatch(
                        id: match.id,
                        receiptLine: match.receiptLine,
                        matchedIngredient: ingredient,
                        confidence: match.confidence,
                        isConfirmed: true,
                        confirmedBy: "user",
                        confirmedAt: Date(),
                        alternativeMatches: match.alternativeMatches
                    )

                    onUpdate(confirmedMatch)
                    isConfirming = false
                    apiService.triggerSuccessHaptic()
                }
            isConfirming = false
        }
    }
}

// MARK: - Ingredient Search View
struct IngredientSearchView: View {
    let initialQuery: String
    let onSelection: (Ingredient) -> Void

    @State private var searchText: String
    @State private var searchResults: [Ingredient] = []
    @State private var isSearching = false
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var apiService: APIService

    init(initialQuery: String, onSelection: @escaping (Ingredient) -> Void) {
        self.initialQuery = initialQuery
        self.onSelection = onSelection
        self._searchText = State(initialValue: initialQuery)
    }

    var body: some View {
        NavigationView {
            ZStack {
                LiquidGlassBackground()

                VStack(spacing: 0) {
                    searchSection
                    resultsSection
                }
            }
            .navigationTitle("Search Ingredients")
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
        .onAppear {
            if !initialQuery.isEmpty {
                performSearch()
            }
        }
    }

    private var searchSection: some View {
        VStack {
            GlassInputField(
                title: "Ingredient Name",
                text: $searchText,
                placeholder: "Search for ingredient..."
            )
            .onSubmit {
                performSearch()
            }
        }
        .padding()
    }

    private var resultsSection: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(searchResults) { ingredient in
                    IngredientResultCard(ingredient: ingredient) {
                        onSelection(ingredient)
                    }
                }
            }
            .padding()
        }
    }

    private func performSearch() {
        guard !searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return
        }

        isSearching = true

        Task {
                // In real app: let results = try await apiService.searchIngredients(query: searchText)
                await MainActor.run {
                    searchResults = [
                        Ingredient(
                            id: "search1",
                            name: "Atlantic Salmon",
                            category: "Fish & Seafood",
                            subcategory: "Fresh Fish",
                            commonNames: ["salmon", "atlantic salmon"],
                            nutritionData: nil,
                            avgPricePerUnit: 22.50,
                            commonUnits: ["g", "kg", "portion"]
                        ),
                        Ingredient(
                            id: "search2",
                            name: "Smoked Salmon",
                            category: "Fish & Seafood",
                            subcategory: "Smoked Fish",
                            commonNames: ["smoked salmon"],
                            nutritionData: nil,
                            avgPricePerUnit: 35.00,
                            commonUnits: ["g", "pack"]
                        )
                    ]
                    isSearching = false
                }
        }
    }
}

// MARK: - Ingredient Result Card
struct IngredientResultCard: View {
    let ingredient: Ingredient
    let onSelect: () -> Void

    var body: some View {
        Button(action: onSelect) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(ingredient.name)
                        .font(.body)
                        .fontWeight(.medium)

                    Text(ingredient.category)
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    if let subcategory = ingredient.subcategory {
                        Text(subcategory)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }

                Spacer()

                if let avgPrice = ingredient.avgPricePerUnit {
                    Text("£\(avgPrice, specifier: "%.2f")/unit")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .buttonStyle(InteractiveGlassCardStyle())
        .glassCard()
    }
}

#Preview {
    MatchReviewView()
        .environmentObject(APIService())
}

// New match card tied to backend suggestions
struct MatchCardView: View {
    let line: APIService.ReceiptLineDTO
    let suggestions: [APIService.LineMatchSuggestionDTO]
    let onConfirmed: () -> Void

    @State private var selected: APIService.LineMatchSuggestionDTO?
    @State private var showingSearch = false
    @State private var isConfirming = false
    @EnvironmentObject private var apiService: APIService

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Line
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(line.rawText)
                        .font(.body)
                        .fontWeight(.medium)
                        .lineLimit(2)
                    Spacer()
                    Text(String(format: "£%.2f", line.linePrice ?? 0))
                        .font(.title3)
                        .fontWeight(.semibold)
                }
                if let q = line.qty, let u = line.unit {
                    Text(String(format: "%.0f %@", q, u))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            // Suggestions
            VStack(alignment: .leading, spacing: 8) {
                Text("Suggestions")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                ForEach(suggestions, id: \.recipeIngredientId) { s in
                    HStack {
                        Text("Ingredient #\(s.recipeIngredientId)")
                        Spacer()
                        Text(String(format: "%.0f%%", s.confidence * 100))
                            .foregroundStyle(.secondary)
                    }
                    .contentShape(Rectangle())
                    .onTapGesture { selected = s }
                    .padding(8)
                    .background(selected?.recipeIngredientId == s.recipeIngredientId ? Color.blue.opacity(0.15) : .clear)
                    .cornerRadius(8)
                }
            }

            // Confirm
            HStack {
                Button("Confirm Match") { confirm() }
                    .buttonStyle(.glass)
                    .disabled(selected == nil || isConfirming)
                Spacer()
                Button("Search Ingredients") { showingSearch = true }
                    .buttonStyle(.glass)
            }
        }
        .glassCard()
        .sheet(isPresented: $showingSearch) {
            IngredientSearchView(initialQuery: "", onSelection: { _ in showingSearch = false })
        }
    }

    private func confirm() {
        guard let s = selected else { return }
        isConfirming = true
        Task {
            do {
                try await apiService.confirmMatch(
                    receiptLineId: line.id,
                    recipeIngredientId: s.recipeIngredientId,
                    qtyConsumed: s.qtyConsumed,
                    priceAllocated: s.priceAllocated
                )
                await MainActor.run { isConfirming = false; apiService.triggerSuccessHaptic(); onConfirmed() }
            } catch {
                await MainActor.run { isConfirming = false }
            }
        }
    }
}
