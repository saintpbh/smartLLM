import WidgetKit
import SwiftUI
import Foundation

// MARK: - Configuration — 모든 데이터를 로컬 파일에서 직접 읽음 (서버 불필요)
// ⚠️ 샌드박스 환경에서 ~(tilde)는 컨테이너 경로로 리다이렉트됨.
//    getpwuid()로 실제 홈 디렉토리(/Users/username)를 얻어야 함.
import Darwin

private enum Config {
    static let realHome: String = {
        if let pw = getpwuid(getuid()), let dir = pw.pointee.pw_dir {
            return String(cString: dir)
        }
        return "/Users/\(NSUserName())"
    }()
    static let workspacePath: String = realHome + "/.gemini/antigravity/scratch/smart-llm"
    static var lessonsDir: String { workspacePath + "/lessons" }
    static var indexPath: String { workspacePath + "/smart-llm-out/index.json" }
    static var graphPath: String { workspacePath + "/smart-llm-out/graph.json" }
    static var lastSeenPath: String { workspacePath + "/.widget_last_seen" }
    static var agentsPath: String { workspacePath + "/AGENTS.md" }
}


// MARK: - Lesson Model
struct LessonInfo: Identifiable, Codable {
    var id: String { filename }
    let filename: String
    let title: String
    let timestamp: Double
    let tags: [String]

    var date: Date { Date(timeIntervalSince1970: timestamp) }
}

// MARK: - Timeline Entry
struct SmartLLMEntry: TimelineEntry {
    let date: Date
    let totalFiles: Int
    let totalLessons: Int
    let newLessonsCount: Int
    let latestLessons: [LessonInfo]
    let isActive: Bool
}

// MARK: - File-Based Timeline Provider (서버 의존성 제거)
struct SmartLLMProvider: TimelineProvider {
    func placeholder(in context: Context) -> SmartLLMEntry {
        SmartLLMEntry(date: .now, totalFiles: 0, totalLessons: 0,
                      newLessonsCount: 0, latestLessons: [], isActive: false)
    }

