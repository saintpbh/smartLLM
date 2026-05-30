import WidgetKit
import SwiftUI
import Foundation

// MARK: - 위젯이 localhost HTTP로 데이터를 읽음 (샌드박스에서 유일하게 작동하는 방법)
private let kDataURL = "http://localhost:18923/widget_data.json"

// MARK: - Codable Models
struct WidgetLessonData: Codable, Identifiable {
    var id: String { filename }
    let filename: String
    let title: String
    let timestamp: Double
    let tags: [String]

    var date: Date { Date(timeIntervalSince1970: timestamp) }
}

struct WidgetSyncData: Codable {
    let totalFiles: Int
    let totalLessons: Int
    let newLessonsCount: Int
    let lessons: [WidgetLessonData]
    let lastUpdated: Double
}

// MARK: - Timeline Entry
struct SmartLLMEntry: TimelineEntry {
    let date: Date
    let totalFiles: Int
    let totalLessons: Int
    let newLessonsCount: Int
    let latestLessons: [WidgetLessonData]
    let isActive: Bool
}

// MARK: - HTTP-Based Timeline Provider
struct SmartLLMProvider: TimelineProvider {
    func placeholder(in context: Context) -> SmartLLMEntry {
        SmartLLMEntry(date: .now, totalFiles: 0, totalLessons: 0,
                      newLessonsCount: 0, latestLessons: [], isActive: false)
    }

    func getSnapshot(in context: Context, completion: @escaping (SmartLLMEntry) -> Void) {
        fetchData { entry in
            completion(entry)
        }
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<SmartLLMEntry>) -> Void) {
        fetchData { entry in
            let nextUpdate = Calendar.current.date(byAdding: .minute, value: 5, to: .now)!
            completion(Timeline(entries: [entry], policy: .after(nextUpdate)))
        }
    }

    private func fetchData(completion: @escaping (SmartLLMEntry) -> Void) {
        guard let url = URL(string: kDataURL) else {
            completion(defaultEntry())
            return
        }

        let request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 3)
        URLSession.shared.dataTask(with: request) { data, response, error in
            guard let data = data,
                  let sync = try? JSONDecoder().decode(WidgetSyncData.self, from: data) else {
                completion(defaultEntry())
                return
            }

            let isActive = (Date().timeIntervalSince1970 - sync.lastUpdated) < 3600
            let entry = SmartLLMEntry(
                date: .now,
                totalFiles: sync.totalFiles,
                totalLessons: sync.totalLessons,
                newLessonsCount: sync.newLessonsCount,
                latestLessons: Array(sync.lessons.prefix(3)),
                isActive: isActive
            )
            completion(entry)
        }.resume()
    }

    private func defaultEntry() -> SmartLLMEntry {
        SmartLLMEntry(date: .now, totalFiles: 0, totalLessons: 0,
                      newLessonsCount: 0, latestLessons: [], isActive: false)
    }
}

// MARK: - Small Widget View
struct SmartLLMSmallView: View {
    var entry: SmartLLMEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(alignment: .top) {
                HStack(spacing: 4) {
                    Text("🧠").font(.system(size: 13))
                    Text("SMART LLM")
                        .font(.system(size: 11, weight: .heavy, design: .rounded))
                        .foregroundStyle(.white)
                }
                Spacer()
                if entry.newLessonsCount > 0 {
                    Text("\(entry.newLessonsCount)")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.white)
                        .frame(width: 18, height: 18)
                        .background(Circle().fill(.red))
                        .shadow(color: .red.opacity(0.6), radius: 4)
                } else {
                    Circle()
                        .fill(entry.isActive ? .green : .gray)
                        .frame(width: 7, height: 7)
                        .shadow(color: entry.isActive ? .green : .clear, radius: 3)
                }
            }

            Text("COGNITIVE LEDGER")
                .font(.system(size: 7, weight: .semibold, design: .monospaced))
                .foregroundStyle(.secondary)

            Spacer(minLength: 2)

            HStack(spacing: 0) {
                VStack(alignment: .leading, spacing: 1) {
                    Text("FILES").font(.system(size: 7, weight: .bold)).foregroundStyle(.secondary)
                    Text("\(entry.totalFiles)")
                        .font(.system(.title2, design: .rounded)).bold().foregroundStyle(.white)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 1) {
                    Text("KNOWLEDGE").font(.system(size: 7, weight: .bold)).foregroundStyle(.secondary)
                    Text("\(entry.totalLessons)")
                        .font(.system(.title2, design: .rounded)).bold()
                        .foregroundStyle(LinearGradient(colors: [.blue, .purple], startPoint: .leading, endPoint: .trailing))
                }
            }

            Spacer(minLength: 2)

            if entry.newLessonsCount > 0 {
                HStack(spacing: 3) {
                    Image(systemName: "sparkles").font(.system(size: 8)).foregroundStyle(.yellow)
                    Text("\(entry.newLessonsCount) new — tap to view")
                        .font(.system(size: 7, weight: .medium)).foregroundStyle(.yellow)
                }
            } else {
                HStack(spacing: 3) {
                    Image(systemName: "checkmark.seal.fill").font(.system(size: 8)).foregroundStyle(.green)
                    Text("All knowledge synced")
                        .font(.system(size: 7, weight: .medium)).foregroundStyle(.secondary)
                }
            }
        }
        .padding(12)
        .widgetURL(URL(string: "smartllm://knowledge"))
    }
}

