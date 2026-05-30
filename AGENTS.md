# AGENTS.md — Agentic Orchestrator Settings

이 규칙은 안티그라비티 에이전트들이 작업할 때 참고할 최우선 규칙 가이드입니다.

<!-- SMART-LLM-START -->
## ⚠️ [CRITICAL CONTRACT MISMATCH WARNING] ⚠️
*경고: 파일 간에 함수/메서드 호출 인자 개수가 정의 명세와 다르게 충돌하는 오류가 감지되었습니다. 에이전트들은 다음 불일치를 즉시 확인하고 바로잡으십시오.*

### 🛑 Contract Violation: `search`
- **정의 파일**: `src/smart_llm/query.py` (매개변수 요구량: 1~2개)
- **오류 호출**: `src/smart_llm/sync.py` (L53에서 3개 인자로 호출함)
- **조치 가이드**: 에이전트는 두 모듈의 파라미터 규격을 일치시키고 인터페이스 깨짐(Breaking Changes)을 방어하십시오.

### 🛑 Contract Violation: `__init__`
- **정의 파일**: `src/smart_llm/watcher.py` (매개변수 요구량: 1~1개)
- **오류 호출**: `src/smart_llm/watcher.py` (L75에서 0개 인자로 호출함)
- **조치 가이드**: 에이전트는 두 모듈의 파라미터 규격을 일치시키고 인터페이스 깨짐(Breaking Changes)을 방어하십시오.


## 🧠 SMART LLM — Workspace Cognitive Architecture Map
*Memorized: 117 code entities, 28 documentation nodes, and 873 relationship boundaries.*

### 🏛️ Cohesive Architecture Communities (GraphRAG Synopsis)
안티그라비티 에이전트들은 다음 구조적 단위(Cohesive Communities)를 기준으로 코드를 탐색하고 작업하십시오.

#### 📦 Community 0 (Cohesion: 0.163)
> 이 모듈성 커뮤니티는 **검색 및 하이브리드 RRF 질의 제어 도메인 (Search, Retrieval, & RRF Routing)**에 특화되어 설계되었습니다. 주요 컴포넌트인 build_graph, build, denseindex 등을 포함하여 유기적인 상호 작용을 수행하며, 내부 의존성 결합선을 기반으로 결합 구조적 안정성을 도모합니다.
* **Primary Entities**:
  - `build_graph` — [[src__smart_llm__build_py::function::build_graph]]
  - `build` — [[src__smart_llm__build_py::module::build]]
  - `denseindex` — [[src__smart_llm__embed_py::class::denseindex]]
  - `simplesemanticvectorizer` — [[src__smart_llm__embed_py::class::simplesemanticvectorizer]]
  - *...and 22 more entities.*

#### 📦 Community 1 (Cohesion: 0.193)
> 이 모듈성 커뮤니티는 **검색 및 하이브리드 RRF 질의 제어 도메인 (Search, Retrieval, & RRF Routing)**에 특화되어 설계되었습니다. 주요 컴포넌트인 serialize_graph, handle_consolidate, handle_ingest 등을 포함하여 유기적인 상호 작용을 수행하며, 내부 의존성 결합선을 기반으로 결합 구조적 안정성을 도모합니다.
* **Primary Entities**:
  - `serialize_graph` — [[src__smart_llm__build_py::function::serialize_graph]]
  - `handle_consolidate` — [[src__smart_llm__cli_py::function::handle_consolidate]]
  - `handle_ingest` — [[src__smart_llm__cli_py::function::handle_ingest]]
  - `handle_query` — [[src__smart_llm__cli_py::function::handle_query]]
  - *...and 15 more entities.*

