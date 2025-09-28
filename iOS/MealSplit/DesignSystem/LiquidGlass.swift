import SwiftUI

// MARK: - Liquid Glass Background
struct LiquidGlassBackground: View {
    var body: some View {
        ZStack {
            // Base gradient background
            LinearGradient(
                gradient: Gradient(colors: [
                    Color.black.opacity(0.8),
                    Color.blue.opacity(0.3),
                    Color.purple.opacity(0.2)
                ]),
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            // Animated glass orbs
            ForEach(0..<3, id: \.self) { index in
                Circle()
                    .fill(
                        RadialGradient(
                            gradient: Gradient(colors: [
                                Color.white.opacity(0.1),
                                Color.clear
                            ]),
                            center: .center,
                            startRadius: 0,
                            endRadius: 100
                        )
                    )
                    .frame(width: 200, height: 200)
                    .blur(radius: 20)
                    .offset(
                        x: CGFloat(index * 100 - 100),
                        y: CGFloat(index * 80 - 120)
                    )
                    .animation(
                        Animation.easeInOut(duration: Double(3 + index))
                            .repeatForever(autoreverses: true),
                        value: index
                    )
            }

            // Ultra thin material overlay
            Rectangle()
                .fill(.ultraThinMaterial)
        }
        .ignoresSafeArea()
    }
}

// MARK: - Glass Card Modifier
extension View {
    func glassCard(padding: CGFloat = 16) -> some View {
        self
            .padding(padding)
            .background {
                RoundedRectangle(cornerRadius: 16)
                    .fill(.ultraThinMaterial)
                    .overlay {
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(.white.opacity(0.2), lineWidth: 1)
                    }
                    .shadow(color: .black.opacity(0.3), radius: 10, x: 0, y: 5)
            }
    }

    func pressableGlassCard(isPressed: Bool = false) -> some View {
        self
            .glassCard()
            .scaleEffect(isPressed ? 0.98 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: isPressed)
    }
}

// MARK: - Glass Button Style
struct GlassButtonStyle: ButtonStyle {
    var isDestructive: Bool = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.body)
            .fontWeight(.medium)
            .foregroundStyle(isDestructive ? .red : .primary)
            .padding(.horizontal, 20)
            .padding(.vertical, 12)
            .background {
                RoundedRectangle(cornerRadius: 12)
                    .fill(.regularMaterial)
                    .overlay {
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(.white.opacity(0.3), lineWidth: 1)
                    }
            }
            .scaleEffect(configuration.isPressed ? 0.96 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

extension ButtonStyle where Self == GlassButtonStyle {
    static var glass: GlassButtonStyle { GlassButtonStyle() }
    static var destructiveGlass: GlassButtonStyle { GlassButtonStyle(isDestructive: true) }
}

// MARK: - Glass Progress View
struct GlassProgressView: View {
    let progress: Double
    let title: String

    var body: some View {
        VStack(spacing: 12) {
            Text(title)
                .font(.subheadline)
                .fontWeight(.medium)

            ProgressView(value: progress)
                .progressViewStyle(GlassProgressViewStyle())
        }
        .glassCard()
    }
}

struct GlassProgressViewStyle: ProgressViewStyle {
    func makeBody(configuration: Configuration) -> some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                RoundedRectangle(cornerRadius: 4)
                    .fill(.ultraThinMaterial)
                    .frame(height: 8)

                RoundedRectangle(cornerRadius: 4)
                    .fill(
                        LinearGradient(
                            gradient: Gradient(colors: [.blue, .purple]),
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .frame(
                        width: geometry.size.width * CGFloat(configuration.fractionCompleted ?? 0),
                        height: 8
                    )
                    .animation(.easeInOut, value: configuration.fractionCompleted)
            }
        }
        .frame(height: 8)
    }
}

// MARK: - Glass Status Chip
struct GlassStatusChip: View {
    let text: String
    let color: Color

    var body: some View {
        Text(text)
            .font(.caption)
            .fontWeight(.medium)
            .padding(.horizontal, 12)
            .padding(.vertical, 4)
            .background(.regularMaterial, in: Capsule())
            .overlay {
                Capsule()
                    .stroke(color.opacity(0.6), lineWidth: 1)
            }
            .foregroundStyle(color)
    }
}

// MARK: - Glass Loading Overlay
struct GlassLoadingOverlay: View {
    let message: String

    var body: some View {
        ZStack {
            Color.black.opacity(0.4)
                .ignoresSafeArea()

            VStack(spacing: 16) {
                ProgressView()
                    .scaleEffect(1.2)
                    .tint(.white)

                Text(message)
                    .font(.body)
                    .fontWeight(.medium)
                    .multilineTextAlignment(.center)
            }
            .glassCard()
            .frame(maxWidth: 280)
        }
    }
}