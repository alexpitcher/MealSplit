import Foundation

// MARK: - Receipt Models
struct Receipt: Codable, Identifiable {
    let id: String
    let userId: String
    let imageUrl: String?
    let uploadDate: Date
    let lines: [ReceiptLine]
    let totalAmount: Double?
    let status: ReceiptStatus

    enum ReceiptStatus: String, Codable, CaseIterable {
        case uploaded = "uploaded"
        case processing = "processing"
        case processed = "processed"
        case failed = "failed"
        case matched = "matched"
    }
}

struct ReceiptLine: Codable, Identifiable {
    let id: String
    let receiptId: String
    let rawText: String
    let linePrice: Double?
    let confidence: Double
    let boundingBox: BoundingBox?
    let normalizedText: String?
    let quantity: Double?
    let unit: String?

    struct BoundingBox: Codable {
        let x: Double
        let y: Double
        let width: Double
        let height: Double
    }
}

// MARK: - Ingredient Models
struct Ingredient: Codable, Identifiable {
    let id: String
    let name: String
    let category: String
    let subcategory: String?
    let commonNames: [String]
    let nutritionData: NutritionData?
    let avgPricePerUnit: Double?
    let commonUnits: [String]

    struct NutritionData: Codable {
        let caloriesPerUnit: Double?
        let proteinPer100g: Double?
        let carbsPer100g: Double?
        let fatPer100g: Double?
    }
}

// MARK: - Matching Models
struct ReceiptLineMatch: Codable, Identifiable {
    let id: String
    let receiptLine: ReceiptLine
    let matchedIngredient: Ingredient?
    let confidence: Double
    let isConfirmed: Bool
    let confirmedBy: String?
    let confirmedAt: Date?
    let alternativeMatches: [AlternativeMatch]

    struct AlternativeMatch: Codable, Identifiable {
        let id: String
        let ingredient: Ingredient
        let confidence: Double
        let matchReason: String
    }
}

// MARK: - Settlement Models
struct WeekSettlement: Codable, Identifiable {
    let id: String
    let weekStart: Date
    let weekEnd: Date
    let userBalances: [UserBalance]
    let totalSpent: Double
    let netAmount: Double
    let isSettled: Bool
    let settlementDate: Date?
    let splitwiseExpenseId: String?

    struct UserBalance: Codable, Identifiable {
        let id: String
        let userId: String
        let userName: String
        let totalSpent: Double
        let shareOfExpenses: Double
        let netBalance: Double // positive = owes money, negative = owed money
        let receiptCount: Int
    }
}

// MARK: - Upload Response Models
struct ReceiptUploadResponse: Codable {
    let receiptId: String
    let status: String
    let message: String
}

struct MatchingResponse: Codable {
    let receiptId: String
    let matches: [ReceiptLineMatch]
    let pendingLines: [ReceiptLine]
    let totalMatches: Int
    let confidence: Double
}

// MARK: - API Error Models
struct APIError: Error, Codable, Equatable {
    let code: String
    let message: String
    let details: [String: String]?

    var localizedDescription: String {
        return message
    }
}

// MARK: - Extensions for UI
extension Receipt.ReceiptStatus {
    var displayName: String {
        switch self {
        case .uploaded: return "Uploaded"
        case .processing: return "Processing"
        case .processed: return "Processed"
        case .failed: return "Failed"
        case .matched: return "Matched"
        }
    }

    var color: Color {
        switch self {
        case .uploaded: return .blue
        case .processing: return .orange
        case .processed: return .green
        case .failed: return .red
        case .matched: return .purple
        }
    }
}

extension ReceiptLineMatch {
    var displayConfidence: String {
        return "\(Int(confidence * 100))%"
    }

    var confidenceColor: Color {
        switch confidence {
        case 0.8...: return .green
        case 0.6..<0.8: return .orange
        default: return .red
        }
    }
}

extension WeekSettlement.UserBalance {
    var balanceColor: Color {
        if netBalance > 0 {
            return .red // Owes money
        } else if netBalance < 0 {
            return .green // Owed money
        } else {
            return .primary // Even
        }
    }

    var balanceDescription: String {
        let amount = abs(netBalance)
        if netBalance > 0 {
            return String(format: "Owes £%.2f", amount)
        } else if netBalance < 0 {
            return String(format: "Owed £%.2f", amount)
        } else {
            return "Even"
        }
    }
}

import SwiftUI
