"""Synchronization connector for Antigravity agents (AGENTS.md compiler)."""

from __future__ import annotations

import re
import json
from pathlib import Path
from smart_llm.proactive import build_proactive_cache_widget
from smart_llm.broker import scan_contract_conflicts, build_conflict_alert_widget
from smart_llm.polyglot import check_polyglot_contracts, build_polyglot_alert_widget

START_MARKER = "<!-- SMART-LLM-START -->"
END_MARKER = "<!-- SMART-LLM-END -->"

def compile_agents_doc(
    workspace_path: Path,
    graph_data: dict,
    wiki_doc_map: dict[str, str]
) -> str:
    """Compile community structure summaries and cohesion metrics into a rule widget."""
    nodes = graph_data.get("nodes", [])
    links = graph_data.get("links", [])
    
    code_count = sum(1 for n in nodes if n.get("file_type") == "code")
    doc_count = sum(1 for n in nodes if n.get("file_type") == "document")
    
    # 1. Compile GraphRAG-style Community Synopses
    from smart_llm.synopsis import build_community_synopsis
    
    lines = [
        "## 🧠 SMART LLM — Workspace Cognitive Architecture Map",
        f"*Memorized: {code_count} code entities, {doc_count} documentation nodes, and {len(links)} relationship boundaries.*",
        "",
        "### 🏛️ Cohesive Architecture Communities (GraphRAG Synopsis)",
        "안티그라비티 에이전트들은 다음 구조적 단위(Cohesive Communities)를 기준으로 코드를 탐색하고 작업하십시오.",
        ""
    ]
    
    # Extract members list to build GraphRAG summaries
    communities: dict[int, list[str]] = {}
    
    for path_str, content in sorted(wiki_doc_map.items()):
        match_cid = re.search(r"community_(\d+)", path_str)
        if not match_cid:
            continue
        cid = int(match_cid.group(1))
        
        # Read cohesion
        cohesion_match = re.search(r"\*\*Cohesion Score\*\*: ([\d.]+)", content)
        cohesion = float(cohesion_match.group(1)) if cohesion_match else 0.0
        
        # Find members
        members_section = re.search(r"## Component Members\n(.*?)(?=\n\n##|$)", content, re.DOTALL)
        members = []
        if members_section:
            for member_line in members_section.group(1).splitlines():
                if member_line.startswith("- "):
                    m_match = re.search(r"`\[\[(.*?)\]\]`", member_line)
                    if m_match:
                        members.append(m_match.group(1))
                        
        if members:
            communities[cid] = members
            
            synopsis = build_community_synopsis(cid, members, graph_data)
            
            lines.append(f"#### 📦 Community {cid} (Cohesion: {cohesion:.3f})")
            lines.append(f"> {synopsis}")
            lines.append("* **Primary Entities**:")
            for m in members[:4]:
                m_label = m.split("::")[-1] or m
                lines.append(f"  - `{m_label}` — [[{m}]]")
            if len(members) > 4:
                lines.append(f"  - *...and {len(members) - 4} more entities.*")
            lines.append("")

    # 2. Compile Call Boundaries
    lines.append("### 🔗 Cross-Module Call Boundaries")
    lines.append("에이전트는 이 경계를 건너서 작업할 때 사이드 이펙트(부작용) 검증을 최우선으로 고려하십시오:")
    
    connections = set()
    for link in links:
        src = link.get("source", "")
        tgt = link.get("target", "")
        rel = link.get("relation", "")
        
        if "::" in src and "::" in tgt and not src.startswith("__unresolved__") and not tgt.startswith("__unresolved__"):
            src_file = src.split("::")[0].replace("__", "/")
            tgt_file = tgt.split("::")[0].replace("__", "/")
            if src_file != tgt_file and len(connections) < 10:
                connections.add(f"- `{src_file}` --[{rel}]--> `{tgt_file}`")
                
    if connections:
        lines.extend(sorted(connections))
    else:
        lines.append("- *No high-level cross-module couplings detected.*")
        
    lines.append("")
    return "\n".join(lines)


def sync_agents_file(workspace_path: Path) -> Path:
    """Overwrites or injects compiled memory rules into AGENTS.md in the workspace root."""
    workspace_path = Path(workspace_path).resolve()
    agents_path = workspace_path / "AGENTS.md"
    out_dir = workspace_path / "smart-llm-out"
    
    graph_file = out_dir / "graph.json"
    index_file = out_dir / "index.json"
    
    if not graph_file.exists() or not index_file.exists():
        raise FileNotFoundError("Workspace is not ingested yet. Please run 'smart-llm ingest' first.")
        
    with open(graph_file, "r", encoding="utf-8") as f:
        graph_data = json.load(f)
    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)
        
    doc_map = index_data.get("doc_map", {})
    
    # --- A1. Compile Conflict Broker Alert Widget (Broker Phase) ---
    conflicts = scan_contract_conflicts(workspace_path)
    broker_widget = build_conflict_alert_widget(conflicts)
    
    # --- A2. Compile Polyglot Mismatch Alert Widget (Polyglot Phase) ---
    violations = check_polyglot_contracts(workspace_path)
    polyglot_widget = build_polyglot_alert_widget(violations)
    
    # --- B. Compile Core Architecture Map (GraphRAG Phase) ---
    compiled_map = compile_agents_doc(workspace_path, graph_data, doc_map)
    
    # --- C. Compile Proactive Pre-fetching Widget (Proactive Phase) ---
    from smart_llm.git_diff import get_git_changes
    from smart_llm.build import build_graph
    
    focus_file = "src/smart_llm/cli.py"  # Default
    changes = get_git_changes(workspace_path)
    
    if changes.get("modified"):
        focus_file = changes["modified"][0]
        
    G = build_graph(graph_data)
    proactive_widget = build_proactive_cache_widget(G, focus_file, doc_map)
    
    # --- D. Merge all widgets into single dynamic memory block ---
    block_parts = []
    if broker_widget:
        block_parts.append(broker_widget)
    if polyglot_widget:
        block_parts.append(polyglot_widget)
    block_parts.append(compiled_map)
    if proactive_widget:
        block_parts.append(proactive_widget)
        
    block_content = f"{START_MARKER}\n" + "\n".join(block_parts) + f"{END_MARKER}"
    
    if agents_path.exists():
        try:
            current_text = agents_path.read_text(encoding="utf-8")
        except (OSError, IOError):
            current_text = ""
            
        if START_MARKER in current_text and END_MARKER in current_text:
            pattern = re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER)
            updated_text = re.sub(pattern, block_content, current_text, flags=re.DOTALL)
        else:
            updated_text = current_text.rstrip() + "\n\n" + block_content + "\n"
    else:
        updated_text = (
            "# AGENTS.md — Agentic Orchestrator Settings\n\n"
            "이 규칙은 안티그라비티 에이전트들이 작업할 때 참고할 최우선 규칙 가이드입니다.\n\n"
            + block_content + "\n"
        )
        
    agents_path.write_text(updated_text, encoding="utf-8")
    
    # Sync SQLite Ledger with latest metrics as well
    try:
        from smart_llm.sqlite_ledger import init_ledger, set_state
        init_ledger(workspace_path)
        set_state(workspace_path, "agents_rules_sync", {
            "last_synced_at": Path(agents_path).stat().st_mtime,
            "conflicts_count": len(conflicts),
            "polyglot_violations_count": len(violations)
        })
    except Exception:
        pass
        
    return agents_path
