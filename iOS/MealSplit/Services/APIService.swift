import Foundation
import UIKit
import Combine

@MainActor
class APIService: ObservableObject {
    // MARK: - Published Properties
    @Published var isLoading = false
    @Published var lastError: APIError?

    // MARK: - Private Properties
    private let session = URLSession.shared
    private var baseURL: String { SettingsStore.shared.baseURL }
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()
    private class TrustingDelegate: NSObject, URLSessionDelegate {
        func urlSession(_ session: URLSession, didReceive challenge: URLAuthenticationChallenge,
                        completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
            if challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
               let trust = challenge.protectionSpace.serverTrust {
                completionHandler(.useCredential, URLCredential(trust: trust))
            } else {
                completionHandler(.performDefaultHandling, nil)
            }
        }
    }

    private func fetchData(for request: URLRequest) async throws -> (Data, URLResponse) {
        if SettingsStore.shared.allowInsecureTLS {
            let config = URLSessionConfiguration.default
            let session = URLSession(configuration: config, delegate: TrustingDelegate(), delegateQueue: nil)
            return try await session.data(for: request)
        } else {
            return try await URLSession.shared.data(for: request)
        }
    }

    // MARK: - Initialization
    init() {
        setupDateFormatting()
    }

    private func setupDateFormatting() {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        decoder.dateDecodingStrategy = .iso8601
        encoder.dateEncodingStrategy = .iso8601
    }

    // MARK: - Receipt Operations
    struct ReceiptListItemDTO: Codable, Identifiable {
        let id: Int
        let filename: String?
        let uploadDate: String?
        let totalAmount: Double?
        let storeName: String?
        let ocrStatus: String?
        let userId: Int?
        enum CodingKeys: String, CodingKey {
            case id
            case filename
            case uploadDate = "upload_date"
            case totalAmount = "total_amount"
            case storeName = "store_name"
            case ocrStatus = "ocr_status"
            case userId = "user_id"
        }
    }

    func getReceipts() async throws -> [ReceiptListItemDTO] {
        guard let url = URL(string: "\(baseURL)/receipts/") else {
            throw APIError(code: "invalid_url", message: "Invalid receipts URL", details: nil)
        }
        return try await performRequest(url: url, method: "GET")
    }

    struct PlanningWeekDTO: Codable, Identifiable {
        let id: Int
        let householdId: Int
        let weekStart: String
        enum CodingKeys: String, CodingKey { case id; case householdId = "household_id"; case weekStart = "week_start" }
    }

    func getPlanningWeeks(householdId: Int) async throws -> [PlanningWeekDTO] {
        var c = URLComponents(string: "\(baseURL)/planning/weeks")!
        c.queryItems = [URLQueryItem(name: "household_id", value: String(householdId))]
        guard let url = c.url else { throw APIError(code: "invalid_url", message: "Invalid weeks URL", details: nil) }
        return try await performRequest(url: url, method: "GET")
    }

