import SwiftUI
import AppKit
import WidgetKit

// MARK: - Shared Codable (Widget과 동일 구조)
struct WidgetLessonSync: Codable {
    let filename: String
    let title: String
    let timestamp: Double
    let tags: [String]
}

struct WidgetSyncPayload: Codable {
    let totalFiles: Int
    let totalLessons: Int
    let newLessonsCount: Int
    let lessons: [WidgetLessonSync]
    let lastUpdated: Double
}

// MARK: - App Group Container에 데이터 동기화
private let kGroupID = "group.com.bongpark.SmartLLM"

func syncDataToWidget() {
    let home = NSHomeDirectory()
    let workspacePath = home + "/.gemini/antigravity/scratch/smart-llm"
    let lessonsDir = workspacePath + "/lessons"
    let indexPath = workspacePath + "/smart-llm-out/index.json"
    let lastSeenPath = workspacePath + "/.widget_last_seen"

    let fm = FileManager.default

    // 1. 파일 수 읽기
    var totalFiles = 0
    if let data = try? Data(contentsOf: URL(fileURLWithPath: indexPath)),
       let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
       let docMap = json["doc_map"] as? [String: Any] {
        totalFiles = docMap.count
    }

    // 2. Lessons 읽기
    var lessons: [WidgetLessonSync] = []
    if let files = try? fm.contentsOfDirectory(atPath: lessonsDir) {
        for file in files where file.hasSuffix(".md") {
            let path = lessonsDir + "/" + file
            guard let attrs = try? fm.attributesOfItem(atPath: path),
                  let modDate = attrs[.modificationDate] as? Date,
                  let content = try? String(contentsOfFile: path, encoding: .utf8) else { continue }

            let firstLine = content.components(separatedBy: .newlines).first ?? ""
            let title = firstLine
                .replacingOccurrences(of: "# Lesson Learned: ", with: "")
                .replacingOccurrences(of: "# ", with: "")
                .trimmingCharacters(in: .whitespaces)

            var tags: [String] = []
            for line in content.components(separatedBy: .newlines) {
                if line.contains("Context/Tags") {
                    tags = line.components(separatedBy: "`")
                        .enumerated()
                        .filter { $0.offset % 2 == 1 }
                        .map { $0.element }
                    break
                }
            }

            lessons.append(WidgetLessonSync(
                filename: file, title: title,
                timestamp: modDate.timeIntervalSince1970, tags: tags
            ))
        }
    }
    lessons.sort { $0.timestamp > $1.timestamp }

    // 3. Last Seen
    var lastSeen: Double = 0
    if let content = try? String(contentsOfFile: lastSeenPath, encoding: .utf8).trimmingCharacters(in: .whitespacesAndNewlines),
       let ts = Double(content) {
        lastSeen = ts
    }
    let newCount = lessons.filter { $0.timestamp > lastSeen }.count

    // 4. JSON 생성
    let payload = WidgetSyncPayload(
        totalFiles: totalFiles,
        totalLessons: lessons.count,
        newLessonsCount: newCount,
        lessons: lessons,
        lastUpdated: Date().timeIntervalSince1970
    )

    // 5. App Group 컨테이너에 쓰기
    let groupDir = home + "/Library/Group Containers/\(kGroupID)"
    try? fm.createDirectory(atPath: groupDir, withIntermediateDirectories: true)
    let dataPath = groupDir + "/widget_data.json"

    if let jsonData = try? JSONEncoder().encode(payload) {
        try? jsonData.write(to: URL(fileURLWithPath: dataPath))
        print("📡 Widget data synced to: \(dataPath)")
    }

    // 6. Widget 타임라인 즉시 갱신
    WidgetCenter.shared.reloadAllTimelines()
}

// MARK: - Lesson Model for App UI
struct AppLessonInfo: Identifiable {
    var id: String { filename }
    let filename: String
    let title: String
    let date: Date
    let tags: [String]
    let errorText: String
    let resolutionText: String
    let isNew: Bool
}

// MARK: - Knowledge Store
class KnowledgeStore: ObservableObject {
    @Published var lessons: [AppLessonInfo] = []
    @Published var newCount: Int = 0