    func getSnapshot(in context: Context, completion: @escaping (SmartLLMEntry) -> Void) {
        completion(readLocalData())
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<SmartLLMEntry>) -> Void) {
        let entry = readLocalData()
        // 5분마다 자동 갱신
        let nextUpdate = Calendar.current.date(byAdding: .minute, value: 5, to: .now)!
        completion(Timeline(entries: [entry], policy: .after(nextUpdate)))
    }

    // MARK: - 로컬 파일에서 모든 데이터를 직접 읽음
    private func readLocalData() -> SmartLLMEntry {
        let totalFiles = readTotalFiles()
        let lessons = readLessons()
        let lastSeen = readLastSeenDate()
        let newLessons = lessons.filter { $0.date > lastSeen }

        let isActive: Bool = {
            let fm = FileManager.default
            guard let attrs = try? fm.attributesOfItem(atPath: Config.agentsPath),
                  let modDate = attrs[.modificationDate] as? Date else { return false }
            return modDate.timeIntervalSinceNow > -3600 // 1시간 이내 갱신이면 active
        }()

        return SmartLLMEntry(
            date: .now,
            totalFiles: totalFiles,
            totalLessons: lessons.count,
            newLessonsCount: newLessons.count,
            latestLessons: Array(lessons.prefix(3)),
            isActive: isActive
        )
    }

    private func readTotalFiles() -> Int {
        // index.json → doc_map 키 수
        if let data = try? Data(contentsOf: URL(fileURLWithPath: Config.indexPath)),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let docMap = json["doc_map"] as? [String: Any] {
            return docMap.count
        }
        // Fallback: graph.json
        if let data = try? Data(contentsOf: URL(fileURLWithPath: Config.graphPath)),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let nodes = json["nodes"] as? [[String: Any]] {
            return nodes.count
        }
        return 0
    }

    private func readLessons() -> [LessonInfo] {
        let fm = FileManager.default
        guard let files = try? fm.contentsOfDirectory(atPath: Config.lessonsDir) else { return [] }

        return files
            .filter { $0.hasSuffix(".md") }
            .compactMap { filename -> LessonInfo? in
                let path = Config.lessonsDir + "/" + filename
                guard let attrs = try? fm.attributesOfItem(atPath: path),
                      let modDate = attrs[.modificationDate] as? Date else { return nil }

                let title = parseTitle(from: path)
                let tags = parseTags(from: path)

                return LessonInfo(
                    filename: filename,
                    title: title,
                    timestamp: modDate.timeIntervalSince1970,
                    tags: tags
                )
            }
            .sorted { $0.timestamp > $1.timestamp }
    }

    private func parseTitle(from path: String) -> String {
        guard let data = try? Data(contentsOf: URL(fileURLWithPath: path)),
              let content = String(data: data, encoding: .utf8) else {
            return "Unknown Lesson"
        }
        let firstLine = content.components(separatedBy: .newlines).first ?? ""
        return firstLine
            .replacingOccurrences(of: "# Lesson Learned: ", with: "")
            .replacingOccurrences(of: "# ", with: "")
            .trimmingCharacters(in: .whitespaces)
    }

    private func parseTags(from path: String) -> [String] {
        guard let data = try? Data(contentsOf: URL(fileURLWithPath: path)),
              let content = String(data: data, encoding: .utf8) else { return [] }
        for line in content.components(separatedBy: .newlines) {
            if line.contains("Context/Tags") {
                return line.components(separatedBy: "`")
                    .enumerated()
                    .filter { $0.offset % 2 == 1 }
                    .map { $0.element }
            }
        }
        return []
    }

    private func readLastSeenDate() -> Date {
        guard let content = try? String(contentsOfFile: Config.lastSeenPath, encoding: .utf8)
                .trimmingCharacters(in: .whitespacesAndNewlines),
              let ts = Double(content) else {
            return Date.distantPast
        }
        return Date(timeIntervalSince1970: ts)
    }
}

// MARK: - Widget Views

