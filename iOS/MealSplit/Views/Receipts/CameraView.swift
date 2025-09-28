import SwiftUI

struct CameraView: View {
    @StateObject private var cameraService = CameraService()
    @EnvironmentObject private var apiService: APIService
    @State private var selectedImage: UIImage?
    @State private var showingImagePicker = false
    @State private var showingCamera = false
    @State private var sourceType: UIImagePickerController.SourceType = .camera
    @State private var uploadProgress: Double = 0
    @State private var isUploading = false
    @State private var uploadedReceiptId: String?
    @State private var showingAlert = false
    @State private var alertMessage = ""

    var body: some View {
        ZStack {
            LiquidGlassBackground()

            if !cameraService.isAuthorized {
                CameraPermissionView {
                    cameraService.requestCameraPermission()
                }
            } else {
                mainContentView
            }

            // Loading overlay
            if isUploading {
                GlassLoadingOverlay(message: "Processing receipt...")
            }

            // Error alert
            if showingAlert {
                alertOverlay
            }
        }
        .sheet(isPresented: $showingImagePicker) {
            CameraViewRepresentable(
                selectedImage: $selectedImage,
                isPresented: $showingImagePicker,
                sourceType: sourceType
            )
        }
        .onReceive(apiService.$lastError) { error in
            if let error = error {
                alertMessage = error.localizedDescription
                showingAlert = true
                apiService.triggerErrorHaptic()
            }
        }
    }

    private var mainContentView: some View {
        VStack(spacing: 0) {
            headerView

            Spacer()

            if let image = selectedImage {
                selectedImageView(image)
            } else {
                capturePromptView
            }

            Spacer()

            controlsView
        }
        .padding()
    }

    private var headerView: some View {
        GlassSectionHeader(
            title: "Capture Receipt",
            subtitle: uploadedReceiptId != nil ? "Receipt uploaded successfully" : "Take a photo or select from library"
        )
    }

    private func selectedImageView(_ image: UIImage) -> some View {
        VStack(spacing: 20) {
            // Image preview
            Image(uiImage: image)
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(maxHeight: 400)
                .clipShape(RoundedRectangle(cornerRadius: 16))
                .glassCard()

            // Upload progress
            if isUploading {
                GlassProgressView(
                    progress: uploadProgress,
                    title: "Processing receipt..."
                )
            }

            // Success indicator
            if let receiptId = uploadedReceiptId {
                HStack(spacing: 12) {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(.green)
                        .font(.title2)

                    VStack(alignment: .leading) {
                        Text("Receipt Uploaded")
                            .font(.headline)
                            .fontWeight(.semibold)

                        Text("ID: \(receiptId)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()
                }
                .glassCard()
            }
        }
    }

    private var capturePromptView: some View {
        VStack(spacing: 24) {
            VStack(spacing: 16) {
                Image(systemName: "camera.viewfinder")
                    .font(.system(size: 80))
                    .foregroundStyle(.blue)

                VStack(spacing: 8) {
                    Text("Ready to Capture")
                        .font(.title2)
                        .fontWeight(.semibold)

                    Text("Take a clear photo of your receipt with all text visible")
                        .font(.body)
                        .multilineTextAlignment(.center)
                        .foregroundStyle(.secondary)
                }
            }

            // Guidelines
            receiptGuidelinesView
        }
        .glassCard()
    }

    private var receiptGuidelinesView: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Tips for best results:")
                .font(.subheadline)
                .fontWeight(.medium)

            VStack(alignment: .leading, spacing: 8) {
                guidelineRow(icon: "lightbulb", text: "Use good lighting")
                guidelineRow(icon: "crop", text: "Keep receipt flat and centered")
                guidelineRow(icon: "textformat", text: "Ensure all text is readable")
                guidelineRow(icon: "camera.metering.spot", text: "Avoid shadows and glare")
            }
        }
        .padding()
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
    }

    private func guidelineRow(icon: String, text: String) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundStyle(.blue)
                .frame(width: 16)

            Text(text)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }

    private var controlsView: some View {
        VStack(spacing: 16) {
            if selectedImage != nil {
                // Action buttons for selected image
                HStack(spacing: 16) {
                    Button("Retake") {
                        retakePhoto()
                    }
                    .buttonStyle(.glass)
                    .disabled(isUploading)

                    if uploadedReceiptId == nil {
                        Button("Upload Receipt") {
                            uploadSelectedImage()
                        }
                        .buttonStyle(.glass)
                        .disabled(isUploading)
                    } else {
                        Button("New Receipt") {
                            resetCapture()
                        }
                        .buttonStyle(.glass)
                    }
                }
            } else {
                // Capture buttons
                HStack(spacing: 20) {
                    Button("Photo Library") {
                        openPhotoLibrary()
                    }
                    .buttonStyle(.glass)

                    if cameraService.isCameraAvailable {
                        Button("Take Photo") {
                            openCamera()
                        }
                        .buttonStyle(.glass)
                    }
                }
            }
        }
    }

    private var alertOverlay: some View {
        ZStack {
            Color.black.opacity(0.4)
                .ignoresSafeArea()
                .onTapGesture {
                    dismissAlert()
                }

            GlassAlertCard(
                title: "Upload Error",
                message: alertMessage,
                type: .error,
                primaryAction: GlassAlertCard.AlertAction(title: "OK") {
                    dismissAlert()
                },
                secondaryAction: GlassAlertCard.AlertAction(title: "Retry") {
                    dismissAlert()
                    if selectedImage != nil {
                        uploadSelectedImage()
                    }
                }
            )
            .padding()
        }
    }

    // MARK: - Actions
    private func openCamera() {
        sourceType = .camera
        showingImagePicker = true
        apiService.triggerHapticFeedback(.light)
    }

    private func openPhotoLibrary() {
        sourceType = .photoLibrary
        showingImagePicker = true
        apiService.triggerHapticFeedback(.light)
    }

    private func retakePhoto() {
        selectedImage = nil
        uploadedReceiptId = nil
        apiService.triggerHapticFeedback(.light)
    }

    private func resetCapture() {
        selectedImage = nil
        uploadedReceiptId = nil
        uploadProgress = 0
        apiService.clearError()
        apiService.triggerHapticFeedback(.light)
    }

    private func uploadSelectedImage() {
        guard let image = selectedImage else { return }

        isUploading = true
        uploadProgress = 0

        // Simulate progress updates
        Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { timer in
            uploadProgress += 0.1
            if uploadProgress >= 1.0 {
                timer.invalidate()
            }
        }

        Task {
            do {
                let response = try await apiService.uploadReceipt(image: image)
                await MainActor.run {
                    uploadedReceiptId = response.receiptId
                    isUploading = false
                    uploadProgress = 1.0
                    apiService.triggerSuccessHaptic()
                }
            } catch {
                await MainActor.run {
                    isUploading = false
                    uploadProgress = 0
                    alertMessage = error.localizedDescription
                    showingAlert = true
                }
            }
        }
    }

    private func dismissAlert() {
        showingAlert = false
        apiService.clearError()
    }
}

#Preview {
    CameraView()
        .environmentObject(APIService())
}