    private let workspacePath = NSHomeDirectory() + "/.gemini/antigravity/scratch/smart-llm"
    private var lessonsDir: String { workspacePath + "/lessons" }
    private var lastSeenPath: String { workspacePath + "/.widget_last_seen" }

    func load() {
        let fm = FileManager.default
        let lastSeen = readLastSeen()

        guard let files = try? fm.contentsOfDirectory(atPath: lessonsDir) else { return }

        lessons = files
            .filter { $0.hasSuffix(".md") }
            .compactMap { filename -> AppLessonInfo? in
                let path = lessonsDir + "/" + filename
                guard let attrs = try? fm.attributesOfItem(atPath: path),
                      let modDate = attrs[.modificationDate] as? Date,
                      let content = try? String(contentsOfFile: path, encoding: .utf8) else { return nil }

                let title = parseSectionAfter("# Lesson Learned: ", in: content)
                    ?? filename.replacingOccurrences(of: ".md", with: "")
                let tags = parseTags(from: content)
                let errorText = parseSectionAfter("## 🛑 Resolved Error\n", in: content) ?? ""
                let resolution = parseSectionAfter("## 💡 Successful Resolution\n", in: content) ?? ""

                return AppLessonInfo(
                    filename: filename, title: title, date: modDate, tags: tags,
                    errorText: errorText, resolutionText: resolution,
                    isNew: modDate > lastSeen
                )
            }
            .sorted { $0.date > $1.date }

        newCount = lessons.filter { $0.isNew }.count
        
        // 데이터 로드 후 위젯에 동기화
        syncDataToWidget()
    }

    func markAllAsRead() {
        let ts = String(Date().timeIntervalSince1970)
        try? ts.write(toFile: lastSeenPath, atomically: true, encoding: .utf8)
        load() // reload + re-sync to widget
    }

    private func readLastSeen() -> Date {
        guard let content = try? String(contentsOfFile: lastSeenPath, encoding: .utf8)
                .trimmingCharacters(in: .whitespacesAndNewlines),
              let ts = Double(content) else {
            return Date.distantPast
        }
        return Date(timeIntervalSince1970: ts)
    }

    private func parseSectionAfter(_ marker: String, in content: String) -> String? {
        guard let range = content.range(of: marker) else { return nil }
        let rest = content[range.upperBound...]
        let line = rest.components(separatedBy: "\n").first?.trimmingCharacters(in: .whitespaces)
        return line?.isEmpty == true ? nil : line
    }

    private func parseTags(from content: String) -> [String] {
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
}

// MARK: - Knowledge List View
struct KnowledgeListView: View {
    @ObservedObject var store: KnowledgeStore
    @State private var selectedLesson: AppLessonInfo?

    private let dateFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd HH:mm"
        return f
    }()

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                HStack(spacing: 8) {
                    Text("🧠").font(.title2)
                    Text("Knowledge Base")
                        .font(.system(.title2, design: .rounded)).fontWeight(.bold)
                }
                Spacer()
                if store.newCount > 0 {
                    Button(action: { store.markAllAsRead() }) {
                        HStack(spacing: 4) {
                            Image(systemName: "checkmark.circle.fill")
                            Text("Mark All Read")
                        }
                        .font(.system(size: 12, weight: .medium))
                        .padding(.horizontal, 10).padding(.vertical, 5)
                        .background(.blue.opacity(0.2)).cornerRadius(8)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 20).padding(.top, 16).padding(.bottom, 12)

            HStack(spacing: 20) {
                Label("\(store.lessons.count) lessons", systemImage: "book.closed.fill")
                    .font(.system(size: 12)).foregroundStyle(.secondary)
                if store.newCount > 0 {
                    Label("\(store.newCount) new", systemImage: "sparkles")
                        .font(.system(size: 12, weight: .semibold)).foregroundStyle(.yellow)
                }
                Spacer()
            }
            .padding(.horizontal, 20).padding(.bottom, 8)

            Divider().padding(.horizontal, 16)

            if store.lessons.isEmpty {
                Spacer()
                VStack(spacing: 12) {
                    Image(systemName: "tray").font(.system(size: 40)).foregroundStyle(.secondary)
                    Text("No lessons recorded yet").foregroundStyle(.secondary)
                }
                Spacer()
            } else {
                ScrollView {
                    LazyVStack(spacing: 2) {
                        ForEach(store.lessons) { lesson in
                            LessonRow(lesson: lesson, dateFormatter: dateFormatter)
                                .onTapGesture { selectedLesson = lesson }
                        }
                    }
                    .padding(.horizontal, 12).padding(.vertical, 8)
                }
            }
        }
        .sheet(item: $selectedLesson) { lesson in
            LessonDetailView(lesson: lesson)
        }
    }
}

