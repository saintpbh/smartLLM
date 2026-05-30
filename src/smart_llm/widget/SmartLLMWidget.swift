import WidgetKit
import SwiftUI
import Foundation

// Struct to parse JSON response
struct WidgetStats: Codable {
    let total_files: Int
    let alerts_count: Int
    let active_alert: String
}

struct Provider: TimelineProvider {
    typealias Entry = SimpleEntry

    func placeholder(in context: Context) -> SimpleEntry {
        SimpleEntry(date: Date(), totalFiles: 0, alertsCount: 0, activeAlert: "Initializing...", isOnline: false)
    }

    func getSnapshot(in context: Context, completion: @escaping (SimpleEntry) -> ()) {
        fetchLatestData { entry in
            completion(entry)
        }
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<Entry>) -> ()) {
        fetchLatestData { entry in
            let nextUpdate = Calendar.current.date(byAdding: .second, value: 5, to: Date())!
            let timeline = Timeline(entries: [entry], policy: .after(nextUpdate))
            completion(timeline)
        }
    }
    
    private func fetchLatestData(completion: @escaping (SimpleEntry) -> Void) {
        guard let url = URL(string: "http://127.0.0.1:8000/api/widget_stats") else {
            completion(fallbackLocalEntry(status: "URL Error"))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 1.5 // Fast timeout for responsive widget loading
        
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                print("Widget fetch error: \(error.localizedDescription)")
                completion(self.readFromLocalFilesystem(status: "Server Offline"))
                return
            }
            
            guard let data = data else {
                completion(self.readFromLocalFilesystem(status: "No data received"))
                return
            }
            
            do {
                let stats = try JSONDecoder().decode(WidgetStats.self, from: data)
                let entry = SimpleEntry(
                    date: Date(),
                    totalFiles: stats.total_files,
                    alertsCount: stats.alerts_count,
                    activeAlert: stats.active_alert,
                    isOnline: true
                )
                completion(entry)
            } catch {
                print("Widget parse error: \(error)")
                completion(self.readFromLocalFilesystem(status: "Parse error"))
            }
        }
        task.resume()
    }
    
    // File fallback reading directly from the project directory
    private func readFromLocalFilesystem(status: String) -> SimpleEntry {
        let workspacePath = "WORKSPACE_PATH_PLACEHOLDER"
        let indexPath = "\(workspacePath)/smart-llm-out/index.json"
        
        var totalFiles = 0
        
        // 1. Try to read index.json directly to count files
        if let fileData = try? Data(contentsOf: URL(fileURLWithPath: indexPath)) {
            if let json = try? JSONSerialization.jsonObject(with: fileData, options: []) as? [String: Any] {
                if let docMap = json["doc_map"] as? [String: Any] {
                    totalFiles = docMap.count
                }
            }
        }
        
        // 2. Alert fallback
        return SimpleEntry(
            date: Date(),
            totalFiles: totalFiles,
            alertsCount: 0,
            activeAlert: "Offline - Run dashboard server",
            isOnline: false
        )
    }
    
    private func fallbackLocalEntry(status: String) -> SimpleEntry {
        SimpleEntry(
            date: Date(),
            totalFiles: 0,
            alertsCount: 0,
            activeAlert: status,
            isOnline: false
        )
    }
}

struct SimpleEntry: TimelineEntry {
    let date: Date
    let totalFiles: Int
    let alertsCount: Int
    let activeAlert: String
    let isOnline: Bool
}

struct SmartLLMWidgetEntryView : View {
    var entry: Provider.Entry
    
    @Environment(\.widgetFamily) var family

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Header
            HStack {
                HStack(spacing: 6) {
                    Text("🧠")
                        .font(.system(size: 16))
                    Text("SMART LLM")
                        .font(.system(.subheadline, design: .rounded))
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                }
                Spacer()
                
                // Status Beacon
                HStack(spacing: 4) {
                    Circle()
                        .fill(entry.isOnline ? Color.green : Color.orange)
                        .frame(width: 8, height: 8)
                        .shadow(color: entry.isOnline ? .green : .orange, radius: 3)
                    
                    if entry.alertsCount > 0 {
                        Circle()
                            .fill(Color.red)
                            .frame(width: 8, height: 8)
                            .shadow(color: .red, radius: 3)
                    }
                }
            }
            
            Text("COGNITIVE LEDGER")
                .font(.system(size: 9, weight: .semibold, design: .monospaced))
                .foregroundColor(.gray)
            
            Divider()
                .background(Color.white.opacity(0.15))
            
            // Grid Metrics
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("FILES")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundColor(.gray)
                    Text("\(entry.totalFiles)")
                        .font(.system(.title2, design: .rounded))
                        .bold()
                        .foregroundColor(.white)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 2) {
                    Text("ALERTS")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundColor(.gray)
                    Text("\(entry.alertsCount)")
                        .font(.system(.title2, design: .rounded))
                        .bold()
                        .foregroundColor(entry.alertsCount > 0 ? .red : .green)
                }
            }
            .padding(.vertical, 2)
            
            // Status Line / Active Alert
            VStack(alignment: .leading) {
                if entry.alertsCount > 0 {
                    HStack(alignment: .top, spacing: 4) {
                        Text("⚠️")
                            .font(.system(size: 10))
                        Text(entry.activeAlert)
                            .font(.system(size: 9, weight: .medium))
                            .foregroundColor(.yellow)
                            .lineLimit(family == .systemSmall ? 2 : 3)
                    }
                } else {
                    HStack(spacing: 4) {
                        Text("✓")
                            .font(.system(size: 10))
                            .foregroundColor(.green)
                        Text(entry.isOnline ? "All systems synced & healthy" : "Running offline mode")
                            .font(.system(size: 9))
                            .foregroundColor(.gray)
                    }
                }
            }
            .frame(maxHeight: .infinity, alignment: .bottom)
        }
        .padding(14)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .containerBackground(for: .widget) {
            ZStack {
                // Glassmorphism styling background
                Color(red: 25/255, green: 27/255, blue: 38/255)
                
                // Top highlighted gradient bubble
                RadialGradient(
                    gradient: Gradient(colors: [
                        Color.blue.opacity(0.15),
                        Color.purple.opacity(0.05),
                        Color.clear
                    ]),
                    center: .topTrailing,
                    startRadius: 0,
                    endRadius: 100
                )
            }
        }
    }
}

@main
struct SmartLLMWidget: Widget {
    let kind: String = "com.bongpark.smartllm.Widget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: Provider()) { entry in
            SmartLLMWidgetEntryView(entry: entry)
        }
        .configurationDisplayName("SMART LLM Monitor")
        .description("Real-time cognitive ledger files and rule constraint status.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
