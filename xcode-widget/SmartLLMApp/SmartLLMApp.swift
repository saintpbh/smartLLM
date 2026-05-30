import SwiftUI

@main
struct SmartLLMApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

struct ContentView: View {
    var body: some View {
        ZStack {
            Color(red: 21/255, green: 23/255, blue: 33/255)
                .ignoresSafeArea()
            
            VStack(spacing: 24) {
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
                
                VStack(spacing: 6) {
                    Text("SMART LLM Widget Hub")
                        .font(.system(.title, design: .rounded))
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                    
                    Text("macOS Tahoe — Native WidgetKit Registered")
                        .font(.subheadline)
                        .foregroundColor(.gray)
                }
                
                VStack(alignment: .leading, spacing: 12) {
                    Text("위젯을 바탕화면에 추가하는 방법:")
                        .font(.headline)
                        .foregroundColor(.blue)
                    
                    Label("바탕화면 우클릭 → 위젯 편집... 선택", systemImage: "1.circle.fill")
                    Label("왼쪽 목록에서 SMART LLM 검색", systemImage: "2.circle.fill")
                    Label("소형/중형 위젯을 바탕화면으로 드래그!", systemImage: "3.circle.fill")
                }
                .font(.system(.body, design: .rounded))
                .foregroundColor(.white.opacity(0.9))
                .padding(18)
                .background(Color.white.opacity(0.06))
                .cornerRadius(16)
                
                Button(action: { NSApplication.shared.terminate(nil) }) {
                    Text("닫기")
                        .fontWeight(.medium)
                        .padding(.horizontal, 24)
                        .padding(.vertical, 8)
                }
                .buttonStyle(.bordered)
            }
            .padding(32)
        }
        .frame(width: 480, height: 420)
        .preferredColorScheme(.dark)
    }
}
