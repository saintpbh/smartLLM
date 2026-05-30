import Cocoa
import WebKit

class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    var window: NSWindow!
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Create borderless resizable window
        let mask: NSWindow.StyleMask = [.borderless, .resizable]
        window = NSWindow(
            contentRect: NSRect(x: 100, y: 100, width: 170, height: 170),
            styleMask: mask,
            backing: .buffered,
            defer: false
        )
        
        window.title = "SMART LLM Widget"
        window.isOpaque = false
        window.backgroundColor = .clear
        window.hasShadow = true
        window.level = .floating // Keep floating on desktop
        window.delegate = self
        
        // 1. Native Apple Glassmorphism: NSVisualEffectView
        let visualEffectView = NSVisualEffectView(frame: NSRect(x: 0, y: 0, width: 170, height: 170))
        visualEffectView.autoresizingMask = [.width, .height]
        visualEffectView.material = .hudWindow // iOS-style dark glassmorphism
        visualEffectView.state = .active
        visualEffectView.blendingMode = .behindWindow
        
        // Round corners natively (Mac standard widget radius is 28pt)
        visualEffectView.wantsLayer = true
        visualEffectView.layer?.cornerRadius = 28
        visualEffectView.layer?.masksToBounds = true
        
        // 2. High-performance Native WKWebView pointing to localhost
        let webView = WKWebView(frame: NSRect(x: 0, y: 0, width: 170, height: 170))
        webView.autoresizingMask = [.width, .height]
        webView.setValue(false, forKey: "drawsBackground") // Transparent background inside webview
        
        if let url = URL(string: "http://localhost:8000/widget") {
            let request = URLRequest(url: url)
            webView.load(request)
        }
        
        visualEffectView.addSubview(webView)
        window.contentView = visualEffectView
        
        // Enable dragging from anywhere on the widget
        window.isMovableByWindowBackground = true
        
        window.makeKeyAndOrderFront(nil)
        
        // Hide dock icon to make it a true desktop widget (accessory style)
        NSApp.setActivationPolicy(.accessory)
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