struct SmartLLMSmallView: View {
    var entry: SmartLLMEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            // Header + Badge
            HStack(alignment: .top) {
                HStack(spacing: 4) {
                    Text("🧠")
                        .font(.system(size: 13))
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

            // Metrics
            HStack(spacing: 0) {
                VStack(alignment: .leading, spacing: 1) {
                    Text("FILES")
                        .font(.system(size: 7, weight: .bold))
                        .foregroundStyle(.secondary)
                    Text("\(entry.totalFiles)")
                        .font(.system(.title2, design: .rounded))
                        .bold()
                        .foregroundStyle(.white)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 1) {
                    Text("KNOWLEDGE")
                        .font(.system(size: 7, weight: .bold))
                        .foregroundStyle(.secondary)
                    Text("\(entry.totalLessons)")
                        .font(.system(.title2, design: .rounded))
                        .bold()
                        .foregroundStyle(
                            LinearGradient(colors: [.blue, .purple], startPoint: .leading, endPoint: .trailing)
                        )
                }
            }

            Spacer(minLength: 2)

            // Status
            if entry.newLessonsCount > 0 {
                HStack(spacing: 3) {
                    Image(systemName: "sparkles")
                        .font(.system(size: 8))
                        .foregroundStyle(.yellow)
                    Text("\(entry.newLessonsCount) new insight\(entry.newLessonsCount > 1 ? "s" : "") — tap to view")
                        .font(.system(size: 7, weight: .medium))
                        .foregroundStyle(.yellow)
                }
            } else {
                HStack(spacing: 3) {
                    Image(systemName: "checkmark.seal.fill")
                        .font(.system(size: 8))
                        .foregroundStyle(.green)
                    Text("All knowledge synced")
                        .font(.system(size: 7, weight: .medium))
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(12)
        .widgetURL(URL(string: "smartllm://knowledge"))
    }
}

struct SmartLLMMediumView: View {
    var entry: SmartLLMEntry

    private var dateFormatter: DateFormatter {
        let f = DateFormatter()
        f.dateFormat = "MM/dd HH:mm"
        return f
    }

    var body: some View {
        HStack(spacing: 12) {
            // Left: Metrics
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 4) {
                    Text("🧠")
                        .font(.system(size: 13))
                    Text("SMART LLM")
                        .font(.system(size: 11, weight: .heavy, design: .rounded))
                        .foregroundStyle(.white)
                    if entry.newLessonsCount > 0 {
                        Text("\(entry.newLessonsCount)")
                            .font(.system(size: 9, weight: .bold))
                            .foregroundColor(.white)
                            .frame(width: 16, height: 16)
                            .background(Circle().fill(.red))
                            .shadow(color: .red.opacity(0.6), radius: 3)
                    }
                }

                Text("COGNITIVE LEDGER")
                    .font(.system(size: 7, weight: .semibold, design: .monospaced))
                    .foregroundStyle(.secondary)

                Spacer(minLength: 2)

                HStack(spacing: 16) {
                    VStack(alignment: .leading, spacing: 1) {
                        Text("FILES")
                            .font(.system(size: 7, weight: .bold))
                            .foregroundStyle(.secondary)
                        Text("\(entry.totalFiles)")
                            .font(.system(.title3, design: .rounded))
                            .bold()
                            .foregroundStyle(.white)
                    }
                    VStack(alignment: .leading, spacing: 1) {
                        Text("KNOWLEDGE")
                            .font(.system(size: 7, weight: .bold))
                            .foregroundStyle(.secondary)
                        Text("\(entry.totalLessons)")
                            .font(.system(.title3, design: .rounded))
                            .bold()
                            .foregroundStyle(.blue)
                    }
                }

                Spacer(minLength: 2)

                // Status
                HStack(spacing: 3) {
                    Circle()
                        .fill(entry.isActive ? .green : .gray)
                        .frame(width: 5, height: 5)
                    Text(entry.isActive ? "Watching" : "Idle")
                        .font(.system(size: 7))
                        .foregroundStyle(.secondary)
                }
            }

            Divider()
                .frame(height: 60)
                .background(.white.opacity(0.1))

            // Right: Latest Lessons
            VStack(alignment: .leading, spacing: 6) {
                Text("LATEST INSIGHTS")
                    .font(.system(size: 7, weight: .bold, design: .monospaced))
                    .foregroundStyle(.secondary)

                if entry.latestLessons.isEmpty {
                    Spacer()
                    Text("No lessons yet")
                        .font(.system(size: 9))
                        .foregroundStyle(.secondary)
                    Spacer()
                } else {
                    ForEach(entry.latestLessons.prefix(3)) { lesson in
                        HStack(alignment: .top, spacing: 4) {
                            // New indicator
                            if lesson.date > (Calendar.current.date(byAdding: .hour, value: -24, to: .now) ?? .now) {
                                Circle()
                                    .fill(.blue)
                                    .frame(width: 5, height: 5)
                                    .offset(y: 3)
                            } else {
                                Circle()
                                    .fill(.clear)
                                    .frame(width: 5, height: 5)
                            }

                            VStack(alignment: .leading, spacing: 1) {
                                Text(lesson.title)
                                    .font(.system(size: 8, weight: .medium))
                                    .foregroundStyle(.white)
                                    .lineLimit(1)
                                Text(dateFormatter.string(from: lesson.date))
                                    .font(.system(size: 7))
                                    .foregroundStyle(.secondary)
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

// MARK: - Main Widget View Router
struct SmartLLMWidgetView: View {
    var entry: SmartLLMEntry
    @Environment(\.widgetFamily) var family

    var body: some View {
        Group {
            switch family {
            case .systemMedium:
                SmartLLMMediumView(entry: entry)
            default:
                SmartLLMSmallView(entry: entry)
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
        .description("AI 지식 축적 실시간 모니터 — 서버 불필요, 로컬 파일 직접 읽기")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