#### 📦 Community 10 (Cohesion: 1.000)
> 이 모듈성 커뮤니티는 **시스템 유틸리티 및 일반 구성 컴포넌트 도메인 (System Infrastructure & Utilities)**에 특화되어 설계되었습니다. 주요 컴포넌트인 setup 등을 포함하여 유기적인 상호 작용을 수행하며, 내부 의존성 결합선을 기반으로 결합 구조적 안정성을 도모합니다.
* **Primary Entities**:
  - `setup` — [[setup_py::module::setup]]

#### 📦 Community 2 (Cohesion: 0.111)
> 이 모듈성 커뮤니티는 **검색 및 하이브리드 RRF 질의 제어 도메인 (Search, Retrieval, & RRF Routing)**에 특화되어 설계되었습니다. 주요 컴포넌트인 agents, agents_md___agentic_orchestrator_settings, cohesive_architecture_communities__graphrag_synopsis 등을 포함하여 유기적인 상호 작용을 수행하며, 내부 의존성 결합선을 기반으로 결합 구조적 안정성을 도모합니다.
* **Primary Entities**:
  - `agents` — [[agents_md::file::agents]]
  - `agents_md___agentic_orchestrator_settings` — [[agents_md::header::agents_md___agentic_orchestrator_settings]]
  - `cohesive_architecture_communities__graphrag_synopsis` — [[agents_md::header::cohesive_architecture_communities__graphrag_synopsis]]
  - `community_0__cohesion__0_170` — [[agents_md::header::community_0__cohesion__0_170]]
  - *...and 15 more entities.*

#### 📦 Community 3 (Cohesion: 0.261)
> 이 모듈성 커뮤니티는 **tree-sitter 기반 다국어 AST 구문 분석 및 구조 추출 도메인 (AST & Doc Parsing)**에 특화되어 설계되었습니다. 주요 컴포넌트인 _count_parameters, _find_calls_and_arg_counts, scan_contract_conflicts 등을 포함하여 유기적인 상호 작용을 수행하며, 내부 의존성 결합선을 기반으로 결합 구조적 안정성을 도모합니다.
* **Primary Entities**:
  - `_count_parameters` — [[src__smart_llm__broker_py::function::_count_parameters]]
  - `_find_calls_and_arg_counts` — [[src__smart_llm__broker_py::function::_find_calls_and_arg_counts]]
  - `scan_contract_conflicts` — [[src__smart_llm__broker_py::function::scan_contract_conflicts]]
  - `broker` — [[src__smart_llm__broker_py::module::broker]]
  - *...and 14 more entities.*

#### 📦 Community 4 (Cohesion: 0.231)
> 이 모듈성 커뮤니티는 **tree-sitter 기반 다국어 AST 구문 분석 및 구조 추출 도메인 (AST & Doc Parsing)**에 특화되어 설계되었습니다. 주요 컴포넌트인 _extract_python_api_endpoints, _extract_ts_fetches, build_polyglot_alert_widget 등을 포함하여 유기적인 상호 작용을 수행하며, 내부 의존성 결합선을 기반으로 결합 구조적 안정성을 도모합니다.
* **Primary Entities**:
  - `_extract_python_api_endpoints` — [[src__smart_llm__polyglot_py::function::_extract_python_api_endpoints]]
  - `_extract_ts_fetches` — [[src__smart_llm__polyglot_py::function::_extract_ts_fetches]]
  - `build_polyglot_alert_widget` — [[src__smart_llm__polyglot_py::function::build_polyglot_alert_widget]]
  - `check_polyglot_contracts` — [[src__smart_llm__polyglot_py::function::check_polyglot_contracts]]
  - *...and 9 more entities.*

