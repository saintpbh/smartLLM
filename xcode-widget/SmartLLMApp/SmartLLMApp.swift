import SwiftUI
import AppKit
import WidgetKit

// MARK: - Lesson Model (shared with widget)
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

// MARK: - Knowledge List ViewModel
class KnowledgeStore: ObservableObject {
    @Published var lessons: [AppLessonInfo] = []
    @Published var newCount: Int = 0

    private let workspacePath = NSString(string: "~/.gemini/antigravity/scratch/smart-llm").expandingTildeInPath
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
                    filename: filename,
                    title: title,
                    date: modDate,
                    tags: tags,
                    errorText: errorText,
                    resolutionText: resolution,
                    isNew: modDate > lastSeen
                )
            }
            .sorted { $0.date > $1.date }

        newCount = lessons.filter { $0.isNew }.count
    }

    func markAllAsRead() {
        let ts = String(Date().timeIntervalSince1970)
        try? ts.write(toFile: lastSeenPath, atomically: true, encoding: .utf8)
        // Widget 타임라인 즉시 갱신
        WidgetCenter.shared.reloadAllTimelines()
        load()
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
            // Header
            HStack {
                HStack(spacing: 8) {
                    Text("🧠")
                        .font(.title2)
                    Text("Knowledge Base")
                        .font(.system(.title2, design: .rounded))
                        .fontWeight(.bold)
                }
                Spacer()
                if store.newCount > 0 {
                    Button(action: { store.markAllAsRead() }) {
                        HStack(spacing: 4) {
                            Image(systemName: "checkmark.circle.fill")
                            Text("Mark All Read")
                        }
                        .font(.system(size: 12, weight: .medium))
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(.blue.opacity(0.2))
                        .cornerRadius(8)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 20)
            .padding(.top, 16)
            .padding(.bottom, 12)

            // Count summary
            HStack(spacing: 20) {
                Label("\(store.lessons.count) lessons", systemImage: "book.closed.fill")
                    .font(.system(size: 12))
                    .foregroundStyle(.secondary)
                if store.newCount > 0 {
                    Label("\(store.newCount) new", systemImage: "sparkles")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(.yellow)
                }
                Spacer()
            }
            .padding(.horizontal, 20)
            .padding(.bottom, 8)

            Divider().padding(.horizontal, 16)

            // Lesson List
            if store.lessons.isEmpty {
                Spacer()
                VStack(spacing: 12) {
                    Image(systemName: "tray")
                        .font(.system(size: 40))
                        .foregroundStyle(.secondary)
                    Text("No lessons recorded yet")
                        .foregroundStyle(.secondary)
                    Text("Use 'smart-llm learn' to record debugging insights")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
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
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                }
            }
        }
        .sheet(item: $selectedLesson) { lesson in
            LessonDetailView(lesson: lesson)
        }
    }
}

// MARK: - Lesson Row
struct LessonRow: View {
    let lesson: AppLessonInfo
    let dateFormatter: DateFormatter

    var body: some View {
        HStack(spacing: 10) {
            // New indicator
            Circle()
                .fill(lesson.isNew ? .blue : .clear)
                .frame(width: 8, height: 8)

            VStack(alignment: .leading, spacing: 3) {
                Text(lesson.title)
                    .font(.system(size: 13, weight: lesson.isNew ? .semibold : .regular))
                    .foregroundStyle(.white)
                    .lineLimit(2)

                HStack(spacing: 6) {
                    Text(dateFormatter.string(from: lesson.date))
                        .font(.system(size: 10))
                        .foregroundStyle(.secondary)

                    ForEach(lesson.tags.prefix(3), id: \.self) { tag in
                        Text(tag)
                            .font(.system(size: 9, weight: .medium))
                            .padding(.horizontal, 5)
                            .padding(.vertical, 1)
                            .background(.blue.opacity(0.15))
                            .cornerRadius(4)
                            .foregroundStyle(.blue)
                    }
                }
            }
            Spacer()

            Image(systemName: "chevron.right")
                .font(.system(size: 10))
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(lesson.isNew ? Color.blue.opacity(0.06) : .clear)
        )
    }
}

// MARK: - Lesson Detail View
struct LessonDetailView: View {
    let lesson: AppLessonInfo
    @Environment(\.dismiss) var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text(lesson.title)
                    .font(.system(.title3, design: .rounded))
                    .fontWeight(.bold)
                Spacer()
                Button(action: { dismiss() }) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }

            HStack(spacing: 8) {
                ForEach(lesson.tags, id: \.self) { tag in
                    Text(tag)
                        .font(.system(size: 11, weight: .medium))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(.blue.opacity(0.15))
                        .cornerRadius(6)
                        .foregroundStyle(.blue)
                }
            }

            Divider()

            if !lesson.errorText.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Label("Error", systemImage: "exclamationmark.triangle.fill")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(.red)
                    Text(lesson.errorText)
                        .font(.system(size: 12))
                        .foregroundStyle(.white.opacity(0.9))
                        .padding(10)
                        .background(.red.opacity(0.08))
                        .cornerRadius(8)
                }
            }

            if !lesson.resolutionText.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Label("Resolution", systemImage: "checkmark.circle.fill")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(.green)
                    Text(lesson.resolutionText)
                        .font(.system(size: 12))
                        .foregroundStyle(.white.opacity(0.9))
                        .padding(10)
                        .background(.green.opacity(0.08))
                        .cornerRadius(8)
                }
            }

            Spacer()

            Button("Open Lesson File") {
                let path = NSString(string: "~/.gemini/antigravity/scratch/smart-llm/lessons/\(lesson.filename)").expandingTildeInPath
                NSWorkspace.shared.open(URL(fileURLWithPath: path))
            }
            .buttonStyle(.bordered)
        }
        .padding(20)
        .frame(width: 500, height: 400)
        .preferredColorScheme(.dark)
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