// MARK: - Medium Widget View
struct SmartLLMMediumView: View {
    var entry: SmartLLMEntry

    private var dateFormatter: DateFormatter {
        let f = DateFormatter()
        f.dateFormat = "MM/dd HH:mm"
        return f
    }

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 4) {
                    Text("🧠").font(.system(size: 13))
                    Text("SMART LLM")
                        .font(.system(size: 11, weight: .heavy, design: .rounded)).foregroundStyle(.white)
                    if entry.newLessonsCount > 0 {
                        Text("\(entry.newLessonsCount)")
                            .font(.system(size: 9, weight: .bold)).foregroundColor(.white)
                            .frame(width: 16, height: 16)
                            .background(Circle().fill(.red))
                    }
                }
                Text("COGNITIVE LEDGER")
                    .font(.system(size: 7, weight: .semibold, design: .monospaced)).foregroundStyle(.secondary)
                Spacer(minLength: 2)
                HStack(spacing: 16) {
                    VStack(alignment: .leading, spacing: 1) {
                        Text("FILES").font(.system(size: 7, weight: .bold)).foregroundStyle(.secondary)
                        Text("\(entry.totalFiles)").font(.system(.title3, design: .rounded)).bold().foregroundStyle(.white)
                    }
                    VStack(alignment: .leading, spacing: 1) {
                        Text("KNOWLEDGE").font(.system(size: 7, weight: .bold)).foregroundStyle(.secondary)
                        Text("\(entry.totalLessons)").font(.system(.title3, design: .rounded)).bold().foregroundStyle(.blue)
                    }
                }
                Spacer(minLength: 2)
                HStack(spacing: 3) {
                    Circle().fill(entry.isActive ? .green : .gray).frame(width: 5, height: 5)
                    Text(entry.isActive ? "Watching" : "Idle").font(.system(size: 7)).foregroundStyle(.secondary)
                }
            }
            Divider().frame(height: 60).background(.white.opacity(0.1))
            VStack(alignment: .leading, spacing: 6) {
                Text("LATEST INSIGHTS")
                    .font(.system(size: 7, weight: .bold, design: .monospaced)).foregroundStyle(.secondary)
                if entry.latestLessons.isEmpty {
                    Spacer()
                    Text("No lessons yet").font(.system(size: 9)).foregroundStyle(.secondary)
                    Spacer()
                } else {
                    ForEach(entry.latestLessons.prefix(3)) { lesson in
                        HStack(alignment: .top, spacing: 4) {
                            Circle().fill(.blue).frame(width: 5, height: 5).offset(y: 3)
                            VStack(alignment: .leading, spacing: 1) {
                                Text(lesson.title)
                                    .font(.system(size: 8, weight: .medium)).foregroundStyle(.white).lineLimit(1)
                                Text(dateFormatter.string(from: lesson.date))
                                    .font(.system(size: 7)).foregroundStyle(.secondary)
                            }
                        }
                    }
                }
                Spacer(minLength: 0)
            }
        }
        .padding(12)
        .widgetURL(URL(string: "smartllm://knowledge"))
    }
}

// MARK: - Widget View Router
struct SmartLLMWidgetView: View {
    var entry: SmartLLMEntry
    @Environment(\.widgetFamily) var family

    var body: some View {
        Group {
            switch family {
            case .systemMedium: SmartLLMMediumView(entry: entry)
            default: SmartLLMSmallView(entry: entry)
            }
        }
        .containerBackground(for: .widget) {
            ZStack {
                Color(red: 18/255, green: 20/255, blue: 30/255)
                RadialGradient(
                    colors: [.blue.opacity(0.10), .purple.opacity(0.06), .clear],
                    center: .topTrailing, startRadius: 0, endRadius: 120
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
        .description("AI 지식 축적 실시간 모니터")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
