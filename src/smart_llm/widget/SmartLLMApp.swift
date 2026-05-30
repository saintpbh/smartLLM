import SwiftUI
import AppKit

@main
struct SmartLLMApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .windowStyle(.hiddenTitleBar)
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Center the window on the screen
        if let window = NSApplication.shared.windows.first {
            window.title = "SMART LLM Widget Hub"
            window.isMovableByWindowBackground = true
            window.titlebarAppearsTransparent = true
            window.standardWindowButton(.zoomButton)?.isHidden = true
            window.center()
        }
    }
    
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}

struct ContentView: View {
    var body: some View {
        VStack(spacing: 24) {
            // Top Accent Graphic
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [Color.blue.opacity(0.8), Color.purple.opacity(0.8)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 80, height: 80)
                    .blur(radius: 8)
                
                Image(systemName: "cpu.fill")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 40, height: 40)
                    .foregroundColor(.white)
            }
            .padding(.top, 10)
            
            VStack(spacing: 6) {
                Text("SMART LLM Widget Hub")
                    .font(.system(.title, design: .rounded))
                    .fontWeight(.bold)
                    .foregroundColor(.white)
                
                Text("macOS Tahoe Native Widget Registered")
                    .font(.subheadline)
                    .foregroundColor(.gray)
            }
            
            // Instruction Box
            VStack(alignment: .leading, spacing: 12) {
                Text("How to add this widget to your Desktop:")
                    .font(.headline)
                    .foregroundColor(.blue)
                
                HStack(alignment: .top, spacing: 8) {
                    Text("1.")
                        .font(.body)
                        .bold()
                        .foregroundColor(.blue)
                    Text("Right-click anywhere on your desktop and select **Edit Widgets...** (or click the date/time in your top Menu Bar and select Edit Widgets at the very bottom).")
                }
                
                HStack(alignment: .top, spacing: 8) {
                    Text("2.")
                        .font(.body)
                        .bold()
                        .foregroundColor(.blue)
                    Text("Search for **SMART LLM** in the Widget Gallery list on the left side.")
                }
                
                HStack(alignment: .top, spacing: 8) {
                    Text("3.")
                        .font(.body)
                        .bold()
                        .foregroundColor(.blue)
                    Text("Select the small or medium size and drag it directly to your Desktop or Notification Center!")
                }
            }
            .font(.system(.body, design: .rounded))
            .foregroundColor(.white.opacity(0.9))
            .padding(18)
            .background(Color.white.opacity(0.06))
            .cornerRadius(16)
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(Color.white.opacity(0.1), lineWidth: 1)
            )
            
            HStack(spacing: 16) {
                Button(action: {
                    // Open Widget Gallery programmatically on macOS Sonoma/Sequoia/Tahoe if possible
                    // Widget gallery can be opened via standard AppleScript or open command triggers
                    let script = "tell application \"System Events\" to click menu bar item 1 of menu bar 2 of application process \"ControlCenter\""
                    if let appleScript = NSAppleScript(source: script) {
                        var error: NSDictionary?
                        appleScript.executeAndReturnError(&error)
                    }
                }) {
                    HStack {
                        Image(systemName: "plus.circle.fill")
                        Text("Add Widget Guide")
                            .fontWeight(.semibold)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                }
                .buttonStyle(.borderedProminent)
                .accentColor(.blue)
                
                Button(action: {
                    NSApplication.shared.terminate(nil)
                }) {
                    Text("Close Hub")
                        .fontWeight(.medium)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                }
                .buttonStyle(.bordered)
            }
        }
        .padding(32)
        .frame(width: 520, height: 460)
        .background(
            ZStack {
                Color(red: 21/255, green: 23/255, blue: 33/255)
                
                // Beautiful ambient glow
                RadialGradient(
                    gradient: Gradient(colors: [
                        Color.blue.opacity(0.12),
                        Color.purple.opacity(0.05),
                        Color.clear
                    ]),
                    center: .center,
                    startRadius: 0,
                    endRadius: 280
                )
            }
        )
        .preferredColorScheme(.dark)
    }
}
