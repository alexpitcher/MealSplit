# MealSplit iOS App

A premium SwiftUI app with liquid glass design that makes receipt splitting feel effortless.

## Features

### 🔸 Liquid Glass Design System
- Full-screen glassy backgrounds with `LiquidGlassBackground()`
- Glass card containers with `.glassCard()` modifier
- Material accent elements with `.regularMaterial`
- Glass-styled interactions with `.buttonStyle(.glass)`

### 📱 Core Functionality
- **Receipt Capture**: Camera integration with PhotosUI picker
- **OCR Processing**: Backend integration for text extraction
- **Ingredient Matching**: Smart matching with confidence scoring
- **Settlement Calculation**: Weekly expense splitting and balancing
- **Splitwise Integration**: Automatic expense creation

## Project Structure

```
MealSplit/
├── Views/
│   ├── Receipts/
│   │   ├── CameraView.swift          # Camera capture with glass UI
│   │   └── MatchReviewView.swift     # Match confirmation interface
│   ├── Settlements/
│   │   └── SettlementView.swift      # Weekly settlement breakdown
│   └── Shared/
│       ├── EmptyStateView.swift      # Reusable empty states
│       └── HapticManager.swift       # Haptic feedback utilities
├── DesignSystem/
│   ├── LiquidGlass.swift            # Core glass components
│   └── GlassCard.swift              # Reusable card components
├── Models/
│   └── Receipt.swift                # Data models and API types
├── Services/
│   ├── APIService.swift             # Backend integration
│   └── CameraService.swift          # Camera and permissions
├── MealSplitApp.swift              # App entry point
├── ContentView.swift               # Main tab navigation
└── Info.plist                     # App configuration
```

## Design System Usage

### Backgrounds
```swift
ZStack {
    LiquidGlassBackground()
    // Your content here
}
```

### Glass Cards
```swift
VStack {
    // Content
}
.glassCard()
```

### Glass Buttons
```swift
Button("Action") {
    // Handle action
}
.buttonStyle(.glass)
```

### Status Indicators
```swift
GlassStatusChip(text: "Confidence: 85%", color: .green)
```

## Setup Instructions

### 1. Backend Configuration
Use the in-app setup wizard on first launch to configure your server URL, optional insecure TLS, and preferences. No code changes required.

### 2. Camera Permissions
The app requests camera and photo library permissions automatically. Ensure your Info.plist includes:
- `NSCameraUsageDescription`
- `NSPhotoLibraryUsageDescription`

### 3. Dependencies
This project uses only native iOS frameworks:
- SwiftUI
- UIKit
- AVFoundation
- Photos

## Key Components

### LiquidGlassBackground
Creates the signature glass morphism background with animated orbs and material layers.

### GlassCard
Provides consistent glass card styling with proper shadows and material effects.

### APIService
Handles all backend communication with proper error handling and loading states.

### CameraService
Manages camera permissions and photo capture with native iOS integration.

## Testing

Connect the app to a running MealSplit backend using the setup wizard. The app avoids mock data in production flows and will inform you via errors if the server is unavailable. Enable offline caching in the wizard to browse recent data when offline.

## Performance Considerations

- Lazy loading for long lists
- Image compression before upload
- Background processing for OCR
- Efficient glass effect rendering
- Haptic feedback for premium feel

## Accessibility

The glass design system maintains proper contrast ratios and supports:
- VoiceOver navigation
- Dynamic Type scaling
- High contrast mode
- Reduced motion preferences

## Build Requirements

- iOS 16.0+
- Xcode 15.0+
- Swift 5.9+

## Glass Design Guidelines

1. **Consistency**: Every screen uses `LiquidGlassBackground()`
2. **Hierarchy**: Content wrapped in `.glassCard()` containers
3. **Interactions**: All buttons use `.buttonStyle(.glass)`
4. **Feedback**: Material accents for status and progress
5. **Performance**: Glass effects optimized for older devices

## Future Enhancements

- [ ] Custom camera overlay with manual controls
- [ ] Offline receipt storage and sync
- [ ] Group management and invitations
- [ ] Advanced ingredient database search
- [ ] Receipt history and analytics
- [ ] Export to other expense apps

The visual polish of the glass design system makes testing more enjoyable and helps spot UX issues early. The consistent glass aesthetic creates a premium feel that makes daily expense splitting feel effortless.
