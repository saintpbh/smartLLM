"""Sleep-Phase Cognitive Memory Consolidation (Graph pruning & optimization)."""

from __future__ import annotations

import json
import networkx as nx
from pathlib import Path
from smart_llm.build import serialize_graph

def prune_and_consolidate_graph(G: nx.DiGraph) -> nx.DiGraph:
    """Consolidate knowledge graph by pruning isolated placeholders and merging duplicate links."""
    # 1. Prune isolated placeholder nodes
    nodes_to_remove = []
    for nid in G.nodes():
        node_type = G.nodes[nid].get("file_type", "")
        deg = G.degree(nid)
        
        # If it is a placeholder or external ref node and has no links, prune it
        if (node_type == "placeholder" or "__unresolved__" in nid) and deg == 0:
            nodes_to_remove.append(nid)
            
    G.remove_nodes_from(nodes_to_remove)
    
    # 2. Merge duplicate parallel edges if any exist (accumulating weight)
    # NetworkX DiGraph doesn't allow parallel edges between same (u, v) under same key,
    # but we can verify link metadata. If there are multiple edges in raw links,
    # build resolved them into one edge.
    
    return G


def run_sleep_consolidation(workspace_path: Path) -> dict:
    """Load, prune, and rebuild community structures and indices to optimize memory density."""
    workspace_path = Path(workspace_path).resolve()
    out_dir = workspace_path / "smart-llm-out"
    graph_file = out_dir / "graph.json"
    
    if not graph_file.exists():
        return {"status": "error", "message": "graph.json not found. Run ingest first."}
        
    with open(graph_file, "r", encoding="utf-8") as f:
        graph_data = json.load(f)
        
    from smart_llm.build import build_graph
    G = build_graph(graph_data)
    
    original_node_count = G.number_of_nodes()
    original_edge_count = G.number_of_edges()
    
    # Prune
    G_pruned = prune_and_consolidate_graph(G)
    
    pruned_node_count = G_pruned.number_of_nodes()
    pruned_edge_count = G_pruned.number_of_edges()
    
    # Save back
    graph_data_pruned = serialize_graph(G_pruned)
    with open(graph_file, "w", encoding="utf-8") as f:
        json.dump(graph_data_pruned, f, ensure_ascii=False, indent=2)
        
    # Re-run modularity clustering on optimized graph
    from smart_llm.cluster import cluster_graph, calculate_cohesion
    from smart_llm.cli import make_wiki_document
    
    communities = cluster_graph(G_pruned)
    cohesions = calculate_cohesion(G_pruned, communities)
    
    wiki_dir = out_dir / "wiki"
    wiki_dir.mkdir(exist_ok=True)
    
    doc_map = {}
    for cid, members in communities.items():
        doc_content = make_wiki_document(cid, members, cohesions[cid], graph_data_pruned)
        wiki_file = wiki_dir / f"community_{cid}.md"
        wiki_file.write_text(doc_content, encoding="utf-8")
        
        rel_wiki_path = f"wiki/community_{cid}.md"
        doc_map[rel_wiki_path] = doc_content
        
    # Update search index
    index_file = out_dir / "index.json"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            index_data = json.load(f)
    else:
        index_data = {}
        
    index_data["doc_map"] = doc_map
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
        
    return {
        "status": "success",
        "nodes_pruned": original_node_count - pruned_node_count,
        "edges_pruned": original_edge_count - pruned_edge_count,
        "total_communities": len(communities)
    }
