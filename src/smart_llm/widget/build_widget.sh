#!/bin/bash
set -e

WORKSPACE_PATH="/Users/bongpark/.gemini/antigravity/scratch/smart-llm"
SRC_DIR="$WORKSPACE_PATH/src/smart_llm/widget"
OUT_DIR="$WORKSPACE_PATH/smart-llm-out"
APP_BUNDLE="$OUT_DIR/SmartLLM.app"

echo "🔨 [SMART LLM] Initializing Native Widget Compilation..."
echo "📂 Workspace: $WORKSPACE_PATH"

# 1. Clean and recreate directories
echo "⚡ Step 1: Cleaning previous bundle builds..."
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"
mkdir -p "$APP_BUNDLE/Contents/PlugIns/SmartLLMWidgetExtension.appex/Contents/MacOS"

# 2. Compile Main App
echo "⚡ Step 2: Compiling SwiftUI Main Hub Application..."
xcrun -sdk macosx swiftc \
  -O \
  -parse-as-library \
  -target arm64-apple-macos14.0 \
  -sdk "$(xcrun --show-sdk-path)" \
  -framework SwiftUI \
  -framework AppKit \
  -o "$APP_BUNDLE/Contents/MacOS/SmartLLM" \
  "$SRC_DIR/SmartLLMApp.swift"

# 3. Replace workspace path and Compile Widget Extension
echo "⚡ Step 3: Compiling SwiftUI WidgetKit Extension..."
sed "s|WORKSPACE_PATH_PLACEHOLDER|$WORKSPACE_PATH|g" "$SRC_DIR/SmartLLMWidget.swift" > "$SRC_DIR/SmartLLMWidget.compiled.swift"

xcrun -sdk macosx swiftc \
  -O \
  -parse-as-library \
  -target arm64-apple-macos14.0 \
  -sdk "$(xcrun --show-sdk-path)" \
  -framework WidgetKit \
  -framework SwiftUI \
  -framework Foundation \
  -o "$APP_BUNDLE/Contents/PlugIns/SmartLLMWidgetExtension.appex/Contents/MacOS/SmartLLMWidgetExtension" \
  "$SRC_DIR/SmartLLMWidget.compiled.swift"

rm -f "$SRC_DIR/SmartLLMWidget.compiled.swift"

# 4. Write PList Configuration metadata
echo "⚡ Step 4: Writing Info.plist configuration metadata..."
cp "$SRC_DIR/Info.plist" "$APP_BUNDLE/Contents/Info.plist"
cp "$SRC_DIR/Info-Widget.plist" "$APP_BUNDLE/Contents/PlugIns/SmartLLMWidgetExtension.appex/Contents/Info.plist"

# 5. Codesign the entire bundle with Sandbox entitlements (Mandatory for WidgetKit)
echo "⚡ Step 5: Performing secure codesigning with Sandbox entitlements..."
codesign --force --sign - --entitlements "$SRC_DIR/Widget.entitlements" --options runtime "$APP_BUNDLE/Contents/PlugIns/SmartLLMWidgetExtension.appex"
codesign --force --sign - --entitlements "$SRC_DIR/App.entitlements" --options runtime "$APP_BUNDLE"

# 6. Deploy to system Applications and User Applications
echo "⚡ Step 6: Deploying SmartLLM.app to System and User Applications directories..."
mkdir -p ~/Applications
rm -rf ~/Applications/SmartLLM.app
cp -R "$APP_BUNDLE" ~/Applications/

# Copy to system /Applications if possible (for maximum reliability of WidgetKit scan)
rm -rf /Applications/SmartLLM.app
cp -R "$APP_BUNDLE" /Applications/ || echo "⚠️ Could not write to system /Applications, using user applications."

# 7. PlugInKit registration
echo "⚡ Step 7: Registering WidgetKit Extension in macOS System Services..."
pluginkit -a ~/Applications/SmartLLM.app/Contents/PlugIns/SmartLLMWidgetExtension.appex
pluginkit -a /Applications/SmartLLM.app/Contents/PlugIns/SmartLLMWidgetExtension.appex || true

echo "🚀 [SMART LLM] Build and Deployment complete! Native macOS Widget App Bundle registered successfully."
echo "📂 System Location: /Applications/SmartLLM.app"
echo "📂 User Location: ~/Applications/SmartLLM.app"
