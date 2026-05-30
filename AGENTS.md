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
- **오류 호출**: `src/smart_llm/watcher.py` (L75에서 0개 인자로 호출함)
- **조치 가이드**: 에이전트는 두 모듈의 파라미터 규격을 일치시키고 인터페이스 깨짐(Breaking Changes)을 방어하십시오.


## 📝 PERSISTENT HARD-LEARNED LESSONS (실패 방지 지식 원장) 📝
*경고: 과거 동일 작업 도메인에서 발생했던 결함 및 해결 노하우입니다. 에이전트들은 다음 해결 전략을 코딩 시작 전에 반드시 복기하십시오.*

### 🛡️ Lesson: GPIOA Moder bit setting had bit shift overlap
- **영향 영역**: `gpio`, `stm32`
- **과거 오류**: *"GPIOA Moder bit setting had bit shift overlap..."*
- **해결 전략**: **Use GPIO_MODER_MODER5_0 instead of raw 0x01 shift on Pin A5**

## 🧠 SMART LLM — Workspace Cognitive Architecture Map
*Memorized: 153 code entities, 23 documentation nodes, and 0 relationship boundaries.*

### 🏛️ Cohesive Architecture Communities (GraphRAG Synopsis)
안티그라비티 에이전트들은 다음 구조적 단위(Cohesive Communities)를 기준으로 코드를 탐색하고 작업하십시오.

### 🔗 Cross-Module Call Boundaries
에이전트는 이 경계를 건너서 작업할 때 사이드 이펙트(부작용) 검증을 최우선으로 고려하십시오:
- *No high-level cross-module couplings detected.*

### ⚡ Proactive Memory Cache (0ms Pre-fetched Context)
*에이전트가 현재 `src/smart_llm/widget_app.py` 파일 부근에서 작업 중임을 감지하여, 결합도가 높은 다음 컴포넌트를 선제 로드했습니다.*

#### 🔍 Predicted Target: `/Users/bongpark/.gemini/antigravity/scratch/smart-llm/setup.py` (Coupling Score: 0.0)
*(상세 아키텍처 개요는 위키 커뮤니티 문서를 참고하십시오)*

#### 🔍 Predicted Target: `/Users/bongpark/.gemini/antigravity/scratch/smart-llm/tests/test_git_diff.py` (Coupling Score: 0.0)
*(상세 아키텍처 개요는 위키 커뮤니티 문서를 참고하십시오)*
<!-- SMART-LLM-END -->