#### 📦 Community 5 (Cohesion: 0.303)
> 이 모듈성 커뮤니티는 **NetworkX 기반 지식 그래프 컴파일 및 레퍼런스 결합 도메인 (DiGraph Building)**에 특화되어 설계되었습니다. 주요 컴포넌트인 build_conflict_alert_widget, handle_sync_agents, _get_db_connection 등을 포함하여 유기적인 상호 작용을 수행하며, 내부 의존성 결합선을 기반으로 결합 구조적 안정성을 도모합니다.
* **Primary Entities**:
  - `build_conflict_alert_widget` — [[src__smart_llm__broker_py::function::build_conflict_alert_widget]]
  - `handle_sync_agents` — [[src__smart_llm__cli_py::function::handle_sync_agents]]
  - `_get_db_connection` — [[src__smart_llm__sqlite_ledger_py::function::_get_db_connection]]
  - `get_active_alerts` — [[src__smart_llm__sqlite_ledger_py::function::get_active_alerts]]
  - *...and 8 more entities.*

#### 📦 Community 6 (Cohesion: 0.417)
> 이 모듈성 커뮤니티는 **시스템 유틸리티 및 일반 구성 컴포넌트 도메인 (System Infrastructure & Utilities)**에 특화되어 설계되었습니다. 주요 컴포넌트인 cognitivefileeventhandler, debouncedindexscheduler, __init__ 등을 포함하여 유기적인 상호 작용을 수행하며, 내부 의존성 결합선을 기반으로 결합 구조적 안정성을 도모합니다.
* **Primary Entities**:
  - `cognitivefileeventhandler` — [[src__smart_llm__watcher_py::class::cognitivefileeventhandler]]
  - `debouncedindexscheduler` — [[src__smart_llm__watcher_py::class::debouncedindexscheduler]]
  - `__init__` — [[src__smart_llm__watcher_py::method::__init__]]
  - `_should_process` — [[src__smart_llm__watcher_py::method::_should_process]]
  - *...and 5 more entities.*

#### 📦 Community 7 (Cohesion: 0.222)
> 이 모듈성 커뮤니티는 **검색 및 하이브리드 RRF 질의 제어 도메인 (Search, Retrieval, & RRF Routing)**에 특화되어 설계되었습니다. 주요 컴포넌트인 readme, clone_the_repository_and_navigate_to_it, index_your_current_project 등을 포함하여 유기적인 상호 작용을 수행하며, 내부 의존성 결합선을 기반으로 결합 구조적 안정성을 도모합니다.
* **Primary Entities**:
  - `readme` — [[readme_md::file::readme]]
  - `clone_the_repository_and_navigate_to_it` — [[readme_md::header::clone_the_repository_and_navigate_to_it]]
  - `index_your_current_project` — [[readme_md::header::index_your_current_project]]
  - `install_the_package_in_editable_mode` — [[readme_md::header::install_the_package_in_editable_mode]]
  - *...and 5 more entities.*

#### 📦 Community 8 (Cohesion: 0.278)
> 이 모듈성 커뮤니티는 **실시간 Git-diff 변경 감지 및 증분 메모리 컴파일 도메인 (Git Incremental Updates)**에 특화되어 설계되었습니다. 주요 컴포넌트인 get_git_changes, incremental_update_graph, git_diff 등을 포함하여 유기적인 상호 작용을 수행하며, 내부 의존성 결합선을 기반으로 결합 구조적 안정성을 도모합니다.
* **Primary Entities**:
  - `get_git_changes` — [[src__smart_llm__git_diff_py::function::get_git_changes]]
  - `incremental_update_graph` — [[src__smart_llm__git_diff_py::function::incremental_update_graph]]
  - `git_diff` — [[src__smart_llm__git_diff_py::module::git_diff]]
  - `compile_agents_doc` — [[src__smart_llm__sync_py::function::compile_agents_doc]]
  - *...and 5 more entities.*

