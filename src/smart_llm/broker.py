"""Consensus Conflict Broker - detects AST interface mismatches between files iteratively."""

from __future__ import annotations

import re
from pathlib import Path
from tree_sitter import Parser
from smart_llm.extract import _get_language, _find_identifier

def _count_parameters(node, ext: str) -> tuple[int, int]:
    """Count (total_parameters, required_parameters) in a function definition node.
    
    Ignores self/cls bound parameters and correctly identifies default parameter formats.
    """
    total = 0
    required = 0
    
    # Locate parameters list child node
    params_node = None
    for child in node.children:
        if child.type in ("parameters", "formal_parameters", "parameter_list"):
            params_node = child
            break
            
    if not params_node:
        return 0, 0

    for p in params_node.children:
        # Skip separator syntax tokens
        if p.type in (",", "(", ")", "*", "**", "/", "self", "cls"):
            continue
            
        p_text = p.text.decode("utf-8", errors="ignore") if p.text else ""
        # Skip class instance binding targets
        if p_text in ("self", "cls") or p.type in ("self", "cls"):
            continue
            
        # Check if the parameter has a default value (e.g. default_parameter, typed_default_parameter)
        if "default" in p.type or "optional" in p.type:
            total += 1
            # Does not increase required count
        else:
            total += 1
            required += 1
            
    return total, required

def _find_calls_and_arg_counts(root_node, ext: str) -> list[tuple[str, int, int]]:
    """Iteratively find calls in a tree-sitter AST, returning list of (function_name, arg_count, line_number)."""
    calls = []
    stack = [root_node]
    
    while stack:
        node = stack.pop()
        
        if node.type in ("call", "call_expression"):
            func = node.child_by_field_name("function")
            if func is None and node.children:
                func = node.children[0]
                
            args_node = None
            for child in node.children:
                if child.type in ("argument_list", "arguments"):
                    args_node = child
                    break
                    
            if func and args_node:
                func_name = func.text.decode("utf-8", errors="ignore") if func.text else ""
                if "." in func_name:
                    func_name = func_name.rsplit(".", 1)[-1]
                    
                # Count arguments
                arg_count = sum(1 for c in args_node.children if c.type not in (",", "(", ")", "[", "]", "{", "}"))
                line_no = node.start_point[0] + 1
                calls.append((func_name, arg_count, line_no))
                
        # Push children in reverse order to maintain DFS order
        for child in reversed(node.children):
            stack.append(child)
            
    return calls


def scan_contract_conflicts(workspace_path: Path) -> list[dict]:
    """Scan all code files in the workspace, checking if function call sites match their definitions."""
    workspace_path = Path(workspace_path).resolve()
    
    # 1. Scan files
    from smart_llm.detect import detect_files
    scan_res = detect_files(workspace_path)
    code_files = [workspace_path / f for f in scan_res["files"]["code"]]
    
    definitions: dict[str, dict] = {}  # func_name -> {file, required_params, total_params}
    call_sites: list[dict] = []  # List of {func_name, args_count, file, line}
    
    for file_path in code_files:
        ext = file_path.suffix.lower()
        lang = _get_language(ext)
        if lang is None:
            continue
            
        try:
            code = file_path.read_bytes()
        except (OSError, IOError):
            continue
            
        parser = Parser(lang)
        tree = parser.parse(code)
        
        # Traverse tree for definitions iteratively
        stack = [tree.root_node]
        while stack:
            node = stack.pop()
            if node.type in ("function_definition", "function_declaration", "method_definition", "method_declaration", "function_item"):
                name = _find_identifier(node)
                if not name:
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        name = name_node.text.decode("utf-8", errors="ignore") if name_node.text else ""
                if name:
                    total_p, req_p = _count_parameters(node, ext)
                    definitions[name] = {
                        "file": str(file_path.relative_to(workspace_path)),
                        "required_params": req_p,
                        "total_params": total_p
                    }
            for child in reversed(node.children):
                stack.append(child)
        
        # Find calls
        calls = _find_calls_and_arg_counts(tree.root_node, ext)
        for func_name, arg_count, line in calls:
            call_sites.append({
                "func_name": func_name,
                "args_count": arg_count,
                "file": str(file_path.relative_to(workspace_path)),
                "line": line
            })

    # 2. Check for mismatches
    conflicts = []
    for call in call_sites:
        name = call["func_name"]
        if name in definitions:
            defn = definitions[name]
            # Mismatch if argument count is less than required parameters
            # or greater than total parameters
            if call["args_count"] < defn["required_params"] or call["args_count"] > defn["total_params"]:
                # Prevent self-mismatches in overloaded languages
                if call["file"] == defn["file"] and call["args_count"] == defn["total_params"]:
                    continue
                conflicts.append({
                    "function_name": name,
                    "defined_in": defn["file"],
                    "required_params": defn["required_params"],
                    "total_params": defn["total_params"],
                    "called_in": call["file"],
                    "called_line": call["line"],
                    "args_provided": call["args_count"]
                })
                
    return conflicts


def build_conflict_alert_widget(conflicts: list[dict]) -> str:
    """Compile mismatch warnings into a premium alert block for AGENTS.md."""
    if not conflicts:
        return ""
        
    lines = [
        "## ⚠️ [CRITICAL CONTRACT MISMATCH WARNING] ⚠️",
        "*경고: 파일 간에 함수/메서드 호출 인자 개수가 정의 명세와 다르게 충돌하는 오류가 감지되었습니다. 에이전트들은 다음 불일치를 즉시 확인하고 바로잡으십시오.*",
        ""
    ]
    
    for c in conflicts:
        lines.append(
            f"### 🛑 Contract Violation: `{c['function_name']}`\n"
            f"- **정의 파일**: `{c['defined_in']}` (매개변수 요구량: {c['required_params']}~{c['total_params']}개)\n"
            f"- **오류 호출**: `{c['called_in']}` (L{c['called_line']}에서 {c['args_provided']}개 인자로 호출함)\n"
            f"- **조치 가이드**: 에이전트는 두 모듈의 파라미터 규격을 일치시키고 인터페이스 깨짐(Breaking Changes)을 방어하십시오.\n"
        )
        
    lines.append("")
    return "\n".join(lines)