struct LessonRow: View {
    let lesson: AppLessonInfo
    let dateFormatter: DateFormatter

    var body: some View {
        HStack(spacing: 10) {
            Circle().fill(lesson.isNew ? .blue : .clear).frame(width: 8, height: 8)
            VStack(alignment: .leading, spacing: 3) {
                Text(lesson.title)
                    .font(.system(size: 13, weight: lesson.isNew ? .semibold : .regular))
                    .foregroundStyle(.white).lineLimit(2)
                HStack(spacing: 6) {
                    Text(dateFormatter.string(from: lesson.date))
                        .font(.system(size: 10)).foregroundStyle(.secondary)
                    ForEach(lesson.tags.prefix(3), id: \.self) { tag in
                        Text(tag).font(.system(size: 9, weight: .medium))
                            .padding(.horizontal, 5).padding(.vertical, 1)
                            .background(.blue.opacity(0.15)).cornerRadius(4).foregroundStyle(.blue)
                    }
                }
            }
            Spacer()
            Image(systemName: "chevron.right").font(.system(size: 10)).foregroundStyle(.secondary)
        }
        .padding(.horizontal, 12).padding(.vertical, 8)
        .background(RoundedRectangle(cornerRadius: 8).fill(lesson.isNew ? Color.blue.opacity(0.06) : .clear))
    }
}

struct LessonDetailView: View {
    let lesson: AppLessonInfo
    @Environment(\.dismiss) var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text(lesson.title).font(.system(.title3, design: .rounded)).fontWeight(.bold)
                Spacer()
                Button(action: { dismiss() }) {
                    Image(systemName: "xmark.circle.fill").font(.title3).foregroundStyle(.secondary)
                }.buttonStyle(.plain)
            }
            HStack(spacing: 8) {
                ForEach(lesson.tags, id: \.self) { tag in
                    Text(tag).font(.system(size: 11, weight: .medium))
                        .padding(.horizontal, 8).padding(.vertical, 3)
                        .background(.blue.opacity(0.15)).cornerRadius(6).foregroundStyle(.blue)
                }
            }
            Divider()
            if !lesson.errorText.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Label("Error", systemImage: "exclamationmark.triangle.fill")
                        .font(.system(size: 12, weight: .bold)).foregroundStyle(.red)
                    Text(lesson.errorText).font(.system(size: 12))
                        .padding(10).background(.red.opacity(0.08)).cornerRadius(8)
                }
            }
            if !lesson.resolutionText.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Label("Resolution", systemImage: "checkmark.circle.fill")
                        .font(.system(size: 12, weight: .bold)).foregroundStyle(.green)
                    Text(lesson.resolutionText).font(.system(size: 12))
                        .padding(10).background(.green.opacity(0.08)).cornerRadius(8)
                }
            }
            Spacer()
            Button("Open Lesson File") {
                let path = NSHomeDirectory() + "/.gemini/antigravity/scratch/smart-llm/lessons/\(lesson.filename)"
                NSWorkspace.shared.open(URL(fileURLWithPath: path))
            }.buttonStyle(.bordered)
        }
        .padding(20).frame(width: 500, height: 400).preferredColorScheme(.dark)
    }
}

// MARK: - Main App
@main
struct SmartLLMApp: App {
    @StateObject private var store = KnowledgeStore()

    var body: some Scene {
        WindowGroup {
            KnowledgeListView(store: store)
                .frame(minWidth: 520, minHeight: 400)
                .preferredColorScheme(.dark)
                .background(Color(red: 21/255, green: 23/255, blue: 33/255))
                .onAppear { store.load() }
                .onOpenURL { url in
                    if url.scheme == "smartllm" {
                        store.load()
                        NSApp.activate(ignoringOtherApps: true)
                    }
                }
        }
        .windowResizability(.contentSize)
    }
}
