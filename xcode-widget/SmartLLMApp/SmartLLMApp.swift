import SwiftUI
import AppKit
import WidgetKit

// MARK: - 내장 HTTP 서버 (위젯 데이터 제공)
// 샌드박스 위젯이 파일을 직접 읽을 수 없으므로 localhost HTTP로 제공
class WidgetDataServer {
    static let shared = WidgetDataServer()
    private let port: UInt16 = 18923
    private var serverSocket: Int32 = -1
    private let acceptQueue = DispatchQueue(label: "widget-http-accept", qos: .background)
    private let clientQueue = DispatchQueue(label: "widget-http-client", qos: .utility, attributes: .concurrent)
    private var jsonPath: String = ""

    func start(servingPath: String) {
        jsonPath = servingPath
        acceptQueue.async { [self] in
            serverSocket = socket(AF_INET, SOCK_STREAM, 0)
            guard serverSocket >= 0 else { return }

            var yes: Int32 = 1
            setsockopt(serverSocket, SOL_SOCKET, SO_REUSEADDR, &yes, socklen_t(MemoryLayout<Int32>.size))
            setsockopt(serverSocket, SOL_SOCKET, SO_REUSEPORT, &yes, socklen_t(MemoryLayout<Int32>.size))

            var addr = sockaddr_in()
            addr.sin_family = sa_family_t(AF_INET)
            addr.sin_port = port.bigEndian
            addr.sin_addr.s_addr = UInt32(0x7f000001).bigEndian

            let bindResult = withUnsafePointer(to: &addr) { ptr in
                ptr.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                    Darwin.bind(serverSocket, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
                }
            }
            guard bindResult == 0 else {
                print("⚠️ HTTP server bind failed on port \(port)")
                return
            }

            Darwin.listen(serverSocket, 10)
            print("📡 Widget HTTP server running on http://localhost:\(port)/")

            while serverSocket >= 0 {
                let client = Darwin.accept(serverSocket, nil, nil)
                if client < 0 { continue }

                // 별도 concurrent queue에서 클라이언트 처리
                let path = jsonPath
                clientQueue.async {
                    Self.handleClient(client, jsonPath: path)
                }
            }
        }
    }

    private static func handleClient(_ client: Int32, jsonPath: String) {
        // Read request (최대 2KB)
        var buffer = [UInt8](repeating: 0, count: 2048)
        let bytesRead = Darwin.recv(client, &buffer, buffer.count, 0)
        guard bytesRead > 0 else {
            Darwin.close(client)
            return
        }

        // Serve JSON
        let body: Data
        if let data = try? Data(contentsOf: URL(fileURLWithPath: jsonPath)) {
            body = data
        } else {
            body = "{\"totalFiles\":0,\"totalLessons\":0,\"newLessonsCount\":0,\"lessons\":[],\"lastUpdated\":0}".data(using: .utf8)!
        }

        let header = "HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: \(body.count)\r\nConnection: close\r\n\r\n"

        // Send header + body
        if let headerData = header.data(using: .utf8) {
            headerData.withUnsafeBytes { ptr in
                _ = Darwin.send(client, ptr.baseAddress!, headerData.count, 0)
            }
        }
        body.withUnsafeBytes { ptr in
            _ = Darwin.send(client, ptr.baseAddress!, body.count, 0)
        }

        // Graceful shutdown
        Darwin.shutdown(client, SHUT_WR)
        Darwin.close(client)
    }
}


// MARK: - 위젯 데이터 생성 + JSON 저장
private let kGroupID = "group.com.bongpark.SmartLLM"

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

func getWidgetDataPath() -> String {
    let groupDir = NSHomeDirectory() + "/Library/Group Containers/\(kGroupID)"
    try? FileManager.default.createDirectory(atPath: groupDir, withIntermediateDirectories: true)
    return groupDir + "/widget_data.json"
}

func syncDataToWidget() {
    let home = NSHomeDirectory()
    let workspacePath = home + "/.gemini/antigravity/scratch/smart-llm"
    let lessonsDir = workspacePath + "/lessons"
    let indexPath = workspacePath + "/smart-llm-out/index.json"
    let lastSeenPath = workspacePath + "/.widget_last_seen"
    let fm = FileManager.default

    var totalFiles = 0
    if let data = try? Data(contentsOf: URL(fileURLWithPath: indexPath)),
       let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
       let docMap = json["doc_map"] as? [String: Any] {
        totalFiles = docMap.count
    }

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
                        .enumerated().filter { $0.offset % 2 == 1 }.map { $0.element }
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

    var lastSeen: Double = 0
    if let content = try? String(contentsOfFile: lastSeenPath, encoding: .utf8)
        .trimmingCharacters(in: .whitespacesAndNewlines), let ts = Double(content) {
        lastSeen = ts
    }

    let payload = WidgetSyncPayload(
        totalFiles: totalFiles,
        totalLessons: lessons.count,
        newLessonsCount: lessons.filter { $0.timestamp > lastSeen }.count,
        lessons: lessons,
        lastUpdated: Date().timeIntervalSince1970
    )

    let dataPath = getWidgetDataPath()
    if let jsonData = try? JSONEncoder().encode(payload) {
        try? jsonData.write(to: URL(fileURLWithPath: dataPath))
    }

    WidgetCenter.shared.reloadAllTimelines()
}

