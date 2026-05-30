# AGENTS.md — Agentic Orchestrator Settings

이 규칙은 안티그라비티 에이전트들이 작업할 때 참고할 최우선 규칙 가이드입니다.

<!-- SMART-LLM-START -->
## ⚠️ [CRITICAL CONTRACT MISMATCH WARNING] ⚠️
*경고: 파일 간에 함수/메서드 호출 인자 개수가 정의 명세와 다르게 충돌하는 오류가 감지되었습니다. 에이전트들은 다음 불일치를 즉시 확인하고 바로잡으십시오.*

### 🛑 Contract Violation: `search`
- **정의 파일**: `src/smart_llm/query.py` (매개변수 요구량: 1~2개)
- **오류 호출**: `src/smart_llm/sync.py` (L53에서 3개 인자로 호출함)
- **조치 가이드**: 에이전트는 두 모듈의 파라미터 규격을 일치시키고 인터페이스 깨짐(Breaking Changes)을 방어하십시오.

### 🛑 Contract Violation: `run`
- **정의 파일**: `src/smart_llm/widget_app.py` (매개변수 요구량: 0~0개)
- **오류 호출**: `src/smart_llm/git_diff.py` (L20에서 5개 인자로 호출함)
- **조치 가이드**: 에이전트는 두 모듈의 파라미터 규격을 일치시키고 인터페이스 깨짐(Breaking Changes)을 방어하십시오.

### 🛑 Contract Violation: `search`
- **정의 파일**: `src/smart_llm/query.py` (매개변수 요구량: 1~2개)
- **오류 호출**: `src/smart_llm/learn.py` (L74에서 3개 인자로 호출함)
- **조치 가이드**: 에이전트는 두 모듈의 파라미터 규격을 일치시키고 인터페이스 깨짐(Breaking Changes)을 방어하십시오.

### 🛑 Contract Violation: `search`
- **정의 파일**: `src/smart_llm/query.py` (매개변수 요구량: 1~2개)
- **오류 호출**: `src/smart_llm/learn.py` (L75에서 3개 인자로 호출함)
- **조치 가이드**: 에이전트는 두 모듈의 파라미터 규격을 일치시키고 인터페이스 깨짐(Breaking Changes)을 방어하십시오.

### 🛑 Contract Violation: `search`
- **정의 파일**: `src/smart_llm/query.py` (매개변수 요구량: 1~2개)
- **오류 호출**: `src/smart_llm/learn.py` (L76에서 3개 인자로 호출함)
- **조치 가이드**: 에이전트는 두 모듈의 파라미터 규격을 일치시키고 인터페이스 깨짐(Breaking Changes)을 방어하십시오.

### 🛑 Contract Violation: `search`
- **정의 파일**: `src/smart_llm/query.py` (매개변수 요구량: 1~2개)
- **오류 호출**: `src/smart_llm/learn.py` (L77에서 3개 인자로 호출함)
- **조치 가이드**: 에이전트는 두 모듈의 파라미터 규격을 일치시키고 인터페이스 깨짐(Breaking Changes)을 방어하십시오.

### 🛑 Contract Violation: `__init__`
- **정의 파일**: `src/smart_llm/widget_app.py` (매개변수 요구량: 1~1개)
- **오류 호출**: `src/smart_llm/watcher.py` (L83에서 0개 인자로 호출함)
- **조치 가이드**: 에이전트는 두 모듈의 파라미터 규격을 일치시키고 인터페이스 깨짐(Breaking Changes)을 방어하십시오.


## 📝 PERSISTENT HARD-LEARNED LESSONS (실패 방지 지식 원장) 📝
*경고: 과거 동일 작업 도메인에서 발생했던 결함 및 해결 노하우입니다. 에이전트들은 다음 해결 전략을 코딩 시작 전에 반드시 복기하십시오.*

### 🛡️ Lesson: macOS WidgetKit 위젯에서 com.apple.security.app-sandbox=true + c
- **영향 영역**: `macos`, `widgetkit`, `sandbox`, `entitlements`, `ad-hoc-signing`
- **과거 오류**: *"macOS WidgetKit 위젯에서 com.apple.security.app-sandbox=true + com.apple.security.files.home-directory.read-only=true 설정 시, ad-hoc 서명(Sign to Run Locally)..."*
- **해결 전략**: **macOS 위젯 확장은 iOS와 달리 샌드박스가 필수가 아님. com.apple.security.app-sandbox 엔타이틀먼트를 완전히 제거하면 비샌드박스 모드로 실행되어 홈 디렉토리 파일을 자유롭게 읽을 수 있음. 로컬 개발용 ad-hoc 서명에서는 이 방식이 유일하게 안정적**

### 🛡️ Lesson: swiftc CLI로 컴파일한 WidgetKit 확장 프로그램이 pluginkit에는 등록되지만 macOS
- **영향 영역**: `macos`, `widgetkit`, `xcode`, `swiftui`, `widget-gallery`, `chronod`
- **과거 오류**: *"swiftc CLI로 컴파일한 WidgetKit 확장 프로그램이 pluginkit에는 등록되지만 macOS 위젯 갤러리(Edit Widgets)에 노출되지 않음. chronod가 프로비저닝 서명 검증을 통과하지 못함..."*
- **해결 전략**: **WidgetKit 위젯은 반드시 Xcode 프로젝트(.xcodeproj)를 통해 빌드해야 함. xcodegen으로 project.yml에서 프로젝트를 생성하고, xcodebuild CLI로 빌드하면 Xcode GUI 없이도 프로비저닝/서명이 자동 처리되어 위젯 갤러리에 정상 노출됨. swiftc + codesign ad-hoc 조합으로는 절대 불가**

### 🛡️ Lesson: GPIOA Moder bit setting had bit shift overlap
- **영향 영역**: `gpio`, `stm32`
- **과거 오류**: *"GPIOA Moder bit setting had bit shift overlap..."*
- **해결 전략**: **Use GPIO_MODER_MODER5_0 instead of raw 0x01 shift on Pin A5**

## 🧠 SMART LLM — Workspace Cognitive Architecture Map
*Memorized: 155 code entities, 33 documentation nodes, and 0 relationship boundaries.*

### 🏛️ Cohesive Architecture Communities (GraphRAG Synopsis)
안티그라비티 에이전트들은 다음 구조적 단위(Cohesive Communities)를 기준으로 코드를 탐색하고 작업하십시오.

### 🔗 Cross-Module Call Boundaries
에이전트는 이 경계를 건너서 작업할 때 사이드 이펙트(부작용) 검증을 최우선으로 고려하십시오:
- *No high-level cross-module couplings detected.*

### ⚡ Proactive Memory Cache (0ms Pre-fetched Context)
*에이전트가 현재 `AGENTS.md` 파일 부근에서 작업 중임을 감지하여, 결합도가 높은 다음 컴포넌트를 선제 로드했습니다.*

#### 🔍 Predicted Target: `/Users/bongpark/.gemini/antigravity/scratch/smart-llm/setup.py` (Coupling Score: 0.0)
*(상세 아키텍처 개요는 위키 커뮤니티 문서를 참고하십시오)*

#### 🔍 Predicted Target: `/Users/bongpark/.gemini/antigravity/scratch/smart-llm/tests/test_git_diff.py` (Coupling Score: 0.0)
*(상세 아키텍처 개요는 위키 커뮤니티 문서를 참고하십시오)*
<!-- SMART-LLM-END -->