    func uploadReceipt(image: UIImage) async throws -> ReceiptUploadResponse {
        isLoading = true
        defer { isLoading = false }

        guard let imageData = image.jpegData(compressionQuality: 0.8) else {
            throw APIError(code: "image_compression_failed", message: "Failed to compress image", details: nil)
        }

        let url = URL(string: "\(baseURL)/receipts/")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        // Create multipart form data
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        if let token = SettingsStore.shared.accessToken, !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        var body = Data()

        // Add image data
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"receipt.jpg\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n".data(using: .utf8)!)
        let iso = ISO8601DateFormatter().string(from: Date())
        let fields:[(String,String)] = [("household_id", String(SettingsStore.shared.householdId)), ("store_name", ""), ("purchased_at", iso)]
        for (name,value) in fields {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n".data(using: .utf8)!)
            body.append(value.data(using: .utf8)!)
            body.append("\r\n".data(using: .utf8)!)
        }
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        do {
            let (data, response) = try await fetchData(for: request)

            if let httpResponse = response as? HTTPURLResponse {
                guard 200...299 ~= httpResponse.statusCode else {
                    let errorData = try? decoder.decode(APIError.self, from: data)
                    let error = errorData ?? APIError(
                        code: "http_error",
                        message: "HTTP \(httpResponse.statusCode)",
                        details: nil
                    )
                    lastError = error
                    throw error
                }
            }

            let uploadResponse = try decoder.decode(ReceiptUploadResponse.self, from: data)
            return uploadResponse

        } catch {
            if let apiError = error as? APIError {
                lastError = apiError
                throw apiError
            } else {
                let apiError = APIError(
                    code: "network_error",
                    message: error.localizedDescription,
                    details: nil
                )
                lastError = apiError
                throw apiError
            }
        }
    }

    func getReceipt(id: String) async throws -> Receipt {
        let url = URL(string: "\(baseURL)/receipts/\(id)")!
        return try await performRequest(url: url, method: "GET")
    }

    func deleteReceipt(id: String) async throws {
        let url = URL(string: "\(baseURL)/receipts/\(id)")!
        let _: EmptyResponse = try await performRequest(url: url, method: "DELETE")
    }

    // MARK: - Matching Operations
    struct ReceiptLineDTO: Codable, Identifiable {
        let id: Int
        let rawText: String
        let linePrice: Double?
        let qty: Double?
        let unit: String?
        enum CodingKeys: String, CodingKey {
            case id
            case rawText = "raw_text"
            case linePrice = "line_price"
            case qty
            case unit
        }
    }

    struct LineMatchSuggestionDTO: Codable, Identifiable {
        // id may be zero for suggestions
        let id: Int?
        let receiptLineId: Int
        let recipeIngredientId: Int
        let confidence: Double
        let qtyConsumed: Double
        let unit: String
        let priceAllocated: Double
        enum CodingKeys: String, CodingKey {
            case id
            case receiptLineId = "receipt_line_id"
            case recipeIngredientId = "recipe_ingredient_id"
            case confidence
            case qtyConsumed = "qty_consumed"
            case unit
            case priceAllocated = "price_allocated"
        }
    }

    struct PendingMatchesDTO: Codable {
        let receiptLines: [ReceiptLineDTO]
        let suggestedMatches: [LineMatchSuggestionDTO]
        enum CodingKeys: String, CodingKey {
            case receiptLines = "receipt_lines"
            case suggestedMatches = "suggested_matches"
        }
    }

    func getPendingMatches(receiptId: Int, weekId: Int = 1) async throws -> PendingMatchesDTO {
        guard let url = URL(string: "\(baseURL)/receipts/\(receiptId)/matches/pending?week_id=\(weekId)") else {
            throw APIError(code: "invalid_url", message: "Invalid matches URL", details: nil)
        }
        return try await performRequest(url: url, method: "GET")
    }

    func confirmMatch(receiptLineId: Int, recipeIngredientId: Int, qtyConsumed: Double, priceAllocated: Double) async throws {
        guard let url = URL(string: "\(baseURL)/receipts/matches/\(receiptLineId)/confirm") else {
            throw APIError(code: "invalid_url", message: "Invalid confirm URL", details: nil)
        }
        let body: [String: Any] = [
            "receipt_line_id": receiptLineId,
            "recipe_ingredient_id": recipeIngredientId,
            "qty_consumed": qtyConsumed,
            "price_allocated": priceAllocated
        ]
        let _: EmptyResponse = try await performRequest(url: url, method: "POST", body: body)
    }

    func searchIngredients(query: String) async throws -> [Ingredient] {
        guard !query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return []
        }

        var components = URLComponents(string: "\(baseURL)/ingredients/search")!
        components.queryItems = [URLQueryItem(name: "q", value: query)]

        guard let url = components.url else {
            throw APIError(code: "invalid_url", message: "Invalid search URL", details: nil)
        }

        return try await performRequest(url: url, method: "GET")
    }

    // MARK: - Settlement Operations
    func getWeekSettlement(weekId: Int = 1) async throws -> WeekSettlement {
        guard let url = URL(string: "\(baseURL)/settlements/weeks/\(weekId)/settlement") else {
            throw APIError(code: "invalid_url", message: "Invalid settlement URL", details: nil)
        }
        return try await performRequest(url: url, method: "GET")
    }

    func createSplitwiseExpense(settlementId: String) async throws -> WeekSettlement {
        let url = URL(string: "\(baseURL)/settlements/\(settlementId)/splitwise")!
        return try await performRequest(url: url, method: "POST")
    }

    // MARK: - Generic Request Handler
    private func performRequest<T: Codable>(
        url: URL,
        method: String,
        body: [String: Any]? = nil
    ) async throws -> T {
        isLoading = true
        defer { isLoading = false }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = SettingsStore.shared.accessToken, !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body = body {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
        }

        do {
            let (data, response) = try await fetchData(for: request)

            if let httpResponse = response as? HTTPURLResponse {
                guard 200...299 ~= httpResponse.statusCode else {
                    let errorData = try? decoder.decode(APIError.self, from: data)
                    let error = errorData ?? APIError(
                        code: "http_error",
                        message: "HTTP \(httpResponse.statusCode)",
                        details: nil
                    )
                    lastError = error
                    throw error
                }
            }

            let result = try decoder.decode(T.self, from: data)
            if method == "GET" && SettingsStore.shared.cachingEnabled {
                cacheResponse(data: data, for: url)
            }
            return result

        } catch {
            if method == "GET" && SettingsStore.shared.cachingEnabled, let cached = loadCached(for: url) {
                if let result = try? decoder.decode(T.self, from: cached) {
                    return result
                }
            }
            if let apiError = error as? APIError {
                lastError = apiError
                throw apiError
            } else {
                let apiError = APIError(
                    code: "network_error",
                    message: error.localizedDescription,
                    details: nil
                )
                lastError = apiError
                throw apiError
            }
        }
    }

    // MARK: - Utility Methods
    func clearError() {
        lastError = nil
    }

    func updateBaseURL(_ newBaseURL: String) {
        // Remove this in production - for development only
        // baseURL = newBaseURL
    }
}

