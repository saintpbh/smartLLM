"""Polyglot Cross-Language Contract Resolution (TS fetch ↔ Python FastAPI)."""

from __future__ import annotations

import re
from pathlib import Path
from tree_sitter import Parser
from smart_llm.extract import _get_language

def _extract_ts_fetches(root_node, code_bytes: bytes) -> list[tuple[str, int]]:
    """Scan TS tree-sitter AST iteratively for fetch calls and their string literal endpoints."""
    fetches = []
    stack = [root_node]
    
    while stack:
        node = stack.pop()
        
        # Check call expressions
        if node.type == "call_expression":
            func = node.child_by_field_name("function")
            if func and func.text.decode("utf-8", errors="ignore") == "fetch":
                # Find the string literal first argument (endpoint)
                args_node = node.child_by_field_name("arguments")
                if args_node and args_node.children:
                    for arg in args_node.children:
                        if arg.type in ("string", "string_fragment", "template_string"):
                            # Extract literal value
                            url = arg.text.decode("utf-8", errors="ignore").strip('"').strip("'").strip("`")
                            line_no = node.start_point[0] + 1
                            fetches.append((url, line_no))
                            break
                            
        for child in reversed(node.children):
            stack.append(child)
            
    return fetches

def _extract_python_api_endpoints(root_node, code_bytes: bytes) -> list[tuple[str, str, int]]:
    """Scan Python AST for FastAPI route decorators and their paths, e.g. @app.get("/api/...")"""
    endpoints = []
    stack = [root_node]
    
    while stack:
        node = stack.pop()
        
        # Check decorated definition node in Python tree-sitter
        if node.type == "decorated_definition":
            decorators = []
            func_node = None
            
            for child in node.children:
                if child.type == "decorator":
                    decorators.append(child)
                elif child.type == "function_definition":
                    func_node = child
                    
            if decorators and func_node:
                for decorator in decorators:
                    dec_text = decorator.text.decode("utf-8", errors="ignore")
                    # Check for API decorators
                    if any(kw in dec_text for kw in (".get", ".post", ".put", ".delete", "route")):
                        # Extract path string
                        path_match = re.search(r"['\"`](/api/[\w{}/_-]*)['\"`]", dec_text)
                        if path_match:
                            path = path_match.group(1)
                            func_name_node = func_node.child_by_field_name("name")
                            func_name = func_name_node.text.decode("utf-8", errors="ignore") if func_name_node else "unknown"
                            line_no = func_node.start_point[0] + 1
                            endpoints.append((path, func_name, line_no))
                                
        for child in reversed(node.children):
            stack.append(child)
            
    return endpoints


def check_polyglot_contracts(workspace_path: Path) -> list[dict]:
    """Identify contract violations between TypeScript fetch requests and Python backend endpoints."""
    workspace_path = Path(workspace_path).resolve()
    
    from smart_llm.detect import detect_files
    scan_res = detect_files(workspace_path)
    
    ts_files = [workspace_path / f for f in scan_res["files"]["code"] if f.endswith((".ts", ".tsx", ".js", ".jsx"))]
    py_files = [workspace_path / f for f in scan_res["files"]["code"] if f.endswith(".py")]
    
    # 1. Extract backend endpoints
    backend_endpoints: dict[str, dict] = {}  # normalized_path -> {raw_path, func_name, file, line}
    for file_path in py_files:
        lang = _get_language(".py")
        if not lang:
            continue
        try:
            code = file_path.read_bytes()
        except (OSError, IOError):
            continue
            
        parser = Parser(lang)
        tree = parser.parse(code)
        
        endpoints = _extract_python_api_endpoints(tree.root_node, code)
        for path, func_name, line in endpoints:
            # Normalize path for comparison (e.g. /api/users/{user_id} -> /api/users/{} )
            normalized = re.sub(r"{[\w_]+}", "{}", path)
            backend_endpoints[normalized] = {
                "raw_path": path,
                "func_name": func_name,
                "file": str(file_path.relative_to(workspace_path)),
                "line": line
            }

    # 2. Extract client fetches
    client_fetches: list[dict] = []
    for file_path in ts_files:
        ext = file_path.suffix.lower()
        lang = _get_language(ext)
        if not lang:
            continue
        try:
            code = file_path.read_bytes()
        except (OSError, IOError):
            continue
            
        parser = Parser(lang)
        tree = parser.parse(code)
        
        fetches = _extract_ts_fetches(tree.root_node, code)
        for url, line in fetches:
            client_fetches.append({
                "url": url,
                "file": str(file_path.relative_to(workspace_path)),
                "line": line
            })

    # 3. Check for mismatches
    violations = []
    for fetch in client_fetches:
        url = fetch["url"]
        
        # Only process relative backend API endpoints
        if not url.startswith("/api/"):
            continue
            
        # Normalize the calling URL (e.g. /api/users/123 -> /api/users/{} )
        normalized_url = re.sub(r"/(\d+|\w{8}-\w{4}-\w{4}-\w{4}-\w{12})(?=/|$)", "/{}", url)
        normalized_url = re.sub(r"/\$\{\w+\}", "/{}", normalized_url)
        
        matched_endpoint = None
        # Direct exact match
        if url in backend_endpoints:
            matched_endpoint = backend_endpoints[url]
        # Normalized match (handles path variables)
        elif normalized_url in backend_endpoints:
            matched_endpoint = backend_endpoints[normalized_url]
            
        if matched_endpoint:
            raw_back = matched_endpoint["raw_path"]
            if "{" in raw_back and not ("{" in url or "$" in url or normalized_url != url):
                violations.append({
                    "endpoint": raw_back,
                    "defined_in": matched_endpoint["file"],
                    "defined_line": matched_endpoint["line"],
                    "called_in": fetch["file"],
                    "called_line": fetch["line"],
                    "called_url": url,
                    "error_type": "Path Variable Missing (요구되는 경로 매개변수가 누락됨)"
                })
        else:
            if backend_endpoints:
                violations.append({
                    "endpoint": url,
                    "defined_in": "Backend Route Missing",
                    "defined_line": 0,
                    "called_in": fetch["file"],
                    "called_line": fetch["line"],
                    "called_url": url,
                    "error_type": "Endpoint Unresolved (정의되지 않은 API 엔드포인트 호출)"
                })

    return violations


def build_polyglot_alert_widget(violations: list[dict]) -> str:
    """Compile polyglot contract warnings into a premium alert block for AGENTS.md."""
    if not violations:
        return ""
        
    lines = [
        "## 🌐 [POLYGLOT CROSS-LANGUAGE CONTRACT WARNING] 🌐",
        "*경고: TypeScript 프론트엔드와 Python 백엔드 간에 API 호출 엔드포인트 또는 경로 매개변수 규격이 다르게 충돌하는 오류가 감지되었습니다. 에이전트들은 다음 불일치를 즉시 확인하고 바로잡으십시오.*",
        ""
    ]
    
    for v in violations:
        lines.append(
            f"### 🔗 Polyglot Mismatch: `{v['called_url']}`\n"
            f"- **오류 타입**: `{v['error_type']}`\n"
            f"- **정의 파일**: `{v['defined_in']}` (L{v['defined_line']})\n"
            f"- **오류 호출**: `{v['called_in']}` (L{v['called_line']}에서 호출)\n"
            f"- **조치 가이드**: API 명세와 요청 패스를 일치시켜 클라이언트-서버 통신 실패를 방어하십시오.\n"
        )
        
    lines.append("")
    return "\n".join(lines)
