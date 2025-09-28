import Foundation
import Combine

final class ReceiptsState: ObservableObject {
    @Published var selectedReceiptId: Int?
}