// MARK: - Caching
extension APIService {
    private func cacheDir() -> URL? {
        FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first?.appendingPathComponent("MealSplitCache")
    }
    private func cacheKey(for url: URL) -> String { url.absoluteString.replacingOccurrences(of: "/", with: "_") }
    private func cacheResponse(data: Data, for url: URL) {
        guard let dir = cacheDir() else { return }
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let file = dir.appendingPathComponent(cacheKey(for: url))
        try? data.write(to: file)
    }
    private func loadCached(for url: URL) -> Data? {
        guard let dir = cacheDir() else { return nil }
        let file = dir.appendingPathComponent(cacheKey(for: url))
        return try? Data(contentsOf: file)
    }
}

// MARK: - Helper Types
private struct EmptyResponse: Codable {}

// MARK: - Preview Helper
extension APIService {
    static func preview() -> APIService { APIService() }
}

// MARK: - Auth
extension APIService {
    struct TokenResponse: Codable { let access_token: String; let refresh_token: String; let token_type: String }

    func login(email: String, password: String) async throws {
        guard let url = URL(string: "\(baseURL)/auth/login") else {
            throw APIError(code: "invalid_url", message: "Invalid login URL", details: nil)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = ["email": email, "password": password]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, response) = try await fetchData(for: request)
        if let http = response as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
            let err = (try? decoder.decode(APIError.self, from: data)) ?? APIError(code: "login_failed", message: "HTTP \(http.statusCode)", details: nil)
            throw err
        }
        let tokens = try decoder.decode(TokenResponse.self, from: data)
        SettingsStore.shared.accessToken = tokens.access_token
    }
}
// MARK: - Connectivity
extension APIService {
    func testConnection(baseURL: String) async throws {
        guard let url = URL(string: baseURL.trimmingCharacters(in: .whitespacesAndNewlines) + "/health") else {
            throw APIError(code: "invalid_url", message: "Invalid base URL", details: nil)
        }
        var req = URLRequest(url: url)
        req.httpMethod = "GET"
        let (_, response) = try await fetchData(for: req)
        if let http = response as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
            throw APIError(code: "http_error", message: "HTTP \(http.statusCode)", details: nil)
        }
    }
}
// MARK: - Households
extension APIService {
    struct HouseholdDTO: Codable, Identifiable { let id: Int; let name: String }
    func getHouseholds() async throws -> [HouseholdDTO] {
        guard let url = URL(string: "\(baseURL)/households/") else {
            throw APIError(code: "invalid_url", message: "Invalid households URL", details: nil)
        }
        return try await performRequest(url: url, method: "GET")
    }
}

// MARK: - Haptic Feedback Helper
extension APIService {
    func triggerHapticFeedback(_ style: UIImpactFeedbackGenerator.FeedbackStyle) {
        let generator = UIImpactFeedbackGenerator(style: style)
        generator.impactOccurred()
    }

    func triggerSuccessHaptic() {
        let generator = UINotificationFeedbackGenerator()
        generator.notificationOccurred(.success)
    }

    func triggerErrorHaptic() {
        let generator = UINotificationFeedbackGenerator()
        generator.notificationOccurred(.error)
    }
}
