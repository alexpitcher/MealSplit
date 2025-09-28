import SwiftUI
import UIKit
import AVFoundation

// MARK: - Camera Service
class CameraService: NSObject, ObservableObject {
    @Published var isAuthorized = false
    @Published var isCameraAvailable = false
    @Published var capturedImage: UIImage?

    override init() {
        super.init()
        checkCameraAuthorization()
        checkCameraAvailability()
    }

    private func checkCameraAuthorization() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            isAuthorized = true
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                DispatchQueue.main.async {
                    self?.isAuthorized = granted
                }
            }
        case .denied, .restricted:
            isAuthorized = false
        @unknown default:
            isAuthorized = false
        }
    }

    private func checkCameraAvailability() {
        isCameraAvailable = UIImagePickerController.isSourceTypeAvailable(.camera)
    }

    func requestCameraPermission() {
        AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
            DispatchQueue.main.async {
                self?.isAuthorized = granted
            }
        }
    }
}

// MARK: - Camera View Representable
struct CameraViewRepresentable: UIViewControllerRepresentable {
    @Binding var selectedImage: UIImage?
    @Binding var isPresented: Bool
    let sourceType: UIImagePickerController.SourceType

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = sourceType
        picker.delegate = context.coordinator
        picker.allowsEditing = false
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let parent: CameraViewRepresentable

        init(_ parent: CameraViewRepresentable) {
            self.parent = parent
        }

        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey : Any]) {
            if let image = info[.originalImage] as? UIImage {
                parent.selectedImage = image
            }
            parent.isPresented = false
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            parent.isPresented = false
        }
    }
}

// MARK: - Camera Permission View
struct CameraPermissionView: View {
    let onRequestPermission: () -> Void

    var body: some View {
        ZStack {
            LiquidGlassBackground()

            VStack(spacing: 24) {
                VStack(spacing: 16) {
                    Image(systemName: "camera.fill")
                        .font(.system(size: 60))
                        .foregroundStyle(.blue)

                    VStack(spacing: 8) {
                        Text("Camera Access Required")
                            .font(.title2)
                            .fontWeight(.semibold)

                        Text("MealSplit needs camera access to capture receipt photos for expense splitting.")
                            .font(.body)
                            .multilineTextAlignment(.center)
                            .foregroundStyle(.secondary)
                    }
                }

                Button("Enable Camera Access") {
                    onRequestPermission()
                }
                .buttonStyle(.glass)
            }
            .glassCard()
            .padding()
        }
    }
}

// MARK: - Camera Capture Button
struct CameraCaptureButton: View {
    let action: () -> Void
    @State private var isPressed = false

    var body: some View {
        Button(action: action) {
            ZStack {
                Circle()
                    .fill(.ultraThinMaterial)
                    .frame(width: 80, height: 80)
                    .overlay {
                        Circle()
                            .stroke(.white.opacity(0.3), lineWidth: 2)
                    }

                Circle()
                    .fill(.white)
                    .frame(width: 60, height: 60)
                    .scaleEffect(isPressed ? 0.9 : 1.0)
            }
        }
        .scaleEffect(isPressed ? 0.95 : 1.0)
        .animation(.easeInOut(duration: 0.1), value: isPressed)
        .onLongPressGesture(minimumDuration: 0, maximumDistance: .infinity) { isPressing in
            isPressed = isPressing
        } perform: {
            action()
        }
    }
}

// MARK: - Image Preview with Controls
struct ImagePreviewWithControls: View {
    let image: UIImage
    let onRetake: () -> Void
    let onConfirm: () -> Void
    @State private var isUploading = false

    var body: some View {
        VStack(spacing: 20) {
            // Image preview in glass container
            Image(uiImage: image)
                .resizable()
                .aspectRatio(contentMode: .fit)
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .glassCard()

            // Control buttons
            HStack(spacing: 16) {
                Button("Retake") {
                    onRetake()
                }
                .buttonStyle(.glass)
                .disabled(isUploading)

                Button("Upload Receipt") {
                    isUploading = true
                    onConfirm()
                }
                .buttonStyle(.glass)
                .disabled(isUploading)
            }

            if isUploading {
                GlassProgressView(
                    progress: 0.5, // This would be bound to actual upload progress
                    title: "Uploading receipt..."
                )
            }
        }
    }
}

// MARK: - Camera Control Overlay
struct CameraControlOverlay: View {
    let onCameraCapture: () -> Void
    let onPhotoLibrary: () -> Void
    let hasSelectedImage: Bool

    var body: some View {
        VStack {
            Spacer()

            HStack {
                // Photo library button
                Button(action: onPhotoLibrary) {
                    Image(systemName: "photo.on.rectangle")
                        .font(.title2)
                        .foregroundStyle(.white)
                        .frame(width: 50, height: 50)
                        .background(.regularMaterial, in: Circle())
                }

                Spacer()

                // Main capture button
                CameraCaptureButton(action: onCameraCapture)

                Spacer()

                // Flash toggle or settings
                Button(action: {}) {
                    Image(systemName: "bolt.slash")
                        .font(.title2)
                        .foregroundStyle(.white)
                        .frame(width: 50, height: 50)
                        .background(.regularMaterial, in: Circle())
                }
            }
            .padding(.horizontal, 40)
            .padding(.bottom, 50)
        }
    }
}

// MARK: - Receipt Guidelines Overlay
struct ReceiptGuidelinesOverlay: View {
    @State private var showGuidelines = true

    var body: some View {
        if showGuidelines {
            VStack {
                HStack {
                    Spacer()
                    Button(action: { showGuidelines = false }) {
                        Image(systemName: "xmark")
                            .font(.title3)
                            .foregroundStyle(.white)
                            .frame(width: 30, height: 30)
                            .background(.regularMaterial, in: Circle())
                    }
                    .padding()
                }

                Spacer()

                VStack(spacing: 12) {
                    Image(systemName: "doc.text.viewfinder")
                        .font(.largeTitle)
                        .foregroundStyle(.blue)

                    Text("Position receipt in center")
                        .font(.headline)
                        .fontWeight(.medium)

                    Text("Ensure good lighting and all text is visible")
                        .font(.subheadline)
                        .multilineTextAlignment(.center)
                        .foregroundStyle(.secondary)
                }
                .glassCard()
                .padding()

                Spacer()
            }
            .transition(.opacity.combined(with: .scale))
        }
    }
}
