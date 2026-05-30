import WidgetKit
import SwiftUI
import Foundation

// MARK: - Data Model
struct WidgetStats: Codable {
    let total_files: Int
    let alerts_count: Int
    let active_alert: String
}

// MARK: - Timeline Entry
struct SmartLLMEntry: TimelineEntry {
    let date: Date
    let totalFiles: Int
    let alertsCount: Int
    let activeAlert: String
    let isOnline: Bool
}

// MARK: - Timeline Provider
struct SmartLLMProvider: TimelineProvider {
    func placeholder(in context: Context) -> SmartLLMEntry {
        SmartLLMEntry(date: .now, totalFiles: 0, alertsCount: 0, activeAlert: "Loading...", isOnline: false)
    }

    func getSnapshot(in context: Context, completion: @escaping (SmartLLMEntry) -> Void) {
        fetchData { entry in completion(entry) }
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<SmartLLMEntry>) -> Void) {
        fetchData { entry in
            let next = Calendar.current.date(byAdding: .second, value: 15, to: .now)!
            completion(Timeline(entries: [entry], policy: .after(next)))
        }
    }

    private func fetchData(completion: @escaping (SmartLLMEntry) -> Void) {
        guard let url = URL(string: "http://127.0.0.1:8000/api/widget_stats") else {
            completion(offlineEntry())
            return
        }
        var req = URLRequest(url: url)
        req.timeoutInterval = 2
        URLSession.shared.dataTask(with: req) { data, _, error in
            guard error == nil, let data = data,
                  let stats = try? JSONDecoder().decode(WidgetStats.self, from: data) else {
                completion(offlineEntry())
                return
            }
            completion(SmartLLMEntry(
                date: .now,
                totalFiles: stats.total_files,
                alertsCount: stats.alerts_count,
                activeAlert: stats.active_alert,
                isOnline: true
            ))
        }.resume()
    }

    private func offlineEntry() -> SmartLLMEntry {
        // Fallback: read index.json directly from disk
        let indexPath = NSString(string: "~/.gemini/antigravity/scratch/smart-llm/smart-llm-out/index.json").expandingTildeInPath
        var files = 0
        if let data = try? Data(contentsOf: URL(fileURLWithPath: indexPath)),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let docMap = json["doc_map"] as? [String: Any] {
            files = docMap.count
        }
        return SmartLLMEntry(date: .now, totalFiles: files, alertsCount: 0, activeAlert: "Offline", isOnline: false)
    }
}

// MARK: - Widget View
struct SmartLLMWidgetView: View {
    var entry: SmartLLMEntry
    @Environment(\.widgetFamily) var family

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            // Header
            HStack {
                HStack(spacing: 5) {
                    Text("🧠")
                        .font(.system(size: 14))
                    Text("SMART LLM")
                        .font(.system(size: 12, weight: .bold, design: .rounded))
                        .foregroundStyle(.white)
                }
                Spacer()
                Circle()
                    .fill(entry.isOnline ? .green : .orange)
                    .frame(width: 7, height: 7)
                    .shadow(color: entry.isOnline ? .green : .orange, radius: 3)
            }

            Text("COGNITIVE LEDGER")
                .font(.system(size: 8, weight: .semibold, design: .monospaced))
                .foregroundStyle(.secondary)

            Divider()

            // Metrics
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("FILES")
                        .font(.system(size: 8, weight: .bold))
                        .foregroundStyle(.secondary)
                    Text("\(entry.totalFiles)")
                        .font(.system(.title2, design: .rounded))
                        .bold()
                        .foregroundStyle(.white)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 2) {
                    Text("ALERTS")
                        .font(.system(size: 8, weight: .bold))
                        .foregroundStyle(.secondary)
                    Text("\(entry.alertsCount)")
                        .font(.system(.title2, design: .rounded))
                        .bold()
                        .foregroundStyle(entry.alertsCount > 0 ? .red : .green)
                }
            }

            Spacer(minLength: 0)

            // Status
            if entry.alertsCount > 0 {
                HStack(alignment: .top, spacing: 3) {
                    Text("⚠️").font(.system(size: 9))
                    Text(entry.activeAlert)
                        .font(.system(size: 8, weight: .medium))
                        .foregroundStyle(.yellow)
                        .lineLimit(2)
                }
            } else {
                HStack(spacing: 3) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 9))
                        .foregroundStyle(.green)
                    Text(entry.isOnline ? "All systems synced" : "Offline mode")
                        .font(.system(size: 8))
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(12)
        .containerBackground(for: .widget) {
            ZStack {
                Color(red: 25/255, green: 27/255, blue: 38/255)
                RadialGradient(
                    colors: [.blue.opacity(0.12), .purple.opacity(0.05), .clear],
                    center: .topTrailing, startRadius: 0, endRadius: 100
                )
            }
        }
    }
}

// MARK: - Widget Declaration
@main
struct SmartLLMWidget: Widget {
    let kind = "com.bongpark.SmartLLMWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: SmartLLMProvider()) { entry in
            SmartLLMWidgetView(entry: entry)
        }
        .configurationDisplayName("SMART LLM Monitor")
        .description("실시간 지식 축적 상황 및 제약 위반 경고 모니터링")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