#### 📦 Community 9 (Cohesion: 0.333)
> 이 모듈성 커뮤니티는 **NetworkX 기반 지식 그래프 컴파일 및 레퍼런스 결합 도메인 (DiGraph Building)**에 특화되어 설계되었습니다. 주요 컴포넌트인 call_llm, detect_llm_provider, llm 등을 포함하여 유기적인 상호 작용을 수행하며, 내부 의존성 결합선을 기반으로 결합 구조적 안정성을 도모합니다.
* **Primary Entities**:
  - `call_llm` — [[src__smart_llm__llm_py::function::call_llm]]
  - `detect_llm_provider` — [[src__smart_llm__llm_py::function::detect_llm_provider]]
  - `llm` — [[src__smart_llm__llm_py::module::llm]]
  - `_infer_semantic_domain` — [[src__smart_llm__synopsis_py::function::_infer_semantic_domain]]
  - *...and 5 more entities.*

### 🔗 Cross-Module Call Boundaries
에이전트는 이 경계를 건너서 작업할 때 사이드 이펙트(부작용) 검증을 최우선으로 고려하십시오:
- `tests/test_git_diff_py` --[calls]--> `src/smart_llm/git_diff_py`
- `tests/test_git_diff_py` --[calls]--> `src/smart_llm/sync_py`
- `tests/test_git_diff_py` --[imports]--> `src/smart_llm/git_diff_py`
- `tests/test_git_diff_py` --[imports]--> `src/smart_llm/sync_py`
- `tests/test_ultimate_py` --[calls]--> `src/smart_llm/polyglot_py`
- `tests/test_ultimate_py` --[calls]--> `src/smart_llm/proactive_py`
- `tests/test_ultimate_py` --[calls]--> `src/smart_llm/sqlite_ledger_py`
- `tests/test_ultimate_py` --[imports]--> `src/smart_llm/polyglot_py`
- `tests/test_ultimate_py` --[imports]--> `src/smart_llm/proactive_py`
- `tests/test_ultimate_py` --[imports]--> `src/smart_llm/sqlite_ledger_py`

### ⚡ Proactive Memory Cache (0ms Pre-fetched Context)
*에이전트가 현재 `src/smart_llm/cli.py` 파일 부근에서 작업 중임을 감지하여, 결합도가 높은 다음 컴포넌트를 선제 로드했습니다.*

#### 🔍 Predicted Target: `/Users/bongpark/.gemini/antigravity/scratch/smart-llm/setup.py` (Coupling Score: 0.0)
*주요 연결 지식: `[[wiki/community_7.md]]`*
```markdown
# Community Memory 7
**Cohesion Score**: 0.222

## Component Members
- **readme** (file) — `[[readme_md::file::readme]]`
- **clone_the_repository_and_navigate_to_it** (header) — `[[readme_md::header::clone_the_repository_and_navigate_to_it]]`
- **index_your_current_project** (header) — `[[readme_md::header::index_your_current_project]]`
- **install_the_package_in_editable_mode** (header) — `[[readme_md::header::install_the_package_in_editable_mode]]`
- **installation___setup** (header) — `[[readme_md::header::installation___setup]]`
- **key_features** (header) — `[[readme_md::header::key_features]]`
```

#### 🔍 Predicted Target: `/Users/bongpark/.gemini/antigravity/scratch/smart-llm/tests/test_git_diff.py` (Coupling Score: 0.0)
*주요 연결 지식: `[[wiki/community_2.md]]`*
```markdown
# Community Memory 2
**Cohesion Score**: 0.111

## Component Members
- **agents** (file) — `[[agents_md::file::agents]]`
- **agents_md___agentic_orchestrator_settings** (header) — `[[agents_md::header::agents_md___agentic_orchestrator_settings]]`
- **cohesive_architecture_communities__graphrag_synopsis** (header) — `[[agents_md::header::cohesive_architecture_communities__graphrag_synopsis]]`
- **community_0__cohesion__0_170** (header) — `[[agents_md::header::community_0__cohesion__0_170]]`
- **community_1__cohesion__0_178** (header) — `[[agents_md::header::community_1__cohesion__0_178]]`
- **community_2__cohesion__0_190** (header) — `[[agents_md::header::community_2__cohesion__0_190]]`
```
<!-- SMART-LLM-END -->
