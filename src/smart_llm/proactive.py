"""Proactive context pre-fetching and predictive target model using Dijkstra semantic graph routing."""

from __future__ import annotations

import networkx as nx
from pathlib import Path

def predict_next_targets(
    G: nx.DiGraph,
    focus_file_rel: str,
    top_k: int = 3
) -> list[tuple[str, float]]:
    """Predict which files the agent will likely inspect next using Dijkstra semantic-weighted path routing."""
    if G.number_of_nodes() == 0:
        return []

    # Map the relative file path to the corresponding node in the graph
    focus_node = None
    focus_stem = Path(focus_file_rel).stem.lower() if focus_file_rel else ""
    
    if focus_file_rel:
        for nid in G.nodes():
            node_file = G.nodes[nid].get("source_file", "")
            if focus_file_rel in node_file or focus_stem in nid:
                focus_node = nid
                break
            
    if not focus_node:
        # Fallback: return highest degree nodes (hubs) in the graph
        degree_sorted = sorted(G.degree(), key=lambda x: x[1], reverse=True)
        hubs = []
        for nid, deg in degree_sorted:
            source_file = G.nodes[nid].get("source_file", "")
            if source_file and source_file not in hubs:
                hubs.append((source_file, float(deg)))
            if len(hubs) >= top_k:
                break
        return hubs

    # 1. Run Dijkstra shortest path length from focus_node
    undirected = G.to_undirected()
    try:
        # Computes shortest path length to all reachable nodes using edge weight
        lengths = nx.single_source_dijkstra_path_length(undirected, focus_node, weight="weight")
    except Exception:
        # Fallback to standard hop length if Dijkstra fails
        lengths = nx.single_source_shortest_path_length(undirected, focus_node)

    # 2. Accumulate proximity scores (closer distance = higher score)
    predictions: dict[str, float] = {}
    for target_nid, distance in lengths.items():
        if target_nid == focus_node:
            continue
            
        source_file = G.nodes[target_nid].get("source_file", "")
        if not source_file or focus_file_rel in source_file:
            continue
            
        # Score is reciprocal of distance (closer = higher score)
        score = 1.0 / (distance + 0.01)
        predictions[source_file] = max(predictions.get(source_file, 0.0), score)

    # If no predictions, fallback to hubs
    if not predictions:
        return predict_next_targets(G, "", top_k=top_k)

    # Sort predicted next files by score descending
    sorted_preds = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
    
    # Map back to relative paths
    results = []
    for abs_path_str, score in sorted_preds:
        rel_path = abs_path_str
        if "/scratch/" in abs_path_str:
            rel_path = abs_path_str.split("/scratch/")[-1].split("/", 1)[-1]
        elif "/proj/" in abs_path_str:
            rel_path = abs_path_str.split("/proj/")[-1]
        results.append((rel_path, score))
        
    return results[:top_k]


def build_proactive_cache_widget(
    G: nx.DiGraph,
    focus_file: str,
    doc_map: dict[str, str]
) -> str:
    """Compile a Markdown pre-fetch cache block containing predicted component contexts."""
    predictions = predict_next_targets(G, focus_file, top_k=2)
    
    if not predictions:
        return ""
        
    lines = [
        "### ⚡ Proactive Memory Cache (0ms Pre-fetched Context)",
        f"*에이전트가 현재 `{focus_file}` 파일 부근에서 작업 중임을 감지하여, 결합도가 높은 다음 컴포넌트를 선제 로드했습니다.*",
        ""
    ]
    
    for rel_path, score in predictions:
        matched_wiki = None
        simplified_name = Path(rel_path).stem
        
        for k, v in doc_map.items():
            if simplified_name in v.lower():
                matched_wiki = k
                break
                
        lines.append(f"#### 🔍 Predicted Target: `{rel_path}` (Coupling Score: {score:.1f})")
        if matched_wiki:
            lines.append(f"*주요 연결 지식: `[[{matched_wiki}]]`*")
        
        if matched_wiki and matched_wiki in doc_map:
            wiki_content = doc_map[matched_wiki]
            lines.append("```markdown")
            excerpt = "\n".join(wiki_content.splitlines()[:10])
            lines.append(excerpt)
            lines.append("```")
        else:
            lines.append("*(상세 아키텍처 개요는 위키 커뮤니티 문서를 참고하십시오)*")
        lines.append("")
        
    return "\n".join(lines)