// MARK: - Lesson Model (UI)
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

        lessons = files.filter { $0.hasSuffix(".md") }.compactMap { filename -> AppLessonInfo? in
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
                errorText: errorText, resolutionText: resolution, isNew: modDate > lastSeen
            )
        }.sorted { $0.date > $1.date }

        newCount = lessons.filter { $0.isNew }.count
        syncDataToWidget()
    }

    func markAllAsRead() {
        let ts = String(Date().timeIntervalSince1970)
        try? ts.write(toFile: lastSeenPath, atomically: true, encoding: .utf8)
        load()
    }

    private func readLastSeen() -> Date {
        guard let content = try? String(contentsOfFile: lastSeenPath, encoding: .utf8)
                .trimmingCharacters(in: .whitespacesAndNewlines), let ts = Double(content) else {
            return Date.distantPast
        }
        return Date(timeIntervalSince1970: ts)
    }

    private func parseSectionAfter(_ marker: String, in content: String) -> String? {
        guard let range = content.range(of: marker) else { return nil }
        let line = content[range.upperBound...].components(separatedBy: "\n").first?.trimmingCharacters(in: .whitespaces)
        return line?.isEmpty == true ? nil : line
    }

    private func parseTags(from content: String) -> [String] {
        for line in content.components(separatedBy: .newlines) {
            if line.contains("Context/Tags") {
                return line.components(separatedBy: "`").enumerated().filter { $0.offset % 2 == 1 }.map { $0.element }
            }
        }
        return []
    }
}

// MARK: - Views
struct KnowledgeListView: View {
    @ObservedObject var store: KnowledgeStore
    @State private var selectedLesson: AppLessonInfo?

    private let dateFormatter: DateFormatter = {
        let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd HH:mm"; return f
    }()

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                HStack(spacing: 8) {
                    Text("🧠").font(.title2)
                    Text("Knowledge Base").font(.system(.title2, design: .rounded)).fontWeight(.bold)
                }
                Spacer()
                if store.newCount > 0 {
                    Button(action: { store.markAllAsRead() }) {
                        HStack(spacing: 4) {
                            Image(systemName: "checkmark.circle.fill")
                            Text("Mark All Read")
                        }.font(.system(size: 12, weight: .medium))
                        .padding(.horizontal, 10).padding(.vertical, 5)
                        .background(.blue.opacity(0.2)).cornerRadius(8)
                    }.buttonStyle(.plain)
                }
            }.padding(.horizontal, 20).padding(.top, 16).padding(.bottom, 12)

            HStack(spacing: 20) {
                Label("\(store.lessons.count) lessons", systemImage: "book.closed.fill")
                    .font(.system(size: 12)).foregroundStyle(.secondary)
                if store.newCount > 0 {
                    Label("\(store.newCount) new", systemImage: "sparkles")
                        .font(.system(size: 12, weight: .semibold)).foregroundStyle(.yellow)
                }
                Spacer()
            }.padding(.horizontal, 20).padding(.bottom, 8)

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
                    }.padding(.horizontal, 12).padding(.vertical, 8)
                }
            }
        }
        .sheet(item: $selectedLesson) { LessonDetailView(lesson: $0) }
    }
}

struct LessonRow: View {
    let lesson: AppLessonInfo; let dateFormatter: DateFormatter

    var body: some View {
        HStack(spacing: 10) {
            Circle().fill(lesson.isNew ? .blue : .clear).frame(width: 8, height: 8)
            VStack(alignment: .leading, spacing: 3) {
                Text(lesson.title)
                    .font(.system(size: 13, weight: lesson.isNew ? .semibold : .regular))
                    .foregroundStyle(.white).lineLimit(2)
                HStack(spacing: 6) {
                    Text(dateFormatter.string(from: lesson.date)).font(.system(size: 10)).foregroundStyle(.secondary)
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
        }.padding(20).frame(width: 500, height: 400).preferredColorScheme(.dark)
    }
}

// MARK: - Main App
@main
struct SmartLLMApp: App {
    @StateObject private var store = KnowledgeStore()

    init() {
        // 앱 시작 시 HTTP 서버 자동 기동
        let dataPath = getWidgetDataPath()
        WidgetDataServer.shared.start(servingPath: dataPath)
    }

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
